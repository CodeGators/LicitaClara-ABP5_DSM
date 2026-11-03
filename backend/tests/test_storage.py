import hashlib
from io import BytesIO

import pytest
from licita_backend.storage.local import LocalObjectStorage


def test_local_storage_round_trip_and_atomic_failure(tmp_path):
    storage = LocalObjectStorage(tmp_path / "objects")
    info = storage.put("raw/test/file.bin", BytesIO(b"original"))
    assert info.sha256 == hashlib.sha256(b"original").hexdigest()
    assert info.size_bytes == 8

    class BrokenSource:
        def read(self, size):
            raise OSError("interrupted")

    with pytest.raises(OSError):
        storage.put(info.key, BrokenSource())
    with storage.open(info.key) as stream:
        assert stream.read() == b"original"
    assert list((tmp_path / "objects/raw/test").iterdir()) == [
        tmp_path / "objects/raw/test/file.bin"
    ]


@pytest.mark.parametrize("key", ["../outside", "/absolute", "a/../../outside", "a\\b", ""])
def test_storage_rejects_unsafe_keys(tmp_path, key):
    with pytest.raises(ValueError):
        LocalObjectStorage(tmp_path).put(key, BytesIO(b"test"))


def test_storage_rejects_symlink_escape(tmp_path):
    root = tmp_path / "objects"
    root.mkdir()
    (root / "escape").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        LocalObjectStorage(root).put("escape/outside", BytesIO(b"test"))
