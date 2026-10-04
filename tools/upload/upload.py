#!/usr/bin/env python3
"""upload: turn the game's sounds and pictures into Roblox asset ids, through Open Cloud.

    python3 tools/upload/upload.py plan               # check every file in assets/; sends nothing
    python3 tools/upload/upload.py upload             # upload what's new or changed (asks first; safe to rerun)
    python3 tools/upload/upload.py status [--refresh] # what's uploaded; --refresh asks Roblox about moderation

Sounds go in assets/audio/ (.ogg, .mp3, .wav, .flac) and pictures in assets/images/ (.png, .jpg, .bmp, .tga). Each
file's name becomes its name in the game, so call them things like Yay.ogg or WandIcon.png. The ids land in
src/shared/AssetIds.luau (use them as AssetIds.Audio.Yay) and the record of what's uploaded in
tools/upload/uploaded.json. Commit both. Standard library only. See tools/upload/README.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
import urllib.parse
import uuid
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "publish"))
import mediainfo  # noqa: E402
from opencloud import (  # noqa: E402
    ApiError,
    OpenCloud,
    ToolError,
    ask,
    creator_of,
    default_root,
    get_api_key,
    load_config,
)

# Limits as of October 2026: https://create.roblox.com/docs/cloud/guides/usage-assets
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
AUDIO_MAX_SECONDS = 7 * 60
AUDIO_MAX_SAMPLE_RATE = 48_000
AUDIO_CHANNELS = {1, 2, 3, 6}  # mono, stereo, 3.0 and 5.1
IMAGE_MAX_SIDE = 8000  # "smaller than 8000x8000"
NAME_MAX = 50  # Roblox's display-name limit
LUAU_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

CONTENT_TYPES = {
    ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav", ".flac": "audio/flac",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".bmp": "image/bmp", ".tga": "image/tga",
}
# folder under assets/, the table in AssetIds.luau, the Roblox asset type, the file extensions
KINDS = {
    "Audio": ("audio", "Audio", {".mp3", ".ogg", ".wav", ".flac"}),
    "Image": ("images", "Images", {".png", ".jpg", ".jpeg", ".bmp", ".tga"}),
}
STATE_NAME = "uploaded.json"
LUAU_PATH = Path("src") / "shared" / "AssetIds.luau"

AUTH_HELP = ("Roblox didn't accept the API key. Check that it has the Assets API with Read and Write, that it hasn't "
             "expired, and that your current IP address is on its allowed list (tools/upload/README.md, step 1).")
AUDIO_REMINDER = """
Two things before the sounds work for players:
  1. Each new sound plays only after Roblox's moderation approves it (usually minutes). `status --refresh` shows it.
  2. Studio plays every sound because you're signed in as the owner, but players' devices may not. If a sound is
     silent in the live game, open the sound in Creator Hub → Permissions → Experiences and give your game Use
     permission, even though you own both. Then check the live Error Report (your game → Monitoring → Error Report)
     after the next publish: "User is not authorized to access Asset" means a sound still needs it."""


@dataclass
class Item:
    kind: str  # "Audio" or "Image"
    name: str
    path: Path
    rel: str
    data: bytes = b""
    sha256: str = ""
    info: mediainfo.MediaInfo | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{KINDS[self.kind][1]}/{self.name}"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------------------------------------------
# Scanning and checking


def check(item: Item) -> None:
    """Read the file and check it against the upload limits."""
    if not LUAU_NAME.match(item.name):
        item.errors.append("rename it using only letters, digits and _ (starting with a letter), e.g. Yay_Sound"
                           f"{item.path.suffix}, so the game can use it as AssetIds.{KINDS[item.kind][1]}.<name>")
    elif len(item.name) > NAME_MAX:
        item.errors.append(f"the name is {len(item.name)} characters; Roblox allows {NAME_MAX}")
    try:
        item.data = item.path.read_bytes()
    except OSError as exc:
        item.errors.append(f"can't read the file ({exc.strerror})")
        return
    item.sha256 = hashlib.sha256(item.data).hexdigest()
    if not item.data:
        item.errors.append("the file is empty")
        return
    if len(item.data) > MAX_UPLOAD_BYTES:
        item.errors.append(f"{len(item.data) / 1048576:.1f} MB is over the 20 MB upload limit")
    try:
        info = item.info = mediainfo.probe(item.data, item.path.suffix)
    except mediainfo.ProbeError as exc:
        item.errors.append(str(exc))
        return
    if item.kind == "Audio":
        if info.duration is None:
            item.warnings.append("couldn't work out how long it is")
        elif info.duration > AUDIO_MAX_SECONDS:
            item.errors.append(f"it's {info.duration / 60:.1f} minutes long; Roblox allows 7")
        if info.sample_rate and info.sample_rate > AUDIO_MAX_SAMPLE_RATE:
            item.errors.append(f"its sample rate is {info.sample_rate} Hz; Roblox allows up to 48 kHz")
        if info.channels and info.channels not in AUDIO_CHANNELS:
            item.errors.append(f"it has {info.channels} channels; Roblox takes mono, stereo, 3.0 or 5.1")
    elif not info.width or not info.height:
        item.errors.append("the picture has no size")
    elif info.width >= IMAGE_MAX_SIDE or info.height >= IMAGE_MAX_SIDE:
        item.errors.append(f"it's {info.width}x{info.height}; Roblox needs smaller than 8000x8000")


def scan(root: Path, only: set[str]) -> list[Item]:
    items = []
    for kind, (folder, _table, exts) in KINDS.items():
        directory = root / "assets" / folder
        if not directory.is_dir():
            continue
        found = sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in exts)
        stems: dict[str, int] = {}
        for p in found:
            stems[p.stem.lower()] = stems.get(p.stem.lower(), 0) + 1
        for path in found:
            if only and path.stem not in only:
                continue
            item = Item(kind, path.stem, path, path.relative_to(root).as_posix())
            check(item)
            if stems[path.stem.lower()] > 1:
                item.errors.append(f"another file in assets/{folder} has the same name; names must be unique")
            items.append(item)
        ignored = [p.name for p in directory.iterdir() if p.is_file() and p.suffix.lower() not in exts
                   and not p.name.startswith(".")]
        if ignored:
            print(f"(skipping files in assets/{folder} that can't be uploaded: {', '.join(sorted(ignored))})")
    return items


# ---------------------------------------------------------------------------------------------------------------
# State and outputs


def state_path(root: Path) -> Path:
    return root / "tools" / "upload" / STATE_NAME


def load_state(root: Path) -> dict:
    path = state_path(root)
    if not path.exists():
        return {"assets": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ToolError(f"{path.relative_to(root)} isn't valid JSON ({exc}). Fix or restore it from git.") from None
    state.setdefault("assets", {})
    return state


def luau_module(state: dict) -> str:
    tables: dict[str, dict[str, str]] = {table: {} for _folder, table, _exts in KINDS.values()}
    for key, entry in state["assets"].items():
        table, _, name = key.partition("/")
        if table in tables and entry.get("assetId") and LUAU_NAME.match(name):
            tables[table][name] = f"rbxassetid://{entry['assetId']}"
    lines = [
        "-- AssetIds: every uploaded sound and picture, by name. Written by tools/upload/upload.py, not by hand.",
        "-- Use it like: sound.SoundId = AssetIds.Audio.Yay",
        "return {",
    ]
    for table, ids in tables.items():
        if not ids:
            lines.append(f"\t{table} = {{}},")
            continue
        lines.append(f"\t{table} = {{")
        lines += [f'\t\t{name} = "{ids[name]}",' for name in sorted(ids, key=str.lower)]
        lines.append("\t},")
    lines.append("}")
    return "\n".join(lines) + "\n"


def save(root: Path, state: dict) -> None:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    luau = root / LUAU_PATH
    luau.parent.mkdir(parents=True, exist_ok=True)
    luau.write_text(luau_module(state), encoding="utf-8")


def decide(item: Item, entry: dict | None) -> tuple[str, str]:
    """(action, reason). Actions: invalid, resume, skip, upload."""
    if item.errors:
        return "invalid", "; ".join(item.errors)
    if entry and entry.get("pending"):
        return "resume", "was still processing at Roblox last time; will collect it"
    if entry and entry.get("assetId"):
        if entry.get("sha256") == item.sha256:
            return "skip", f"uploaded (rbxassetid://{entry['assetId']})"
        return "upload", "changed since it was uploaded, so it goes up as a new asset"
    return "upload", "new"


# ---------------------------------------------------------------------------------------------------------------
# Talking to Open Cloud


def multipart(request: dict, filename: str, content_type: str, data: bytes) -> tuple[bytes, str]:
    boundary = f"barg-{uuid.uuid4().hex}"
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    body = b"".join([
        f'--{boundary}\r\nContent-Disposition: form-data; name="request"\r\n\r\n'.encode(),
        json.dumps(request).encode(),
        f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="fileContent"; filename="{safe_name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        data,
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    return body, f"multipart/form-data; boundary={boundary}"


def operation_id_of(op: dict) -> str:
    op_id = op.get("operationId") or str(op.get("path", "")).rsplit("/", 1)[-1]
    if not op_id:
        raise ApiError(0, f"Roblox didn't say how to follow the upload: {json.dumps(op)[:200]}")
    return op_id


def asset_digits(value) -> str | None:
    match = re.fullmatch(r"(?:rbxassetid://)?(\d+)", str(value or "").strip())
    return match.group(1) if match else None


def finish(client: OpenCloud, entry: dict, timeout: float, sleep, clock=time.monotonic) -> str:
    """Follow the entry's pending upload until it's done. Returns "done", "failed" or "pending"."""
    pending = entry["pending"]
    delay, deadline = 1.0, clock() + timeout
    while True:
        op = client.request("GET", f"/assets/v1/operations/{urllib.parse.quote(pending['operationId'], safe='')}")
        if op.get("done"):
            break
        if clock() + delay > deadline:
            print("    still processing at Roblox; run `upload` again later to collect it")
            return "pending"
        sleep(delay)
        delay = min(delay * 1.5, 10.0)
    entry.pop("pending")
    if op.get("error"):
        error = op["error"]
        message = error.get("message", json.dumps(error)) if isinstance(error, dict) else str(error)
        entry["lastError"] = client.redact(str(message))[:300]
        print(f"    FAILED: {entry['lastError']}")
        return "failed"
    response = op.get("response") or {}
    asset_id = asset_digits(response.get("assetId") or str(response.get("path", "")).rsplit("/", 1)[-1])
    if not asset_id:
        entry["lastError"] = "Roblox finished the upload without giving an asset id"
        print(f"    FAILED: {entry['lastError']}")
        return "failed"
    if entry.get("assetId") and entry["assetId"] != asset_id:
        entry.setdefault("history", []).append({"assetId": entry["assetId"], "sha256": entry.get("sha256"),
                                                "replacedAt": now_iso()})
    entry.update({
        "assetId": asset_id,
        "sha256": pending["sha256"],
        "kind": pending["kind"],
        "file": pending["file"],
        "uploadedAt": now_iso(),
        "moderation": (response.get("moderationResult") or {}).get("moderationState"),
    })
    entry.pop("lastError", None)
    moderation = f" (moderation: {entry['moderation']})" if entry.get("moderation") else ""
    print(f"    rbxassetid://{asset_id}{moderation}")
    return "done"


# ---------------------------------------------------------------------------------------------------------------
# Commands


def describe(item: Item) -> str:
    info = item.info
    if not info:
        return ""
    if info.kind == "audio":
        length = f"{info.duration:.1f} s" if info.duration is not None else "? s"
        return f"{info.format}, {length}, {len(item.data) / 1024:.0f} KB"
    return f"{info.format}, {info.width}x{info.height}, {len(item.data) / 1024:.0f} KB"


def cmd_plan(args) -> int:
    root = args.root
    items = scan(root, args.only)
    if not items:
        print("Nothing to check: put sounds in assets/audio/ and pictures in assets/images/.")
        return 0
    state = load_state(root)
    counts: dict[str, int] = {}
    new_audio = 0
    labels = {"upload": "UPLOAD", "resume": "COLLECT", "skip": "done", "invalid": "ERROR"}
    for item in items:
        action, reason = decide(item, state["assets"].get(item.key))
        counts[action] = counts.get(action, 0) + 1
        new_audio += action == "upload" and item.kind == "Audio"
        print(f"  {labels[action]:<8} {item.rel:<36} {describe(item):<28} {reason}")
        for warning in item.warnings:
            print(f"           warning: {warning}")
    print(f"\n{counts.get('upload', 0)} to upload, {counts.get('resume', 0)} to collect, {counts.get('skip', 0)} "
          f"already done, {counts.get('invalid', 0)} with problems. Nothing was sent to Roblox.")
    if new_audio:
        print("Open Cloud allows 10 new sounds a month, or 100 once your account is ID-verified (as of October 2026).")
    return 1 if counts.get("invalid") else 0


def cmd_upload(args) -> int:
    root = args.root
    items = scan(root, args.only)
    state = load_state(root)
    work, invalid = [], []
    for item in items:
        action, reason = decide(item, state["assets"].get(item.key))
        if action == "invalid":
            invalid.append(item)
            print(f"  ERROR {item.rel}: {reason}")
        elif action in ("upload", "resume"):
            work.append((item, action, reason))
    new = [w for w in work if w[1] == "upload"]
    if args.limit is not None and len(new) > args.limit:
        held = {id(w[0]) for w in new[args.limit:]}
        work = [w for w in work if id(w[0]) not in held]
        print(f"  ({len(held)} held back by --limit)")
        new = new[:args.limit]
    if not work:
        print("Nothing to upload." + (" Fix the errors above first." if invalid else ""))
        save(root, state)
        return 1 if invalid else 0

    config = load_config(root)
    creator = creator_of(config)
    owner = f"group {creator['groupId']}" if "groupId" in creator else f"user {creator['userId']}"
    print(f"Will upload {len(new)} new file(s) owned by {owner}"
          + (f" and collect {len(work) - len(new)} that were still processing" if len(work) > len(new) else "") + ":")
    for item, _action, reason in work:
        print(f"  {item.rel:<36} {reason}")
    if new and not ask("Go ahead?", yes=args.yes):
        print("Stopped. Nothing was uploaded.")
        return 1
    key, source = get_api_key(config["keychainService"])
    print(f"Using the API key from {source}.")
    client = OpenCloud(key, sleep=args.sleep)

    results = {"done": 0, "failed": 0, "pending": 0}
    audio_done = False
    for index, (item, action, _reason) in enumerate(work, 1):
        entry = state["assets"].setdefault(item.key, {"kind": item.kind, "file": item.rel})
        print(f"[{index}/{len(work)}] {item.rel}")
        try:
            if action == "resume":
                outcome = finish(client, entry, args.poll_timeout, args.sleep)
                save(root, state)
                if outcome != "done" or entry.get("sha256") == item.sha256:
                    results[outcome] += 1
                    audio_done |= outcome == "done" and item.kind == "Audio"
                    continue
                print("    the file changed while that upload was processing; uploading the new version")
            asset_type = args.image_type if item.kind == "Image" else "Audio"
            request = {
                "assetType": asset_type,
                "displayName": item.name,
                "description": f"{item.name}, uploaded with tools/upload/upload.py",
                "creationContext": {"creator": creator, "expectedPrice": 0},
            }
            body, content_type = multipart(request, item.path.name, CONTENT_TYPES[item.path.suffix.lower()],
                                           item.data)
            op = client.request("POST", "/assets/v1/assets", body=body, content_type=content_type,
                                retry_creates=False)
            entry["pending"] = {"operationId": operation_id_of(op), "sha256": item.sha256, "kind": item.kind,
                                "file": item.rel, "startedAt": now_iso()}
            save(root, state)
            outcome = finish(client, entry, args.poll_timeout, args.sleep)
            results[outcome] += 1
            audio_done |= outcome == "done" and item.kind == "Audio"
        except ApiError as exc:
            save(root, state)
            if exc.status in (401, 403):
                raise ToolError(f"{AUTH_HELP}\n(Roblox's message: {exc.message})", 3) from None
            entry["lastError"] = str(exc)[:300]
            results["failed"] += 1
            print(f"    FAILED: {exc}")
        save(root, state)

    print(f"\nDone: {results['done']} uploaded, {results['pending']} still processing, {results['failed']} failed. "
          f"Ids are in {LUAU_PATH.as_posix()} and tools/upload/{STATE_NAME}.")
    if audio_done:
        print(AUDIO_REMINDER)
    return 0 if not (results["failed"] or invalid) else 1


def cmd_status(args) -> int:
    root = args.root
    state = load_state(root)
    if not state["assets"]:
        print("Nothing uploaded yet.")
        return 0
    client = None
    if args.refresh:
        config = load_config(root)
        key, source = get_api_key(config["keychainService"])
        print(f"Using the API key from {source}.")
        client = OpenCloud(key, sleep=args.sleep)
    for key_name in sorted(state["assets"], key=str.lower):
        entry = state["assets"][key_name]
        if client:
            try:
                if entry.get("pending"):
                    finish(client, entry, 0, args.sleep)
                elif entry.get("assetId"):
                    asset = client.request("GET", f"/assets/v1/assets/{entry['assetId']}?readMask=moderationResult")
                    entry["moderation"] = (asset.get("moderationResult") or {}).get("moderationState")
            except ApiError as exc:
                if exc.status in (401, 403):
                    save(root, state)
                    raise ToolError(f"{AUTH_HELP}\n(Roblox's message: {exc.message})", 3) from None
                print(f"  couldn't refresh {key_name}: {exc}")
        if entry.get("pending"):
            shown = "still processing"
        elif entry.get("assetId"):
            shown = f"rbxassetid://{entry['assetId']}" + (f"  ({entry['moderation']})" if entry.get("moderation")
                                                          else "")
        else:
            shown = f"not uploaded: {entry.get('lastError', 'unknown')}"
        print(f"  {key_name:<30} {shown}")
    if client:
        save(root, state)
    return 0


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=lambda p: Path(p).expanduser().resolve(), default=default_root(),
                        help=argparse.SUPPRESS)
    common.add_argument("--only", action="append", default=[], metavar="NAMES",
                        help="only these files, by name without the extension (comma-separated, repeatable)")
    parser = argparse.ArgumentParser(prog="upload.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", parents=[common], help="check the files and show what would be uploaded")
    plan.set_defaults(fn=cmd_plan)
    up = sub.add_parser("upload", parents=[common], help="upload anything new or changed (safe to rerun)")
    up.add_argument("--yes", action="store_true", help="don't ask first")
    up.add_argument("--limit", type=int, help="upload at most this many new files this time")
    up.add_argument("--poll-timeout", type=float, default=300.0, help="seconds to wait for each upload (default 300)")
    up.add_argument("--image-type", choices=("Image", "Decal"), default="Image",
                    help="what pictures become: Image ids go straight into ImageLabel.Image (default)")
    up.set_defaults(fn=cmd_upload)
    st = sub.add_parser("status", parents=[common], help="show what's uploaded")
    st.add_argument("--refresh", action="store_true", help="ask Roblox about moderation and unfinished uploads")
    st.set_defaults(fn=cmd_status)
    return parser


def main(argv: list[str] | None = None, *, sleep=None) -> int:
    args = build_parser().parse_args(argv)
    args.only = {name.strip() for value in args.only for name in value.split(",") if name.strip()}
    args.sleep = sleep or time.sleep
    try:
        return args.fn(args)
    except ToolError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        print("\nStopped. Anything already uploaded is recorded; run `upload` again to carry on.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
