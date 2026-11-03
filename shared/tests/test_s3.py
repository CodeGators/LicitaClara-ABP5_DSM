import hashlib
import io

import pytest
from licita_shared.storage.s3 import S3ObjectStorage


class Client:
    def put_object(self, **values):
        self.body = values["Body"].read()
        self.values = values

    def head_object(self, **values):
        return {"ContentLength": len(self.body), "Metadata": self.values["Metadata"]}

    def get_object(self, **values):
        return {"Body": io.BytesIO(self.body)}


def test_s3_put_confirms_metadata_and_reads_same_bytes():
    client = Client()
    store = S3ObjectStorage("private", client)
    result = store.put("raw/test.zip", io.BytesIO(b"content"))
    assert result.sha256 == hashlib.sha256(b"content").hexdigest()
    assert client.values["ContentMD5"]
    with store.open(result.key) as stream:
        assert stream.read() == b"content"
    client.head_object = lambda **_: {"ContentLength": 0}
    with pytest.raises(OSError):
        store.put("raw/test.zip", io.BytesIO(b"content"))
