import json
from collections import Counter

from licita_ml.normalize import RowError, day
from licita_ml.readers import kind_of, records
from licita_ml.transform import canonical_row


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


class Stage:
    def __init__(self):
        self.rows = {}
        self.stats = {}
        self.rejects = []
        self.dispositions = {}

    def reject(self, origin, reason):
        if self.dispositions.get(origin) == "rejeitados":
            return
        self.dispositions[origin] = "rejeitados"
        self.rejects.append(
            {"arquivo_id": origin[0], "membro": origin[1], "linha": origin[2], "motivo": reason}
        )

    def resolve(self, objects, files, settings, start, end, catalog):
        material = [f for f in files if kind_of(f) == "material"]
        if not material:
            raise ValueError("Recorte requer arquivo material")
        selected, purchases = set(), set()
        for file in material:
            for _, _, r, _ in records(objects, file, settings):
                if r.get("codigo_item_catalogo") != catalog:
                    continue
                try:
                    if start <= day(r.get("data_compra"), True) <= end:
                        selected.add(r["id_compra_item"])
                        purchases.add(r["id_compra"])
                except RowError:
                    pass
        if len(selected) > 20000:
            raise ValueError("Recorte excede limite de 20 mil itens")
        if not selected:
            raise ValueError("Recorte sem itens na referência de preços")
        for file in files:
            file_id = str(file["id"])
            kind = kind_of(file)
            self.stats[file_id] = Counter(
                total=0, filtrados=0, aceitos=0, rejeitados=0, descartados=0
            )
            for member, line, raw, query in records(objects, file, settings):
                counts = self.stats[file_id]
                counts["total"] += 1
                origin = (file_id, member, line)
                purchase = raw.get("id_compra", raw.get("idCompra"))
                item = raw.get("id_compra_item", raw.get("idCompraItem"))
                if (
                    (
                        kind == "material"
                        and (raw.get("codigo_item_catalogo") != catalog or item not in selected)
                    )
                    or (
                        kind in ("compra", "compra_api", "contratos_api")
                        and purchase not in purchases
                    )
                    or (
                        kind
                        in (
                            "compra_item",
                            "itens_api",
                            "item_resultado",
                            "resultados_api",
                            "propostas",
                        )
                        and item not in selected
                    )
                ):
                    counts["filtrados"] += 1
                    continue
                if len(self.dispositions) >= 20000:
                    raise ValueError(
                        "Recorte excede limite de 20 mil linhas selecionadas; reduza o período"
                    )
                try:
                    domain, key, rank, values = canonical_row(kind, raw, query)
                    if domain == "referencia" and not start <= values["data_compra"] <= end:
                        counts["filtrados"] += 1
                        continue
                    entry = {
                        "domain": domain,
                        "key": key,
                        "rank": rank,
                        "values": values,
                        "origin": origin,
                        "source": file["fonte"],
                        "raw": json.loads(encode(raw)),
                    }
                    group = (domain, key)
                    previous = self.rows.get(group)
                    if previous is None:
                        self.rows[group] = entry
                        self.dispositions[origin] = "aceitos"
                    elif rank > previous["rank"]:
                        if not previous.get("conflict"):
                            self.dispositions[previous["origin"]] = "descartados"
                        self.rows[group] = entry
                        self.dispositions[origin] = "aceitos"
                    elif rank == previous["rank"] and previous.get("conflict"):
                        self.reject(origin, "CONFLITO_SEM_PRECEDENCIA")
                    elif rank < previous["rank"] or encode(values) == encode(previous["values"]):
                        self.dispositions[origin] = "descartados"
                    else:
                        # Conflito não é decidido por ordem de leitura ou valor do preço.
                        self.reject(previous["origin"], "CONFLITO_SEM_PRECEDENCIA")
                        self.reject(origin, "CONFLITO_SEM_PRECEDENCIA")
                        previous["conflict"] = True
                except RowError as error:
                    self.reject(origin, error.code)
        self.rows = {key: value for key, value in self.rows.items() if not value.get("conflict")}
        return selected, purchases

    def reconcile(self):
        for counts in self.stats.values():
            for key in ["aceitos", "rejeitados", "descartados"]:
                counts[key] = 0
        for origin, state in self.dispositions.items():
            self.stats[origin[0]][state] += 1
        for counts in self.stats.values():
            assert counts["total"] == sum(
                counts[k] for k in ["filtrados", "aceitos", "rejeitados", "descartados"]
            )
        return self.stats
