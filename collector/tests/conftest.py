import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from acquisition_helpers import zip_bytes
from licita_collector.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        collector_database_url="postgresql+psycopg://test:test@localhost/test_test",
        storage_root=tmp_path / "objects",
        collector_temp_dir=tmp_path / "tmp",
        collector_extract_dir=tmp_path / "extracted",
        collector_attempts=2,
    )


@pytest.fixture
def source():
    state = {
        "body": zip_bytes(),
        "etag": '"v1"',
        "fail": False,
        "ranges": [],
        "missing": False,
        "html": False,
        "ranged": True,
        "truncated": False,
        "transient": 0,
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_HEAD(self):
            self.respond(True)

        def do_GET(self):
            self.respond(False)

        def respond(self, head):
            if self.path.endswith("/"):
                data = b'<a href="compra_2026_09.csv.zip">arquivo</a>'
                self.send_response(200)
            elif state["missing"]:
                self.send_error(404)
                return
            else:
                if not head and state["transient"]:
                    state["transient"] -= 1
                    self.send_error(503)
                    return
                data = b"<html>Erro</html>" if state["html"] else state["body"]
                interval = self.headers.get("Range")
                if interval and not head:
                    start, end = map(int, interval.removeprefix("bytes=").split("-"))
                    state["ranges"].append(start)
                    if state["fail"] and start > 0:
                        self.send_error(503)
                        return
                    self.send_response(206)
                    self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
                    data = data[start : end + 1]
                else:
                    self.send_response(200)
                self.send_header("ETag", state["etag"])
                if state["ranged"]:
                    self.send_header("Accept-Ranges", "bytes")
                if state["html"]:
                    self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if not head:
                self.wfile.write(data[:10] if state["truncated"] else data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/", state
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
