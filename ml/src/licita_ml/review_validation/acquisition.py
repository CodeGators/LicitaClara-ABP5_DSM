"""Snapshots HTTP limitados e cache conferido por hash para a revisão."""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from licita_ml.experiments.data import canonical

API = "https://dadosabertos.compras.gov.br"
ROOT = Path("data/validacao_nucleo/revisao_assistida")


_LOCK_GUARD = Lock()
_LOCKS = {}


def binary_download(url):
    chunks, total, offset = [], None, 0
    started = time.monotonic()
    content_type = ""
    while total is None or offset < total:
        if time.monotonic() - started > 45:
            raise TimeoutError("Documento excedeu 45 segundos")
        end = offset + 16383 if total is None else min(offset + 16383, total - 1)
        request = Request(url, headers={"Range": f"bytes={offset}-{end}"})
        with urlopen(request, timeout=12) as response:
            content_type = response.headers.get("Content-Type", "")
            if response.status != 206:
                if offset:
                    raise ValueError("Servidor não preservou transferência por partes")
                data = bytearray()
                while len(data) <= 16 * 1024**2:
                    if time.monotonic() - started > 45:
                        raise TimeoutError("Documento excedeu 45 segundos")
                    part = response.read1(min(8192, 16 * 1024**2 + 1 - len(data)))
                    if not part:
                        return bytes(data), content_type
                    data.extend(part)
                raise ValueError("Documento excede 16 MiB")
            match = re.fullmatch(
                r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", "")
            )
            if not match:
                raise ValueError("Content-Range inválido")
            first, last, size = map(int, match.groups())
            if first != offset or last != min(end, size - 1) or size > 16 * 1024**2:
                raise ValueError("Faixa de documento inválida ou grande demais")
            if total is not None and size != total:
                raise ValueError("Documento mudou durante download")
            total = size
            expected = last - first + 1
            collected = bytearray()
            while len(collected) < expected:
                if time.monotonic() - started > 45:
                    raise TimeoutError("Documento excedeu 45 segundos")
                part = response.read1(min(8192, expected - len(collected)))
                if not part:
                    break
                collected.extend(part)
            data = bytes(collected)
            if len(data) != last - first + 1:
                raise ValueError("Documento truncado")
            chunks.append(data)
            offset += len(data)
    return b"".join(chunks), content_type


def snapshot(url, binary=False):
    with _LOCK_GUARD:
        lock = _LOCKS.setdefault(url, Lock())
    with lock:
        return _snapshot(url, binary)


def _snapshot(url, binary=False):
    folder = ROOT / "fontes"
    folder.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()
    path = folder / (key + (".bin" if binary else ".json"))
    meta_path = folder / (key + ".meta.json")
    if path.exists() and meta_path.exists():
        raw = path.read_bytes()
        meta = json.loads(meta_path.read_text())
        if meta["url"] != url or meta["sha256"] != hashlib.sha256(raw).hexdigest():
            raise ValueError("Cache divergente")
    else:
        attempts = 1 if binary else 3
        for attempt in range(attempts):
            try:
                if binary:
                    raw, content_type = binary_download(url)
                else:
                    with urlopen(url, timeout=25) as response:
                        raw = response.read(16 * 1024**2 + 1)
                        if len(raw) > 16 * 1024**2:
                            raise ValueError("Resposta ultrapassa 16 MiB")
                        content_type = response.headers.get("Content-Type", "")
                break
            except HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                    raise
                time.sleep(attempt + 1)
            except OSError:
                if attempt == attempts - 1:
                    raise
                time.sleep(attempt + 1)
        if not binary:
            json.loads(raw)
        meta = {
            "url": url,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "coletado_em_utc": datetime.now(timezone.utc).isoformat(),
            "content_type": content_type,
            "arquivo": str(path),
        }
        path.write_bytes(raw)
        meta_path.write_text(canonical(meta) + "\n")
    return (raw if binary else json.loads(raw, parse_float=Decimal)), meta


def pages(endpoint, query):
    rows, sources, seen = [], [], set()
    expected = None
    for page in range(1, 101):
        url = API + endpoint + "?" + urlencode(query | {"pagina": page, "tamanhoPagina": 500})
        payload, meta = snapshot(url)
        if not isinstance(payload.get("resultado"), list):
            raise ValueError("Resposta incompatível")
        total = int(payload["totalRegistros"])
        if expected is not None and total != expected:
            raise ValueError("Total mudou entre páginas")
        expected = total
        key = canonical(payload["resultado"])
        if payload["resultado"] and key in seen:
            raise ValueError("Página repetida")
        seen.add(key)
        rows.extend(payload["resultado"])
        sources.append(meta)
        if page >= int(payload["totalPaginas"]):
            break
    else:
        raise ValueError("Limite de páginas excedido")
    if len(rows) != expected:
        raise ValueError("Contagem divergente")
    return rows, sources
