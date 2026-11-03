"""Autoencoder 2→1→2; erro de reconstrução não é probabilidade de irregularidade."""

import hashlib
import itertools
import time
import warnings

import joblib
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from licita_ml.experiments.evaluate import (
    SEEDS,
    correlation,
    features,
    overlap,
    top_indices,
    train_reference,
)

NAMES = ["log_preco_mediana", "log_quantidade"]
PARAMETERS = {
    "hidden_layer_sizes": (1,),
    "activation": "tanh",
    "solver": "lbfgs",
    "alpha": 0.001,
    "max_iter": 2000,
    "max_fun": 50000,
    "tol": 0.00001,
    "early_stopping": False,
}


def fit(train, train_end, seed):
    median = train_reference(train, train_end=train_end)
    x = features(train, median, NAMES)
    if len(train) < 100 or np.any(np.ptp(x, axis=0) == 0):
        raise ValueError("Treino insuficiente ou atributo constante para AE multivariado")
    scaler = StandardScaler().fit(x)
    z = scaler.transform(x)
    model = MLPRegressor(**PARAMETERS, random_state=seed)
    with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=1):
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(z, z)
    notices = [str(w.message) for w in caught if issubclass(w.category, ConvergenceWarning)]
    if not np.isfinite(model.loss_):
        raise ValueError("Perda não finita")
    return {
        "model": model,
        "scaler": scaler,
        "mediana_treino": median,
        "features": NAMES,
        "train_end": train_end,
        "seed": seed,
        "ids_treino": [r["id"] for r in train],
    }, notices


def score(bundle, rows):
    z = bundle["scaler"].transform(features(rows, bundle["mediana_treino"], bundle["features"]))
    reconstructed = bundle["model"].predict(z)
    errors = np.square(z - reconstructed)
    scores = np.mean(errors, axis=1)
    if errors.shape != z.shape or not np.isfinite(errors).all():
        raise ValueError("Reconstrução inválida")
    return scores, errors


def evaluate_autoencoder(train, test, train_end, root, k):
    started = time.monotonic()
    ids = [r["id"] for r in test]
    all_scores, tops, fits = [], [], []
    anchor = None
    for seed in SEEDS:
        bundle, notices = fit(train, train_end, seed)
        scores, errors = score(bundle, test)
        all_scores.append(scores)
        tops.append(top_indices(scores, ids, k))
        path = root / f"autoencoder-{seed}.joblib"
        joblib.dump(bundle, path, compress=3)
        restored = joblib.load(path)  # Somente o artefato recém-gerado por este processo.
        replay_scores, replay_errors = score(restored, test)
        if not np.array_equal(scores, replay_scores) or not np.array_equal(errors, replay_errors):
            raise ValueError("Recarga do Autoencoder não reproduziu scores/parcelas")
        fits.append(
            {
                "seed": seed,
                "iteracoes": int(bundle["model"].n_iter_),
                "perda_treino": float(bundle["model"].loss_),
                "avisos_convergencia": notices,
                "convergiu": not notices,
                "replay_exato": True,
                "artefato": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
        if seed == 42:
            anchor = (bundle, scores, errors)
    correlations = [correlation(a, b) for a, b in itertools.combinations(all_scores, 2)]
    correlations = [c for c in correlations if c is not None]
    spearman = float(np.median(correlations)) if correlations else None
    jaccard = float(np.median([overlap(a, b) for a, b in itertools.combinations(tops, 2)]))
    bundle, scores, errors = anchor
    median = bundle["mediana_treino"]
    normal = [r for r in test if 0.8 <= float(r["price"] / median) <= 1.2]
    sensitivity = []
    for multiplier in (3, 10):
        copied = [dict(row, price=row["price"] * multiplier) for row in normal]
        if not copied:
            sensitivity.append({"multiplicador": multiplier, "n": 0, "fracao_score_aumentou": None})
        else:
            before, _ = score(bundle, normal)
            after, _ = score(bundle, copied)
            sensitivity.append(
                {
                    "multiplicador": multiplier,
                    "n": len(copied),
                    "fracao_score_aumentou": float(np.mean(after > before)),
                    "deslocamento_mediano": float(np.median(after - before)),
                }
            )
    stable = spearman is not None and spearman >= 0.80 and jaccard >= 0.60
    converged = all(f["convergiu"] for f in fits)
    result = {
        "arquitetura": [2, 1, 2],
        "parametros_treinaveis": 7,
        "parametros": PARAMETERS,
        "features": NAMES,
        "seeds": list(SEEDS),
        "ancora_seed": 42,
        "mediana_treino": str(median),
        "preprocessamento": {
            "media_treino": bundle["scaler"].mean_.tolist(),
            "escala_treino": bundle["scaler"].scale_.tolist(),
            "n_treino": int(bundle["scaler"].n_samples_seen_),
        },
        "spearman_mediana_seeds": spearman,
        "jaccard_topk_mediana": jaccard,
        "estabilidade_aprovada": stable,
        "convergencia_todas_seeds": converged,
        "aprovado_tecnicamente": stable and converged,
        "ajustes": fits,
        "top_ids": [ids[i] for i in top_indices(scores, ids, k)],
        "sensibilidade_sintetica": sensitivity,
        "score_min": float(min(scores)),
        "score_max": float(max(scores)),
        "duracao_segundos": round(time.monotonic() - started, 3),
        "utilidade_comprovada": False,
    }
    contributions = []
    for uid, row_errors, total in zip(ids, errors, errors.sum(axis=1), strict=True):
        contributions.append(
            {
                "id": uid,
                "erros_quadraticos": dict(zip(NAMES, row_errors.tolist(), strict=True)),
                "fracoes_erro_total": None
                if total == 0
                else dict(zip(NAMES, (row_errors / total).tolist(), strict=True)),
                "interpretacao": "parcelas do erro de reconstrução; não são causas ou pesos do IF",
            }
        )
    return result, scores.tolist(), contributions
