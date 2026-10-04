"""Tests for new-game.py: the game folder a parent starts from.

Run from the repo root: python3 -m unittest discover -s tests
"""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("new_game", KIT / "new-game.py")
new_game = importlib.util.module_from_spec(spec)
spec.loader.exec_module(new_game)


class NameTests(unittest.TestCase):
    def test_pascal_case_names(self):
        cases = {"Spark Garden": "SparkGarden", "our-game": "OurGame", "gun flower 2": "GunFlower2",
                 "3 little pigs": "Game3LittlePigs", "!!!": "Game"}
        for given, want in cases.items():
            with self.subTest(given):
                self.assertEqual(new_game.pascal(given), want)

    def test_title_from_folder(self):
        self.assertEqual(new_game.title_from_folder(Path("/x/our-cool_game")), "Our Cool Game")


class MakeGameTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.dest = self.tmp / "our-game"
        # A throwaway git identity, so the first commit works anywhere
        self.env = {k: os.environ.get(k) for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME",
                                                   "GIT_COMMITTER_EMAIL")}
        os.environ.update({"GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
                           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def make(self, *args):
        with redirect_stdout(StringIO()):
            return new_game.main([str(self.dest), *args])

    def test_folder_has_the_game_skills_picker_and_tools(self):
        # Act
        self.assertEqual(self.make("--name", "Rainbow Rush"), 0)
        # Assert
        d = self.dest
        for rel in ["default.project.json", "CLAUDE.md", "SPEC.md", "ARCHITECTURE.md", "tests/run.luau",
                    "src/server/Main.server.luau", "tools/playtest/run.py",
                    ".claude/skills/pick/SKILL.md", ".claude/skills/dream/SKILL.md", ".claude/skills/publish/SKILL.md",
                    "tools/picker/picker.py", "tools/picker/CONTRACT.md", "tools/picker/assets/picker.js",
                    "tools/picker/sample/round.json", "tools/publish/publish.py", "tools/publish/opencloud.py",
                    "tools/upload/upload.py", "assets/audio/.gitkeep", "assets/images/.gitkeep"]:
            self.assertTrue((d / rel).exists(), f"missing {rel}")
        # The kit's own tests and generated files stay behind
        for rel in ["tools/picker/tests", "tools/publish/tests", "tools/upload/tests", "tools/picker/sample/out"]:
            self.assertFalse((d / rel).exists(), f"{rel} shouldn't be copied")
        self.assertFalse(list(d.rglob("__pycache__")))

    def test_the_game_is_renamed(self):
        self.make("--name", "Rainbow Rush")
        project = json.loads((self.dest / "default.project.json").read_text())
        self.assertEqual(project["name"], "RainbowRush")
        config = (self.dest / "src/shared/Config.luau").read_text()
        self.assertIn('Config.GAME_NAME = "Rainbow Rush"', config)

    def test_git_repository_with_a_first_commit(self):
        if not shutil.which("git"):
            self.skipTest("git isn't installed")
        self.make()
        log = new_game.git(self.dest, "log", "--oneline").stdout
        self.assertIn("chore: start Our Game from build-a-roblox-game", log)
        self.assertEqual(new_game.git(self.dest, "status", "--porcelain").stdout.strip(), "")

    def test_no_git_option(self):
        self.make("--no-git")
        self.assertFalse((self.dest / ".git").exists())

    def test_every_skill_is_valid_and_its_paths_exist_in_the_game(self):
        import re
        import subprocess
        import sys

        # Files the tools write the first time they run, so a new game doesn't have them yet
        generated = {"tools/roblox.json", "tools/publish/history.json", "tools/upload/uploaded.json",
                     "src/shared/AssetIds.luau"}
        self.make()
        skills = sorted((self.dest / ".claude" / "skills").iterdir())
        self.assertEqual([s.name for s in skills], ["build", "dream", "pick", "playtest", "publish", "safety-check"])
        for skill in skills:
            with self.subTest(skill.name):
                text = (skill / "SKILL.md").read_text()
                front = re.match(r"^---\n(.*?)\n---\n", text, re.S)
                self.assertIsNotNone(front, "no frontmatter")
                fields = dict(line.split(": ", 1) for line in front.group(1).splitlines() if ": " in line)
                self.assertEqual(fields.get("name"), skill.name)
                self.assertGreater(len(fields.get("description", "")), 40)
                # Every tool or game file a skill tells Claude to use must exist in a new game folder
                for rel in set(re.findall(r"`((?:tools|src|design|tests)/[\w./-]+?\.(?:py|luau|md|json))`", text)):
                    if "<" not in rel and rel not in generated:
                        self.assertTrue((self.dest / rel).exists(), f"{skill.name} mentions {rel}, which doesn't exist")
        self.assertIn("disable-model-invocation: true", (self.dest / ".claude/skills/publish/SKILL.md").read_text())
        # /pick's commands work from the game folder against the copied picker
        picker = [sys.executable, "tools/picker/picker.py"]
        for command in ("check", "build", "read", "approved"):
            result = subprocess.run([*picker, command, "tools/picker/sample"], cwd=self.dest, capture_output=True,
                                    text=True)
            self.assertEqual(result.returncode, 0, f"picker {command}: {result.stdout}{result.stderr}")
        self.assertTrue((self.dest / "tools/picker/sample/out/picker.html").exists())

    def test_refuses_a_folder_that_isnt_empty(self):
        self.dest.mkdir()
        (self.dest / "precious.txt").write_text("keep me")
        with self.assertRaises(SystemExit):
            self.make()
        self.assertEqual((self.dest / "precious.txt").read_text(), "keep me")


if __name__ == "__main__":
    unittest.main()
