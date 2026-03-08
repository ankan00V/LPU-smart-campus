from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


HOST = "127.0.0.1"
PORT = 8001
DIRECTORY = "."


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main():
    handler = partial(SimpleHTTPRequestHandler, directory=DIRECTORY)
    with ReusableThreadingHTTPServer((HOST, PORT), handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
