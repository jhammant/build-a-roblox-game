"""Tests for publish.py and opencloud.py, against a fake Open Cloud on 127.0.0.1. Nothing reaches Roblox, and the
real Keychain is never read.

Run from the game folder (or the kit): python3 -m unittest discover -s tools/publish/tests
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import opencloud  # noqa: E402
import publish  # noqa: E402
from fakecloud import FakeCloud  # noqa: E402

KEY = "TEST-KEY-do-not-print-0123456789abcdef"
PUBLISH_ROUTE = r"/universes/v1/111/places/222/versions\?versionType=Published"


class PublishTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "Spark Garden"
        (self.root / "tools").mkdir(parents=True)
        self.place = self.root / "game.rbxlx"
        self.place.write_text("<roblox>a place</roblox>", encoding="utf-8")
        self.cloud = FakeCloud().start()
        patches = [
            mock.patch.dict(os.environ, {opencloud.BASE_URL_ENV: self.cloud.url}),
            mock.patch.object(opencloud, "keychain_lookup", return_value=None),  # never the real Keychain
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop(opencloud.KEY_ENV, None)
        self.addCleanup(self.cloud.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_tool(self, *args, key: str | None = KEY) -> tuple[int, str]:
        if key:
            os.environ[opencloud.KEY_ENV] = key
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(out):
            code = publish.main(["--root", str(self.root), *map(str, args)], sleep=lambda s: None)
        return code, out.getvalue()

    def setup_ids(self):
        code, output = self.run_tool("setup", "--universe", "111", "--place", "222", "--user", "333", key=None)
        self.assertEqual(code, 0, output)


class SetupTests(PublishTestCase):
    def test_setup_writes_ids_and_a_keychain_name_from_the_folder(self):
        # Act
        self.setup_ids()
        # Assert
        config = json.loads((self.root / "tools" / "roblox.json").read_text())
        self.assertEqual(config, {"universeId": "111", "placeId": "222", "userId": "333",
                                  "keychainService": "spark-garden-roblox-api-key"})

    def test_setup_rejects_ids_that_arent_numbers_and_wont_overwrite(self):
        code, output = self.run_tool("setup", "--universe", "abc", "--place", "222", "--user", "333", key=None)
        self.assertEqual(code, 1)
        self.assertIn("universeId", output)
        self.setup_ids()
        code, output = self.run_tool("setup", "--universe", "9", "--place", "9", "--user", "9", key=None)
        self.assertEqual(code, 1)
        self.assertIn("--force", output)

    def test_publish_without_setup_explains_what_to_do(self):
        code, output = self.run_tool("--file", self.place, "--yes")
        self.assertEqual(code, 1)
        self.assertIn("publish.py setup", output)
        self.assertEqual(self.cloud.requests, [])


class PublishTests(PublishTestCase):
    def setUp(self):
        super().setUp()
        self.setup_ids()

    def test_publish_sends_the_place_and_records_history(self):
        # Arrange
        self.cloud.on("POST", PUBLISH_ROUTE, (200, {"versionNumber": 7}))
        # Act
        code, output = self.run_tool("--file", self.place, "--yes", "--note", "new wand")
        # Assert
        self.assertEqual(code, 0, output)
        self.assertIn("Published version 7", output)
        self.assertIn("Error Report", output)
        [req] = self.cloud.requests
        self.assertEqual(req.headers["x-api-key"], KEY)
        self.assertEqual(req.headers["content-type"], "application/xml")
        self.assertEqual(req.body, self.place.read_bytes())
        history = json.loads((self.root / "tools" / "publish" / "history.json").read_text())
        self.assertEqual(history[0]["version"], 7)
        self.assertEqual(history[0]["note"], "new wand")
        self.assertNotIn(KEY, output)

    def test_binary_places_are_sent_as_octet_stream(self):
        binary = self.root / "game.rbxl"
        binary.write_bytes(b"<roblox!\x89\xff")
        self.cloud.on("POST", PUBLISH_ROUTE, (200, {"versionNumber": 1}))
        code, output = self.run_tool("publish", "--file", binary, "--yes")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.cloud.requests[0].headers["content-type"], "application/octet-stream")

    def test_409_says_to_close_studio_and_records_nothing(self):
        self.cloud.on("POST", PUBLISH_ROUTE, (409, {"message": "Server is busy"}))
        code, output = self.run_tool("--file", self.place, "--yes")
        self.assertEqual(code, 3)
        self.assertIn("Close the Studio window that has this game open", output)
        self.assertIn("Server is busy", output)
        self.assertEqual(len(self.cloud.requests), 1)  # a 409 isn't retried
        self.assertFalse((self.root / "tools" / "publish" / "history.json").exists())

    def test_401_explains_the_key_and_never_echoes_it(self):
        # Roblox shouldn't echo a key back, but if an error body ever did, it must not reach the screen
        self.cloud.on("POST", PUBLISH_ROUTE, (401, {"message": f"Invalid API key {KEY}"}))
        code, output = self.run_tool("--file", self.place, "--yes")
        self.assertEqual(code, 3)
        self.assertIn("Place Publishing API", output)
        self.assertNotIn(KEY, output)
        self.assertIn("[key removed]", output)

    def test_busy_server_is_retried(self):
        self.cloud.on("POST", PUBLISH_ROUTE, (503, {"message": "try later"}), (200, {"versionNumber": 2}))
        code, output = self.run_tool("--file", self.place, "--yes")
        self.assertEqual(code, 0, output)
        self.assertEqual(len(self.cloud.requests), 2)

    def test_dry_run_sends_nothing_and_needs_no_key(self):
        code, output = self.run_tool("--dry-run", "--file", self.place, key=None)
        self.assertEqual(code, 0, output)
        self.assertIn("nothing was sent", output)
        self.assertEqual(self.cloud.requests, [])

    def test_missing_key_gives_a_clear_message(self):
        code, output = self.run_tool("--file", self.place, "--yes", key=None)
        self.assertEqual(code, 2)
        self.assertIn("No Open Cloud API key found", output)
        self.assertIn(opencloud.KEY_ENV, output)
        self.assertEqual(self.cloud.requests, [])

    def test_without_a_terminal_it_wont_publish_unless_told_to(self):
        with mock.patch.object(sys.stdin, "isatty", return_value=False):
            code, output = self.run_tool("--file", self.place)
        self.assertEqual(code, 2)
        self.assertIn("--yes", output)
        self.assertEqual(self.cloud.requests, [])

    def test_refuses_to_send_the_key_over_plain_http(self):
        self.cloud.on("POST", PUBLISH_ROUTE, (200, {"versionNumber": 1}))
        with mock.patch.dict(os.environ, {opencloud.BASE_URL_ENV: "http://example.com"}):
            code, output = self.run_tool("--file", self.place, "--yes")
        self.assertEqual(code, 1)
        self.assertIn("must be https", output)
        self.assertEqual(self.cloud.requests, [])

    def test_history_lists_what_was_published(self):
        self.cloud.on("POST", PUBLISH_ROUTE, (200, {"versionNumber": 4}))
        self.run_tool("--file", self.place, "--yes", "--note", "boss fight")
        code, output = self.run_tool("history", key=None)
        self.assertEqual(code, 0)
        self.assertIn("v4", output)
        self.assertIn("boss fight", output)


@unittest.skipIf(os.name == "nt", "the fake Rojo is a shell script")
class BuildTests(PublishTestCase):
    def setUp(self):
        super().setUp()
        self.setup_ids()

    def fake_rojo(self, script: str) -> Path:
        path = self.tmp / "rojo"
        path.write_text("#!/bin/sh\n" + script, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        return path

    def test_builds_with_rojo_before_publishing(self):
        rojo = self.fake_rojo('[ "$1" = build ] && [ "$2" = -o ] && printf "<roblox>built</roblox>" > "$3"\n')
        self.cloud.on("POST", PUBLISH_ROUTE, (200, {"versionNumber": 3}))
        code, output = self.run_tool("--rojo", rojo, "--yes")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.cloud.requests[0].body, b"<roblox>built</roblox>")

    def test_a_failed_build_is_reported_and_nothing_is_sent(self):
        rojo = self.fake_rojo('echo "default.project.json: no such file" >&2\nexit 1\n')
        code, output = self.run_tool("--rojo", rojo, "--yes")
        self.assertEqual(code, 1)
        self.assertIn("Rojo couldn't build the place", output)
        self.assertIn("no such file", output)
        self.assertEqual(self.cloud.requests, [])


if __name__ == "__main__":
    unittest.main()
