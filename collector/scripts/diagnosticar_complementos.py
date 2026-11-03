"""Diagnóstico limitado de propostas, contratos e anexos; não importa dados no banco.

Execute na raiz: python3 collector/scripts/diagnosticar_complementos.py
As respostas integrais ficam em data/ (ignorado); o perfil agregado fica em docs/diagnostico/.
"""

import csv
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path("data/diagnostico/complementos")
REPO = "https://repositorio.dados.gov.br/seges/comprasgov/"
API = "https://dadosabertos.compras.gov.br"
PNCP = "https://pncp.gov.br/api/pncp/v1"


def fetch(name, url):
    for attempt in range(2):
        try:
            with urlopen(url, timeout=25) as response:
                raw = response.read(10 * 1024**2 + 1)
                if len(raw) > 10 * 1024**2:
                    raise ValueError("Limite do diagnóstico excedido")
                meta = {"url": url, "url_final": response.url, "status": response.status,
                        "coletado_em_utc": datetime.now(timezone.utc).isoformat(),
                        "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            (ROOT / name).write_bytes(raw)
            (ROOT / (name + ".meta.json")).write_text(json.dumps(meta, indent=2) + "\n")
            print(name, "OK", flush=True)
            return raw, meta
        except (OSError, ValueError) as error:
            if attempt == 1:
                print(name, type(error).__name__, flush=True)
                return None, {"url": url, "erro": type(error).__name__}


def csv_rows(path):
    with ZipFile(path) as archive:
        with archive.open(archive.namelist()[0]) as stream:
            yield from csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"), delimiter=";")


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    requests = {
        "leiame": REPO + "propostas/LEIAME.md",
        "propostas": REPO + "propostas/2026/09/propostas-2026-09.csv.zip",
        "contratos": API + "/modulo-contratos/1_consultarContratos?" + urlencode({
            "codigoOrgao": "26000", "dataVigenciaInicialMin": "2026-09-01",
            "dataVigenciaInicialMax": "2026-09-30", "pagina": 1, "tamanhoPagina": 10}),
        "contratos_por_compra": API + "/modulo-contratos/1.1_consultarContratos_Id?" + urlencode({
            "tipo": "idCompra", "codigo": "15200405001682027"}),
        "compra_contrato": API + "/modulo-contratacoes/1.1_consultarContratacoes_PNCP_14133_Id?" + urlencode({
            "tipo": "idCompra", "codigo": "15200405001682027"}),
        "contrato_pncp": PNCP + "/orgaos/00394445000101/contratos/2026/222",
        "documentos_contrato": PNCP + "/orgaos/00394445000101/contratos/2026/222/arquivos",
        "documentos": PNCP + "/orgaos/10744098000145/compras/2026/187/arquivos",
    }
    replies = {name: fetch(name, url) for name, url in requests.items()}
    rows = list(csv_rows(ROOT / "propostas")) if replies["propostas"][0] else []
    result = {"requisicoes": {name: meta for name, (_, meta) in replies.items()},
              "escopo": "ZIP completo de propostas; amostras limitadas de contratos e anexos, sem garantia de cobertura integral."}
    if rows:
        pairs = {(r["id_compra_item"], r["identificacao_participante"]) for r in rows}
        result["propostas"] = {
            "linhas": len(rows), "ids_distintos": len({r["id"] for r in rows}),
            "pares_item_participante": len(pairs), "compras": len({r["id_compra"] for r in rows}),
            "itens": len({r["id_compra_item"] for r in rows}), "campos": list(rows[0]),
            "ausentes": {k: sum(not r[k] for r in rows) for k in rows[0]},
            "homologado": dict(Counter(r["homologado"] for r in rows)),
            "classificados_nao_vencedores": sum(bool(r["classificacao"]) and r["classificacao"] != "1" for r in rows),
            "data_inclusao_min": min(r["data_hora_inclusao"] for r in rows),
            "data_inclusao_max": max(r["data_hora_inclusao"] for r in rows),
            "inclusao_fora_setembro": sum(not r["data_hora_inclusao"].startswith("2026-09") for r in rows),
        }
        items_path = Path("data/diagnostico/compras/2026-09/compra_item_2026_09.csv.zip")
        if items_path.exists():
            keys = {r["id_compra_item"]: r["id_compra"] for r in csv_rows(items_path)}
            result["propostas"]["linhas_com_item_no_zip_pncp_mesmo_mes"] = sum(r["id_compra_item"] in keys for r in rows)
            result["propostas"]["vinculos_item_compra_divergentes"] = sum(
                r["id_compra_item"] in keys and keys[r["id_compra_item"]] != r["id_compra"] for r in rows)
    payloads = {name: json.loads(raw) for name, (raw, _) in replies.items()
                if raw and name not in ("leiame", "propostas")}
    for name, payload in payloads.items():
        values = payload.get("resultado", [payload]) if isinstance(payload, dict) else payload
        result[name] = {"linhas_amostradas": len(values),
                        "campos": sorted({k for r in values for k in r})}
    contracts = payloads.get("contratos", {}).get("resultado", [])
    purchases = payloads.get("compra_contrato", {}).get("resultado", [])
    if contracts and purchases:
        a, b = contracts[0], purchases[0]
        result["vinculo_contrato_compra"] = {
            "idCompra_igual": a["idCompra"] == b["idCompra"],
            "controle_pncp_igual": a["numeroControlePncpCompra"] == b["numeroControlePNCP"],
            "data_vigencia_inicio": a["dataVigenciaInicial"],
            "ano_compra_na_origem": b["anoCompraPncp"],
            "observacao": "Compra identificada como 2027 com publicação/contrato em 2026; preservar e sinalizar na importação."}
    result["limites"] = [
        "Propostas somente de itens homologados; ausência não significa zero participantes.",
        f"{len(rows) - len(pairs) if rows else 0} linhas excedentes ao par item/participante; preservar ID oficial.",
        "Partição de propostas usa inclusão do item segundo LEIAME; coluna de inclusão do CSV também contém outubro no ZIP de setembro.",
        "Vigência não substitui assinatura. PNCP informa dataAssinatura no detalhe do contrato.",
        "Anexos: somente metadados consultados; binários não baixados.",
        "Diagnóstico não amplia automaticamente os conectores da CLI nem importa linhas de domínio.",
    ]
    output = Path("docs/diagnostico/perfil_complementos_etapa03.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
