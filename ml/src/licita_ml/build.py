"""Converte registros resolvidos em entidades/snapshots com proveniência por origem."""

from collections import defaultdict

import sqlalchemy as sa

from licita_ml.repository import identifier


class Builder:
    def __init__(self, repository, connection, stage, base_id, import_ids):
        self.repo, self.connection, self.stage, self.base_id, self.import_ids = (
            repository,
            connection,
            stage,
            base_id,
            import_ids,
        )
        self.data = defaultdict(dict)
        self.processes = {}
        self.items = {}
        self.contracts = {}
        self.controls = {}

    def add(self, table, key, **values):
        value = identifier(table, key)
        self.data[table][value] = {"id": value, **values}
        return value

    def identity(self, table, key, criteria, **values):
        uid = identifier(table, key)
        if uid in self.data[table]:
            return uid
        t = self.repo.tables[table]
        existing = (
            self.connection.execute(sa.select(t).where(*(t.c[k] == v for k, v in criteria.items())))
            .mappings()
            .one_or_none()
        )
        if existing:
            self.data[table][existing["id"]] = {
                k: v for k, v in existing.items() if k != "criado_em"
            }
            return existing["id"]
        return self.add(table, key, **criteria, **values)

    def supplier(self, code, name):
        if not code:
            return None
        category = (
            "CNPJ"
            if len(code) == 14 and code.isdigit()
            else "CPF"
            if len(code) == 11 and code.isdigit()
            else "OUTRO"
        )
        return self.identity(
            "fornecedores",
            ("comprasgov", category, code),
            {"fonte": "comprasgov", "tipo_identificacao": category, "identificacao": code},
            nome=name or code,
        )

    def provenance(self, entry, column, target):
        file, member, line = entry["origin"]
        key = (self.base_id, self.import_ids[file], member, line, column, target)
        self.add(
            "proveniencias_registros",
            key,
            base_id=self.base_id,
            importacao_id=self.import_ids[file],
            membro_arquivo=member,
            numero_linha=line,
            **{column: target},
        )

    def entries(self, domain):
        return [row for (d, _), row in sorted(self.stage.rows.items()) if d == domain]

    def reject(self, entry, reason):
        self.stage.reject(entry["origin"], reason)

    def run(self):
        for entry in self.entries("processo"):
            v = dict(entry["values"])
            key = entry["key"]
            org = self.identity(
                "orgaos",
                v["orgao_codigo"],
                {"fonte": "comprasgov", "chave_oficial": v.pop("orgao_codigo")},
                nome=v["orgao_nome"],
                cnpj=v.pop("cnpj"),
            )
            modcode = v.pop("modalidade_codigo")
            modname = v.pop("modalidade_nome")
            mod = (
                self.identity(
                    "modalidades",
                    modcode,
                    {"fonte": "comprasgov", "codigo": modcode},
                    nome=modname or modcode,
                )
                if modcode
                else None
            )
            identity = self.identity(
                "processos", key, {"fonte": "comprasgov", "chave_oficial": key}
            )
            uid = self.add(
                "processos_versoes",
                (self.base_id, key),
                base_id=self.base_id,
                processo_id=identity,
                orgao_id=org,
                modalidade_id=mod,
                atributos_origem=entry["raw"],
                **v,
            )
            self.processes[key] = (identity, uid, org)
            if v["numero_controle_pncp"]:
                self.controls[v["numero_controle_pncp"]] = uid
            self.provenance(entry, "processo_versao_id", uid)
        catalogs = {}
        for entry in self.entries("referencia"):
            v = dict(entry["values"])
            key = entry["key"]
            code = v.pop("catalogo")
            description = v["descricao"]
            cat = self.identity(
                "itens_catalogo",
                ("CATMAT", code),
                {"catalogo": "CATMAT", "codigo": code},
                descricao=description,
                codigo_grupo=v.pop("codigo_grupo"),
                codigo_classe=v.pop("codigo_classe"),
                codigo_pdm=v.pop("codigo_pdm"),
            )
            catalogs[v["item"]] = cat
            supplier = self.supplier(v.pop("fornecedor"), v.pop("fornecedor_nome"))
            values = {
                k: v[k]
                for k in [
                    "descricao",
                    "unidade_fornecimento",
                    "sigla_unidade_fornecimento",
                    "capacidade_fornecimento",
                    "sigla_medida",
                    "quantidade",
                    "preco_unitario",
                    "data_compra",
                ]
            }
            uid = self.add(
                "referencias_precos",
                (self.base_id, key),
                base_id=self.base_id,
                catalogo_id=cat,
                fornecedor_id=supplier,
                fonte="comprasgov",
                chave_origem=key,
                id_compra_oficial=v["compra"],
                id_item_oficial=v["id_item_oficial"],
                atributos_origem=entry["raw"],
                **values,
            )
            self.provenance(entry, "referencia_preco_id", uid)
        for entry in self.entries("item"):
            v = dict(entry["values"])
            purchase = v.pop("compra")
            key = entry["key"]
            v.pop("catalogo")
            if purchase not in self.processes:
                self.reject(entry, "PROCESSO_NAO_RESOLVIDO")
                continue
            process, pversion, _ = self.processes[purchase]
            identity = self.identity(
                "itens_processo", (purchase, key), {"processo_id": process, "chave_oficial": key}
            )
            uid = self.add(
                "itens_versoes",
                (self.base_id, key),
                base_id=self.base_id,
                item_id=identity,
                processo_id=process,
                processo_versao_id=pversion,
                catalogo_id=catalogs.get(key),
                atributos_origem=entry["raw"],
                **v,
            )
            self.items[key] = (uid, pversion, purchase)
            self.provenance(entry, "item_versao_id", uid)
        for domain, table, column in [
            ("resultado", "resultados_itens", "resultado_item_id"),
            ("participacao", "participacoes", "participacao_id"),
        ]:
            for entry in self.entries(domain):
                v = dict(entry["values"])
                item = v.pop("item")
                purchase = v.pop("compra")
                if item not in self.items or self.items[item][2] != purchase:
                    self.reject(entry, "ITEM_NAO_RESOLVIDO")
                    continue
                item_id, process_version, _ = self.items[item]
                code = v.pop("fornecedor")
                name = v.pop("fornecedor_nome")
                supplier = self.supplier(code, name)
                values = dict(
                    base_id=self.base_id,
                    item_versao_id=item_id,
                    fornecedor_id=supplier,
                    atributos_origem=entry["raw"],
                )
                if domain == "participacao":
                    values.update(
                        processo_versao_id=process_version,
                        fonte="comprasgov",
                        chave_origem=entry["key"],
                        identificacao_participante=code,
                        nome_participante=name,
                    )
                else:
                    values["fornecedor_nome"] = name
                uid = self.add(table, (self.base_id, entry["key"]), **values, **v)
                self.provenance(entry, column, uid)
        details = {e["key"]: e for e in self.entries("detalhe_contrato")}
        for entry in self.entries("contrato"):
            v = dict(entry["values"])
            purchase = v.pop("compra")
            control = v.pop("controle_compra")
            key = entry["key"]
            if purchase not in self.processes:
                self.reject(entry, "CONTRATO_PROCESSO_NAO_RESOLVIDO")
                continue
            _, pversion, org = self.processes[purchase]
            if control and self.controls.get(control) != pversion:
                self.reject(entry, "CHAVES_CONTRATO_COMPRA_DIVERGENTES")
                continue
            supplier = self.supplier(v.pop("fornecedor"), v["fornecedor_nome"])
            identity = self.identity(
                "contratos", key, {"fonte": "comprasgov", "chave_oficial": key}
            )
            detail = details.get(key)
            if detail and detail["values"]["controle_compra"] != control:
                self.reject(detail, "CHAVES_CONTRATUAIS_DIVERGENTES")
                detail = None
            uid = self.add(
                "contratos_versoes",
                (self.base_id, key),
                base_id=self.base_id,
                contrato_id=identity,
                orgao_id=org,
                fornecedor_id=supplier,
                data_assinatura=detail["values"]["data_assinatura"] if detail else None,
                atributos_origem=entry["raw"],
                **v,
            )
            self.contracts[key] = uid
            link = self.add(
                "contratos_processos",
                (self.base_id, key, purchase),
                base_id=self.base_id,
                contrato_versao_id=uid,
                processo_versao_id=pversion,
                tipo_chave_vinculo="idCompra",
                chave_vinculo=purchase,
            )
            self.provenance(entry, "contrato_versao_id", uid)
            self.provenance(entry, "contrato_processo_id", link)
            if detail:
                self.provenance(detail, "contrato_versao_id", uid)
        for entry in self.entries("detalhe_contrato"):
            if entry["key"] not in self.contracts:
                self.reject(entry, "CONTRATO_NAO_RESOLVIDO")
        for entry in self.entries("documento"):
            v = dict(entry["values"])
            parent_kind = v.pop("parent_kind")
            control = v.pop("parent_control")
            parent = (
                self.controls.get(control)
                if parent_kind == "compras"
                else self.contracts.get(control)
            )
            if not parent:
                self.reject(entry, "DOCUMENTO_PAI_NAO_RESOLVIDO")
                continue
            column = "processo_versao_id" if parent_kind == "compras" else "contrato_versao_id"
            uid = self.add(
                "documentos",
                (self.base_id, entry["key"]),
                base_id=self.base_id,
                fonte="pncp",
                chave_origem=entry["key"],
                atributos_origem=entry["raw"],
                **{column: parent},
                **v,
            )
            self.provenance(entry, "documento_id", uid)
        return {
            name: sorted(rows.values(), key=lambda r: str(r["id"]))
            for name, rows in self.data.items()
        }
