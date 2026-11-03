import io
import json
from datetime import date
from decimal import Decimal

import pyarrow.parquet as pq
import pytest
import sqlalchemy as sa
from licita_ml.normalize import RowError, day, money, text
from licita_ml.pipeline import Pipeline
from licita_ml.readers import SchemaError

START, END = date(2026, 9, 1), date(2026, 9, 30)


def test_normalization_preserves_identifiers_null_and_exact_money():
    assert text(" 000123 ") == "000123"
    assert money("0") == Decimal(0)
    assert money("") is None
    assert money("0.12345678") == Decimal("0.12345678")
    for bad in ["NaN", "Infinity", "-1", "1,23", "0.123456789"]:
        with pytest.raises(RowError):
            money(bad)
    with pytest.raises(RowError):
        day("2026-99-01")


@pytest.mark.integration
def test_complete_import_repeat_parquet_and_correction(database, settings, sources):
    repo, admin = database
    objects, ids, add, material = sources
    pipeline = Pipeline(settings, repo, objects)
    first = pipeline.run(START, END, "486054", ids)
    assert first["contagens"]["participacoes"] == 2
    assert first["contagens"]["documentos"] == 1
    assert first["contagens"]["contratos_versoes"] == 1
    with admin.connect() as c:
        assert c.scalar(sa.text("SELECT identificacao FROM fornecedores")) == "00000000000200"
        assert c.scalar(sa.text("SELECT preco_unitario FROM referencias_precos")) == Decimal(
            "0.12345678"
        )
        assert c.scalar(sa.text("SELECT data_assinatura FROM contratos_versoes")) == date(
            2026, 9, 17
        )
        count = c.scalar(sa.text("SELECT count(*) FROM proveniencias_registros"))
    repeated = pipeline.run(START, END, "486054", ids)
    assert repeated["reutilizada"] and repeated["base_id"] == first["base_id"]
    with admin.connect() as c:
        assert c.scalar(sa.text("SELECT count(*) FROM proveniencias_registros")) == count
    with objects.open(first["manifesto"]) as f:
        manifest = json.load(f)
    artifact = next(a for a in manifest["arquivos_parquet"] if a["tabela"] == "referencias_precos")
    with objects.open(artifact["chave"]) as f:
        table = pq.read_table(io.BytesIO(f.read()))
    assert table["preco_unitario"][0].as_py() == Decimal("0.12345678")
    corrected = add(
        "material",
        [dict(material, preco_unitario="2", data_hora_atualizacao_item="2026-09-17 10:00:00")],
    )
    second = pipeline.run(START, END, "486054", [corrected, *ids[1:]])
    assert second["base_id"] != first["base_id"]
    with admin.connect() as c:
        assert c.scalar(sa.text("SELECT count(*) FROM versoes_base")) == 2
        assert set(c.scalars(sa.text("SELECT preco_unitario FROM referencias_precos"))) == {
            Decimal("0.12345678"),
            Decimal(2),
        }
        assert c.scalar(sa.text("SELECT count(*) FROM processos")) == 1


@pytest.mark.integration
def test_failure_rolls_back_domain_and_retry_succeeds(database, settings, sources):
    repo, admin = database
    objects, ids, _, _ = sources
    pipeline = Pipeline(settings, repo, objects)
    with pytest.raises(RuntimeError, match="Falha injetada"):
        pipeline.run(START, END, "486054", ids, fail_after="itens_versoes")
    with admin.connect() as c:
        assert c.scalar(sa.text("SELECT count(*) FROM processos")) == 0
        assert c.scalar(sa.text("SELECT count(*) FROM versoes_base")) == 0
        assert c.scalar(sa.text("SELECT count(*) FROM importacoes WHERE status='falhou'")) == len(
            ids
        )
    result = pipeline.run(START, END, "486054", ids)
    assert result["status"] == "validada"
    with admin.connect() as c:
        assert c.scalar(sa.text("SELECT count(*) FROM importacoes")) == len(ids)


@pytest.mark.integration
def test_missing_header_aborts_before_domain_writes(database, settings, sources):
    repo, admin = database
    objects, ids, add, material = sources
    del material["preco_unitario"]
    bad = add("material", [material])
    with pytest.raises(SchemaError) as failure:
        Pipeline(settings, repo, objects).run(START, END, "486054", [bad, *ids[1:]])
    assert failure.value.diagnostic["colunas_ausentes"] == ["preco_unitario"]
    with admin.connect() as c:
        assert c.scalar(sa.text("SELECT count(*) FROM versoes_base")) == 0


@pytest.mark.integration
def test_conflicting_equal_timestamp_is_rejected_and_totals_reconcile(database, settings, sources):
    repo, admin = database
    objects, ids, add, material = sources
    conflict = add("material", [material, dict(material, preco_unitario="9"), material])
    result = Pipeline(settings, repo, objects).run(START, END, "486054", [conflict, *ids[1:]])
    stats = result["origem"][str(conflict)]
    assert stats["total"] == 3 and stats["rejeitados"] == 3
    with objects.open(result["manifesto"]) as f:
        manifest = json.load(f)
    with objects.open(manifest["rejeicoes"]["chave"]) as f:
        rejects = [json.loads(line) for line in f]
    assert len([r for r in rejects if r["arquivo_id"] == str(conflict)]) == 3
    assert all("motivo" in r and "valor" not in r for r in rejects)


@pytest.mark.integration
def test_invalid_price_is_quarantined_and_missing_unit_is_not_imputed(database, settings, sources):
    repo, admin = database
    objects, ids, add, material = sources
    good = dict(
        material,
        quantidade="0",
        capacidade_unidade_fornecimento="",
        sigla_unidade_fornecimento="",
        nome_unidade_fornecimento="",
    )
    bad = dict(material, id_item_compra="000999", preco_unitario="NaN")
    source = add("material", [good, bad])
    result = Pipeline(settings, repo, objects).run(START, END, "486054", [source, *ids[1:]])
    stats = result["origem"][str(source)]
    assert stats["total"] == 2 and stats["aceitos"] == 1 and stats["rejeitados"] == 1
    with admin.connect() as connection:
        row = connection.execute(
            sa.text(
                "SELECT quantidade,capacidade_fornecimento,sigla_unidade_fornecimento "
                "FROM referencias_precos"
            )
        ).one()
        assert row == (Decimal(0), None, None)
