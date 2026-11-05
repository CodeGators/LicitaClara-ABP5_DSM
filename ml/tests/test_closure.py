import hashlib
import json

import pytest
from licita_ml.validation.closure import audit, export


def snapshot(tmp_path):
    score = {
        "id": "score",
        "base_id": "base",
        "execucao_id": "run",
        "item_versao_id": "item",
        "resultado_item_id": "result",
        "modelo_id": "model",
        "score_normalizado": "92",
        "atributos": {"comparacao": {"grupo": "group"}, "referencia": {"linha": 12}},
    }
    manifest = {
        "base_id": "base",
        "execucao_id": "run",
        "configuracao": {"contrato": "inferencia-agrupada-v1"},
        "modelos": [
            {
                "id": "model",
                "parametros": {"grupo": "group", "assinatura_catalogo": {"unidade": "kg"}},
            }
        ],
        "scores": [score],
        "contagens": {"scores": 1, "alvos_modelos": 1},
        "cobertura": [
            {
                "status": "analisado_experimental",
                "motivo": None,
                "resultado_item_id": "result",
                "modelo_id": "model",
            }
        ],
    }
    return manifest


def save(tmp_path, manifest):
    path = tmp_path / "manifesto.json"
    raw = json.dumps(manifest).encode()
    path.write_bytes(raw)
    return path, hashlib.sha256(raw).hexdigest()


def test_export_repeat_preserves_review(tmp_path):
    path, sha = save(tmp_path, snapshot(tmp_path))
    output = tmp_path / "exports"
    report = export(path, sha, output)
    editable = output / "revisao_preenchida.csv"
    editable.write_text("parecer humano")
    assert export(path, sha, output) == report
    assert editable.read_text() == "parecer humano"
    assert report["utilidade_validada"] is False
    original = output / "revisao_original.csv"
    assert "pendente" in original.read_text(encoding="utf-8-sig")
    original.write_text("alterado")
    with pytest.raises(ValueError, match="existente divergente"):
        export(path, sha, output)
    assert original.read_text() == "alterado"


def test_rejects_corrupted_manifest(tmp_path):
    path, sha = save(tmp_path, snapshot(tmp_path))
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="Hash"):
        audit(path, sha)


@pytest.mark.parametrize("change", ["group", "duplicate", "coverage", "range", "base"])
def test_rejects_inconsistent_snapshot(tmp_path, change):
    manifest = snapshot(tmp_path)
    score = manifest["scores"][0]
    if change == "group":
        score["atributos"]["comparacao"]["grupo"] = "other"
    elif change == "duplicate":
        manifest["scores"].append(dict(score))
    elif change == "coverage":
        manifest["cobertura"][0]["resultado_item_id"] = "other"
    elif change == "range":
        score["score_normalizado"] = "101"
    else:
        score["base_id"] = "other"
    path, sha = save(tmp_path, manifest)
    with pytest.raises(ValueError):
        audit(path, sha)
