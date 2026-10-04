#!/usr/bin/env python3
"""publish: put a new version of the game live on Roblox, through Open Cloud, without clicking through Studio.

    python3 tools/publish/publish.py setup --universe <id> --place <id> --user <id>   # once, after the first publish
    python3 tools/publish/publish.py --dry-run          # build the place and say what would happen; sends nothing
    python3 tools/publish/publish.py --note "new wand"  # build, ask, publish
    python3 tools/publish/publish.py history            # what's been published from here

The first publish always happens in Studio (File → Publish to Roblox), because that creates the game. This tool
publishes every version after that. It builds the place from src/ with Rojo, so close any Studio window that has the
game open first. Standard library only. See tools/publish/README.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from opencloud import (  # noqa: E402
    DIGITS,
    ApiError,
    OpenCloud,
    ToolError,
    ask,
    config_path,
    default_keychain_service,
    default_root,
    get_api_key,
    load_config,
)

PUBLISH_PATH = "/universes/v1/{universe}/places/{place}/versions?versionType=Published"
HISTORY_NAME = "history.json"

BUSY_HELP = ("Roblox said the place is busy (409). That nearly always means a Studio window has this game open "
             "(Team Create keeps it locked). Close the Studio window that has this game open, then try again.")
AUTH_HELP = ("Roblox didn't accept the API key. Check that it has the Place Publishing API with Write for this "
             "game, that it hasn't expired, and that your current IP address is on its allowed list "
             "(tools/publish/README.md, step 2).")


def history_path(root: Path) -> Path:
    return root / "tools" / "publish" / HISTORY_NAME


def find_rojo(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    found = shutil.which("rojo")
    if found:
        return found
    rokit = Path.home() / ".rokit" / "bin" / ("rojo.exe" if os.name == "nt" else "rojo")
    if rokit.exists():
        return str(rokit)
    raise ToolError("Can't find Rojo. Run `rokit install` in the game folder, then try again.")


def build_place(root: Path, rojo: str, out: Path) -> None:
    result = subprocess.run([rojo, "build", "-o", str(out)], cwd=root, capture_output=True, text=True)
    if result.returncode != 0 or not out.exists():
        detail = (result.stdout + result.stderr).strip()[-1500:]
        raise ToolError(f"Rojo couldn't build the place:\n{detail}")


def git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    except FileNotFoundError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def read_history(root: Path) -> list:
    path = history_path(root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def write_history(root: Path, history: list) -> None:
    path = history_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=1) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------------------------------------------
# Commands


def cmd_setup(args) -> int:
    root = args.root
    ids = {"universeId": args.universe, "placeId": args.place, "userId": args.user}
    if args.group:
        ids["groupId"] = args.group
    bad = [k for k, v in ids.items() if not DIGITS.match(str(v))]
    if bad:
        raise ToolError(f"These should be numbers from Creator Hub: {', '.join(bad)}.")
    path = config_path(root)
    if path.exists() and not args.force:
        raise ToolError(f"{path.relative_to(root)} already exists. Add --force to replace it.")
    service = args.keychain_service or default_keychain_service(root)
    config = {**ids, "keychainService": service}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path.relative_to(root)}. It holds ids only, never the key, so it's safe to commit.")
    print("\nNext, store your Open Cloud API key (tools/publish/README.md, step 2):")
    if sys.platform == "darwin":
        print(f'  security add-generic-password -a "$USER" -s {service} -w')
    else:
        print("  set the ROBLOX_API_KEY environment variable for this terminal session only")
    print("Then try:  python3 tools/publish/publish.py --dry-run")
    return 0


def cmd_history(args) -> int:
    history = read_history(args.root)
    if not history:
        print("Nothing has been published with this tool yet.")
        return 0
    for row in history:
        dirty = " +changes" if row.get("dirty") else ""
        note = f"  {row['note']}" if row.get("note") else ""
        print(f"v{row.get('version', '?'):<5} {row.get('at', '')}  {row.get('commit') or 'no git'}{dirty}{note}")
    return 0


def cmd_publish(args) -> int:
    root = args.root
    config = load_config(root)
    universe, place = str(config["universeId"]), str(config["placeId"])

    with tempfile.TemporaryDirectory() as tmp:
        if args.file:
            path = Path(args.file).expanduser().resolve()
            if not path.is_file():
                raise ToolError(f"No place file at {path}.")
        else:
            path = Path(tmp) / f"{root.name}.rbxlx"
            print("Building the place from src/ with Rojo…")
            build_place(root, find_rojo(args.rojo), path)
        if path.suffix.lower() not in (".rbxlx", ".rbxl"):
            raise ToolError("The place file must be .rbxlx or .rbxl.")
        body = path.read_bytes()

        commit = git(root, "rev-parse", "--short", "HEAD")
        dirty = bool(git(root, "status", "--porcelain", "--", "src"))
        made_from = f"commit {commit}" if commit else "a folder that isn't a git repository"
        print(f"Place file: {path.name} ({len(body) / 1024:.0f} KB), made from {made_from}"
              + (", plus changes in src/ that aren't committed" if dirty else ""))
        print(f"Publishing to: game {universe}, place {place} (https://www.roblox.com/games/{place})")

        if args.dry_run:
            print("Dry run: nothing was sent to Roblox.")
            return 0
        if not ask("Publish this as the live version?", yes=args.yes):
            print("Stopped. Nothing was published.")
            return 1

        key, source = get_api_key(config["keychainService"])
        print(f"Using the API key from {source}.")
        client = OpenCloud(key, sleep=args.sleep)
        content_type = "application/xml" if path.suffix.lower() == ".rbxlx" else "application/octet-stream"
        try:
            result = client.request("POST", PUBLISH_PATH.format(universe=universe, place=place), body=body,
                                    content_type=content_type)
        except ApiError as exc:
            if exc.status == 409:
                raise ToolError(f"{BUSY_HELP}\n(Roblox's message: {exc.message})", 3) from None
            if exc.status in (401, 403):
                raise ToolError(f"{AUTH_HELP}\n(Roblox's message: {exc.message})", 3) from None
            if exc.status == 404:
                raise ToolError("Roblox can't find that game or place. Check the ids in tools/roblox.json against "
                                f"Creator Hub.\n(Roblox's message: {exc.message})", 3) from None
            raise ToolError(f"Publishing failed: {exc}", 3) from None

    version = result.get("versionNumber")
    print(f"Published version {version}. It's live for new servers now; players in old servers keep the old "
          "version until they rejoin.")
    print("Check the Error Report in Creator Hub in a few minutes (your game → Monitoring → Error Report). It's the "
          "only way to see errors on players' devices.")
    history = read_history(root)
    history.append({
        "version": version,
        "commit": commit or None,
        "dirty": dirty,
        "place": place,
        "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "note": args.note,
    })
    write_history(root, history)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="publish.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=lambda p: Path(p).expanduser().resolve(), default=default_root(),
                        help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command")

    pub = sub.add_parser("publish", help="build and publish a new live version (the default)")
    pub.add_argument("--dry-run", action="store_true", help="build and report, but send nothing")
    pub.add_argument("--yes", action="store_true", help="publish without asking")
    pub.add_argument("--note", default="", help="a note kept in tools/publish/history.json")
    pub.add_argument("--file", help="publish this .rbxlx or .rbxl instead of building src/")
    pub.add_argument("--rojo", help=argparse.SUPPRESS)
    pub.set_defaults(fn=cmd_publish)

    setup = sub.add_parser("setup", help="write tools/roblox.json with the game's ids (once)")
    setup.add_argument("--universe", required=True, help="the game's Universe ID")
    setup.add_argument("--place", required=True, help="the start place's Place ID")
    setup.add_argument("--user", required=True, help="your Roblox user id (the owner)")
    setup.add_argument("--group", help="a group id, only if a group owns the game")
    setup.add_argument("--keychain-service", help="Keychain name for the API key (default: <folder>-roblox-api-key)")
    setup.add_argument("--force", action="store_true", help="replace an existing tools/roblox.json")
    setup.set_defaults(fn=cmd_setup)

    hist = sub.add_parser("history", help="list what's been published from here")
    hist.set_defaults(fn=cmd_history)
    return parser


def main(argv: list[str] | None = None, *, sleep=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # `publish.py --dry-run` means `publish.py publish --dry-run` (a leading --root is skipped over)
    i = 0
    while i < len(argv) and argv[i].startswith("--root"):
        i += 1 if "=" in argv[i] else 2
    if i >= len(argv) or argv[i] not in {"publish", "setup", "history", "-h", "--help"}:
        argv.insert(min(i, len(argv)), "publish")
    args = build_parser().parse_args(argv)
    args.sleep = sleep or __import__("time").sleep
    try:
        return args.fn(args)
    except ToolError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
