#!/usr/bin/env python3
"""new-game: make a game folder for you and your child from this kit.

    python3 new-game.py ~/Games/our-game
    python3 new-game.py ~/Games/our-game --name "Our Game"

It copies the starter game (template/), the Claude skills (skills/ → .claude/skills/), the picker
(picker/ → tools/picker/) and the publishing tools (tools/ → tools/), names the game, and makes the folder a git
repository with a first commit, so every change Claude makes can be seen and undone.

Standard library only, Python 3.9 or later.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
TEMPLATE_NAME = "SparkGarden"  # the template's project name, replaced with the new game's name
TEMPLATE_TITLE = "Spark Garden"  # the template's display name
# Files in the template that carry the game's name: (path, text to replace, "project" or "title")
NAME_FILES = [
    ("default.project.json", f'"name": "{TEMPLATE_NAME}"', "project"),
    ("src/shared/Config.luau", f'Config.GAME_NAME = "{TEMPLATE_TITLE}"', "title"),
]
CACHES = ("__pycache__", "*.pyc", ".DS_Store")
TEMPLATE_SKIP = shutil.ignore_patterns(*CACHES, "*.rbxl", "*.rbxlx")
# The kit's own tests and generated or per-game files stay behind when the picker and tools are copied
TOOL_SKIP = shutil.ignore_patterns(*CACHES, "tests", "out", "dump", "picks.json", "PICKS.md", "picks.resolved.json",
                                   "history.json", "uploaded.json", "roblox.json")


def pascal(name: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", name)
    joined = "".join(w[:1].upper() + w[1:] for w in words)
    if not joined or not joined[0].isalpha():
        joined = "Game" + joined
    return joined


def title_from_folder(folder: Path) -> str:
    words = re.findall(r"[A-Za-z0-9]+", folder.name)
    return " ".join(w[:1].upper() + w[1:] for w in words) or "Our Game"


def copy_tree(src: Path, dest: Path, ignore=TOOL_SKIP):
    shutil.copytree(src, dest, ignore=ignore, dirs_exist_ok=True)


def rename_game(dest: Path, title: str) -> list[str]:
    """Put the new game's name into the files that carry the template's name. Returns the files changed."""
    changed = []
    names = {"project": pascal(title), "title": title.replace('"', "")}
    for rel, old, kind in NAME_FILES:
        path = dest / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        current = TEMPLATE_NAME if kind == "project" else TEMPLATE_TITLE
        new = text.replace(old, old.replace(current, names[kind]))
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(rel)
    return changed


def git(dest: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=dest, capture_output=True, text=True)


def make_game(dest: Path, title: str, init_git: bool = True) -> dict:
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"{dest} already exists and isn't empty. Pick a new folder name.")
    dest.mkdir(parents=True, exist_ok=True)

    copy_tree(KIT / "template", dest, ignore=TEMPLATE_SKIP)
    for skill in sorted((KIT / "skills").iterdir()):
        if (skill / "SKILL.md").exists():
            copy_tree(skill, dest / ".claude" / "skills" / skill.name)
    copy_tree(KIT / "picker", dest / "tools" / "picker")
    for tool in ("publish", "upload"):
        copy_tree(KIT / "tools" / tool, dest / "tools" / tool)
    for folder in ("assets/audio", "assets/images"):
        (dest / folder).mkdir(parents=True, exist_ok=True)
        (dest / folder / ".gitkeep").touch()
    renamed = rename_game(dest, title)

    committed = False
    if init_git and shutil.which("git"):
        git(dest, "init", "-q")
        git(dest, "add", "-A")
        result = git(dest, "commit", "-q", "-m", f"chore: start {title} from build-a-roblox-game")
        committed = result.returncode == 0
    return {"renamed": renamed, "committed": committed, "project": pascal(title)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", help="where to make the game folder, for example ~/Games/our-game")
    parser.add_argument("--name", help="the game's name (default: from the folder name). You can change it later")
    parser.add_argument("--no-git", action="store_true", help="don't make a git repository")
    args = parser.parse_args(argv)

    dest = Path(args.folder).expanduser().resolve()
    title = args.name or title_from_folder(dest)
    info = make_game(dest, title, init_git=not args.no_git)

    print(f"Made “{title}” in {dest}")
    print("  starter game, Claude skills (/dream /pick /build /playtest /publish /safety-check), picker and tools")
    if not args.no_git:
        print("  git repository: " + ("first commit made" if info["committed"] else
                                      "created, but the first commit failed (set your git name and email, then "
                                      "run `git commit -m start`)"))
    print("\nNext, in a terminal:")
    print(f"  cd {dest}")
    print("  rokit install")
    print("  rojo plugin install")
    print("  rojo build -o Game.rbxlx")
    print("Then open Game.rbxlx in Roblox Studio, run `rojo serve`, connect Rojo, press Play, and start `claude`.")
    print("The guide's chapter 1 walks through each step: guide/01-get-ready.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
