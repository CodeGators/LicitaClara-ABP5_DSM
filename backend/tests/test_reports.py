import csv
import io
from uuid import uuid4

import pytest
import sqlalchemy as sa
import test_consultas as shared
from licita_backend.models import procurement as p
from licita_backend.services import reports
from licita_backend.services.report_pdf import pdf_file
from pypdf import PdfReader

query_database = shared.query_database
populated = shared.populated
query_client = shared.query_client


def urls(data):
    base = f"/api/v1/relatorios/processos/{data['first']}"
    return base + "/previa", base + "/arquivo"


def test_preview_pdf_csv_same_snapshot_public_and_decimal_exact(query_client):
    client, data = query_client
    preview, download = urls(data)
    params = {"base_id": data["base"], "titulo": "Análise de preços e órgãos"}
    response = client.get(preview, params=params)
    assert response.status_code == 200, response.text
    snapshot = response.json()
    assert snapshot["resumo"]["itens"] == 2
    assert snapshot["analise"] is None
    assert snapshot["processo"]["valor_homologado_itens_recorte"] == "0.60000001"
    args = {**params, "snapshot_sha256": snapshot["snapshot_sha256"]}
    pdf = client.get(download, params={**args, "formato": "pdf"})
    assert pdf.status_code == 200, pdf.text[:200] if pdf.status_code != 200 else ""
    assert pdf.content.startswith(b"%PDF-")
    text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "sem análise selecionada" in text
    assert "Análise de preços e órgãos" in text and "R$ 0,60" in text
    assert "Precisão original do preço unitário: 0.10000001" in text
    assert snapshot["snapshot_sha256"] in text
    assert "Sem análise disponível" in text and "Não há score integral validado" in text
    result = client.get(download, params={**args, "formato": "csv"})
    assert result.status_code == 200
    rows = list(csv.DictReader(io.StringIO(result.content.decode("utf-8-sig")), delimiter=";"))
    assert len(rows) == 4  # One canceled result retained; no multiplication of co-winners.
    assert rows[0]["preco_unitario"] == "0.10000001"
    assert {r["snapshot_sha256"] for r in rows} == {snapshot["snapshot_sha256"]}
    assert pdf.headers["x-snapshot-sha256"] == result.headers["x-snapshot-sha256"]
    assert "attachment;" in pdf.headers["content-disposition"]
    assert client.get(preview, params=params).json() == snapshot


def test_wrong_selection_stale_preview_and_limits_fail_explicitly(query_client, monkeypatch):
    client, data = query_client
    preview, download = urls(data)
    params = {"base_id": data["base"]}
    snapshot = client.get(preview, params=params).json()
    assert (
        client.get(
            download, params={**params, "formato": "pdf", "snapshot_sha256": "0" * 64}
        ).status_code
        == 409
    )
    assert client.get(preview, params={**params, "execucao_id": str(uuid4())}).status_code == 404
    assert (
        client.get(preview.replace(data["first"], str(uuid4())), params=params).status_code == 404
    )
    assert client.get(preview, params={**params, "usuario_id": str(uuid4())}).status_code == 422
    assert (
        client.get(
            download,
            params={**params, "formato": "html", "snapshot_sha256": snapshot["snapshot_sha256"]},
        ).status_code
        == 422
    )
    assert client.get(preview, params={**params, "titulo": "  "}).status_code == 422
    monkeypatch.setattr(reports, "MAX_ITEMS", 1)
    assert client.get(preview, params=params).status_code == 413


def test_changed_data_rejected_instead_of_downloading_different_preview(query_client):
    client, data = query_client
    preview, download = urls(data)
    params = {"base_id": data["base"]}
    original = client.get(preview, params=params).json()
    with data["engine"].begin() as cn:
        cn.execute(p.itens_versoes.update().values(descricao="Descrição atualizada"))
    response = client.get(
        download,
        params={**params, "formato": "csv", "snapshot_sha256": original["snapshot_sha256"]},
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "value", ["=1+1", " +SUM(A1:A2)", "@formula", "-formula", "\tformula", "\nformula"]
)
def test_csv_formula_neutralization(value):
    assert reports.safe_cell(value) == "'" + value


def test_pdf_escapes_markup_and_paginates_long_text(query_client):
    client, data = query_client
    preview, _ = urls(data)
    snapshot = client.get(preview, params={"base_id": data["base"]}).json()
    snapshot["titulo"] = '<img src="https://invalid.example/remote.png"/> & Relatório'
    snapshot["itens"][0]["descricao"] = "Descrição longa com acentuação. " * 1000
    raw = pdf_file(snapshot)
    reader = PdfReader(io.BytesIO(raw))
    assert len(reader.pages) > 1
    assert "<img src=" in reader.pages[0].extract_text()


def test_scores_stay_separate_and_historical_publication_remains_reproducible(query_client):
    from uuid import UUID

    from licita_backend.models import analysis as a

    client, data = query_client
    with data["engine"].begin() as cn:
        base = UUID(data["base"])
        item = UUID(data["item_version_first"])
        process = cn.scalar(
            sa.select(p.itens_versoes.c.processo_versao_id).where(p.itens_versoes.c.id == item)
        )
        result = cn.scalar(
            sa.select(p.resultados_itens.c.id).where(
                p.resultados_itens.c.item_versao_id == item,
                p.resultados_itens.c.sequencial_resultado == 1,
            )
        )
        execution = shared.add(
            cn,
            a.execucoes_analise,
            base_id=base,
            versao_politica_score="experimental-v1",
            status="concluida",
            concluido_em=sa.func.now(),
            configuracao={"experimental": True, "cobertura": []},
        )
        publication = shared.add(
            cn,
            a.publicacoes_analise,
            nome="experimental:" + str(base),
            base_id=base,
            execucao_id=execution,
        )
        for algorithm, index in [("isolation_forest", "92.000"), ("autoencoder", "78.500")]:
            model = shared.add(
                cn,
                a.versoes_modelo,
                base_treino_id=base,
                algoritmo=algorithm,
                versao="test",
                versao_codigo="test",
                chave_artefato="test",
                sha256_artefato="a" * 64,
            )
            cn.execute(a.execucoes_modelos.insert().values(execucao_id=execution, modelo_id=model))
            shared.add(
                cn,
                a.resultados_modelo,
                base_id=base,
                execucao_id=execution,
                modelo_id=model,
                processo_versao_id=process,
                item_versao_id=item,
                resultado_item_id=result,
                tipo_alvo="resultado",
                score_bruto="0.123",
                score_normalizado=index,
                versao_normalizacao="cdf-treino-v1",
                atributos={
                    "comparacao": {"grupo": "test", "mediana": "0.08000000", "n_treino": 100},
                    "referencia": {
                        "razao_preco_mediana": "1.25",
                        "membro": "material.csv",
                        "linha": 2,
                        "arquivo_sha256": "b" * 64,
                    },
                },
            )
    preview, download = urls(data)
    params = {"base_id": data["base"], "execucao_id": str(execution)}
    original = client.get(preview, params=params).json()
    assert original["resumo"] == {"itens": 2, "itens_analisados": 1, "scores": 2}
    assert len(original["itens"][0]["scores"]) == 2
    # Active flag changing must not replace a pinned historical execution.
    with data["engine"].begin() as cn:
        cn.execute(
            a.publicacoes_analise.update()
            .where(a.publicacoes_analise.c.id == publication)
            .values(ativa=False)
        )
    assert client.get(preview, params=params).json() == original
    response = client.get(
        download,
        params={**params, "formato": "csv", "snapshot_sha256": original["snapshot_sha256"]},
    )
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
    assert len(rows) == 5
    scored = [r for r in rows if r["modelo_id"]]
    assert {r["algoritmo"] for r in scored} == {"isolation_forest", "autoencoder"}
    assert all(r["mediana_treino"] == "0.08000000" for r in scored)
    assert all(r["homologado_recorte"] == "0.60000001" for r in rows)
    assert client.get(preview, params={**params, "base_id": data["old"]}).status_code == 404


def test_csv_preserves_quoted_newlines_and_neutralizes_formula_from_real_fields(query_client):
    client, data = query_client
    with data["engine"].begin() as cn:
        cn.execute(p.itens_versoes.update().values(descricao="=SUM(1;2)"))
        cn.execute(p.resultados_itens.update().values(fornecedor_nome='Fornecedor "A"\nLinha dois'))
    preview, download = urls(data)
    params = {"base_id": data["base"], "titulo": "=1+1"}
    snapshot = client.get(preview, params=params).json()
    response = client.get(
        download,
        params={**params, "formato": "csv", "snapshot_sha256": snapshot["snapshot_sha256"]},
    )
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
    assert len(rows) == 4
    assert all(row["titulo"] == "'=1+1" and row["descricao"] == "'=SUM(1;2)" for row in rows)
    assert all(row["fornecedor"] == 'Fornecedor "A"\nLinha dois' for row in rows)


def test_pdf_rounding_is_display_only_and_preserves_tiny_values():
    from licita_backend.services.report_pdf import money, number

    assert money("9007199254740993.995") == "R$ 9.007.199.254.740.994,00"
    assert money("0.004") == "R$ 0,004"
    assert number("3.00000001") == "3"
    assert number("88.125") == "88,13"
    assert number("-1.235") == "-1,24"
    assert number("-0.00000001") == "-0,00000001"
    assert money(None) == "Não informado"
