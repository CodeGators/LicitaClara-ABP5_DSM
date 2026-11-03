"""Registra snapshots anteriores pelo mesmo contrato de aquisição, sem fingir coleta antiga."""

import hashlib
import io
import json
from pathlib import Path

from licita_collector.errors import CollectionError


class CachedHistory:
    def __init__(self, settings, scope, root):
        self.settings, self.scope, self.root = settings, scope, Path(root)
        self.metadata = {}

    def request(self, url):
        # A API inclui a página explicitamente. Só aceitar a URL exata do protocolo.
        from urllib.parse import parse_qs, urlsplit

        page = int(parse_qs(urlsplit(url).query)["pagina"][0])
        if url != self.scope.url(page):
            raise CollectionError("URL de cache incompatível")
        path = self.root / f"historico_{self.scope.query['catalogo']}_pagina_{page}.json"
        meta_path = path.with_suffix(".meta.json")
        if not path.is_file() or not meta_path.is_file():
            raise CollectionError("Página ou metadado ausente no cache histórico")
        if path.stat().st_size > self.settings.collector_max_download_bytes:
            raise CollectionError("Página histórica excede limite")
        raw, meta = path.read_bytes(), json.loads(meta_path.read_text())
        if (
            meta.get("url") != url
            or meta.get("sha256") != hashlib.sha256(raw).hexdigest()
            or meta.get("bytes") != len(raw)
            or meta.get("status") != 200
        ):
            raise CollectionError("Cache histórico diverge de URL, hash, tamanho ou status")
        self.metadata[url] = {
            "sha256": meta["sha256"],
            "bytes": len(raw),
            "url": url,
            "coletado_em_utc_original": meta.get("coletado_em_utc"),
            "modo": "registro_offline_de_snapshot_anterior",
        }
        return io.BytesIO(raw)

    def provenance(self, url):
        return self.metadata[url]
