"""Validação CRC e extração confinada, sem confiar em nomes/tamanhos do ZIP."""

import hashlib
import os
import shutil
import stat
from pathlib import Path, PurePosixPath
from tempfile import mkdtemp
from zipfile import BadZipFile, ZipFile

from licita_collector.errors import InvalidArchive


def members(archive, settings):
    entries = archive.infolist()
    if not entries or len(entries) > settings.collector_max_members:
        raise InvalidArchive("Quantidade de membros inválida")
    total, names = 0, set()
    for info in entries:
        path = PurePosixPath(info.filename)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in info.filename
            or ":" in info.filename
            or not info.filename
            or info.filename in names
            or stat.S_ISLNK(info.external_attr >> 16)
            or info.flag_bits & 1
        ):
            raise InvalidArchive("Caminho, duplicação ou tipo de membro inválido")
        names.add(info.filename)
        if info.is_dir():
            continue
        if path.suffix.lower() != ".csv":
            raise InvalidArchive("O pacote deve conter somente arquivos CSV")
        total += info.file_size
        if (
            total > settings.collector_max_uncompressed_bytes
            or info.file_size / max(info.compress_size, 1)
            > settings.collector_max_compression_ratio
        ):
            raise InvalidArchive("Limites de expansão do ZIP excedidos")
        yield info


def validate(path: Path, settings):
    try:
        with path.open("rb") as stream:
            if stream.read(2) != b"PK":
                raise InvalidArchive("Conteúdo recebido não é ZIP")
            stream.seek(0)
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        actual, count = 0, 0
        with ZipFile(path) as archive:
            for info in members(archive, settings):
                count += 1
                with archive.open(info) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        actual += len(chunk)
                        if actual > settings.collector_max_uncompressed_bytes:
                            raise InvalidArchive("Tamanho descompactado excedido")
        if count == 0:
            raise InvalidArchive("ZIP sem CSV")
        return {
            "sha256": sha,
            "bytes": path.stat().st_size,
            "membros": count,
            "bytes_descompactados": actual,
        }
    except (BadZipFile, RuntimeError, EOFError, NotImplementedError) as error:
        raise InvalidArchive("ZIP corrompido ou não suportado") from error


def extract(path: Path, target: Path, settings):
    validate(path, settings)
    if target.exists():
        raise InvalidArchive("Destino já existe; conteúdo anterior foi preservado")
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(mkdtemp(prefix=".extract-", dir=target.parent))
    try:
        with ZipFile(path) as archive:
            for info in members(archive, settings):
                dest = temp / info.filename
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, dest.open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
        os.rename(temp, target)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return target
