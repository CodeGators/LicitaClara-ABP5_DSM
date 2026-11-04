"""Agrupamento revisado, controle de qualidade e lotes sem perder grupos."""

import json
from pathlib import Path

import pytest
from licita_ml.catalog.pipeline import prepare as catalog
from licita_ml.grouped.temporal import prepare, structural_blockers, validate
from licita_ml.organized.pipeline import prepare as organize
from licita_ml.training.dataset import load
from test_organized import write
from test_temporal import history


@pytest.fixture
def grouped_source(tmp_path):
    folder, data = history.__wrapped__(tmp_path)
    records = []
    for i, code in enumerate(("000123", "000124")):
        for row in data["material"]:
            copy = dict(
                row,
                codigo_item_catalogo=code,
                id_compra_item=row["id_compra_item"] + str(i),
                id_item_compra=row["id_item_compra"] + str(i),
                descricao_item="CANETA, COR: AZUL, MATERIAL: PLASTICO",
                descricao_detalhada_item="CANETA MATERIALPLASTICO, CORAZUL"
                if i
                else "CANETA, COR: AZUL; MATERIAL: PLASTICO",
            )
            records.append(copy)
    data["material"] = records
    for kind, values in data.items():
        write(folder, kind, values)
    base = Path(organize([folder], tmp_path / "organized")["diretorio"])
    cat = Path(catalog(base, tmp_path / "catalog")["diretorio"])
    return base, cat


def test_all_eligible_groups_are_batched_and_loader_replays(grouped_source, tmp_path):
    base, cat = grouped_source
    result = prepare(base, cat, tmp_path / "output", batch_size=1)
    manifest = result["manifesto"]
    assert manifest["candidatos"] == manifest["grupos_selecionados"] == 2
    assert len(manifest["lotes"]) == 2
    seen = set()
    for item in manifest["lotes"]:
        m, groups = load(Path(result["diretorio"]) / item["diretorio"])
        assert len(groups) == 1
        g = next(iter(groups.values()))
        assert len(g["train"]) == 140 and len(g["test"]) == 40
        assert len(g["id"]) == 64 and g["group"][2] == "un"
        assert not seen.intersection(groups)
        seen.update(groups)
        assert m["tabelas"]["alvos_resultados"] == 0
    assert prepare(base, cat, tmp_path / "output", batch_size=1)["reutilizada"]
    path = Path(result["diretorio"]) / "triagem.json"
    path.write_text("broken")
    with pytest.raises(ValueError, match="Triagem corrompida"):
        validate(Path(result["diretorio"]))


def test_generic_books_require_identification():
    attr = {
        "modo": "atributos_nomeados",
        "produto": "livro literatura",
        "atributos": [["idioma", "portugues"]],
    }
    assert "OBRA_EDICAO_ISBN_NAO_CONFIRMADOS" in structural_blockers(
        {"especificacao": attr, "especificacao_catalogo": attr}
    )


def test_unstructured_details_are_not_approved_by_count():
    assert structural_blockers(
        {
            "especificacao": {"modo": "texto_preservado", "texto": "caneta"},
            "especificacao_catalogo": {
                "modo": "atributos_nomeados",
                "produto": "caneta",
                "atributos": [["cor", "azul"]],
            },
        }
    ) == ["ESPECIFICACAO_NAO_ESTRUTURADA_REQUER_REVISAO"]


def test_incompatible_catalog_base_is_rejected(grouped_source, tmp_path):
    base, cat = grouped_source
    path = base / "manifesto.json"
    doc = json.loads(path.read_text())
    doc["nota"] = "outra versao"
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="outra base"):
        prepare(base, cat, tmp_path / "output")
