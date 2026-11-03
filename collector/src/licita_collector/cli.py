"""Comandos operacionais; erros não expõem URLs de banco ou credenciais."""

import argparse
import json
from importlib.metadata import version
from uuid import UUID

from sqlalchemy import create_engine

from licita_collector.config import Settings
from licita_collector.repository import Repository
from licita_collector.service import Collector, storage
from licita_collector.source import FILES, Scope, month, months


def main():
    parser = argparse.ArgumentParser(description="Coleta versionada do Compras.gov.br")
    parser.add_argument("--version", action="version", version=version("licita-collector"))
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("coletar")
    collect.add_argument("--inicio", required=True, type=month)
    collect.add_argument("--fim", required=True, type=month)
    collect.add_argument(
        "--arquivos",
        nargs="+",
        choices=list(FILES),
        default=["compra", "compra_item", "item_resultado", "material"],
    )
    complement = commands.add_parser("complementar")
    complement.add_argument("--competencia", required=True, type=month)
    complement.add_argument("--material-arquivo", required=True, type=UUID)
    complement.add_argument("--catalogo", required=True)
    resume = commands.add_parser("retomar")
    resume.add_argument("--execucao-id", required=True, type=UUID)
    process = commands.add_parser("reprocessar")
    process.add_argument("--arquivo-id", required=True, type=UUID)
    process.add_argument("--extrair", action="store_true")
    args = parser.parse_args()
    engine = None
    try:
        settings = Settings()
        engine = create_engine(
            settings.collector_database_url.get_secret_value(),
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
        repository = Repository(engine)
        service = Collector(settings, repository, storage(settings))
        if args.command == "complementar":
            from licita_collector.complement import complement, selected_purchases

            purchases = selected_purchases(
                repository, service.objects, args.material_arquivo, args.catalogo
            )
            if not purchases:
                raise ValueError("Recorte sem compras; confira o catálogo")
            result = complement(service, purchases, args.competencia)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            return int(bool(result["falhas"]))
        if args.command == "coletar":
            scopes = [
                Scope(kind, date)
                for date in months(args.inicio, args.fim)
                for kind in dict.fromkeys(args.arquivos)
            ]
            failed = False
            for scope in scopes:
                try:
                    result = service.collect(scope)
                except Exception as error:
                    failed = True
                    result = {
                        "status": "falhou",
                        "codigo": getattr(error, "code", "FALHA_INTERNA"),
                        "tipo": type(error).__name__,
                        "execucao_id": getattr(error, "execucao_id", None),
                    }
                print(
                    json.dumps({"arquivo": scope.filename, **result}, ensure_ascii=False),
                    flush=True,
                )
            return int(failed)
        if args.command == "retomar":
            result = service.collect(repository.execution(args.execucao_id), args.execucao_id)
        else:
            result = service.reprocess(args.arquivo_id, unpack=args.extrair)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "falhou",
                    "codigo": getattr(error, "code", "FALHA_INTERNA"),
                    "tipo": type(error).__name__,
                    "execucao_id": getattr(error, "execucao_id", None),
                }
            ),
            flush=True,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()
