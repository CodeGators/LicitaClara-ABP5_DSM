"""Aquisição limitada de anexos e índice de páginas; não atribui irregularidade."""

import hashlib
import io
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from zipfile import BadZipFile, ZipFile

from licita_ml.experiments.core import write_json
from licita_ml.experiments.data import normalized
from licita_ml.review_validation.acquisition import ROOT, snapshot


def candidates(documents):
    selected = [
        d for d in documents if d.get("statusAtivo") is not False and (d.get("url") or d.get("uri"))
    ]

    def priority(doc):
        kind = normalized(doc.get("tipoDocumentoNome"))
        return (
            0 if kind == "termo de referencia" else 1 if kind == "edital" else 2,
            doc.get("sequencialDocumento", 0),
        )

    return sorted(selected, key=priority)[:2]


def pdf_sources(data):
    if data.startswith(b"%PDF-"):
        return [("documento.pdf", data)]
    if data.startswith(b"PK\x03\x04"):
        with ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > 100 or sum(m.file_size for m in members) > 64 * 1024**2:
                raise ValueError("ZIP excede limites de membros ou expansão")
            selected = [
                m for m in members if m.filename.lower().endswith(".pdf") and not m.is_dir()
            ]
            if any(m.file_size > 16 * 1024**2 or m.flag_bits & 1 for m in selected):
                raise ValueError("PDF grande demais ou criptografado")
            # Ler somente em memória; nomes do ZIP nunca se tornam caminhos locais.
            return [(member.filename, archive.read(member)) for member in selected[:6]]
    return []


def inspect_document(document):
    url = document.get("url") or document["uri"]
    result = {"titulo": document.get("titulo"), "url": url}
    try:
        public_url = url.replace(
            "https://pncp.gov.br/pncp-api/v1/", "https://pncp.gov.br/api/pncp/v1/", 1
        )
        cached = ROOT / "fontes" / (hashlib.sha256(url.encode()).hexdigest() + ".bin")
        data, meta = snapshot(url if cached.exists() else public_url, binary=True)
        result["fonte"] = meta
        pdfs = pdf_sources(data)
        if not pdfs:
            result["estado"] = "formato_nao_pdf_ou_zip_sem_pdf"
            result["assinatura_hex"] = data[:8].hex()
            return result
        folder = ROOT / "textos"
        folder.mkdir(parents=True, exist_ok=True)
        indexed = []
        for name, content in pdfs:
            if not content.startswith(b"%PDF-"):
                raise ValueError("Membro com extensão PDF sem assinatura PDF")
            key = hashlib.sha256(content).hexdigest()
            pdf = folder / (key + ".pdf")
            pdf.write_bytes(content)
            dest = folder / (key + ".txt")
            subprocess.run(
                ["pdftotext", "-layout", str(pdf), str(dest)],
                check=True,
                timeout=30,
                capture_output=True,
            )
            text = dest.read_text(errors="replace")
            pages = text.split("\f")
            indexed.append(
                {
                    "membro": name,
                    "pdf": str(pdf),
                    "sha256_pdf": key,
                    "texto": str(dest),
                    "sha256_texto": hashlib.sha256(dest.read_bytes()).hexdigest(),
                    "paginas_total": len(pages) - (not pages[-1].strip()),
                    "paginas_marca_texto": [
                        i
                        for i, page in enumerate(pages, 1)
                        if "marca texto" in normalized(page) or "486374" in page
                    ],
                    "paginas_condicoes": [
                        i
                        for i, page in enumerate(pages, 1)
                        if any(
                            term in normalized(page)
                            for term in ("frete", "local de entrega", "prazo de entrega")
                        )
                    ],
                    "tem_texto": bool(text.strip()),
                }
            )
        result["pdfs"] = indexed
        result["estado"] = (
            "texto_extraido" if any(p["tem_texto"] for p in indexed) else "pdf_sem_texto"
        )
    except (OSError, ValueError, BadZipFile, subprocess.SubprocessError) as error:
        result["estado"] = "falha_acesso_ou_extracao"
        result["erro"] = type(error).__name__ + ": " + str(error)
    return result


def main():
    review = json.loads((ROOT / "conferencia_documental.json").read_text())
    docs_by_url, mapping = {}, {}
    for case in review["revisoes"]:
        selected = candidates(case["documentos"])
        mapping[case["id"]] = [d.get("url") or d["uri"] for d in selected]
        docs_by_url.update({d.get("url") or d["uri"]: d for d in selected})
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(inspect_document, document) for document in docs_by_url.values()]
        inspected = []
        for future in as_completed(futures):
            result = future.result()
            inspected.append(result)
            print(f"Documento {len(inspected)}/{len(futures)}: {result['estado']}", flush=True)
        inspected.sort(key=lambda document: document["url"])
    report = {
        "documentos": inspected,
        "documentos_por_caso": mapping,
        "parecer_humano_independente": False,
    }
    write_json(ROOT / "documentos_extraidos.json", report)
    print(
        json.dumps(
            {
                "documentos": len(inspected),
                "texto_extraido": sum(x["estado"] == "texto_extraido" for x in inspected),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
