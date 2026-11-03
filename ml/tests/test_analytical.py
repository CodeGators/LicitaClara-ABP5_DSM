"""Exemplos conhecidos e limites temporais; sem rótulos artificiais de fraude."""

import hashlib
import io
import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pyarrow.parquet as pq
import pytest
import sqlalchemy as sa
from licita_ml.analytical.pipeline import AnalyticalPipeline
from licita_ml.analytical.rules import (
    Policy,
    concentration,
    contract_interval,
    estimated_difference,
    frequency,
    participant_count,
    prepare_references,
    reference_row,
)
from licita_ml.analytical.sources import read_history
from licita_ml.pipeline import Pipeline
from licita_ml.readers import SchemaError

POLICY = Policy(date(2025, 10, 1), date(2026, 6, 30), date(2026, 9, 30))


def raw_row(n=0, evaluation=False, **changes):
    raw = {
        "codigoItemCatalogo": "486374",
        "idCompra": f"{1000 + n:017}",
        "idItemCompra": f"{1000 + n:020}",
        "idCompraItem": f"{1000 + n:017}00001",
        "niFornecedor": f"{n % 4:014}",
        "forma": "SISRP",
        "codigoOrgao": str(n % 3),
        "precoUnitario": "1.00000001",
        "quantidade": "10",
        "siglaUnidadeFornecimento": "UN",
        "capacidadeUnidadeFornecimento": "0",
        "descricaoDetalhadaItem": "Caneta amarela",
        "dataCompra": "2026-08-01" if evaluation else "2026-01-01",
        "dataResultado": "2026-08-02" if evaluation else "2026-01-02",
        "dataHoraAtualizacaoItem": "2026-09-01T00:00:00",
    }
    return {**raw, **changes}


def dataset():
    return [reference_row(raw_row(n)) for n in range(100)] + [
        reference_row(raw_row(n + 100, True)) for n in range(35)
    ]


def test_strict_grouping_preserves_keys_and_never_converts_boxes():
    unit = reference_row(raw_row())
    box = reference_row(
        raw_row(1, siglaUnidadeFornecimento="CX", capacidadeUnidadeFornecimento="100")
    )
    other = reference_row(raw_row(2, descricaoDetalhadaItem="Caneta verde"))
    assert len({r["grupo"] for r in [unit, box, other]}) == 3
    assert unit["compra"].startswith("0") and unit["item_fonte"].startswith("0")
    assert unit["preco_unitario"] == Decimal("1.00000001")
    with pytest.raises(ValueError, match="CAPACIDADE_EMBALAGEM_AUSENTE"):
        reference_row(raw_row(siglaUnidadeFornecimento="CX"))


def test_training_reference_never_uses_future_prices_and_reports_minimums():
    first = dataset()
    reports = prepare_references(first, POLICY, {})
    assert reports[0]["elegivel_tecnicamente"]
    assert reports[0]["treino"] == 100 and reports[0]["avaliacao"] == 35
    assert reports[0]["mediana_treino"] == "1.00000001"
    second = dataset()
    for row in second[100:]:
        row["preco_unitario"] = Decimal("99999")
    changed = prepare_references(second, POLICY, {})
    assert changed[0]["mediana_treino"] == reports[0]["mediana_treino"]
    assert first[0]["atributos"] == second[0]["atributos"]
    assert first[0]["snapshot_revisado_apos_corte"] is True


def test_unknown_or_future_results_and_documented_divergences_are_excluded():
    rows = dataset()
    rows[0]["data_resultado"] = None
    rows[1]["data_resultado"] = date(2026, 7, 1)
    excluded = rows[100]["id"]
    report = prepare_references(rows, POLICY, {excluded: {}})[0]
    assert report["treino"] == 98 and report["avaliacao"] == 34
    assert not report["elegivel_tecnicamente"]
    assert rows[0]["atributos"]["preco_mediana"]["motivo"] == "DATA_RESULTADO_AUSENTE"
    assert "RESULTADO_POSTERIOR_AO_CORTE" in rows[1]["motivos_exclusao"]
    assert "DIVERGENCIA_DOCUMENTAL_SUSPENSA" in rows[100]["motivos_exclusao"]


def test_shared_purchases_across_specs_and_pseudoreplication_are_segregated():
    rows = dataset()
    rows.append(
        reference_row(
            raw_row(
                500, True, idCompra=rows[0]["compra"], descricaoDetalhadaItem="Outra especificação"
            )
        )
    )
    rows.extend(reference_row(raw_row(600 + n, idCompra="00000000000000001")) for n in range(6))
    prepare_references(rows, POLICY, {})
    assert "COMPRA_COMPARTILHADA_COM_TREINO" in rows[-7]["motivos_exclusao"]
    assert all("EXCESSO_REFERENCIAS_MESMA_COMPRA" in r["motivos_exclusao"] for r in rows[-6:])


def test_null_quantity_is_not_zero_and_zero_estimate_is_not_a_denominator():
    missing = reference_row(raw_row(quantidade=None))
    zero = reference_row(raw_row(1, quantidade="0"))
    prepare_references([missing, zero], POLICY, {})
    assert missing["atributos"]["log_quantidade"]["valor"] is None
    assert zero["atributos"]["log_quantidade"]["valor"] == 0.0
    assert estimated_difference(Decimal("10"), Decimal("12"), "UN")["valor"] == "0.2"
    assert estimated_difference(Decimal("0"), Decimal("12"), "UN")["valor"] is None
    assert estimated_difference(Decimal("10"), Decimal("12"), None)["valor"] is None


def event(process="p1", supplier="a", amount="75", when=date(2026, 1, 1), cancelled=False):
    return {
        "processo_id": process,
        "fornecedor_id": supplier,
        "valor_total_homologado": None if amount is None else Decimal(amount),
        "data_resultado": when,
        "cancelado": cancelled,
    }


def test_hhi_uses_all_suppliers_and_frequency_counts_purchases_not_rows():
    rows = [
        event(amount="50"),
        event(amount="25"),
        event("p2", "b", "25"),
        event("p3", "c", "9999", cancelled=True),
    ]
    params = {"start": date(2025, 12, 1), "end": date(2026, 1, 31)}
    hhi = concentration(rows, **params)
    assert hhi["valor"] == "0.6250"
    assert hhi["total"] == "100"
    assert hhi["participacoes"] == {"a": "0.75", "b": "0.25"}
    assert frequency(rows, "a", **params)["valor"] == 1
    assert concentration(rows, exclude_process="p1", **params)["valor"] == "1"


@pytest.mark.parametrize(
    "row,reason",
    [
        (event(amount=None), "TOTAL_DESCONHECIDO_NO_UNIVERSO"),
        (event(when=None), "DATA_RESULTADO_AUSENTE_NO_UNIVERSO"),
        (event(amount="0"), "TOTAL_UNIVERSO_NAO_POSITIVO"),
    ],
)
def test_incomplete_hhi_is_unavailable_instead_of_partial_or_zero(row, reason):
    assert concentration([row], start=date(2025, 1, 1), end=date(2026, 9, 30))["motivo"] == reason


def test_participant_completeness_and_contract_signature_are_not_inferred():
    rows = [{"identificacao_participante": "0001"}, {"identificacao_participante": "0001"}]
    assert participant_count(rows, True)["valor"] == 1
    assert participant_count(rows, False)["valor"] is None
    assert participant_count([], False)["valor"] is None
    publication, signature = date(2026, 1, 1), date(2026, 1, 13)
    contract = {"id": "c1", "data_assinatura": signature}
    assert contract_interval(publication, [contract], POLICY.end)["valor"] == 12
    assert contract_interval(publication, [contract], date(2026, 1, 5))["valor"] is None
    assert (
        contract_interval(
            publication,
            [dict(contract, data_assinatura=None, data_vigencia_inicio=signature)],
            POLICY.end,
        )["motivo"]
        == "ASSINATURA_AUSENTE"
    )
    assert contract_interval(publication, [contract, contract], POLICY.end)["valor"] is None


def test_even_complete_participation_does_not_use_future_or_undated_proposals():
    rows = [{"identificacao_participante": "0001", "incluido_na_origem_em": datetime(2026, 1, 1)}]
    assert participant_count(rows, True, as_of=date(2026, 6, 30))["valor"] == 1
    rows[0]["alterado_na_origem_em"] = datetime(2026, 7, 1)
    assert participant_count(rows, True, as_of=date(2026, 6, 30))["valor"] is None
    assert (
        participant_count([{"identificacao_participante": "0001"}], True, as_of=date(2026, 6, 30))[
            "valor"
        ]
        is None
    )


def register_history(admin, objects, rows):
    raw = json.dumps({"resultado": rows, "totalRegistros": len(rows), "totalPaginas": 1}).encode()
    envelope = {
        "schema": "licita-json-v1",
        "kind": "material_historico_api",
        "query": {"catalogo": "486374", "inicio": "2025-10-01", "fim": "2026-09-30"},
        "paginas": [{"pagina": 1, "resposta_original": raw.decode(), "resultado": rows}],
    }
    content = json.dumps(envelope).encode()
    uid = uuid4()
    key = f"raw/history/{uid}.json"
    objects.put(key, io.BytesIO(content))
    with admin.begin() as cn:
        cn.execute(
            sa.text(
                "INSERT INTO arquivos_coletados "
                "(id,fonte,modulo,competencia,url_origem,url_final,"
                "sha256,tamanho_bytes,chave_objeto) "
                "VALUES (:id,'comprasgov','historico/material/teste','2026-09-01',"
                "'https://example.test','https://example.test',:sha,:size,:key)"
            ),
            {
                "id": uid,
                "sha": hashlib.sha256(content).hexdigest(),
                "size": len(content),
                "key": key,
            },
        )
    return uid


@pytest.mark.integration
def test_analytical_manifest_parquet_reuse_and_tamper_do_not_publish_api_base(
    database, settings, sources, tmp_path
):
    repo, admin = database
    objects, ids, _, _ = sources
    base = Pipeline(settings, repo, objects).run(
        date(2026, 9, 1), date(2026, 9, 30), "486054", list(ids)
    )
    history = register_history(
        admin,
        objects,
        [raw_row(n) for n in range(100)] + [raw_row(n + 100, True) for n in range(35)],
    )
    exclusions = tmp_path / "exclusoes.json"
    exclusions.write_text(json.dumps({"versao": "exclusoes-documentais-v1", "exclusoes": []}))
    pipeline = AnalyticalPipeline(settings, repo, objects)
    before = {}
    with admin.connect() as cn:
        for name in ["versoes_base", "processos_versoes", "itens_versoes", "resultados_itens"]:
            before[name] = cn.scalar(sa.text(f'SELECT count(*) FROM "{name}"'))
    result = pipeline.run(UUID(base["base_id"]), [history], POLICY, exclusions)
    assert result["contagens"]["grupos_elegiveis_tecnicamente"] == 1
    assert pipeline.run(UUID(base["base_id"]), [history], POLICY, exclusions)["reutilizada"]
    with objects.open(result["manifesto"]) as stream:
        manifest = json.load(stream)
    assert manifest["snapshot_ponto_no_tempo"] is False
    assert manifest["comparabilidade_documental_aprovada"] is False
    artifact = next(a for a in manifest["artefatos"] if a["entidade"] == "referencias")
    with objects.open(artifact["chave"]) as stream:
        table = pq.read_table(io.BytesIO(stream.read()))
    assert table["preco_unitario"][0].as_py() == Decimal("1.00000001")
    assert table.num_rows == 135
    target_artifact = next(
        a for a in manifest["artefatos"] if a["entidade"] == "resultados_operacionais"
    )
    with objects.open(target_artifact["chave"]) as stream:
        target_rows = pq.read_table(io.BytesIO(stream.read())).to_pylist()
    target = json.loads(target_rows[0]["registro_json"])
    assert target["atributos"]["numero_participantes"]["valor"] is None
    # A fixture não informa data do resultado: o controle temporal precede os demais.
    assert target["data_resultado"] is None
    assert target["atributos"]["numero_participantes"]["motivo"] == "DATA_RESULTADO_AUSENTE"
    assert target["universo"]["tipo"] == "somente_recorte_da_base"
    assert target["proveniencias"][0]["arquivo_id"]
    with admin.connect() as cn:
        for name, count in before.items():
            assert cn.scalar(sa.text(f'SELECT count(*) FROM "{name}"')) == count
    source_key = manifest["fontes"][0]["chave_objeto"]
    with objects.open(source_key) as stream:
        original_source = stream.read()
    objects.put(source_key, io.BytesIO(original_source + b" "))
    with pytest.raises(SchemaError, match="Arquivo diverge"):
        pipeline.run(UUID(base["base_id"]), [history], POLICY, exclusions)
    objects.put(source_key, io.BytesIO(original_source))
    objects.put(artifact["chave"], io.BytesIO(b"corrompido"))
    with pytest.raises(ValueError, match="Artefato analítico diverge"):
        pipeline.run(UUID(base["base_id"]), [history], POLICY, exclusions)


@pytest.mark.integration
def test_history_conflicts_missing_units_and_timestamp_offsets_are_reconciled(
    database, settings, sources
):
    repo, admin = database
    objects, _, _, _ = sources
    rows = [
        raw_row(),
        raw_row(),
        raw_row(1),
        raw_row(1, precoUnitario="99"),
        raw_row(2, siglaUnidadeFornecimento=None),
    ]
    rows += [
        raw_row(3, dataHoraAtualizacaoItem="2026-01-01T12:00:00-03:00"),
        raw_row(3, dataHoraAtualizacaoItem="2026-01-01T15:00:00+00:00"),
    ]
    uid = register_history(admin, objects, rows)
    with repo.engine.connect() as cn:
        files = (
            cn.execute(
                sa.select(repo.tables["arquivos_coletados"]).where(
                    repo.tables["arquivos_coletados"].c.id == uid
                )
            )
            .mappings()
            .all()
        )
    accepted, rejected, _, reconciliation = read_history(objects, files, settings)
    assert len(accepted) == 2
    assert len(rejected) == 3
    assert reconciliation[str(uid)] == {"total": 7, "aceitos": 2, "rejeitados": 3, "descartados": 2}
    assert len(accepted[0]["proveniencias"]) == 2
