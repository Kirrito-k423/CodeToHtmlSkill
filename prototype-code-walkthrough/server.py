#!/usr/bin/env python3
"""PROTOTYPE — one-command local server for the code walkthrough UI."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT.parent / "samples" / "deepep_moe_dis_dispatch.h"
SOURCE = Path(os.environ.get("CODE_WALKTHROUGH_SOURCE", DEFAULT_SOURCE))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/source.h":
            if not SOURCE.exists():
                self.send_error(404, f"Source not found: {SOURCE}")
                return
            payload = SOURCE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "4173"))
    print(f"PROTOTYPE: http://127.0.0.1:{port}/?variant=B")
    print(f"Source: {SOURCE}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
