import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = "127.0.0.1"
PORT = 8001
DIRECTORY = "."
WEB_ASSETS_DIR = Path(DIRECTORY) / "web" / "assets"
DEFAULT_FAVICON = WEB_ASSETS_DIR / "lpu-smart-campus-logo.png"


class StaticAuditHandler(SimpleHTTPRequestHandler):
    def _serve_json(self, payload: dict, status: int) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _serve_text(self, content: str, status: int = 200) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _serve_file(self, file_path: Path, content_type: str) -> bool:
        if not file_path.exists():
            return False
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        return True

    def do_HEAD(self) -> None:
        self._dispatch_request()

    def do_GET(self) -> None:
        self._dispatch_request()

    def _dispatch_request(self) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path == "/auth/me":
            self._serve_json({"detail": "Not authenticated"}, status=401)
            return
        if request_path in {"/favicon.ico", "/apple-touch-icon.png"}:
            if self._serve_file(DEFAULT_FAVICON, "image/png"):
                return
        if request_path == "/robots.txt":
            self._serve_text("User-agent: *\nAllow: /\n")
            return
        super().do_GET()


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main():
    handler = partial(StaticAuditHandler, directory=DIRECTORY)
    with ReusableThreadingHTTPServer((HOST, PORT), handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
