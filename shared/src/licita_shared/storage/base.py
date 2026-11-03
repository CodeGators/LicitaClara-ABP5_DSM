"""Contrato de objetos; chaves são relativas, nunca URLs ou caminhos do cliente."""

from dataclasses import dataclass
from typing import BinaryIO, Protocol


@dataclass(frozen=True)
class StoredObject:
    key: str
    size_bytes: int
    sha256: str


class ObjectStorage(Protocol):
    def put(self, key: str, source: BinaryIO) -> StoredObject: ...

    def open(self, key: str) -> BinaryIO: ...
