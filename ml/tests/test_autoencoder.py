"""Reconstrução, isolamento do treino, pareamento com IF e integridade."""

import io
from datetime import date
from decimal import Decimal

import numpy as np
import pytest
from licita_ml.analytical.pipeline import put_immutable
from licita_ml.analytical.rules import canonical
from licita_ml.comparison.autoencoder import NAMES, evaluate_autoencoder, fit, score
from licita_ml.comparison.pipeline import ComparisonPipeline, compare_vectors
from licita_ml.experiments import evaluate as if_engine
from licita_ml.experiments.evaluate import features
from licita_ml.validation.pipeline import ValidationPipeline, read_manifest
from sklearn.preprocessing import StandardScaler
from test_validation import POLICY, fixture_dataset


def train_rows():
    return [
        {
            "id": str(n),
            "price": Decimal("0.5") + Decimal(n % 9) / 10,
            "quantity": Decimal(1 + n % 13),
            "date": date(2026, 1, 1),
        }
        for n in range(100)
    ]


def test_autoencoder_bottleneck_scaler_training_only_and_exact_replay(tmp_path):
    train = train_rows()
    test = [dict(row, id="test" + row["id"], date=date(2026, 8, 1)) for row in train[:35]]
    result, scores, contributions = evaluate_autoencoder(train, test, POLICY.train_end, tmp_path, 4)
    assert result["arquitetura"] == [2, 1, 2] and result["parametros_treinaveis"] == 7
    assert len(result["ajustes"]) == 5
    assert all(r["replay_exato"] for r in result["ajustes"])
    assert all(v >= 0 for v in scores)
    for value, parts in zip(scores, contributions, strict=True):
        assert np.mean(list(parts["erros_quadraticos"].values())) == pytest.approx(value)
        if parts["fracoes_erro_total"]:
            assert sum(parts["fracoes_erro_total"].values()) == pytest.approx(1)
    bundle, _ = fit(train, POLICY.train_end, 42)
    assert [w.shape for w in bundle["model"].coefs_] == [(2, 1), (1, 2)]
    assert sum(w.size for w in bundle["model"].coefs_ + bundle["model"].intercepts_) == 7
    expected = StandardScaler().fit(features(train, bundle["mediana_treino"], NAMES))
    assert np.array_equal(bundle["scaler"].mean_, expected.mean_)
    assert np.array_equal(bundle["scaler"].scale_, expected.scale_)
    old_mean, old_scale = bundle["scaler"].mean_.copy(), bundle["scaler"].scale_.copy()
    score(bundle, [dict(test[0], price=Decimal("9999999"))])
    assert np.array_equal(old_mean, bundle["scaler"].mean_)
    assert np.array_equal(old_scale, bundle["scaler"].scale_)
    assert result["preprocessamento"]["n_treino"] == 100
    assert not result["utilidade_comprovada"]


def test_reconstruction_error_is_zero_for_identity_model():
    class Identity:
        def transform(self, x):
            return x

        def predict(self, x):
            return x

    bundle = {
        "model": Identity(),
        "scaler": Identity(),
        "mediana_treino": Decimal(1),
        "features": NAMES,
    }
    scores, errors = score(bundle, train_rows()[:3])
    assert np.array_equal(scores, np.zeros(3)) and np.array_equal(errors, np.zeros((3, 2)))


def test_no_future_constant_or_insufficient_training():
    rows = train_rows()
    with pytest.raises(ValueError, match="futura"):
        fit([dict(r, date=date(2026, 8, 1)) for r in rows], POLICY.train_end, 42)
    with pytest.raises(ValueError, match="insuficiente"):
        fit(rows[:99], POLICY.train_end, 42)
    with pytest.raises(ValueError, match="constante"):
        fit([dict(r, quantity=Decimal(1)) for r in rows], POLICY.train_end, 42)


def test_pairwise_comparison_preserves_denominator_and_rejects_missing_scores():
    result = compare_vectors({"a": [1, 2, 3, 4], "b": [4, 3, 2, 1]}, list("abcd"), 2)[0]
    assert result["sobreposicao_topk"] == 0 and result["spearman"] == -1
    with pytest.raises(ValueError, match="universo"):
        compare_vectors({"a": [1, 2, 3], "b": [1, 2]}, list("abc"), 2)


def test_comparison_same_cohort_reuse_and_review_never_publish(tmp_path, monkeypatch):
    objects, source, _ = fixture_dataset(tmp_path / "objects")
    monkeypatch.setattr(if_engine, "CONFIGS", ((200, 256),))
    monkeypatch.setattr(if_engine, "SEEDS", (11, 42))
    validated_if = ValidationPipeline(objects).run(source["chave"], source["sha256"])
    pipeline = ComparisonPipeline(objects)
    result = pipeline.run(validated_if["manifesto"], validated_if["sha256_manifesto"])
    repeat = pipeline.run(validated_if["manifesto"], validated_if["sha256_manifesto"])
    assert repeat["reutilizada"] and result["fingerprint"] == repeat["fingerprint"]
    manifest, contents = read_manifest(
        objects, result["manifesto"], result["sha256_manifesto"], "licita-comparacao-v1"
    )
    assert manifest["vencedor_validado"] is None
    assert not manifest["scores_combinados"] and not manifest["publicacao_autorizada"]
    group = manifest["grupos"][0]
    assert group["treino"] == 100 and group["avaliacao"] == 35
    assert len(group["comparacoes"]) == 10
    for kind in ["treino", "avaliacao"]:
        artifact = next(a for a in manifest["artefatos"] if a["entidade"] == "revisao_" + kind)
        raw = contents[artifact["chave"]]
        assert b"score" not in raw and b"ranking" not in raw
        (tmp_path / (kind + ".csv")).write_bytes(raw)
    review = pipeline.review(
        result["manifesto"],
        result["sha256_manifesto"],
        group["grupo"],
        tmp_path / "treino.csv",
        tmp_path / "avaliacao.csv",
    )
    assert review["avaliacao"]["status"] == "revisao_pendente"
    assert all(r["denominador_original"] == 4 for r in review["avaliacao"]["por_ranking"].values())
    model = next(a for a in manifest["artefatos"] if a["entidade"] == "modelo_ae")
    objects.put(model["chave"], io.BytesIO(b"corrompido"))
    with pytest.raises(ValueError, match="tamanho diverge|SHA-256"):
        pipeline.run(validated_if["manifesto"], validated_if["sha256_manifesto"])


def test_if_cohort_mismatch_rejected_before_autoencoder(tmp_path, monkeypatch):
    objects, source, _ = fixture_dataset(tmp_path / "objects")
    monkeypatch.setattr(if_engine, "CONFIGS", ((200, 256),))
    monkeypatch.setattr(if_engine, "SEEDS", (42, 11))
    result = ValidationPipeline(objects).run(source["chave"], source["sha256"])
    manifest, _ = read_manifest(
        objects, result["manifesto"], result["sha256_manifesto"], "licita-validacao-if-v1"
    )
    manifest["grupos"][0]["treino"] += 1
    pinned = put_immutable(objects, "bad/manifesto.json", canonical(manifest).encode())
    # Alterar o grupo já basta; a checagem acontece antes de ler caminhos relativos.
    with pytest.raises(ValueError, match="Cortes"):
        ComparisonPipeline(objects).run(pinned["chave"], pinned["sha256"])


def test_nonconvergence_cannot_be_approved(tmp_path, monkeypatch):
    from licita_ml.comparison.autoencoder import PARAMETERS

    monkeypatch.setitem(PARAMETERS, "max_iter", 1)
    train = train_rows()
    test = [dict(r, id="test-" + r["id"], date=date(2026, 8, 1)) for r in train[:35]]
    result, _, _ = evaluate_autoencoder(train, test, POLICY.train_end, tmp_path, 4)
    assert not result["convergencia_todas_seeds"]
    assert not result["aprovado_tecnicamente"]
    assert any(r["avisos_convergencia"] for r in result["ajustes"])


def test_insufficient_cohort_never_trains_autoencoder(tmp_path, monkeypatch):
    from licita_ml.comparison.autoencoder import MLPRegressor

    objects, source, _ = fixture_dataset(tmp_path / "objects", eligible=False)
    result_if = ValidationPipeline(objects).run(source["chave"], source["sha256"])
    monkeypatch.setattr(
        MLPRegressor, "fit", lambda *_: pytest.fail("Não treinar com dados insuficientes")
    )
    result = ComparisonPipeline(objects).run(result_if["manifesto"], result_if["sha256_manifesto"])
    assert result["grupos"] == 0 and result["status"] == "inconclusivo_por_dados"
