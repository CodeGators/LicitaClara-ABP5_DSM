"""Publicação atômica no PostgreSQL; artefatos imutáveis anteriores ao commit são retomáveis."""

import hashlib
import json
import resource
import time
from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa

from licita_ml.artifacts import publish
from licita_ml.build import Builder
from licita_ml.readers import kind_of
from licita_ml.repository import identifier
from licita_ml.staging import Stage, encode

VERSION = "preparacao-v1"
ORDER = [
    "orgaos",
    "fornecedores",
    "modalidades",
    "itens_catalogo",
    "processos",
    "itens_processo",
    "contratos",
    "processos_versoes",
    "itens_versoes",
    "referencias_precos",
    "resultados_itens",
    "participacoes",
    "contratos_versoes",
    "contratos_processos",
    "documentos",
    "proveniencias_registros",
]


def code_hash():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class Pipeline:
    def __init__(self, settings, repository, objects):
        self.settings, self.repo, self.objects = settings, repository, objects

    def run(self, start, end, catalog, ids=None, fail_after=None, selected_items=None):
        catalogs = [catalog] if isinstance(catalog, str) else sorted(set(catalog))
        catalog = catalog if isinstance(catalog, str) else catalogs
        if start > end or not catalogs or any(not c.isdigit() for c in catalogs):
            raise ValueError("Período ou CATMAT inválido")
        started = time.monotonic()
        with self.repo.locked() as connection:
            files = self.repo.sources(connection, start, end, ids)
            if not {"material", "compra", "compra_item", "item_resultado"}.issubset(
                {kind_of(f) for f in files}
            ):
                raise ValueError("Faltam arquivos obrigatórios do recorte inicial")
            inputs = [
                {
                    "id": str(f["id"]),
                    "fonte": f["fonte"],
                    "modulo": f["modulo"],
                    "competencia": str(f["competencia"]),
                    "sha256": f["sha256"],
                    "bytes": f["tamanho_bytes"],
                    "chave": f["chave_objeto"],
                }
                for f in files
            ]
            config = {
                "versao": VERSION,
                "codigo_sha256": code_hash(),
                "esquema_leitor": "csv-v1/json-v1",
                "inicio": str(start),
                "fim": str(end),
                "catalogo": catalog,
                "fontes": inputs,
            }
            if selected_items is not None:
                config["itens_selecionados"] = sorted(set(selected_items))
            fingerprint = hashlib.sha256(encode(config).encode()).hexdigest()
            base_id = identifier("versoes_base", fingerprint)
            table = self.repo.tables["versoes_base"]
            existing = (
                connection.execute(sa.select(table).where(table.c.id == base_id))
                .mappings()
                .one_or_none()
            )
            connection.commit()
            if existing:
                with self.objects.open(existing["chave_manifesto"]) as source:
                    raw = source.read()
                if hashlib.sha256(raw).hexdigest() != existing["sha256_manifesto"]:
                    raise ValueError("Manifesto armazenado diverge do banco")
                recorded = json.loads(raw)
                for artifact in recorded["arquivos_parquet"] + [recorded["rejeicoes"]]:
                    with self.objects.open(artifact["chave"]) as source:
                        if hashlib.file_digest(source, "sha256").hexdigest() != artifact["sha256"]:
                            raise ValueError("Parquet armazenado diverge do manifesto")
                return {
                    "status": existing["status"],
                    "base_id": str(base_id),
                    "reutilizada": True,
                    "manifesto": existing["chave_manifesto"],
                    "duracao_segundos": round(time.monotonic() - started, 3),
                }
            stage = Stage()
            import_version = f"{VERSION}:{fingerprint}"
            import_ids = {
                str(f["id"]): identifier("importacoes", (f["id"], import_version)) for f in files
            }
            # Início operacional separado; falha de domínio não deixa snapshots pela metade.
            imports = self.repo.tables["importacoes"]
            with connection.begin():
                self.repo.batch(
                    connection,
                    "importacoes",
                    [
                        {
                            "id": import_ids[str(f["id"])],
                            "arquivo_id": f["id"],
                            "versao_importador": import_version,
                            "status": "executando",
                        }
                        for f in files
                    ],
                    self.settings.processing_batch_size,
                )
                connection.execute(
                    imports.update()
                    .where(imports.c.id.in_(import_ids.values()))
                    .values(status="executando", concluido_em=None)
                )
            committed = False
            try:
                selected, purchases = stage.resolve(
                    self.objects, files, self.settings, start, end, catalog, selected_items
                )
                before = self.repo.sizes(connection)
                builder = Builder(self.repo, connection, stage, base_id, import_ids)
                data = builder.run()
                counts = stage.reconcile()
                connection.commit()
                quality = {
                    "itens_referencia": len(selected),
                    "compras_referencia": len(purchases),
                    "processos_resolvidos": len(builder.processes),
                    "itens_resolvidos": len(builder.items),
                    "participantes_cobertura": "apenas_itens_homologados_na_fonte",
                    "anexos": "metadados_sem_binarios",
                    "assinatura": "somente_quando_recebida_do_PNCP",
                    "historico_participantes_completo": False,
                    "referencias_sem_processo_pncp": len(purchases - set(builder.processes)),
                    "itens_referencia_nao_resolvidos": len(selected - set(builder.items)),
                    "referencias_sem_unidade": sum(
                        not e["values"]["sigla_unidade_fornecimento"]
                        for e in stage.rows.values()
                        if e["domain"] == "referencia"
                    ),
                }
                manifest = {
                    **config,
                    "base_id": str(base_id),
                    "fingerprint": fingerprint,
                    "recorte": quality,
                    "contagens_origem": {key: dict(value) for key, value in counts.items()},
                    "politica_deduplicacao": {
                        "precedencia": (
                            "maior timestamp da origem; em empate API sobre CSV; "
                            "empate divergente da mesma prioridade rejeita grupo"
                        ),
                        "referencias_chave": "id_compra/id_item_compra/ni_fornecedor/forma",
                        "resultados_chave": "id_compra_item/ni_fornecedor/sequencial_resultado",
                        "propostas_chave": "id oficial; nunca apenas participante/item",
                    },
                    "limitacoes": [
                        "Unidades não são imputadas ou convertidas por similaridade textual.",
                        (
                            "Período delimita pesquisa de preços; "
                            "processos relacionados podem ter publicação anterior."
                        ),
                        "Ausência de participantes/documentos não é zero; conferir cobertura.",
                        "Não há scores ou modelo treinado.",
                    ],
                }
                catalog_key = (
                    catalog
                    if isinstance(catalog, str)
                    else hashlib.sha256(encode(catalogs).encode()).hexdigest()[:16]
                )
                prefix = f"datasets/base={fingerprint}/catalogo={catalog_key}"
                stored, manifest = publish(self.objects, self.repo, data, stage, prefix, manifest)
                with connection.begin():
                    self.repo.batch(
                        connection,
                        "versoes_base",
                        [
                            {
                                "id": base_id,
                                "versao": fingerprint,
                                "versao_transformador": VERSION,
                                "versao_codigo": config["codigo_sha256"],
                                "chave_manifesto": stored.key,
                                "sha256_manifesto": stored.sha256,
                                "periodo_inicio": start,
                                "periodo_fim": end,
                                "status": "preparando",
                                "recorte": {"catalogo": "CATMAT", "codigo": catalog},
                                "qualidade": quality,
                            }
                        ],
                    )
                    self.repo.batch(
                        connection,
                        "base_importacoes",
                        [{"base_id": base_id, "importacao_id": uid} for uid in import_ids.values()],
                    )
                    for name in ORDER:
                        self.repo.batch(
                            connection,
                            name,
                            data.get(name, []),
                            self.settings.processing_batch_size,
                        )
                        if fail_after == name:
                            raise RuntimeError("Falha injetada de integração")
                    for name, rows in data.items():
                        t = self.repo.tables[name]
                        if "base_id" in t.c:
                            actual = connection.scalar(
                                sa.select(sa.func.count())
                                .select_from(t)
                                .where(t.c.base_id == base_id)
                            )
                            if actual != len(rows):
                                raise ValueError("Contagem importada diverge do lote preparado")
                    for file_id, values in counts.items():
                        connection.execute(
                            imports.update()
                            .where(imports.c.id == import_ids[file_id])
                            .values(
                                status="parcial" if values["rejeitados"] else "concluido",
                                aceitos=values["aceitos"],
                                rejeitados=values["rejeitados"],
                                diagnostico=dict(values),
                                concluido_em=datetime.now(timezone.utc),
                            )
                        )
                    connection.execute(
                        table.update().where(table.c.id == base_id).values(status="validada")
                    )
                committed = True
                after = self.repo.sizes(connection)
                report = {
                    "status": "validada",
                    "base_id": str(base_id),
                    "reutilizada": False,
                    "manifesto": stored.key,
                    "sha256_manifesto": stored.sha256,
                    "contagens": {name: len(rows) for name, rows in data.items()},
                    "origem": {k: dict(v) for k, v in counts.items()},
                    "qualidade": quality,
                    "duracao_segundos": round(time.monotonic() - started, 3),
                    "memoria_pico_mib": round(
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2
                    ),
                    "bytes_fontes": sum(f["tamanho_bytes"] for f in files),
                    "bytes_manifesto": stored.size_bytes,
                    "bytes_rejeicoes": manifest["rejeicoes"]["bytes"],
                    "bytes_parquet": sum(a["bytes"] for a in manifest["arquivos_parquet"]),
                    "postgres_bytes_com_indices_antes": before,
                    "postgres_bytes_com_indices_depois": after,
                }
                self.settings.processing_work_dir.mkdir(parents=True, exist_ok=True)
                path = self.settings.processing_work_dir / (fingerprint + ".execucao.json")
                path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
                return report
            except Exception as error:
                connection.rollback()
                if committed:
                    raise
                with connection.begin():
                    connection.execute(
                        imports.update()
                        .where(imports.c.id.in_(import_ids.values()))
                        .values(
                            status="falhou",
                            diagnostico={
                                "codigo": getattr(error, "code", "FALHA_PREPARACAO"),
                                "diagnostico": getattr(error, "diagnostic", None),
                                "tipo": type(error).__name__,
                            },
                            concluido_em=datetime.now(timezone.utc),
                        )
                    )
                raise
