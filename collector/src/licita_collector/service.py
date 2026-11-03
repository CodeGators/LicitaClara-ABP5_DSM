"""Orquestra aquisição e registro; a importação de dados pertence à próxima etapa."""

import shutil
import tempfile
from pathlib import Path

from licita_shared.storage.factory import storage  # noqa: F401

from licita_collector.archive import extract, validate
from licita_collector.errors import CollectionError, InvalidArchive
from licita_collector.http import Downloader, HttpClient
from licita_collector.source import BASE_URL, discover


class Collector:
    def __init__(self, settings, repository, objects, http=None, base_url=BASE_URL):
        self.settings, self.repository, self.objects = settings, repository, objects
        self.http = http or HttpClient(settings)
        self.base_url = base_url

    def collect(self, scope, run_id=None):
        completed = False
        with self.repository.locked(scope) as connection:
            identifier, completed = self.repository.start(connection, scope, run_id)
            if not completed:
                folder = self.settings.collector_temp_dir / str(identifier)
                try:
                    if getattr(scope, "is_json", False):
                        from licita_collector.api import acquire

                        download, info, url = acquire(scope, folder, self.http)
                    else:
                        url = discover(scope, self.http, self.base_url)
                        download = Downloader(self.settings, self.http).fetch(url, folder)
                        info = validate(download.path, self.settings)
                    key = (
                        f"raw/{scope.source}/{scope.module}/{scope.competence:%Y/%m}/"
                        f"{info['sha256']}/{scope.filename}"
                    )
                    with download.path.open("rb") as source:
                        stored = self.objects.put(key, source)
                    if stored.sha256 != info["sha256"] or stored.size_bytes != info["bytes"]:
                        raise CollectionError("Armazenamento não confirmou a integridade")
                    artifact_id, reused = self.repository.complete(
                        connection, identifier, scope, url, download, info, key
                    )
                    shutil.rmtree(folder, ignore_errors=True)
                    return {
                        "status": "concluido",
                        "execucao_id": str(identifier),
                        "arquivo_id": str(artifact_id),
                        "reutilizado": reused,
                        **info,
                    }
                except Exception as error:
                    if isinstance(error, InvalidArchive) and folder.exists():
                        for path in folder.iterdir():
                            path.unlink()
                    error.execucao_id = str(identifier)
                    self.repository.fail(connection, identifier, error)
                    raise
        # A conexão do lock foi devolvida antes de abrir outra conexão.
        result = self.reprocess(run_id=identifier)
        return {**result, "execucao_id": str(identifier), "reutilizado": True}

    def reprocess(self, identifier=None, run_id=None, unpack=False):
        row = self.repository.artifact(identifier, run_id)
        self.settings.collector_temp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.settings.collector_temp_dir) as folder:
            path = Path(folder) / "archive.zip"
            size = 0
            with self.objects.open(row["chave_objeto"]) as source, path.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.settings.collector_max_download_bytes:
                        raise InvalidArchive("Objeto excede limite de download")
                    target.write(chunk)
            if row["chave_objeto"].endswith(".json"):
                from licita_collector.api import validate_json

                info = validate_json(path)
                if unpack:
                    raise CollectionError("JSON não requer extração de ZIP")
            else:
                info = validate(path, self.settings)
            if info["sha256"] != row["sha256"] or info["bytes"] != row["tamanho_bytes"]:
                raise InvalidArchive("Objeto diverge do registro de coleta")
            result = {"status": "validado", "arquivo_id": str(row["id"]), **info}
            if unpack:
                target = self.settings.collector_extract_dir / str(row["id"])
                extract(path, target, self.settings)
                result["extracao"] = str(target)
            return result
