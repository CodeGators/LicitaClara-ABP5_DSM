"""Comparação sem rótulos; estabilidade não representa acerto de fraude."""

import hashlib
import itertools
import math
import time
from importlib.metadata import version

import joblib
import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import IsolationForest

from licita_ml.experiments.data import TRAIN_END

SEEDS = (11, 23, 42, 71, 101)
CONFIGS = tuple(itertools.product((200, 500), (64, 256)))


def top_indices(scores, ids, k):
    return sorted(range(len(ids)), key=lambda i: (-float(scores[i]), ids[i]))[:k]


def overlap(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a or b else 1.0


def correlation(a, b):
    if len(a) < 3 or len(set(a)) < 2 or len(set(b)) < 2:
        return None
    result = float(spearmanr(a, b).statistic)
    return result if math.isfinite(result) else None


def features(rows, median, names):
    # Decimal é preservado até a construção da matriz numérica do modelo.
    data = []
    for row in rows:
        values = {
            "log_preco_mediana": math.log(float(row["price"] / median)),
            "log_quantidade": math.log1p(float(row["quantity"])),
        }
        data.append([values[name] for name in names])
    matrix = np.asarray(data, dtype=np.float64)
    if matrix.ndim != 2 or not np.isfinite(matrix).all():
        raise ValueError("Matriz inválida")
    return matrix


def train_reference(rows, *, train_end=TRAIN_END):
    if not rows or any(r["date"] > train_end for r in rows):
        raise ValueError("Treino vazio ou contém observação futura")
    prices = sorted(row["price"] for row in rows)
    n = len(prices)
    return prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2


def evaluate(group, root, *, train_end=TRAIN_END):
    started = time.monotonic()
    train, test = group["train"], group["test"]
    if not train or len(test) < 3:
        raise ValueError("Avaliação insuficiente")
    median = train_reference(train, train_end=train_end)
    ids = [r["id"] for r in test]
    k = min(10, max(3, math.ceil(0.10 * len(test))))
    ratios = np.asarray([float(r["price"] / median) for r in test])
    bilateral = np.abs(np.log(ratios))
    unilateral_top = top_indices(ratios, ids, k)
    bilateral_top = top_indices(bilateral, ids, k)
    result = dict(
        group_id=group["id"],
        modo="principal" if group["eligible"] else "exploratorio",
        treino=len(train),
        teste=len(test),
        top_k=k,
        mediana_treino=str(median),
        fronteira_treino=str(train_end),
        modelos={},
        baseline_sobrepreco=[ids[i] for i in unilateral_top],
        baseline_bilateral=[ids[i] for i in bilateral_top],
    )
    raw_rankings = {}
    for label, names in [
        ("preco", ["log_preco_mediana"]),
        ("preco_quantidade", ["log_preco_mediana", "log_quantidade"]),
    ]:
        x_train, x_test = features(train, median, names), features(test, median, names)
        if not any(np.ptp(x_train[:, j]) > 0 for j in range(x_train.shape[1])):
            raise ValueError("Atributos constantes")
        configurations, all_scores, anchor, anchor_model = [], [], None, None
        seed42_by_config = []
        for trees, samples in CONFIGS:
            scores_by_seed = []
            ranks = []
            for seed in SEEDS:
                model = IsolationForest(
                    n_estimators=trees,
                    max_samples=min(samples, len(train)),
                    max_features=1.0,
                    contamination="auto",
                    random_state=seed,
                    n_jobs=1,
                )
                model.fit(x_train)
                scores = -model.score_samples(x_test)
                if not np.isfinite(scores).all():
                    raise ValueError("Score não finito")
                scores_by_seed.append(scores)
                all_scores.append(scores)
                ranks.append(top_indices(scores, ids, k))
                if seed == 42:
                    seed42_by_config.append(scores)
                if (trees, samples, seed) == (200, 256, 42):
                    anchor, anchor_model = scores, model
            correlations = [correlation(a, b) for a, b in itertools.combinations(scores_by_seed, 2)]
            correlations = [r for r in correlations if r is not None]
            jaccards = [overlap(a, b) for a, b in itertools.combinations(ranks, 2)]
            configurations.append(
                dict(
                    n_estimators=trees,
                    max_samples=min(samples, len(train)),
                    seeds=list(SEEDS),
                    spearman_mediana=float(np.median(correlations)) if correlations else None,
                    jaccard_topk_mediana=float(np.median(jaccards)),
                )
            )
        anchor_top = top_indices(anchor, ids, k)
        anchor_top_set = set(anchor_top)
        shared_unilateral = len(anchor_top_set & set(unilateral_top)) / k
        shared_bilateral = len(anchor_top_set & set(bilateral_top)) / k
        selected = next(
            c
            for c in configurations
            if c["n_estimators"] == 200 and c["max_samples"] == min(256, len(train))
        )
        stable = (
            selected["spearman_mediana"] is not None
            and selected["spearman_mediana"] >= 0.80
            and selected["jaccard_topk_mediana"] >= 0.60
        )
        sensitivity = []
        # Cópias sintéticas ficam fora do ranking real e não têm rótulo de fraude.
        normal_rows = [r for r in test if 0.8 <= float(r["price"] / median) <= 1.2]
        for multiplier in (3, 10):
            copied = [dict(row, price=row["price"] * multiplier) for row in normal_rows]
            if copied:
                before = -anchor_model.score_samples(features(normal_rows, median, names))
                after = -anchor_model.score_samples(features(copied, median, names))
                sensitivity.append(
                    dict(
                        multiplicador=multiplier,
                        n=len(copied),
                        fracao_score_aumentou=float(np.mean(after > before)),
                        deslocamento_mediano=float(np.median(after - before)),
                    )
                )
            else:
                sensitivity.append(dict(multiplicador=multiplier, n=0, fracao_score_aumentou=None))
        folder = root / "modelos"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (group["id"] + "-" + label + ".joblib")
        bundle = {
            "model": anchor_model,
            "mediana_treino": median,
            "features": names,
            "group": group["group"],
            "train_end": train_end,
            "seeds": list(SEEDS),
            "fixed_anchor": (200, min(256, len(train)), 42),
            "sklearn": version("scikit-learn"),
            "numpy": version("numpy"),
        }
        joblib.dump(bundle, path, compress=3)
        restored = joblib.load(path)  # Somente artefato recém-gerado pelo próprio processo.
        replay = -restored["model"].score_samples(
            features(test, restored["mediana_treino"], restored["features"])
        )
        if not np.array_equal(anchor, replay):
            raise ValueError("Artefato carregado não reproduziu os scores")
        config_corr = [correlation(a, b) for a, b in itertools.combinations(seed42_by_config, 2)]
        config_corr = [r for r in config_corr if r is not None]
        result["modelos"][label] = dict(
            features=names,
            configuracoes=configurations,
            ancora_predefinida={
                "n_estimators": 200,
                "max_samples": min(256, len(train)),
                "seed": 42,
                "contamination": "auto",
            },
            estabilidade_aprovada=stable,
            sobreposicao_topk_baseline_sobrepreco=shared_unilateral,
            sobreposicao_topk_baseline_bilateral=shared_bilateral,
            spearman_baseline_sobrepreco=correlation(anchor, ratios),
            spearman_baseline_bilateral=correlation(anchor, bilateral),
            spearman_mediana_entre_configuracoes=(
                float(np.median(config_corr)) if config_corr else None
            ),
            possivel_redundancia_sobrepreco=shared_unilateral >= 0.9,
            sensibilidade_sintetica=sensitivity,
            artefato=str(path),
            sha256_artefato=hashlib.sha256(path.read_bytes()).hexdigest(),
            replay_exato=True,
            score_min=float(np.min(anchor)),
            score_max=float(np.max(anchor)),
            top_ids=[ids[i] for i in anchor_top],
            utilidade_real_comprovada=False,
        )
        raw_rankings[label] = dict(scores=[float(s) for s in anchor], indices=anchor_top)
    result["duracao_segundos"] = round(time.monotonic() - started, 3)
    result["medicoes_nao_sao_acuracia"] = True
    return result, raw_rankings, ratios, bilateral
