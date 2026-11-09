"""Instalação reproduzível da equipe usando os pipelines existentes."""

import argparse
import fcntl
import json
import re
import sys
import tarfile
import threading
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from uuid import UUID

from licita_ml.diagnostics import checksum

ROOT = Path(__file__).resolve().parents[3]


def save(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n")
    temporary.replace(path)


@contextmanager
def locked(folder):
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".equipe.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Já existe um script da equipe usando esta pasta.") from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def inputs(root, manifest):
    """Recusa entradas ausentes ou divergentes antes de modificar o banco."""
    config = json.loads(manifest.read_text())
    if config.get("versao") != 1 or not config.get("arquivos"):
        raise ValueError("Manifesto de entradas inválido.")
    rows, seen = [], set()
    for entry in config["arquivos"]:
        relative = Path(entry["arquivo"])
        path = (root / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(root.resolve()):
            raise ValueError("Arquivo fora da pasta de dados.")
        if (
            len(relative.parts) != 2
            or not re.fullmatch(
                r"(compra|compra_item|item_resultado|material)_\d{4}_\d{2}\.csv\.zip",
                relative.name,
            )
            or relative.parent.name
            != relative.name.removesuffix(".csv.zip").rsplit("_", 2)[1]
            + "-"
            + relative.name.removesuffix(".csv.zip").rsplit("_", 2)[2]
        ):
            raise ValueError("Use AAAA-MM/modulo_AAAA_MM.csv.zip no manifesto.")
        if entry["arquivo"] in seen:
            raise ValueError("Arquivo repetido no manifesto.")
        seen.add(entry["arquivo"])
        if not path.is_file():
            raise ValueError(
                f"Falta {relative}. Confira datasets/equipe ou o caminho informado em --dados."
            )
        if path.stat().st_size != entry["bytes"] or checksum(path) != entry["sha256"]:
            raise ValueError(f"Arquivo divergente: {relative}. Não será usado.")
        rows.append(path)
    return rows


def bundle(paths, root, target):
    """Pacote compartilhável contém só os ZIPs conferidos; nenhum segredo/modelo."""
    target = target.resolve()
    if target.suffix != ".tar" or target in paths:
        raise ValueError("Escolha um arquivo de saída .tar separado dos ZIPs de entrada.")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tar.tmp")
    try:
        with tarfile.open(temporary, "w") as archive:
            for path in paths:
                name = Path("entrada_equipe") / path.relative_to(root.resolve())
                archive.add(path, arcname=str(name), recursive=False)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    target.with_suffix(".tar.sha256").write_text(checksum(target) + "  " + target.name + "\n")
    print(f"Pacote pronto para compartilhar: {target}")


class Progress:
    """Percentual real de grupos concluídos; tempo estimado só após a primeira entrega."""

    def __init__(self, stream=None):
        self.stream = stream or sys.stdout
        self.started = time.monotonic()
        self.completed, self.total = 0, 0
        self.stop = threading.Event()
        self.thread = None

    def render(self):
        elapsed = time.monotonic() - self.started
        ratio = self.completed / self.total if self.total else 0
        bar = "#" * int(ratio * 25) + "-" * (25 - int(ratio * 25))
        remaining = (
            elapsed * (self.total - self.completed) / self.completed if self.completed else None
        )
        eta = f"{remaining / 60:.1f} min (estimativa)" if remaining is not None else "calculando"
        text = (
            f"Treinamento [{bar}] {ratio:.1%} | {self.completed}/{self.total} grupos"
            f" | faltam {1 - ratio:.1%} | decorrido {elapsed / 60:.1f} min | restante: {eta}"
        )
        print(text, file=self.stream, flush=True)

    def update(self, completed, total):
        self.completed, self.total = completed, total
        self.render()

    def __enter__(self):
        if self.stream.isatty():
            self.thread = threading.Thread(target=self.refresh, daemon=True)
            self.thread.start()
        return self

    def refresh(self):
        while not self.stop.wait(15):
            self.render()

    def __exit__(self, *_):
        self.stop.set()
        if self.thread:
            self.thread.join()


def register(paths, settings, repo, objects):
    """Registra ZIP local com proveniência explícita, sem fingir download HTTP."""
    from licita_collector.archive import validate
    from licita_collector.http import Download
    from licita_collector.source import Scope

    class LocalScope(Scope):
        @property
        def parameters(self):
            return {**super().parameters, "modo": "importacao_zip_local"}

    ids = []
    for path in paths:
        kind, year, month = path.name.removesuffix(".csv.zip").rsplit("_", 2)
        scope = LocalScope(kind, date(int(year), int(month), 1))
        info = validate(path, settings)
        key = (
            f"raw/{scope.source}/{scope.module}/{scope.competence:%Y/%m}/"
            f"{info['sha256']}/{scope.filename}"
        )
        with repo.locked(scope) as connection:
            run, _ = repo.start(connection, scope)
            try:
                with path.open("rb") as stream:
                    stored = objects.put(key, stream)
                if stored.sha256 != info["sha256"] or stored.size_bytes != info["bytes"]:
                    raise ValueError("Armazenamento diverge do ZIP local.")
                identifier, _ = repo.complete(
                    connection,
                    run,
                    scope,
                    path.as_uri(),
                    Download(path, path.as_uri(), None),
                    info,
                    key,
                )
                ids.append(identifier)
            except Exception as error:
                repo.fail(connection, run, error)
                raise
        print(f"Registrado: {path.name}", flush=True)
    return ids


def database(settings, attr):
    from sqlalchemy import create_engine

    engine = create_engine(
        getattr(settings, attr).get_secret_value(),
        hide_parameters=True,
        connect_args={"connect_timeout": 10},
    )
    try:
        with engine.connect() as cn:
            from sqlalchemy import text

            for table in ("arquivos_coletados", "publicacoes_analise", "sinteses_processo_modelo"):
                if cn.scalar(text("SELECT to_regclass(:table)"), {"table": table}) is None:
                    raise ValueError("Aplique as migrações do README antes de executar.")
    except Exception:
        engine.dispose()
        raise
    return engine


def populate(args):
    from licita_collector.config import Settings as CollectorSettings
    from licita_collector.repository import Repository as CollectorRepository
    from licita_shared.storage.factory import storage

    from licita_ml.catalog.pipeline import prepare as catalog
    from licita_ml.config import Settings
    from licita_ml.grouped import operational, temporal
    from licita_ml.organized.pipeline import MODULES
    from licita_ml.organized.pipeline import prepare as organize
    from licita_ml.repository import Repository

    print("Conferindo arquivos e hashes...", flush=True)
    paths = inputs(args.dados, args.manifesto)
    if getattr(args, "empacotar", None):
        bundle(paths, args.dados, args.empacotar)
        return
    if args.conferir:
        print(f"{len(paths)} ZIPs conferidos. Banco e modelos não foram alterados.")
        return
    collector_settings, settings = CollectorSettings(), Settings()
    # Conferir os dois logins antes das etapas mais demoradas.
    collector_engine = database(collector_settings, "collector_database_url")
    try:
        engine = database(settings, "processing_database_url")
    except Exception:
        collector_engine.dispose()
        raise
    try:
        from sqlalchemy.engine import make_url

        collector_url = make_url(collector_settings.collector_database_url.get_secret_value())
        processing_url = make_url(settings.processing_database_url.get_secret_value())
        if (collector_url.host, collector_url.port, collector_url.database) != (
            processing_url.host,
            processing_url.port,
            processing_url.database,
        ):
            raise ValueError("Coleta e processamento devem apontar para o mesmo banco.")
        if (collector_settings.storage_backend, collector_settings.storage_root.resolve()) != (
            settings.storage_backend,
            settings.storage_root.resolve(),
        ):
            raise ValueError("Coleta e processamento devem usar o mesmo armazenamento.")
        print("1/5 Organizando os CSVs (retomável)...", flush=True)
        folders = sorted(
            {
                p.parent
                for p in paths
                if all(
                    (p.parent / f"{module}_{p.parent.name.replace('-', '_')}.csv.zip") in paths
                    for module in MODULES
                )
            }
        )
        if not folders:
            raise ValueError("É necessário pelo menos um mês com os quatro módulos completos.")
        included = {p for p in paths if p.parent in folders}
        organized = organize(folders, args.saida / "organizados", sorted(set(paths) - included))
        print("2/5 Catalogando itens e unidades...", flush=True)
        cat = catalog(Path(organized["diretorio"]), args.saida / "catalogo")
        print("3/5 Preparando partições temporais (sem treinar)...", flush=True)
        prep = temporal.prepare(
            Path(organized["diretorio"]),
            Path(cat["diretorio"]),
            args.saida / "preparacao",
        )
        if not prep["manifesto"]["grupos_selecionados"]:
            raise ValueError("Nenhum grupo elegível. Confira os dados e o relatório de triagem.")
        policy = prep["manifesto"]["configuracao"]["politica"]
        begin, end = policy["application_start"][:7], policy["application_end"][:7]
        application = [p for p in paths if begin <= p.parent.name <= end]
        print("4/5 Registrando os ZIPs operacionais no banco...", flush=True)
        ids = register(
            application,
            collector_settings,
            CollectorRepository(collector_engine),
            storage(collector_settings),
        )
        print("5/5 Importando os itens operacionais...", flush=True)
        result = operational.run(
            Path(prep["diretorio"]),
            settings,
            Repository(engine),
            storage(settings),
            ids,
        )
        save(
            args.saida / "estado.json",
            {
                "versao": 1,
                "base_id": result["base_id"],
                "preparacao": prep["diretorio"],
                "preparacao_sha256": checksum(Path(prep["diretorio"]) / "manifesto.json"),
                "manifesto_entradas_sha256": checksum(args.manifesto),
                "importacao": result,
            },
        )
        print(f"Banco populado. Base: {result['base_id']}. Execute treinar_e_analisar.py.")
    finally:
        collector_engine.dispose()
        engine.dispose()


def train(args):
    from licita_shared.storage.factory import storage

    from licita_ml.config import Settings
    from licita_ml.grouped import inference, temporal, training
    from licita_ml.inference.pipeline import InferencePipeline
    from licita_ml.repository import Repository

    state_path = args.saida / "estado.json"
    if not state_path.exists():
        raise ValueError("Execute popular_banco.py primeiro nesta pasta de saída.")
    state = json.loads(state_path.read_text())
    prep = Path(state["preparacao"])
    if checksum(prep / "manifesto.json") != state["preparacao_sha256"]:
        raise ValueError("Preparação alterada. Execute popular_banco.py novamente.")
    temporal.validate(prep)
    settings = Settings()
    engine = database(settings, "processing_database_url")
    try:
        print("1/3 Treinando Isolation Forest e Autoencoder. Pode demorar.", flush=True)
        print("Progresso por grupos em lotes; lotes incompletos reiniciam após interrupção.")
        with Progress() as progress:
            fitted = training.run(
                prep,
                args.saida / "treino",
                args.saida / "revisoes",
                args.processos,
                progress=progress.update,
            )
        save(args.saida / "treino.json", fitted)
        print("2/3 Analisando os itens do banco...", flush=True)
        pipeline = InferencePipeline(settings, Repository(engine), storage(settings))
        result = inference.infer(
            pipeline,
            Path(fitted["diretorio"]),
            UUID(state["base_id"]),
            args.resultado_ate,
        )
        save(args.saida / "inferencia.json", result)
        print("3/3 Publicando a análise experimental para a aplicação...", flush=True)
        published = pipeline.publish(UUID(result["execucao_id"]))
        save(args.saida / "publicacao.json", published)
        print(f"Concluído. Base: {state['base_id']} | Execução: {result['execucao_id']}")
        print("Agora inicie o backend e o frontend. Scores são sinais de anomalia estatística.")
    finally:
        engine.dispose()


def main(command):
    parser = argparse.ArgumentParser(
        description=(
            "Popular banco com os ZIPs da equipe."
            if command == "popular"
            else "Treinar, analisar e publicar Scores experimentais."
        )
    )
    parser.add_argument("--saida", type=Path, default=Path("data/equipe"))
    if command == "popular":
        parser.add_argument("--dados", type=Path, default=Path("datasets/equipe"))
        parser.add_argument("--manifesto", type=Path, default=Path("config/equipe/dados.json"))
        parser.add_argument(
            "--conferir", action="store_true", help="Somente conferir ZIPs e hashes"
        )
        parser.add_argument(
            "--empacotar",
            type=Path,
            metavar="ARQUIVO.tar",
            help="Conferir e empacotar ZIPs para compartilhar, sem acessar o banco",
        )
    else:
        parser.add_argument("--processos", type=int, choices=(1, 2, 3), default=2)
        parser.add_argument("--resultado-ate", type=date.fromisoformat, default=date(2026, 10, 31))
    args = parser.parse_args()
    if Path.cwd().resolve() != ROOT:
        parser.error(f"Execute na raiz do repositório: {ROOT}")
    args.saida = args.saida.resolve()
    try:
        with locked(args.saida):
            (populate if command == "popular" else train)(args)
    except KeyboardInterrupt:
        print("\nInterrompido. Repita o comando para reutilizar etapas completas.", file=sys.stderr)
        return 130
    except Exception as error:
        # Não imprimir URLs de conexão ou repr de erros SQL com credenciais.
        print(
            f"Falha ({type(error).__name__}). Etapas completas foram preservadas.", file=sys.stderr
        )
        if isinstance(error, (ValueError, FileNotFoundError)):
            print(str(error), file=sys.stderr)
        else:
            print("Confira .env, banco/migrações, espaço em disco e dependências.", file=sys.stderr)
        return 1
    return 0
