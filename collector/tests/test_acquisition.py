from datetime import date

import pytest
from acquisition_helpers import zip_bytes
from licita_collector.archive import extract, validate
from licita_collector.errors import InvalidArchive, TransientFailure, Unavailable
from licita_collector.http import Downloader, HttpClient
from licita_collector.source import Scope, discover, month, months


def test_discovery_and_missing(source, settings):
    base, state = source
    http = HttpClient(settings, sleep=lambda _: None)
    scope = Scope("compra", month("2026-09"))
    assert discover(scope, http, base).endswith(scope.filename)
    state["missing"] = True
    with pytest.raises(Unavailable):
        Downloader(settings, http).fetch(base + scope.filename, settings.collector_temp_dir)
    assert list(months(date(2025, 12, 1), date(2026, 1, 1))) == [
        date(2025, 12, 1),
        date(2026, 1, 1),
    ]


def test_resume_only_confirmed_blocks_and_reset_on_change(source, settings):
    base, state = source
    state["body"] = zip_bytes(b"x" * (2 * 1024**2))
    state["fail"] = True
    downloader = Downloader(settings, HttpClient(settings, sleep=lambda _: None))
    folder = settings.collector_temp_dir
    with pytest.raises(TransientFailure):
        downloader.fetch(base + "file.zip", folder)
    assert (folder / "download.part").stat().st_size == 1024**2
    state["ranges"].clear()
    state["fail"] = False
    result = downloader.fetch(base + "file.zip", folder)
    assert state["ranges"][0] == 1024**2
    validate(result.path, settings)
    state["etag"] = '"v2"'
    state["body"] = zip_bytes(b"corrigido")
    state["ranges"].clear()
    result = downloader.fetch(base + "file.zip", folder)
    assert state["ranges"] == [0]
    assert result.path.read_bytes() == state["body"]


@pytest.mark.parametrize("name", ["../fora.csv", "/fora.csv", "a\\fora.csv", "dados.exe"])
def test_reject_unsafe_members(name, settings, tmp_path):
    path = tmp_path / "bad.zip"
    path.write_bytes(zip_bytes(name=name))
    with pytest.raises(InvalidArchive):
        extract(path, tmp_path / "output", settings)
    assert not (tmp_path / "output").exists()


def test_crc_expansion_and_atomic_extraction(settings, tmp_path):
    path = tmp_path / "good.zip"
    path.write_bytes(zip_bytes())
    result = validate(path, settings)
    assert result["membros"] == 1
    target = extract(path, tmp_path / "output", settings)
    assert (target / "dados.csv").read_bytes().startswith(b"id;")
    with pytest.raises(InvalidArchive):
        extract(path, target, settings)
    content = bytearray(path.read_bytes())
    content[40] ^= 1
    path.write_bytes(content)
    with pytest.raises(InvalidArchive):
        validate(path, settings)
    path.write_bytes(zip_bytes(b"abc" * 100))
    settings.collector_max_uncompressed_bytes = 10
    with pytest.raises(InvalidArchive):
        validate(path, settings)


def test_full_stream_retry_html_and_incomplete(source, settings):
    base, state = source
    state["ranged"] = False
    state["transient"] = 1
    downloader = Downloader(settings, HttpClient(settings, sleep=lambda _: None))
    result = downloader.fetch(base + "file.zip", settings.collector_temp_dir)
    validate(result.path, settings)
    assert state["transient"] == 0
    state["html"] = True
    with pytest.raises(InvalidArchive):
        downloader.fetch(base + "file.zip", settings.collector_temp_dir)
    state["html"] = False
    state["truncated"] = True
    with pytest.raises(TransientFailure):
        downloader.fetch(base + "file.zip", settings.collector_temp_dir)


def test_symlink_and_compression_bomb_are_rejected(settings, tmp_path):
    import stat
    from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

    path = tmp_path / "archive.zip"
    info = ZipInfo("link.csv")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with ZipFile(path, "w") as archive:
        archive.writestr(info, "../outside.csv")
    with pytest.raises(InvalidArchive):
        validate(path, settings)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("dados.csv", b"0" * 1024**2)
    with pytest.raises(InvalidArchive):
        validate(path, settings)
