"""Adaptador local com escrita atômica; diretório privado controlado pela aplicação."""

import hashlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO

from licita_shared.storage.base import StoredObject


class LocalObjectStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        if not key or "\\" in key or any(part in ("", ".", "..") for part in key.split("/")):
            raise ValueError("Chave de objeto inválida")
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root) or path == self.root:
            raise ValueError("Chave fora da raiz de armazenamento")
        return path

    def put(self, key: str, source: BinaryIO) -> StoredObject:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            digest, size = hashlib.sha256(), 0
            with NamedTemporaryFile(dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(path)
            return StoredObject(key, size, digest.hexdigest())
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def open(self, key: str) -> BinaryIO:
        return self._path(key).open("rb")
