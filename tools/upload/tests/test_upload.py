"""Tests for upload.py and mediainfo.py, against a fake Open Cloud on 127.0.0.1. Nothing reaches Roblox, and the
real Keychain is never read.

Run from the game folder (or the kit): python3 -m unittest discover -s tools/upload/tests
"""

from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
import zlib
from contextlib import redirect_stderr, redirect_stdout
from email.parser import BytesParser
from email.policy import default as email_policy
from io import StringIO
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1]
sys.path.insert(0, str(TOOLS / "upload"))
sys.path.insert(0, str(TOOLS / "publish"))
sys.path.insert(0, str(TOOLS / "publish" / "tests"))
import mediainfo  # noqa: E402
import opencloud  # noqa: E402
import upload  # noqa: E402
from fakecloud import FakeCloud  # noqa: E402

KEY = "TEST-KEY-do-not-print-fedcba9876543210"
CREATE = r"/assets/v1/assets"


# ---------------------------------------------------------------------------------------------------------------
# Little files to upload


def make_wav(path: Path, seconds: float = 0.1, rate: int = 8000, channels: int = 1):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(1)
        w.setframerate(rate)
        w.writeframes(b"\x80" * int(seconds * rate) * channels)


def make_long_wav(path: Path, seconds: int):
    """A WAV whose header says it's `seconds` long (the samples themselves are left out)."""
    rate = 8000
    header = b"RIFF" + struct.pack("<I", 36) + b"WAVE" + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate, 1, 8)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + b"data" + struct.pack("<I", rate * seconds) + b"\x80" * 16)


def make_png(path: Path, width: int = 4, height: int = 4):
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    raw = b"".join(b"\x00" + b"\xff\x00\x00" * min(width, 4) for _ in range(min(height, 4)))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def parse_multipart(content_type: str, body: bytes) -> dict:
    message = BytesParser(policy=email_policy).parsebytes(
        f"Content-Type: {content_type}\r\n\r\n".encode() + body)
    parts = {}
    for part in message.iter_parts():
        parts[part.get_param("name", header="content-disposition")] = part
    return parts


# ---------------------------------------------------------------------------------------------------------------


class UploadTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "spark-garden"
        (self.root / "tools").mkdir(parents=True)
        (self.root / "tools" / "roblox.json").write_text(json.dumps(
            {"universeId": "111", "placeId": "222", "userId": "333"}))
        self.cloud = FakeCloud().start()
        patches = [
            mock.patch.dict(os.environ, {opencloud.BASE_URL_ENV: self.cloud.url, opencloud.KEY_ENV: KEY}),
            mock.patch.object(opencloud, "keychain_lookup", return_value=None),  # never the real Keychain
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.cloud.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_tool(self, *args) -> tuple[int, str]:
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(out):
            code = upload.main([*map(str, args), "--root", str(self.root)], sleep=lambda s: None)
        output = out.getvalue()
        self.assertNotIn(KEY, output)
        return code, output

    def state(self) -> dict:
        return json.loads((self.root / "tools" / "upload" / "uploaded.json").read_text())

    def luau(self) -> str:
        return (self.root / "src" / "shared" / "AssetIds.luau").read_text()

    def operation(self, op_id: str, *responses):
        self.cloud.on("GET", rf"/assets/v1/operations/{op_id}", *responses)

    @staticmethod
    def done(asset_id: str) -> tuple[int, dict]:
        return 200, {"done": True, "response": {"assetId": asset_id,
                                                "moderationResult": {"moderationState": "Approved"}}}


class PlanTests(UploadTestCase):
    def test_plan_checks_every_file_and_sends_nothing(self):
        # Arrange
        audio, images = self.root / "assets" / "audio", self.root / "assets" / "images"
        make_wav(audio / "Yay.wav")
        make_png(images / "WandIcon.png")
        make_wav(audio / "bad name.wav")
        make_long_wav(audio / "LongSong.wav", seconds=8 * 60)
        make_wav(audio / "TooFancy.wav", rate=96_000)
        make_png(images / "Huge.png", width=9000, height=10)
        (images / "Fake.png").write_text("not really a picture")
        (images / "notes.txt").write_text("ignored")
        # Act
        code, output = self.run_tool("plan")
        # Assert
        self.assertEqual(code, 1)
        lines = {line.split()[1]: line for line in output.splitlines() if line.startswith("  ") and "assets/" in line}
        self.assertTrue(lines["assets/audio/Yay.wav"].strip().startswith("UPLOAD"))
        self.assertTrue(lines["assets/images/WandIcon.png"].strip().startswith("UPLOAD"))
        self.assertIn("letters, digits and _", output)
        self.assertIn("8.0 minutes long; Roblox allows 7", output)
        self.assertIn("96000 Hz", output)
        self.assertIn("9000x10", output)
        self.assertIn("not a PNG file", output)
        self.assertIn("skipping files in assets/images that can't be uploaded: notes.txt", output)
        self.assertIn("Nothing was sent to Roblox", output)
        self.assertEqual(self.cloud.requests, [])

    def test_plan_with_nothing_to_do(self):
        code, output = self.run_tool("plan")
        self.assertEqual(code, 0)
        self.assertIn("assets/audio/", output)

    def test_oversized_files_are_rejected(self):
        make_wav(self.root / "assets" / "audio" / "Big.wav", seconds=1)
        with mock.patch.object(upload, "MAX_UPLOAD_BYTES", 100):
            code, output = self.run_tool("plan")
        self.assertEqual(code, 1)
        self.assertIn("over the 20 MB upload limit", output)


class UploadTests(UploadTestCase):
    def test_upload_sends_a_multipart_create_and_follows_the_operation(self):
        # Arrange
        make_wav(self.root / "assets" / "audio" / "Yay.wav")
        self.cloud.on("POST", CREATE, (200, {"path": "operations/op-1", "operationId": "op-1", "done": False}))
        self.operation("op-1", (200, {"done": False}), (200, {"done": False}), self.done("555"))
        # Act
        code, output = self.run_tool("upload", "--yes")
        # Assert
        self.assertEqual(code, 0, output)
        create = self.cloud.requests[0]
        self.assertEqual(create.headers["x-api-key"], KEY)
        parts = parse_multipart(create.headers["content-type"], create.body)
        request = json.loads(parts["request"].get_content())
        self.assertEqual(request["assetType"], "Audio")
        self.assertEqual(request["displayName"], "Yay")
        self.assertEqual(request["creationContext"], {"creator": {"userId": "333"}, "expectedPrice": 0})
        file_part = parts["fileContent"]
        self.assertEqual(file_part.get_filename(), "Yay.wav")
        self.assertEqual(file_part.get_content_type(), "audio/wav")
        self.assertEqual(file_part.get_payload(decode=True), (self.root / "assets" / "audio" / "Yay.wav").read_bytes())
        self.assertEqual(self.cloud.count("GET", r"/assets/v1/operations/op-1"), 3)
        self.assertEqual(self.state()["assets"]["Audio/Yay"]["assetId"], "555")
        self.assertIn('Yay = "rbxassetid://555",', self.luau())
        self.assertIn("Permissions → Experiences", output)
        self.assertIn("Error Report", output)

    def test_pictures_go_up_as_images_or_decals(self):
        make_png(self.root / "assets" / "images" / "Logo.png")
        self.cloud.on("POST", CREATE, (200, {"operationId": "op-9"}))
        self.operation("op-9", self.done("900"))
        code, output = self.run_tool("upload", "--yes", "--image-type", "Decal")
        self.assertEqual(code, 0, output)
        parts = parse_multipart(self.cloud.requests[0].headers["content-type"], self.cloud.requests[0].body)
        self.assertEqual(json.loads(parts["request"].get_content())["assetType"], "Decal")
        self.assertNotIn("Permissions → Experiences", output)  # the audio reminder is only for sounds
        self.assertIn('Logo = "rbxassetid://900",', self.luau())

    def test_an_upload_still_processing_is_collected_next_time_not_sent_again(self):
        # Arrange: Roblox is slow, and we stop waiting at once
        make_wav(self.root / "assets" / "audio" / "Pop.wav")
        self.cloud.on("POST", CREATE, (200, {"operationId": "op-2"}))
        self.operation("op-2", (200, {"done": False}))
        # Act 1
        code, output = self.run_tool("upload", "--yes", "--poll-timeout", "0")
        # Assert 1
        self.assertEqual(code, 0, output)
        self.assertIn("still processing", output)
        self.assertEqual(self.state()["assets"]["Audio/Pop"]["pending"]["operationId"], "op-2")
        self.assertNotIn("Pop =", self.luau())
        # Act 2: it's finished now
        self.cloud.routes.clear()
        self.cloud.on("POST", CREATE, (500, {"message": "must not be called"}))
        self.operation("op-2", self.done("222"))
        code, output = self.run_tool("upload", "--yes")
        # Assert 2
        self.assertEqual(code, 0, output)
        self.assertEqual(self.cloud.count("POST", CREATE), 1)
        self.assertIn('Pop = "rbxassetid://222",', self.luau())
        # Act 3: nothing new, so nothing is sent
        before = len(self.cloud.requests)
        code, output = self.run_tool("upload", "--yes")
        self.assertEqual(code, 0)
        self.assertIn("Nothing to upload", output)
        self.assertEqual(len(self.cloud.requests), before)

    def test_a_changed_file_goes_up_as_a_new_asset_and_keeps_the_old_id(self):
        path = self.root / "assets" / "audio" / "Boing.wav"
        make_wav(path, seconds=0.1)
        self.cloud.on("POST", CREATE, (200, {"operationId": "op-a"}), (200, {"operationId": "op-b"}))
        self.operation("op-a", self.done("101"))
        self.operation("op-b", self.done("202"))
        self.run_tool("upload", "--yes")
        make_wav(path, seconds=0.2)
        code, output = self.run_tool("upload", "--yes")
        self.assertEqual(code, 0, output)
        entry = self.state()["assets"]["Audio/Boing"]
        self.assertEqual(entry["assetId"], "202")
        self.assertEqual(entry["history"][0]["assetId"], "101")
        self.assertIn('Boing = "rbxassetid://202",', self.luau())

    def test_a_refused_key_stops_with_help(self):
        make_wav(self.root / "assets" / "audio" / "Yay.wav")
        self.cloud.on("POST", CREATE, (401, {"message": f"bad key {KEY}"}))
        code, output = self.run_tool("upload", "--yes")
        self.assertEqual(code, 3)
        self.assertIn("Assets API with Read and Write", output)

    def test_a_failed_upload_is_recorded(self):
        make_wav(self.root / "assets" / "audio" / "Yay.wav")
        self.cloud.on("POST", CREATE, (200, {"operationId": "op-x"}))
        self.operation("op-x", (200, {"done": True, "error": {"message": "moderation rejected the file"}}))
        code, output = self.run_tool("upload", "--yes")
        self.assertEqual(code, 1)
        self.assertIn("moderation rejected the file", output)
        self.assertNotIn("Yay =", self.luau())

    def test_upload_without_a_key_explains_how_to_add_one(self):
        make_wav(self.root / "assets" / "audio" / "Yay.wav")
        with mock.patch.dict(os.environ, {opencloud.KEY_ENV: ""}):
            code, output = self.run_tool("upload", "--yes")
        self.assertEqual(code, 2)
        self.assertIn("No Open Cloud API key found", output)
        self.assertEqual(self.cloud.requests, [])

    def test_only_and_limit_narrow_the_upload(self):
        for name in ("A", "B", "C"):
            make_wav(self.root / "assets" / "audio" / f"{name}.wav")
        self.cloud.on("POST", CREATE, (200, {"operationId": "op-1"}))
        self.operation("op-1", self.done("1"))
        code, output = self.run_tool("upload", "--yes", "--only", "B,C", "--limit", "1")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.cloud.count("POST", CREATE), 1)
        self.assertEqual(list(self.state()["assets"]), ["Audio/B"])

    def test_status_refresh_reads_moderation(self):
        make_wav(self.root / "assets" / "audio" / "Yay.wav")
        self.cloud.on("POST", CREATE, (200, {"operationId": "op-1"}))
        self.operation("op-1", (200, {"done": True, "response": {"assetId": "77"}}))
        self.cloud.on("GET", r"/assets/v1/assets/77\?readMask=moderationResult",
                      (200, {"moderationResult": {"moderationState": "Approved"}}))
        self.run_tool("upload", "--yes")
        code, output = self.run_tool("status", "--refresh")
        self.assertEqual(code, 0, output)
        self.assertIn("rbxassetid://77  (Approved)", output)


class LuauTests(unittest.TestCase):
    STATE = {"assets": {
        "Audio/Yay": {"assetId": "1"},
        "Audio/boing": {"assetId": "2"},
        "Audio/Pending": {"pending": {"operationId": "x"}},
        "Images/Logo": {"assetId": "3"},
    }}

    def test_module_shape(self):
        text = upload.luau_module(self.STATE)
        self.assertTrue(text.startswith("-- AssetIds: "))
        body = text.split("return ", 1)[1]
        self.assertEqual(body, '{\n\tAudio = {\n\t\tboing = "rbxassetid://2",\n\t\tYay = "rbxassetid://1",\n\t},\n'
                               '\tImages = {\n\t\tLogo = "rbxassetid://3",\n\t},\n}\n')
        self.assertIn("\tImages = {},", upload.luau_module({"assets": {"Audio/Yay": {"assetId": "1"}}}))

    def test_module_is_already_formatted_for_stylua(self):
        stylua = shutil.which("stylua") or str(Path.home() / ".rokit" / "bin" / "stylua")
        if not Path(stylua).exists():
            self.skipTest("stylua isn't installed")
        with tempfile.TemporaryDirectory() as tmp:
            # The game folder's settings, and a manifest so Rokit's shim knows which StyLua to run
            (Path(tmp) / "stylua.toml").write_text('syntax = "Luau"\nindent_type = "Tabs"\ncolumn_width = 120\n')
            (Path(tmp) / "rokit.toml").write_text('[tools]\nstylua = "JohnnyMorganz/StyLua@2.5.2"\n')
            path = Path(tmp) / "AssetIds.luau"
            path.write_text(upload.luau_module(self.STATE))
            result = subprocess.run([stylua, "--check", str(path)], cwd=tmp, capture_output=True, text=True)
        if "Failed to find tool" in result.stderr or "not installed" in result.stderr:
            self.skipTest("StyLua 2.5.2 isn't installed through Rokit")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class MediaInfoTests(unittest.TestCase):
    def test_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.wav"
            make_wav(path, seconds=0.5, rate=22050, channels=2)
            info = mediainfo.probe(path.read_bytes(), ".wav")
        self.assertAlmostEqual(info.duration, 0.5, places=3)
        self.assertEqual((info.sample_rate, info.channels), (22050, 2))

    def test_flac(self):
        rate, channels, samples = 44100, 2, 44100 * 3
        packed = (rate << 44) | ((channels - 1) << 41) | (15 << 36) | samples
        info_block = b"\x00" * 10 + packed.to_bytes(8, "big") + b"\x00" * 16
        data = b"fLaC" + b"\x00\x00\x00\x22" + info_block
        info = mediainfo.probe(data, ".flac")
        self.assertEqual((info.sample_rate, info.channels), (44100, 2))
        self.assertAlmostEqual(info.duration, 3.0)

    def test_ogg_vorbis(self):
        ident = b"\x01vorbis" + struct.pack("<IBI", 0, 2, 44100) + b"\x00" * 16
        first = b"OggS" + b"\x00\x02" + struct.pack("<q", 0) + b"\x00" * 12 + bytes([1, len(ident)]) + ident
        last = b"OggS" + b"\x00\x04" + struct.pack("<q", 44100 * 5) + b"\x00" * 13
        info = mediainfo.probe(first + last, ".ogg")
        self.assertEqual(info.format, "ogg/vorbis")
        self.assertAlmostEqual(info.duration, 5.0)

    def test_mp3_with_a_xing_header(self):
        header = struct.pack(">I", 0xFFFB9064)  # MPEG-1 layer III, 128 kbps, 44.1 kHz, joint stereo
        xing = b"Xing" + struct.pack(">II", 1, 1000)
        data = header + b"\x00" * 32 + xing + b"\x00" * 400
        info = mediainfo.probe(data, ".mp3")
        self.assertAlmostEqual(info.duration, 1000 * 1152 / 44100, places=3)

    def test_images(self):
        jpeg = b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 4) + b"\x00\x00" + b"\xff\xc0" + struct.pack(
            ">HBHH", 11, 8, 300, 640) + b"\x00" * 6
        self.assertEqual((mediainfo.probe(jpeg, ".jpg").width, mediainfo.probe(jpeg, ".jpg").height), (640, 300))
        bmp = b"BM" + b"\x00" * 16 + struct.pack("<ii", 32, -16)
        self.assertEqual((mediainfo.probe(bmp, ".bmp").width, mediainfo.probe(bmp, ".bmp").height), (32, 16))
        tga = bytes([0, 0, 2]) + b"\x00" * 9 + struct.pack("<HH", 64, 48) + b"\x00\x00"
        self.assertEqual((mediainfo.probe(tga, ".tga").width, mediainfo.probe(tga, ".tga").height), (64, 48))

    def test_wrong_or_cut_short_files(self):
        with self.assertRaises(mediainfo.ProbeError):
            mediainfo.probe(b"hello", ".png")
        with self.assertRaises(mediainfo.ProbeError):
            mediainfo.probe(b"RIFF\x00\x00", ".wav")
        with self.assertRaises(mediainfo.ProbeError):
            mediainfo.probe(b"data", ".gif")


if __name__ == "__main__":
    unittest.main()
