"""A fake Open Cloud on 127.0.0.1, so the publish and upload tests never touch the real Roblox APIs.

Each route is (method, path regex) -> a list of responses, used in order (the last one repeats). Every request is
recorded with its headers and body so tests can check exactly what would have been sent.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass
class Recorded:
    method: str
    path: str
    headers: dict
    body: bytes


@dataclass
class FakeCloud:
    routes: list = field(default_factory=list)  # [(method, compiled regex, [(status, body), ...])]
    requests: list = field(default_factory=list)

    def on(self, method: str, pattern: str, *responses):
        """Queue responses for a route. Each response is (status, dict | bytes)."""
        self.routes.append((method, re.compile(pattern), list(responses)))
        return self

    def start(self) -> "FakeCloud":
        cloud = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def handle_any(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                headers = {k.lower(): v for k, v in self.headers.items()}
                cloud.requests.append(Recorded(self.command, self.path, headers, body))
                for method, pattern, responses in cloud.routes:
                    if method == self.command and pattern.fullmatch(self.path):
                        status, payload = responses.pop(0) if len(responses) > 1 else responses[0]
                        break
                else:
                    status, payload = 404, {"message": f"fake cloud has no route for {self.command} {self.path}"}
                raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Retry-After", "0")
                self.end_headers()
                self.wfile.write(raw)

            do_GET = do_POST = do_PATCH = handle_any

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def count(self, method: str, pattern: str) -> int:
        rx = re.compile(pattern)
        return sum(1 for r in self.requests if r.method == method and rx.fullmatch(r.path))
