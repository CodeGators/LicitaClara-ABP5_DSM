"""Executa a conferência assistida, mantendo o lote cego original intacto."""

import csv
import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from licita_ml.experiments.core import write_json
from licita_ml.experiments.data import clean, history
from licita_ml.review_validation.acquisition import ROOT
from licita_ml.review_validation.documentary import review_case


def main():
    source = Path("data/validacao_nucleo/resultados/revisao/c2c61e3e795a3068-revisao-cega.csv")
    with source.open() as file:
        cases = list(csv.DictReader(file))
    rows, _ = history("486374", Path("data/validacao_nucleo"), True)
    cleaned, _ = clean(rows, "486374")
    raw_by_id = {row["id"]: rows[row["source_ordinal"] - 1] for row in cleaned}
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()

    def work(case):
        return review_case(case, raw_by_id[case["id"]])

    with ThreadPoolExecutor(max_workers=4) as pool:
        reviews = list(pool.map(work, cases))
    assert original_hash == hashlib.sha256(source.read_bytes()).hexdigest()
    protocol = Path("docs/validacao_nucleo/PROTOCOLO_REVISAO_E_CONFIRMACAO.md")
    report = {
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "sha256_protocolo": hashlib.sha256(protocol.read_bytes()).hexdigest(),
        "sha256_planilha_original": original_hash,
        "amostra": len(cases),
        "estados": dict(Counter(r["conferencia"]["estado"] for r in reviews)),
        "revisoes": reviews,
        "parecer_humano_independente": False,
        "acuracia_fraude_disponivel": False,
    }
    write_json(ROOT / "conferencia_documental.json", report)
    print(
        json.dumps({"amostra": len(cases), "estados": report["estados"]}, ensure_ascii=False),
        flush=True,
    )


if __name__ == "__main__":
    main()
