#!/usr/bin/env python3
"""run: playtest scenarios for this game, driven through Roblox Studio's built-in MCP server.

    python3 tools/playtest/run.py smoke             # STARTS AND STOPS PLAY in the open Studio
    python3 tools/playtest/run.py smoke --dry-run   # prints the planned MCP calls, touches nothing
    python3 tools/playtest/run.py --list            # lists scenarios

A scenario is a JSON file in tools/playtest/scenarios/ with "steps" (run in order) and "cleanup" (always run).
Exit codes: 0 pass, 1 scenario failed, 2 setup problem (no Studio, bad scenario, helper missing).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SCENARIOS = HERE / "scenarios"

# Another MCP client to use instead of the one next to this file (it must define a compatible Client class)
HELPER_ENV = "STUDIO_PY"


def project_name() -> str:
    """The game's name from default.project.json, used to pick the right Studio window."""
    try:
        return json.loads((ROOT / "default.project.json").read_text())["name"]
    except (OSError, KeyError, json.JSONDecodeError):
        return ROOT.name

# Read LogService in a Play datamodel. Structured (message + type), and it starts empty when Play starts.
LOG_SNAPSHOT_LUAU = """\
local LogService = game:GetService("LogService")
local HttpService = game:GetService("HttpService")
local history = LogService:GetLogHistory()
local out = {}
for i = math.max(1, #history - 600), #history do
\tlocal entry = history[i]
\ttable.insert(out, { m = string.sub(entry.message, 1, 600), t = entry.messageType.Name, ts = entry.timestamp })
end
return HttpService:JSONEncode(out)"""

# Script paths that belong to this project (Rojo maps src/ onto these)
OUR_PATHS = (
    "ServerScriptService.",
    "ReplicatedStorage.Shared.",
    "StarterPlayer.StarterPlayerScripts.",
    ".PlayerScripts.",
)


class ScenarioError(Exception):
    """A step failed: the scenario result is FAIL."""


class SetupError(Exception):
    """Can't run at all (no Studio, missing helper, bad scenario file)."""


def our_tags() -> set[str]:
    """Bracket tags our scripts print with: [Main] and every module name under src/ ([Save], [Sparks] ...)."""
    tags = {"Main", project_name()}
    for path in (ROOT / "src").rglob("*.luau"):
        tags.add(path.name.split(".")[0])
    return tags


def is_ours(text: str, tags: set[str]) -> bool:
    if any(p in text for p in OUR_PATHS):
        return True
    match = re.match(r"^\s*\[([A-Za-z]+)\]", text)
    return bool(match and match.group(1) in tags)


def text_of(result: dict | None) -> str:
    if not result:
        return ""
    return "".join(item.get("text", "") for item in result.get("content", []) if item.get("type") == "text")


def parse_json_array(text: str):
    """execute_luau returns the value as text (sometimes quoted); pull the JSON array out of it."""
    for candidate in (text, _unquote(text)):
        start, end = candidate.find("["), candidate.rfind("]")
        if start != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def _unquote(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith('"') and stripped.endswith('"'):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return stripped
    return stripped


def play_state(text: str) -> bool | None:
    """True if Studio reports a running Play session, False if Edit only, None if the text is unclear.

    get_studio_state answers with lines like:
        - Current Studio Mode: Edit
        - Available DataModels: Edit
        - Focused DataModel in the viewport: Edit
    """
    mode = re.search(r"Current Studio Mode:\s*([A-Za-z]+)", text)
    if mode:
        return mode.group(1).lower() != "edit"
    models = re.search(r"Available DataModels:\s*([^\n]+)", text)
    if models:
        return bool(re.search(r"\b(Server|Client)\b", models.group(1)))
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        data = None
    if isinstance(data, dict):
        for key, value in data.items():
            if "play" in key.lower():
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() not in ("", "edit", "editing", "stopped", "none", "false", "idle")
    lowered = text.lower()
    if re.search(r"\b(server|client)\b", lowered):
        return True
    if re.search(r"\bedit\b", lowered):
        return False
    return None


def load_client_class(explicit: str | None):
    """The helper's Client class (preferred), else the vendored fallback next to this file."""
    for path in (explicit, os.environ.get(HELPER_ENV)):
        if path and Path(path).is_file():
            spec = importlib.util.spec_from_file_location("studio_helper", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "Client"):
                return module.Client, path
        elif path and path == explicit:
            raise SetupError(f"--studio-py {path} doesn't exist")
    sys.path.insert(0, str(HERE))
    from studio_client import Client  # noqa: E402

    return Client, str(HERE / "studio_client.py")


def helper_path_for_display(explicit: str | None) -> str:
    for path in (explicit, os.environ.get(HELPER_ENV)):
        if path and Path(path).is_file():
            return path
    return str(HERE / "studio_client.py")


def load_scenario(name: str) -> dict:
    path = Path(name)
    if not path.is_file():
        path = SCENARIOS / f"{name}.json"
    if not path.is_file():
        raise SetupError(f"no scenario {name!r} (looked for {path}); try --list")
    try:
        scenario = json.loads(path.read_text())
    except json.JSONDecodeError as err:
        raise SetupError(f"{path} isn't valid JSON: {err}") from err
    for step in scenario.get("steps", []) + scenario.get("cleanup", []):
        if step.get("op") not in OPS:
            raise SetupError(f"{path}: unknown op {step.get('op')!r} (known: {', '.join(sorted(OPS))})")
    scenario.setdefault("name", path.stem)
    return scenario


class Runner:
    def __init__(self, scenario: dict, args: argparse.Namespace):
        self.scenario = scenario
        self.args = args
        self.client = None
        self.studio_id = args.studio_id
        self.started_play = False
        self.t0 = time.time()
        self.tags = our_tags()
        self.report: dict = {"scenario": scenario["name"], "steps": [], "errors": [], "warnings": [], "result": None}
        self.console_baseline: str | None = None

    # MCP plumbing -----------------------------------------------------------------------------------------------------

    def log(self, message: str):
        print(f"[{time.time() - self.t0:6.1f}s] {message}", flush=True)

    def connect(self):
        client_class, path = load_client_class(self.args.studio_py)
        self.log(f"MCP helper: {path}")
        try:
            self.client = client_class()
            self.client.request("tools/list", {})  # makes the proxy wait for Studio to register its tools
            if not self.studio_id:
                self.studio_id = self.pick_studio()
        except SystemExit as err:  # the client reports MCP failures with SystemExit
            raise SetupError(f"couldn't talk to Studio's MCP server: {err}") from err
        self.log(f"Studio: {self.studio_id}")

    def pick_studio(self) -> str:
        text = text_of(self.client.call("list_roblox_studios", {}))
        try:
            data = json.loads(text)
        except json.JSONDecodeError as err:
            raise SetupError(f"list_roblox_studios gave unexpected output: {text[:300]}") from err
        studios = data if isinstance(data, list) else data.get("studios", data.get("instances", []))
        if not studios:
            raise SetupError(f"no Roblox Studio is connected to the MCP server (is Studio open with {project_name()}?)")
        if len(studios) == 1:
            return studios[0]["id"]
        # Several Studio windows: only ever pick this game's, never someone else's project
        names = {project_name(), *(p.stem for p in ROOT.glob("*.rbxl*"))}
        match = [s for s in studios if any(n and n in json.dumps(s) for n in names)]
        if len(match) == 1:
            return match[0]["id"]
        listing = "; ".join(json.dumps(s)[:120] for s in studios)
        raise SetupError(
            f"{len(studios)} Studio windows are open and {'none' if not match else 'more than one'} looks like this "
            f"game ({', '.join(sorted(names))}). Pass --studio-id to choose. Open: {listing}"
        )

    def call(self, tool: str, args: dict | None = None) -> dict:
        payload = dict(args or {})
        payload["studio_id"] = self.studio_id
        try:
            result = self.client.call(tool, payload)
        except SystemExit as err:
            raise ScenarioError(f"{tool} failed: {err}") from err
        return result or {}

    # Logs -------------------------------------------------------------------------------------------------------------

    def fetch_logs(self) -> list[dict]:
        """Log entries from the Server and Client datamodels; falls back to the Output window text."""
        entries: list[dict] = []
        readable = 0
        for datamodel in ("Server", "Client"):
            try:
                result = self.client.call(
                    "execute_luau",
                    {"studio_id": self.studio_id, "datamodel_type": datamodel, "code": LOG_SNAPSHOT_LUAU},
                )
            except SystemExit:
                continue
            rows = None if (result or {}).get("isError") else parse_json_array(text_of(result))
            if rows is None:
                continue
            readable += 1
            for row in rows:
                entries.append({"source": datamodel, "type": row.get("t", ""), "text": row.get("m", "")})
        if readable == 0:
            entries.extend(self.console_entries())
        return entries

    def console_entries(self) -> list[dict]:
        """Fallback: new lines of get_console_output since Play started. Types are guessed from the text."""
        try:
            text = text_of(self.client.call("get_console_output", {"studio_id": self.studio_id}))
        except SystemExit:
            return []
        if self.console_baseline and text.startswith(self.console_baseline):
            text = text[len(self.console_baseline) :]
        entries = []
        for line in text.splitlines():
            lowered = line.lower()
            if "error" in lowered or re.search(r":\d+: ", line):
                kind = "MessageError"
            elif "warn" in lowered:
                kind = "MessageWarning"
            else:
                kind = "MessageOutput"
            entries.append({"source": "console", "type": kind, "text": line})
        return entries

    # Ops --------------------------------------------------------------------------------------------------------------

    def op_check_edit_mode(self, step: dict):
        text = text_of(self.call("get_studio_state"))
        state = play_state(text)
        if state is None:
            self.log(f"check_edit_mode: couldn't read the play state, carrying on ({text[:120]!r})")
        elif state and not self.args.allow_playing:
            raise ScenarioError(
                "Studio is already in Play mode (someone else may be testing). "
                "Stop it first, or pass --allow-playing to use that session."
            )
        else:
            self.log("check_edit_mode: " + ("Play already running (allowed)" if state else "Studio is in Edit mode"))
        try:
            self.console_baseline = text_of(self.client.call("get_console_output", {"studio_id": self.studio_id}))
        except SystemExit:
            self.console_baseline = None

    def op_start_play(self, step: dict):
        state = play_state(text_of(self.call("get_studio_state")))
        if state and self.args.allow_playing:
            self.log("start_play: already playing, using that session")
            return
        result = self.call("start_stop_play", {"is_start": True})
        if result.get("isError"):
            raise ScenarioError(f"start_stop_play failed: {text_of(result)[:300]}")
        self.started_play = True
        self.log("start_play: Play started")

    def op_stop_play(self, step: dict):
        if not self.started_play:
            if not step.get("only_if_started"):
                self.log("stop_play: skipped (this run didn't start Play)")
            return
        result = self.call("start_stop_play", {"is_start": False})
        if result.get("isError"):
            raise ScenarioError(f"stop_play failed: {text_of(result)[:300]}")
        self.started_play = False
        self.log("stop_play: back in Edit mode")

    def op_sleep(self, step: dict):
        seconds = float(step.get("seconds", 1))
        self.log(f"sleep: {seconds:g}s")
        time.sleep(seconds)

    def op_wait_for_logs(self, step: dict):
        patterns = step["patterns"]
        timeout, poll = float(step.get("timeout", 60)), float(step.get("poll", 2))
        deadline = time.time() + timeout
        seen: dict[str, str] = {}
        entries: list[dict] = []
        while time.time() < deadline:
            entries = self.fetch_logs()
            for pattern in patterns:
                for entry in entries:
                    if pattern in entry["text"] and pattern not in seen:
                        seen[pattern] = entry["source"]
            if len(seen) == len(patterns):
                self.log("wait_for_logs: saw " + ", ".join(f"{p!r} ({s})" for p, s in seen.items()))
                return
            time.sleep(poll)
        missing = [p for p in patterns if p not in seen]
        errors = [e["text"] for e in entries if e["type"] == "MessageError" and is_ours(e["text"], self.tags)]
        hint = ("; latest errors: " + " | ".join(errors[-3:])) if errors else ""
        raise ScenarioError(f"timed out after {timeout:g}s waiting for {missing}{hint}")

    def op_collect_errors(self, step: dict):
        warn_patterns = [re.compile(p) for p in step.get("fail_on_warnings_matching", [])]
        entries = self.fetch_logs()
        errors, warnings, ignored = [], [], 0
        for entry in entries:
            ours = is_ours(entry["text"], self.tags)
            if entry["type"] == "MessageError":
                if ours:
                    errors.append(entry)
                else:
                    ignored += 1
            elif entry["type"] == "MessageWarning" and ours:
                if any(p.search(entry["text"]) for p in warn_patterns):
                    errors.append(entry)
                else:
                    warnings.append(entry)
        self.report["errors"] = errors
        self.report["warnings"] = warnings
        self.log(
            f"collect_errors: {len(errors)} error(s) from our scripts, {len(warnings)} warning(s), "
            f"{ignored} error(s) from other scripts ignored"
        )
        for entry in warnings:
            print(f"    warning ({entry['source']}): {entry['text']}")
        for entry in errors:
            print(f"    ERROR   ({entry['source']}): {entry['text']}")
        if errors:
            raise ScenarioError(f"{len(errors)} error(s) from our scripts")

    def op_execute_luau(self, step: dict):
        """Run a snippet; optional "expect" = substring the returned text must contain."""
        result = self.call("execute_luau", {"datamodel_type": step.get("datamodel", "Server"), "code": step["code"]})
        text = text_of(result)
        label = step.get("label", "execute_luau")
        if result.get("isError"):
            raise ScenarioError(f"{label}: {text[:300]}")
        expect = step.get("expect")
        if expect is not None and expect not in text:
            raise ScenarioError(f"{label}: expected {expect!r} in {text[:300]!r}")
        self.log(f"{label}: ok {text[:120]!r}")

    def op_screenshot(self, step: dict):
        result = self.call("screen_capture", {})
        self.log("screenshot: " + (text_of(result)[:200] or "captured"))

    # Running ----------------------------------------------------------------------------------------------------------

    def run(self) -> int:
        print(f"Scenario: {self.scenario['name']}: {self.scenario.get('description', '')}")
        failed: str | None = None
        try:
            self.connect()
            for index, step in enumerate(self.scenario.get("steps", []), 1):
                self.report["steps"].append({"index": index, "op": step["op"]})
                OPS[step["op"]](self, step)
        except ScenarioError as err:
            failed = str(err)
            self.log(f"FAILED: {failed}")
        finally:
            if self.client is not None:
                for step in self.scenario.get("cleanup", []):
                    try:
                        OPS[step["op"]](self, step)
                    except (ScenarioError, SystemExit) as err:
                        self.log(f"cleanup {step['op']} failed: {err}")
        self.report["result"] = "FAIL" if failed else "PASS"
        self.report["failure"] = failed
        if self.args.report:
            Path(self.args.report).write_text(json.dumps(self.report, indent=2))
            print(f"report: {self.args.report}")
        print(f"RESULT: {self.report['result']}" + (f" ({failed})" if failed else ""))
        return 1 if failed else 0


OPS = {
    "check_edit_mode": Runner.op_check_edit_mode,
    "start_play": Runner.op_start_play,
    "stop_play": Runner.op_stop_play,
    "sleep": Runner.op_sleep,
    "wait_for_logs": Runner.op_wait_for_logs,
    "collect_errors": Runner.op_collect_errors,
    "execute_luau": Runner.op_execute_luau,
    "screenshot": Runner.op_screenshot,
}


# Dry run: describe the MCP calls each step would make --------------------------------------------------------------

def _args(extra: dict) -> str:
    payload = dict(extra)
    payload["studio_id"] = "<auto>"
    return json.dumps(payload)


def describe(step: dict) -> list[str]:
    op = step["op"]
    snapshot = [
        f"execute_luau {_args({'datamodel_type': 'Server', 'code': '<LOG_SNAPSHOT>'})}",
        f"execute_luau {_args({'datamodel_type': 'Client', 'code': '<LOG_SNAPSHOT>'})}",
        f"(fallback if LogService can't be read: get_console_output {_args({})})",
    ]
    if op == "check_edit_mode":
        return [
            f"get_studio_state {_args({})}  -> abort if Play is already running (unless --allow-playing)",
            f"get_console_output {_args({})}  -> baseline for the fallback log reader",
        ]
    if op == "start_play":
        return [f"get_studio_state {_args({})}", f"start_stop_play {_args({'is_start': True})}"]
    if op == "stop_play":
        suffix = "  (only if this run started Play)"
        return [f"start_stop_play {_args({'is_start': False})}{suffix}"]
    if op == "sleep":
        return [f"no MCP call: wait {step.get('seconds', 1)}s"]
    if op == "wait_for_logs":
        head = f"every {step.get('poll', 2)}s for up to {step.get('timeout', 60)}s:"
        until = "until the logs contain all of: " + ", ".join(repr(p) for p in step["patterns"])
        return [head] + ["  " + line for line in snapshot] + [until]
    if op == "collect_errors":
        rule = "fail on MessageError from our scripts"
        if step.get("fail_on_warnings_matching"):
            rule += " or our warnings matching " + ", ".join(repr(p) for p in step["fail_on_warnings_matching"])
        return snapshot + [rule]
    if op == "execute_luau":
        code = step["code"] if len(step["code"]) < 60 else step["code"][:57] + "..."
        return [f"execute_luau {_args({'datamodel_type': step.get('datamodel', 'Server'), 'code': code})}"]
    if op == "screenshot":
        return [f"screen_capture {_args({})}"]
    return [f"(unknown op {op})"]


def dry_run(scenario: dict, args: argparse.Namespace) -> int:
    print(f"Scenario: {scenario['name']}: {scenario.get('description', '')}")
    print(f"MCP helper: {helper_path_for_display(args.studio_py)}  [dry run: not started]")
    studio = args.studio_id or f"<auto>: list_roblox_studios, preferring a name containing {project_name()!r}"
    print(f"Studio: {studio}")
    print("Planned MCP calls:")
    print("  setup: tools/list {}")
    if not args.studio_id:
        print("  setup: list_roblox_studios {}")
    for index, step in enumerate(scenario.get("steps", []), 1):
        lines = describe(step)
        print(f"  {index}. {step['op']:<16} {lines[0]}")
        for line in lines[1:]:
            print(f"     {'':<16} {line}")
    for step in scenario.get("cleanup", []):
        lines = describe(step)
        print(f"  cleanup (always): {step['op']}: {lines[0]}")
    print("\n<LOG_SNAPSHOT> =")
    for line in LOG_SNAPSHOT_LUAU.splitlines():
        print("    " + line.replace("\t", "    "))
    print("\nOur scripts = messages mentioning " + ", ".join(OUR_PATHS) + " or tagged [Main]/[<module>]")
    print("RESULT: DRY RUN (nothing was sent to Studio)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Playtest scenarios over Roblox Studio's built-in MCP server.")
    parser.add_argument("scenario", nargs="?", help="scenario name (tools/playtest/scenarios/<name>.json) or path")
    parser.add_argument("--dry-run", action="store_true", help="print the planned MCP calls and exit")
    parser.add_argument("--list", action="store_true", help="list the scenarios")
    parser.add_argument("--studio-py", help=f"use another MCP client file (default: ${HELPER_ENV}, else studio_client.py)")
    parser.add_argument("--studio-id", help="target this Studio window instead of picking the one named after the game")
    parser.add_argument("--allow-playing", action="store_true", help="use a Play session that's already running")
    parser.add_argument("--report", help="write a JSON report here")
    args = parser.parse_args(argv)

    if args.list:
        for path in sorted(SCENARIOS.glob("*.json")):
            description = json.loads(path.read_text()).get("description", "")
            print(f"{path.stem:<12} {description}")
        return 0
    if not args.scenario:
        parser.print_usage()
        return 2
    try:
        scenario = load_scenario(args.scenario)
        if args.dry_run:
            return dry_run(scenario, args)
        return Runner(scenario, args).run()
    except SetupError as err:
        print(f"SETUP ERROR: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
