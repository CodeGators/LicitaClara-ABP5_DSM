import http.client
import json
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from licita_collector.errors import CollectionError, InvalidArchive, TransientFailure, Unavailable


class HTTPFailure(CollectionError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"A fonte respondeu HTTP {status}")


class HttpClient:
    def __init__(self, settings, sleep=time.sleep):
        self.settings, self.sleep = settings, sleep

    def request(self, url, method="GET", headers=None, attempts=None):
        tries = self.settings.collector_attempts if attempts is None else attempts
        for attempt in range(tries):
            try:
                return urlopen(
                    Request(
                        url,
                        method=method,
                        headers={
                            "User-Agent": "LicitaClara-Collector/0.1",
                            "Accept-Encoding": "identity",
                            **(headers or {}),
                        },
                    ),
                    timeout=self.settings.collector_timeout,
                )
            except HTTPError as error:
                status = error.code
                error.close()
                if status == 404:
                    raise Unavailable("Competência ou arquivo ainda indisponível") from None
                if status not in (408, 429, 500, 502, 503, 504):
                    raise HTTPFailure(status) from None
            except (URLError, OSError, http.client.HTTPException):
                pass
            if attempt + 1 < tries:
                self.sleep(min(2**attempt, 4))
        raise TransientFailure("Limite de tentativas de conexão atingido")


@dataclass
class Download:
    path: Path
    url_final: str
    etag: str | None


class Downloader:
    def __init__(self, settings, http=None):
        self.settings = settings
        self.http = http or HttpClient(settings)

    def fetch(self, url, folder):
        folder.mkdir(parents=True, exist_ok=True)
        path, sidecar = folder / "download.part", folder / "download.json"
        etag, size, ranged, final_url = None, None, False, url
        try:
            with self.http.request(url, method="HEAD") as response:
                etag, final_url = response.headers.get("ETag"), response.url
                length = response.headers.get("Content-Length")
                if length is not None:
                    try:
                        size = int(length)
                    except ValueError:
                        raise InvalidArchive("Tamanho anunciado inválido") from None
                ranged = response.headers.get("Accept-Ranges") == "bytes"
        except HTTPFailure as error:
            if error.status not in (405, 501):
                raise
        if size is not None and (size < 1 or size > self.settings.collector_max_download_bytes):
            raise InvalidArchive("Tamanho anunciado excede limite ou está vazio")
        ranged = ranged and size is not None and etag is not None and not etag.startswith("W/")
        if ranged:
            signature = {"url": url, "etag": etag, "bytes": size}
            try:
                saved = json.loads(sidecar.read_text())
            except (OSError, ValueError):
                saved = None
            if saved != signature or (path.exists() and path.stat().st_size > size):
                path.unlink(missing_ok=True)
            temporary = sidecar.with_suffix(".tmp")
            temporary.write_text(json.dumps(signature))
            temporary.replace(sidecar)
            path.touch(exist_ok=True)
            while path.stat().st_size < size:
                start = path.stat().st_size
                end = min(start + 1024 * 1024, size) - 1
                self._block(url, path, start, end, size, etag)
        else:
            for attempt in range(self.settings.collector_attempts):
                try:
                    with self.http.request(url, attempts=1) as response, path.open("wb") as output:
                        if "text/html" in response.headers.get("Content-Type", ""):
                            raise InvalidArchive("A fonte retornou HTML no lugar do ZIP")
                        final_url, etag = response.url, response.headers.get("ETag")
                        actual = 0
                        while chunk := response.read(1024 * 1024):
                            actual += len(chunk)
                            if actual > self.settings.collector_max_download_bytes:
                                raise InvalidArchive("Download excedeu o limite de bytes")
                            output.write(chunk)
                        expected = response.headers.get("Content-Length")
                        if expected is not None and actual != int(expected):
                            raise OSError("Download incompleto")
                    break
                except (OSError, http.client.HTTPException, TransientFailure):
                    if attempt + 1 == self.settings.collector_attempts:
                        raise TransientFailure("Download interrompido após retentativas") from None
                    self.http.sleep(min(2**attempt, 4))
        return Download(path, final_url, etag)

    def _block(self, url, path, start, end, size, etag):
        for attempt in range(self.settings.collector_attempts):
            try:
                with self.http.request(
                    url,
                    headers={
                        "Range": f"bytes={start}-{end}",
                        "If-Match": etag,
                    },
                    attempts=1,
                ) as response:
                    expected = f"bytes {start}-{end}/{size}"
                    if (
                        response.status != 206
                        or response.headers.get("Content-Range") != expected
                        or response.headers.get("ETag") != etag
                    ):
                        raise InvalidArchive("Fonte não confirmou intervalo e versão do bloco")
                    chunk = response.read(end - start + 2)
                    if len(chunk) != end - start + 1:
                        raise OSError("Bloco incompleto")
                with path.open("ab") as output:
                    output.write(chunk)
                return
            except HTTPFailure as error:
                if error.status == 412:
                    raise TransientFailure(
                        "Fonte mudou durante download; retome a execução"
                    ) from None
                raise
            except (OSError, http.client.HTTPException, TransientFailure):
                if attempt + 1 == self.settings.collector_attempts:
                    raise TransientFailure(
                        "Bloco interrompido; parcial preservado para retomada"
                    ) from None
                self.http.sleep(min(2**attempt, 4))
