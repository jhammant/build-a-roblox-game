"""studio_client: a small stdio client for Roblox Studio's built-in MCP server, used by run.py.

Interface: Client().request(method, params) and Client().call(tool, args). Set $STUDIO_MCP to the StudioMCP
program if it isn't at the macOS default below (on Windows it lives inside Studio's install folder).
"""

import itertools
import json
import os
import select
import subprocess
import time

BIN = os.environ.get("STUDIO_MCP", "/Applications/RobloxStudio.app/Contents/MacOS/StudioMCP")


class Client:
    def __init__(self, binary=BIN):
        self.p = subprocess.Popen(
            [binary],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self.ids = itertools.count(1)
        self.request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "playtest", "version": "1"},
            },
        )
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def send(self, msg):
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()

    def request(self, method, params, timeout=180):
        rid = next(self.ids)
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        deadline = time.time() + timeout
        while time.time() < deadline:
            ready, _, _ = select.select([self.p.stdout], [], [], 1)
            if not ready:
                continue
            line = self.p.stdout.readline()
            if not line:
                raise SystemExit("StudioMCP exited")
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == rid:
                if "error" in msg:
                    raise SystemExit(f"error: {msg['error']}")
                return msg["result"]
        raise SystemExit(f"timeout waiting for {method}")

    def call(self, tool, args):
        return self.request("tools/call", {"name": tool, "arguments": args})
