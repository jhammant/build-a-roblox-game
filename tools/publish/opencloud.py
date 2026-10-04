"""opencloud: what publish.py and upload.py share. The game's config, the API key, and a small Open Cloud client.

Standard library only. The API key comes from the ROBLOX_API_KEY environment variable (for one session) or the macOS
Keychain. It only ever goes in the x-api-key header of an HTTPS request. It is never printed, logged or written to a
file, and every error message has it removed.
"""

from __future__ import annotations

import http.client
import json
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "https://apis.roblox.com"
BASE_URL_ENV = "OPEN_CLOUD_BASE_URL"  # tests only: points the tools at a fake server on 127.0.0.1
KEY_ENV = "ROBLOX_API_KEY"
CONFIG_NAME = "roblox.json"
DIGITS = re.compile(r"^\d{1,20}$")


class ToolError(Exception):
    """A problem the parent can fix, with a message that says how. Exit code goes with it."""

    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------------------------------------------
# The game folder and its config


def default_root() -> Path:
    """The game folder: two levels above tools/<tool>/<script>.py."""
    return Path(__file__).resolve().parents[2]


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "game"


def default_keychain_service(root: Path) -> str:
    return f"{slug(root.name)}-roblox-api-key"


def config_path(root: Path) -> Path:
    return root / "tools" / CONFIG_NAME


def load_config(root: Path) -> dict:
    path = config_path(root)
    if not path.exists():
        raise ToolError(
            f"There's no {path.relative_to(root)} yet. Publish the game once from Studio (File → Publish to Roblox), "
            "then run:\n  python3 tools/publish/publish.py setup --universe <id> --place <id> --user <id>\n"
            "tools/publish/README.md says where to find each id."
        )
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ToolError(f"{path.relative_to(root)} isn't valid JSON ({e}). Run setup again with --force.") from None
    problems = []
    for key in ("universeId", "placeId", "userId"):
        if not DIGITS.match(str(config.get(key, ""))):
            problems.append(f"{key} should be the number from Creator Hub")
    if config.get("groupId") not in (None, "") and not DIGITS.match(str(config["groupId"])):
        problems.append("groupId should be a number, or left out")
    if problems:
        raise ToolError(f"{path.relative_to(root)}: " + "; ".join(problems))
    config.setdefault("keychainService", default_keychain_service(root))
    return config


def creator_of(config: dict) -> dict:
    """Who owns uploaded assets: the group if the config names one, otherwise the user."""
    if config.get("groupId"):
        return {"groupId": str(config["groupId"])}
    return {"userId": str(config["userId"])}


# ---------------------------------------------------------------------------------------------------------------
# The API key


def keychain_lookup(service: str) -> str | None:
    """The key stored in the macOS Keychain under this service name, or None. Never prints it."""
    if not shutil.which("security"):
        return None
    found = subprocess.run(["security", "find-generic-password", "-s", service, "-w"], capture_output=True, text=True)
    if found.returncode == 0 and found.stdout.strip():
        return found.stdout.strip()
    return None


def get_api_key(service: str) -> tuple[str, str]:
    """(key, where it came from). The environment variable wins, so a one-off session can override the Keychain."""
    value = os.environ.get(KEY_ENV, "").strip()
    if value:
        return value, f"the {KEY_ENV} environment variable"
    value = keychain_lookup(service)
    if value:
        return value, f'the Keychain ("{service}")'
    if sys.platform == "darwin":
        how = (f'Store it once in the Keychain (it asks you to paste the key, so it never lands in your history):\n'
               f'  security add-generic-password -a "$USER" -s {service} -w\n'
               f"or set {KEY_ENV} for this terminal session only.")
    else:
        how = (f"Set {KEY_ENV} for this terminal session only (never in a file). In PowerShell 7:\n"
               f'  $env:{KEY_ENV} = Read-Host "Paste the key" -MaskInput\n'
               f"In a bash or zsh terminal:\n  read -rs {KEY_ENV} && export {KEY_ENV}")
    raise ToolError(f"No Open Cloud API key found.\n{how}\nSee tools/publish/README.md for how to create one.", 2)


# ---------------------------------------------------------------------------------------------------------------
# HTTP


def base_url() -> str:
    url = os.environ.get(BASE_URL_ENV, "").strip() or DEFAULT_BASE_URL
    parts = urllib.parse.urlsplit(url)
    local = parts.hostname in ("127.0.0.1", "localhost", "::1")
    if parts.scheme != "https" and not (parts.scheme == "http" and local):
        raise ToolError(f"Refusing to send the API key to {parts.scheme}://{parts.hostname}: it must be https.")
    return url.rstrip("/")


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}" if status else message)
        self.status = status
        self.message = message


def error_message(raw: bytes, status: int) -> str:
    """The most useful line from an Open Cloud error body."""
    try:
        doc = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        text = raw.decode("utf-8", "replace").strip()
        return (text or http.client.responses.get(status, "error"))[:300]
    if isinstance(doc, dict):
        if isinstance(doc.get("errors"), list) and doc["errors"]:
            first = doc["errors"][0]
            return str(first.get("message") if isinstance(first, dict) else first)[:300]
        if isinstance(doc.get("error"), dict):
            return str(doc["error"].get("message", doc["error"]))[:300]
        for key in ("message", "error", "code"):
            if doc.get(key):
                return str(doc[key])[:300]
    return json.dumps(doc)[:300]


class OpenCloud:
    """A small Open Cloud client. Retries 429 and 5xx a few times. The key lives only in this object and the header;
    repr() and every error message leave it out."""

    RETRYABLE = {429, 500, 502, 503, 504}

    def __init__(self, api_key: str, *, url: str | None = None, timeout: float = 180.0, max_retries: int = 3,
                 sleep=time.sleep, out=print, agent: str = "build-a-roblox-game"):
        self.base = url or base_url()
        self._key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.sleep = sleep
        self.out = out
        self.agent = agent

    def __repr__(self) -> str:
        return f"OpenCloud({self.base!r})"

    def redact(self, text: str) -> str:
        return text.replace(self._key, "[key removed]") if self._key else text

    def request(self, method: str, path: str, *, body: bytes | None = None, content_type: str | None = None,
                retry_creates: bool = True) -> dict:
        url = self.base + path
        attempt = 0
        while True:
            headers = {"x-api-key": self._key, "Accept": "application/json", "User-Agent": self.agent}
            if content_type:
                headers["Content-Type"] = content_type
            req = urllib.request.Request(url, data=body, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                    return json.loads(raw) if raw.strip() else {}
            except urllib.error.HTTPError as exc:
                with exc:
                    raw = exc.read()
                message = self.redact(error_message(raw, exc.code))
                if exc.code not in self.RETRYABLE or attempt >= self.max_retries:
                    raise ApiError(exc.code, message) from None
                wait = self._retry_after(exc.headers, attempt)
                self.out(f"  Roblox said {exc.code} ({'too many requests' if exc.code == 429 else 'busy'}); "
                         f"trying again in {wait:.0f} s")
            except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as exc:
                reason = getattr(exc, "reason", exc)
                never_sent = isinstance(reason, (ConnectionRefusedError, socket.gaierror))
                if method == "POST" and not never_sent and not retry_creates:
                    raise ApiError(0, f"the connection dropped mid-request ({self.redact(str(reason))}). It may "
                                      "have gone through, so check Creator Hub before trying again.") from None
                if attempt >= self.max_retries:
                    raise ApiError(0, f"couldn't reach Roblox ({self.redact(str(reason))})") from None
                wait = min(30.0, 2.0**attempt) + random.uniform(0, 0.5)
                self.out(f"  network problem ({self.redact(str(reason))}); trying again in {wait:.0f} s")
            self.sleep(wait)
            attempt += 1

    @staticmethod
    def _retry_after(headers, attempt: int) -> float:
        for name in ("retry-after", "x-ratelimit-reset"):
            value = headers.get(name) if headers is not None else None
            try:
                if value is not None:
                    return min(120.0, max(0.0, float(value.split(",")[0])))
            except ValueError:
                pass
        return min(30.0, 2.0**attempt) + random.uniform(0, 0.5)


def ask(question: str, *, yes: bool) -> bool:
    """True if --yes was given or the parent typed y. Refuses to guess when there's no terminal to ask in."""
    if yes:
        return True
    if not sys.stdin.isatty():
        raise ToolError("Not running in a terminal, so not asking: add --yes to go ahead.", 2)
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
