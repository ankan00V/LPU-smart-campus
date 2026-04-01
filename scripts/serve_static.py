import errno
import json
import os
import signal
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import sleep
from urllib.error import URLError
from urllib.request import urlopen


HOST = os.getenv("STATIC_AUDIT_HOST", "127.0.0.1")
PORT = int(os.getenv("STATIC_AUDIT_PORT", "8001"))
DIRECTORY = os.getenv("STATIC_AUDIT_DIRECTORY", ".")
WEB_ASSETS_DIR = Path(DIRECTORY) / "web" / "assets"
DEFAULT_FAVICON = WEB_ASSETS_DIR / "lpu-smart-campus-logo.png"
EXPECTED_SHELL_MARKER = "LPU Smart Campus Command Deck"


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


def _compatible_server_already_running(host: str, port: int) -> bool:
    try:
        with urlopen(f"http://{host}:{port}/web/", timeout=2) as response:
            body = response.read(8192).decode("utf-8", errors="ignore")
            return int(response.getcode()) == 200 and EXPECTED_SHELL_MARKER in body
    except (OSError, URLError):
        return False


def _wait_for_shutdown_signal() -> None:
    keep_running = True

    def _handle_signal(_signum, _frame) -> None:
        nonlocal keep_running
        keep_running = False

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    while keep_running:
        sleep(0.5)


def main():
    handler = partial(StaticAuditHandler, directory=DIRECTORY)
    try:
        with ReusableThreadingHTTPServer((HOST, PORT), handler) as httpd:
            httpd.serve_forever()
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE and _compatible_server_already_running(HOST, PORT):
            print(f"Reusing compatible static audit server at http://{HOST}:{PORT}/web/")
            _wait_for_shutdown_signal()
            return
        raise


if __name__ == "__main__":
    main()
