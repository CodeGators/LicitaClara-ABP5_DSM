"""Importar todos os itens da aplicação dos grupos preparados, sem corte por score."""

from datetime import date
from pathlib import Path

import pyarrow.dataset as ds

from licita_ml.analytical.operational import read_base
from licita_ml.grouped.temporal import validate
from licita_ml.pipeline import Pipeline


def selection(preparation):
    preparation = Path(preparation)
    source = validate(preparation)
    items, codes, purchases = set(), set(), set()
    for batch in source["lotes"]:
        table = ds.dataset(preparation / batch["diretorio"] / "referencias_temporais.parquet")
        for row in table.to_table(
            columns=["item", "catalogo", "compra"], filter=ds.field("particao") == "aplicacao"
        ).to_pylist():
            items.add(row["item"])
            codes.add(row["catalogo"])
            purchases.add(row["compra"])
    if not items:
        raise ValueError("Sem itens na janela de aplicação")
    if len(items) > 20000:
        raise ValueError("Aplicação excede 20 mil itens; preparar lotes explícitos")
    return {
        "itens": sorted(items),
        "catalogos": sorted(codes),
        "compras": sorted(purchases),
        "inicio": source["configuracao"]["politica"]["application_start"],
        "fim": source["configuracao"]["politica"]["application_end"],
    }


def run(
    preparation, settings, repository, objects, ids=None, fail_after=None, preserve_base_id=None
):
    chosen = selection(preparation)
    if preserve_base_id is not None:
        with repository.locked() as cn:
            _, data = read_base(repository, cn, preserve_base_id)
        chosen = preserve_selection(chosen, data)

    result = Pipeline(settings, repository, objects).run(
        date.fromisoformat(chosen["inicio"]),
        date.fromisoformat(chosen["fim"]),
        chosen["catalogos"],
        ids,
        fail_after,
        selected_items=chosen["itens"],
    )
    return {
        **result,
        "itens_solicitados": len(chosen["itens"]),
        "catalogos_solicitados": len(chosen["catalogos"]),
        "compras_solicitadas": len(chosen["compras"]),
    }


def preserve_selection(chosen, data):
    """A atualização de modelos não deve apagar itens anteriormente consultáveis."""
    selected = set(chosen["itens"])
    for item in data["itens_versoes"]:
        origin = item["atributos_origem"]
        uid = origin.get("idCompraItem") or origin.get("id_compra_item")
        if not uid:
            raise ValueError("Item anterior sem identidade oficial; não reduzir cobertura")
        selected.add(str(uid))
    if len(selected) > 20000:
        raise ValueError("União operacional excede limite; preparar lotes explícitos")
    return {
        **chosen,
        "itens": sorted(selected),
        "catalogos": sorted(set(chosen["catalogos"]) | set(data["catalogos"].values())),
    }
