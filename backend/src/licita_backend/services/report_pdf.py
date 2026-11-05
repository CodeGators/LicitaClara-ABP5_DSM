"""PDF paginado a partir do mesmo snapshot público usado na prévia."""

import io
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

TEAL = colors.HexColor("#00878b")
NAVY = colors.HexColor("#173650")


@lru_cache(maxsize=1)
def fonts():
    folder = Path(reportlab.__file__).parent / "fonts"
    pdfmetrics.registerFont(TTFont("Licita", str(folder / "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("LicitaBold", str(folder / "VeraBd.ttf")))


def display(value):
    return "Não informado" if value is None or value == "" else str(value)


def money(value):
    if value is None:
        return "Não informado"
    integer, _, fraction = str(value).partition(".")
    sign = "-" if integer.startswith("-") else ""
    integer = integer.lstrip("-")
    groups = []
    while integer:
        groups.insert(0, integer[-3:])
        integer = integer[:-3]
    return "R$ " + sign + ".".join(groups) + "," + fraction.rstrip("0").ljust(2, "0")


def pdf_file(data):
    fonts()
    body = ParagraphStyle(
        "body", fontName="Licita", fontSize=9, leading=13, textColor=NAVY, spaceAfter=7
    )
    heading = ParagraphStyle(
        "heading", parent=body, fontName="LicitaBold", fontSize=13, leading=17, spaceBefore=12
    )
    small = ParagraphStyle("small", parent=body, fontSize=7, leading=10)

    def para(value, style=body):
        return Paragraph(escape(display(value)).replace("\n", "<br/>"), style)

    content = []
    process = data["processo"]
    content += [
        para(data["titulo"], heading),
        para(f"Compra {process['numero_compra']} · {process['orgao_nome']}"),
        para(process["objeto"]),
        para(
            "Dados oficiais · "
            + ("análise experimental" if data["analise"] else "sem análise selecionada")
        ),
        para("01 / Síntese do processo", heading),
    ]
    for label, key in [
        ("Estimado global", "valor_estimado_processo"),
        ("Homologado global", "valor_homologado_processo"),
        ("Homologado dos itens do recorte", "valor_homologado_itens_recorte"),
    ]:
        content.append(para(f"{label}: {money(process[key])}"))
    content += [
        para(f"Modalidade: {display(process['modalidade_nome'])}"),
        para(
            f"Itens importados: {data['resumo']['itens']}"
            f" · Com análise: {data['resumo']['itens_analisados']}"
        ),
        para("Valores globais e valores do recorte são medidas distintas; não somar."),
        para("02 / Itens, resultados e comparação", heading),
    ]
    for item in data["itens"]:
        content += [
            para(f"Item {item['numero_item']} — {item['descricao']}", heading),
            para(
                f"Unidade: {display(item['unidade_medida'])}"
                f" · Quantidade do item: {display(item['quantidade'])}"
            ),
            para(f"Preço unitário estimado: {money(item['valor_unitario_estimado'])}"),
        ]
        if not item["resultados"]:
            content.append(para("Sem resultado conhecido."))
        for result in item["resultados"]:
            content.append(
                para(
                    f"Fornecedor: {result['fornecedor_nome']}"
                    f" · Resultado {'cancelado' if result['cancelado'] else 'não cancelado'}"
                )
            )
            table = Table(
                [
                    [para(label, small), para(value, small)]
                    for label, value in [
                        ("Preço unitário homologado", money(result["valor_unitario_homologado"])),
                        ("Quantidade homologada", display(result["quantidade_homologada"])),
                        ("Total do resultado", money(result["valor_total_homologado"])),
                        ("Data do resultado", display(result["data_resultado"])),
                    ]
                ],
                colWidths=[220, 287],
                splitInRow=1,
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f2f6f8")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            content.append(table)
        if not item["scores"]:
            content.append(para("Sem análise disponível para este item na seleção."))
        for score in item["scores"]:
            content += [
                para(
                    f"{score['algoritmo']}"
                    f" · índice {score['indice']} / 100"
                    f" · resultado {score['resultado_item_id']}"
                ),
                para(
                    f"Mediana do treino: {money(score['mediana_treino'])}"
                    f" · Preço/mediana: {display(score['razao_preco_mediana'])}"
                    f" · Exemplos de treino: {display(score['n_treino'])}"
                ),
                para(f"Modelo: {score['modelo_id']} · Grupo: {display(score['grupo'])}", small),
                para(
                    f"Fonte: {score['fonte'].get('membro')}"
                    f" · Registro CSV: {score['fonte'].get('linha')}"
                    f" · SHA-256: {score['fonte'].get('arquivo_sha256')}",
                    small,
                ),
            ]
        reasons = sorted({r["motivo"] for r in item["cobertura"] if r.get("motivo")})
        if reasons:
            content.append(para("Motivos de ausência: " + ", ".join(reasons), small))
    content.append(para("03 / Método e limites de interpretação", heading))
    content.extend(para(value) for value in data["limites"])
    content.append(para("Fonte e rastreabilidade", heading))
    content.append(para(data["fonte"]))
    content.append(para(f"Base: {data['base']['id']} · Versão: {data['base']['versao']}", small))
    content.append(
        para(
            f"Período da base: {data['base']['periodo_inicio']} a {data['base']['periodo_fim']}",
            small,
        )
    )
    content.append(para(f"Manifesto da base: {data['base']['manifesto_sha256']}", small))
    content.append(
        para(f"Execução: {(data['analise'] or {}).get('id', 'Sem análise selecionada')}", small)
    )
    content.append(
        para(f"Manifesto da análise: {(data['analise'] or {}).get('manifesto_sha256')}", small)
    )
    content.append(para(f"Snapshot: {data['snapshot_sha256']}", small))
    content.append(Spacer(1, 10))
    out = io.BytesIO()

    def page(canvas, doc):
        canvas.setFont("LicitaBold", 15)
        canvas.setFillColor(NAVY)
        canvas.drawString(44, A4[1] - 36, "Licita Clara")
        canvas.setStrokeColor(TEAL)
        canvas.line(44, A4[1] - 46, A4[0] - 44, A4[1] - 46)
        canvas.setFont("Licita", 7)
        canvas.drawString(44, 28, "FATEC Jacareí · Anomalias em compras públicas")
        canvas.drawRightString(A4[0] - 44, 28, f"Página {doc.page}")

    SimpleDocTemplate(
        out,
        pagesize=A4,
        rightMargin=44,
        leftMargin=44,
        topMargin=60,
        bottomMargin=45,
        title=data["titulo"],
        author="Licita Clara",
    ).build(content, onFirstPage=page, onLaterPages=page)
    return out.getvalue()
