"""Objetos privados em S3/R2; não cria buckets nem altera ACLs."""

import base64
import hashlib
from tempfile import TemporaryFile
from typing import BinaryIO

from licita_shared.storage.base import StoredObject


class S3ObjectStorage:
    def __init__(self, bucket: str, client):
        self.bucket, self.client = bucket, client

    def put(self, key: str, source: BinaryIO) -> StoredObject:
        sha, md5, size = hashlib.sha256(), hashlib.md5(usedforsecurity=False), 0
        with TemporaryFile() as staged:
            while chunk := source.read(1024 * 1024):
                staged.write(chunk)
                sha.update(chunk)
                md5.update(chunk)
                size += len(chunk)
            staged.seek(0)
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=staged,
                ContentLength=size,
                ContentMD5=base64.b64encode(md5.digest()).decode(),
                Metadata={"sha256": sha.hexdigest()},
            )
        result = self.client.head_object(Bucket=self.bucket, Key=key)
        if (
            result["ContentLength"] != size
            or result.get("Metadata", {}).get("sha256") != sha.hexdigest()
        ):
            raise OSError("Objeto remoto não confirmou tamanho e metadados esperados")
        return StoredObject(key, size, sha.hexdigest())

    def open(self, key: str) -> BinaryIO:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"]
