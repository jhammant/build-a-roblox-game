#!/usr/bin/env python3
"""picker: turn a round of board JSON files into a tap-to-pick page, collect the picks, and read them back.

Commands (run `picker.py <command> -h` for the options):

  check <round>     validate round.json and every board (CONTRACT.md has the rules)
  build <round>     write out/picker.html (publish as an artifact) and out/picker.standalone.html
  serve <round>     serve the page on your home network and save picks to picks.json
  read <round>      write PICKS.md and picks.resolved.json from the saved picks
  approved <round>  write out/approved.html: only the options your child picked
  sheet <round>     render every option into out/sheet.png, so Claude can look at its drawings

Standard library only, Python 3.9 or later.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import xml.etree.ElementTree as ET
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"

ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
MAX_ONE_OPTIONS = 3  # "three options, never more"
MANY_OPTIONS = (2, 16)
TWEAK_CHOICES = (2, 30)
NAME_MAX = 32
BLURB_MAX = 100
NOTE_MAX = 300
PICK_TEXT_MAX = 60
PICK_LIST_MAX = 60
PICK_KEYS_MAX = 80
PAGE_WARN_BYTES = 8 * 1024 * 1024
PAGE_MAX_BYTES = 15 * 1024 * 1024
BODY_MAX_BYTES = 64 * 1024
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
               ".svg": "image/svg+xml"}
DOT_COLOURS = ["#FF4D5E", "#FF9F1C", "#FFD447", "#3FD46B", "#33B5FF", "#A877FF", "#FF6FB5"]
FONTS_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
              '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700'
              '&family=Nunito:wght@500;700;800&display=swap">')

# SVG pieces that could run code, load something from outside, or navigate away
SVG_FORBIDDEN_TAGS = {"script", "foreignObject", "image", "iframe", "object", "embed", "audio", "video", "a",
                      "animate", "set", "animateMotion", "animateTransform", "handler", "listener"}
EXTERNAL_URL_RE = re.compile(r"url\(\s*['\"]?\s*(?!#)", re.I)


# ---------------------------------------------------------------------------------------------------------------
# Problems: every check collects all of them, so one run lists everything to fix


class Problems:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: str, msg: str):
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str):
        self.warnings.append(f"{where}: {msg}")

    def report(self, out=None):
        out = out or sys.stderr
        for w in self.warnings:
            print(f"  warning  {w}", file=out)
        for e in self.errors:
            print(f"  ERROR    {e}", file=out)

    @property
    def ok(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------------------------------------------------------
# Loading and checking a round


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def check_svg(svg: str, where: str, problems: Problems):
    if not isinstance(svg, str) or not svg.strip():
        problems.error(where, "svg is empty")
        return
    if re.search(r"<!(DOCTYPE|ENTITY)", svg, re.I):
        problems.error(where, "svg must not contain a DOCTYPE or ENTITY declaration")
        return
    try:
        root = ET.fromstring(svg.strip())
    except ET.ParseError as e:
        problems.error(where, f"svg isn't valid XML ({e})")
        return
    if local_name(root.tag) != "svg":
        problems.error(where, f"svg root is <{local_name(root.tag)}>, not <svg>")
    if "viewBox" not in root.attrib:
        problems.warn(where, "svg has no viewBox, so it may not scale to the card")
    for el in root.iter():
        tag = local_name(el.tag)
        if tag in SVG_FORBIDDEN_TAGS:
            problems.error(where, f"svg contains <{tag}>; drawings must be self-contained and inert")
        if tag == "style" and el.text and (EXTERNAL_URL_RE.search(el.text) or "@import" in el.text):
            problems.error(where, "svg <style> loads something from outside the drawing")
        for name, value in el.attrib.items():
            attr = local_name(name)
            if attr.lower().startswith("on"):
                problems.error(where, f"svg has an event attribute ({attr}=)")
            if "javascript:" in value.lower().replace(" ", ""):
                problems.error(where, "svg contains a javascript: link")
            if attr == "href" and not value.startswith("#"):
                problems.error(where, f"svg links outside itself (href=\"{value[:40]}\"); only #ids are allowed")
            if EXTERNAL_URL_RE.search(value):
                problems.error(where, f"svg attribute {attr} loads something from outside the drawing")


def section_from_filename(path: Path) -> str:
    return re.sub(r"^\d+[-_]", "", path.stem)


def load_json(path: Path, problems: Problems):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.error(path.name, "file not found")
    except json.JSONDecodeError as e:
        problems.error(path.name, f"isn't valid JSON ({e})")
    return None


def load_round(round_dir: Path) -> tuple[dict, Problems]:
    """Load round.json and boards/*.json, checking everything against CONTRACT.md."""
    problems = Problems()
    round_dir = Path(round_dir)
    meta = load_json(round_dir / "round.json", problems) or {}
    if meta and not isinstance(meta, dict):
        problems.error("round.json", "must be a JSON object")
        meta = {}
    rid = meta.get("id")
    if not isinstance(rid, str) or not ID_RE.match(rid):
        problems.error("round.json", "id is missing or uses characters other than letters, digits, - and _")
        rid = "round"
    if not isinstance(meta.get("title"), str) or not meta.get("title", "").strip():
        problems.error("round.json", "title is missing")
    collection = meta.get("collection") or f"picks-{rid}"
    if not ID_RE.match(collection):
        problems.error("round.json", "collection uses characters other than letters, digits, - and _")

    boards = []
    files = sorted((round_dir / "boards").glob("*.json"))
    if not files:
        problems.error("boards/", "no board files found")
    seen_sections = set()
    for path in files:
        data = load_json(path, problems)
        if not isinstance(data, dict):
            if data is not None:
                problems.error(path.name, "must be a JSON object")
            continue
        board = check_board(data, path, problems)
        if board["section"] in seen_sections:
            problems.error(path.name, f"section \"{board['section']}\" is used by another board")
        seen_sections.add(board["section"])
        boards.append(board)

    rnd = {
        "dir": round_dir,
        "id": rid,
        "title": meta.get("title", ""),
        "intro": meta.get("intro", ""),
        "game": meta.get("game", ""),
        "done": meta.get("done") or "Tell Claude “picks are in” and it will start building.",
        "collection": collection,
        "boards": boards,
    }
    return rnd, problems


def check_board(data: dict, path: Path, problems: Problems) -> dict:
    where = path.name
    section = data.get("section") or section_from_filename(path)
    if not isinstance(section, str) or not ID_RE.match(section):
        problems.error(where, f"section \"{section}\" must use only letters, digits, - and _")
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        problems.error(where, "title is missing")
    groups = data.get("groups")
    if not isinstance(groups, list) or not groups:
        problems.error(where, "groups must be a non-empty list")
        groups = []
    seen_keys = set()
    clean_groups = []
    for gi, group in enumerate(groups):
        gwhere = f"{where} group {gi + 1}"
        if not isinstance(group, dict):
            problems.error(gwhere, "must be an object")
            continue
        key = group.get("key")
        if not isinstance(key, str) or not ID_RE.match(key):
            problems.error(gwhere, "key is missing or uses characters other than letters, digits, - and _")
            key = f"group{gi + 1}"
        gwhere = f"{where} [{key}]"
        if key in seen_keys:
            problems.error(gwhere, "key is used twice on this board")
        seen_keys.add(key)
        if not isinstance(group.get("title"), str) or not group["title"].strip():
            problems.error(gwhere, "title is missing")
        mode = group.get("mode", "one")
        if mode not in ("one", "many"):
            problems.error(gwhere, f"mode must be \"one\" or \"many\", not \"{mode}\"")
            mode = "one"
        options = group.get("options")
        if not isinstance(options, list):
            problems.error(gwhere, "options must be a list")
            options = []
        if mode == "one":
            if len(options) > MAX_ONE_OPTIONS:
                problems.error(gwhere, f"has {len(options)} options; a pick-one choice has three, never more")
            elif len(options) < MAX_ONE_OPTIONS:
                problems.warn(gwhere, f"has {len(options)} option(s); boards usually offer three (A, B, C)")
        else:
            lo, hi = MANY_OPTIONS
            if not lo <= len(options) <= hi:
                problems.error(gwhere, f"has {len(options)} options; a tap-any choice has {lo} to {hi}")
        seen_values = set()
        clean_options = []
        for oi, opt in enumerate(options):
            owhere = f"{gwhere} option {oi + 1}"
            if not isinstance(opt, dict):
                problems.error(owhere, "must be an object")
                continue
            value = opt.get("value")
            if not isinstance(value, str) or not ID_RE.match(value):
                problems.error(owhere, "value is missing or uses characters other than letters, digits, - and _")
                value = f"opt{oi + 1}"
            owhere = f"{gwhere} option {value}"
            if value in seen_values:
                problems.error(owhere, "value is used twice in this group")
            seen_values.add(value)
            name = opt.get("name")
            if not isinstance(name, str) or not name.strip():
                problems.error(owhere, "name is missing")
                name = value
            elif len(name) > NAME_MAX:
                problems.warn(owhere, f"name is {len(name)} characters; keep it under {NAME_MAX} so a child can read it")
            blurb = opt.get("blurb", "")
            if not isinstance(blurb, str):
                problems.error(owhere, "blurb must be text")
                blurb = ""
            elif len(blurb) > BLURB_MAX:
                problems.warn(owhere, f"blurb is {len(blurb)} characters; keep it under {BLURB_MAX}")
            has_svg, has_image = "svg" in opt, "image" in opt
            if has_svg == has_image:
                problems.error(owhere, "needs exactly one of svg or image")
            if has_svg:
                check_svg(opt["svg"], owhere, problems)
            if has_image:
                img = path.parent / str(opt["image"])
                if img.suffix.lower() not in IMAGE_TYPES:
                    problems.error(owhere, f"image must be one of {', '.join(sorted(IMAGE_TYPES))}")
                elif not img.is_file():
                    problems.error(owhere, f"image file {opt['image']} not found next to the board")
            clean_options.append({**opt, "value": value, "name": name, "blurb": blurb})
        tweaks = group.get("tweaks") or []
        clean_tweaks = []
        if not isinstance(tweaks, list):
            problems.error(gwhere, "tweaks must be a list")
            tweaks = []
        for ti, tweak in enumerate(tweaks):
            twhere = f"{gwhere} tweak {ti + 1}"
            if not isinstance(tweak, dict):
                problems.error(twhere, "must be an object")
                continue
            tkey = tweak.get("key")
            if not isinstance(tkey, str) or not ID_RE.match(tkey):
                problems.error(twhere, "key is missing or uses characters other than letters, digits, - and _")
                continue
            choices = tweak.get("choices")
            lo, hi = TWEAK_CHOICES
            if not isinstance(choices, list) or not lo <= len(choices) <= hi or not all(
                isinstance(c, str) and 0 < len(c) <= PICK_TEXT_MAX for c in choices
            ):
                problems.error(twhere, f"choices must be {lo} to {hi} short pieces of text")
                continue
            default = tweak.get("default", choices[0])
            if default not in choices:
                problems.error(twhere, f"default \"{default}\" isn't one of the choices")
            clean_tweaks.append({"key": tkey, "label": tweak.get("label") or tkey, "choices": choices,
                                 "default": default})
        clean_groups.append({**group, "key": key, "mode": mode, "options": clean_options, "tweaks": clean_tweaks})
    mode_default = 220 if all(g["mode"] == "one" for g in clean_groups) else 110
    card_width = data.get("cardWidth", mode_default)
    if not isinstance(card_width, int) or not 60 <= card_width <= 480:
        problems.warn(where, "cardWidth should be a whole number of pixels between 60 and 480")
        card_width = mode_default
    return {
        "file": path,
        "section": section,
        "title": data.get("title", section),
        "question": data.get("question", ""),
        "cardWidth": card_width,
        "groups": clean_groups,
    }


# ---------------------------------------------------------------------------------------------------------------
# Saved picks: the same sanitising the page and the server apply


def sanitise_doc(doc) -> dict:
    """Clamp one board's saved document to the contract's shape and sizes."""
    out = {"picks": {}, "note": "", "at": 0}
    if not isinstance(doc, dict):
        return out
    picks = doc.get("picks")
    if isinstance(picks, dict):
        for k in list(picks.keys())[:PICK_KEYS_MAX]:
            v = picks[k]
            if not isinstance(k, str) or len(k) > 2 * 40 + 1:
                continue
            if isinstance(v, str):
                out["picks"][k] = v[:PICK_TEXT_MAX]
            elif isinstance(v, list):
                out["picks"][k] = [x[:PICK_TEXT_MAX] for x in v if isinstance(x, str)][:PICK_LIST_MAX]
    note = doc.get("note")
    if isinstance(note, str):
        out["note"] = " ".join(note.split())[:NOTE_MAX]
    at = doc.get("at")
    if isinstance(at, (int, float)) and at >= 0:
        out["at"] = int(at)
    return out


def docs_from_any(data) -> dict:
    """Accept picks.json, a {section: doc} map, or an artifact database dump, and return {section: doc}."""
    if isinstance(data, dict) and isinstance(data.get("docs"), dict):
        data = data["docs"]
    elif isinstance(data, dict) and isinstance(data.get("documents"), list):
        data = data["documents"]
    docs = {}
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict) and ("picks" in v or "note" in v):
                docs[k] = sanitise_doc(v)
    elif isinstance(data, list):
        for row in data:
            if not isinstance(row, dict):
                continue
            ident = row.get("id") or row.get("doc_id") or row.get("path") or row.get("name")
            body = row.get("data") if isinstance(row.get("data"), dict) else row
            if isinstance(ident, str) and isinstance(body, dict):
                docs[ident.rsplit("/", 1)[-1]] = sanitise_doc(body)
    return docs


def read_picks_file(path: Path) -> dict:
    if not path.exists():
        return {}
    return docs_from_any(json.loads(path.read_text(encoding="utf-8")))


def write_json_atomic(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------------------------------------------
# Building pages


def prefix_ids(svg: str, prefix: str) -> str:
    for ident in sorted(set(re.findall(r"\bid=[\"']([^\"']+)[\"']", svg)), key=len, reverse=True):
        new = f"{prefix}-{ident}"
        svg = re.sub(rf"\bid=([\"']){re.escape(ident)}\1", rf"id=\g<1>{new}\g<1>", svg)
        svg = svg.replace(f"url(#{ident})", f"url(#{new})")
        svg = re.sub(rf"href=([\"'])#{re.escape(ident)}\1", rf"href=\g<1>#{new}\g<1>", svg)
    return svg


def clean_svg(svg: str, prefix: str) -> str:
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
    svg = re.sub(r"<svg\b", '<svg aria-hidden="true" focusable="false"', svg, count=1)
    return prefix_ids(svg, prefix)


def image_data_uri(board: dict, opt: dict) -> str:
    path = board["file"].parent / str(opt["image"])
    mime = IMAGE_TYPES[path.suffix.lower()]
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def option_art(board: dict, opt: dict, prefix: str) -> str:
    if "svg" in opt:
        return clean_svg(opt["svg"], prefix)
    return f'<img alt="" src="{image_data_uri(board, opt)}">'


def esc(text) -> str:
    return html.escape(str(text or ""), quote=True)


def option_html(board: dict, group: dict, opt: dict, n: int, picked_view=False) -> str:
    section, gkey = board["section"], group["key"]
    many = group["mode"] == "many"
    kind = "chip" if many else "opt"
    art = option_art(board, opt, f"{section[:6]}{n}")
    letter = "" if many else f'<span class="letter">{esc(opt["value"])}</span>'
    blurb = f'<span class="blurb">{esc(opt["blurb"])}</span>' if opt.get("blurb") and not many else ""
    text = (f'<span class="opt-text"><span class="opt-head">{letter}<span class="opt-name">{esc(opt["name"])}</span>'
            f"</span>{blurb}</span>")
    if picked_view:
        return f'<div class="{kind} is-picked"><span class="art">{art}</span>{text}</div>'
    oid = f"{section}-{gkey}-{opt['value']}"
    input_type = "checkbox" if many else "radio"
    sticker = "YES!" if many else "PICKED!"
    return (f'<label class="{kind}" for="{esc(oid)}">'
            f'<input type="{input_type}" class="sr-only" name="{esc(section)}-{esc(gkey)}" id="{esc(oid)}" '
            f'value="{esc(opt["value"])}" data-s="{esc(section)}" data-g="{esc(gkey)}">'
            f'<span class="sticker" aria-hidden="true">{sticker}</span><span class="art">{art}</span>{text}</label>')


def tweaks_html(board: dict, group: dict) -> str:
    if not group["tweaks"]:
        return ""
    parts = []
    for tweak in group["tweaks"]:
        tid = f"tw-{board['section']}-{group['key']}-{tweak['key']}"
        opts = "".join(f'<option value="{esc(c)}"{" selected" if c == tweak["default"] else ""}>{esc(c)}</option>'
                       for c in tweak["choices"])
        parts.append(f'<label class="tweak" for="{esc(tid)}"><span>{esc(tweak["label"])}</span>'
                     f'<select id="{esc(tid)}" data-s="{esc(board["section"])}" '
                     f'data-t="{esc(group["key"])}.{esc(tweak["key"])}" data-default="{esc(tweak["default"])}">'
                     f"{opts}</select></label>")
    return f'<div class="tweaks">{"".join(parts)}</div>'


def board_head(board: dict, i: int) -> str:
    question = f'<p class="question">{esc(board["question"])}</p>' if board["question"] else ""
    return (f'<div class="board-head"><span class="num" style="--dot: {DOT_COLOURS[i % len(DOT_COLOURS)]}">{i + 1}'
            f'</span><div class="board-title"><h2 id="h-{esc(board["section"])}">{esc(board["title"])}</h2>'
            f"{question}</div></div>")


def section_html(board: dict, i: int) -> str:
    blocks, n = [], 0
    for group in board["groups"]:
        many = group["mode"] == "many"
        opts = []
        for opt in group["options"]:
            n += 1
            opts.append(option_html(board, group, opt, n))
        hint = "(tap any)" if many else "(pick one)"
        sub = f'<p class="sub">{esc(group["subtitle"])}</p>' if group.get("subtitle") else ""
        width = board["cardWidth"] if not many else min(board["cardWidth"], 160)
        blocks.append(
            f'<div class="group"><h3>{esc(group["title"])} <span class="hint">{hint}</span></h3>{sub}'
            f'<fieldset class="{"chips" if many else "opts"}" style="--min: {width}px">'
            f'<legend class="sr-only">{esc(group["title"])}</legend>{"".join(opts)}</fieldset>'
            f"{tweaks_html(board, group)}</div>")
    s = esc(board["section"])
    return (f'<section class="board" id="{s}" aria-labelledby="h-{s}">{board_head(board, i)}{"".join(blocks)}'
            f'<div class="note"><label for="note-{s}">Anything to change in “{esc(board["title"])}”?</label>'
            f'<input type="text" id="note-{s}" data-s="{s}" data-note="1" maxlength="{NOTE_MAX}" autocomplete="off" '
            f'placeholder="Type any changes or ideas"></div></section>')


def page_meta(rnd: dict) -> dict:
    return {
        "round": rnd["id"],
        "collection": rnd["collection"],
        "sections": [{
            "key": b["section"],
            "title": b["title"],
            "groups": [{
                "key": g["key"],
                "title": g["title"],
                "mode": g["mode"],
                "names": {o["value"]: o["name"] for o in g["options"]},
                "tweaks": [{"key": t["key"], "label": t["label"], "choices": t["choices"], "default": t["default"]}
                           for t in g["tweaks"]],
            } for g in b["groups"]],
        } for b in rnd["boards"]],
    }


def script_json(data) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")


def fill(template: str, values: dict) -> str:
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: values[m.group(1)], template)


def head_html(title: str) -> str:
    return f"<title>{esc(title)}</title>\n{FONTS_LINK}\n"


def standalone(head: str, body: str) -> str:
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
            f"{head}</head>\n<body>\n{body}\n</body>\n</html>\n")


def build_picker(rnd: dict) -> tuple[str, str]:
    css = (ASSETS / "picker.css").read_text(encoding="utf-8")
    js = (ASSETS / "picker.js").read_text(encoding="utf-8")
    template = (ASSETS / "picker.html").read_text(encoding="utf-8")
    sections, toc, dots = [], [], []
    for i, board in enumerate(rnd["boards"]):
        s = esc(board["section"])
        sections.append(section_html(board, i))
        toc.append(f'<a class="toc-chip" href="#{s}" data-toc="{s}">{esc(board["title"])}</a>')
        dots.append(f'<li class="dot" data-board="{s}" style="--dot: {DOT_COLOURS[i % len(DOT_COLOURS)]}" '
                    f'title="{esc(board["title"])}"><span class="sr-only">{esc(board["title"])}</span></li>')
    body = fill(template, {
        "CSS": css,
        "JS": js,
        "GAME": esc(rnd["game"]),
        "TITLE": esc(rnd["title"]),
        "INTRO": esc(rnd["intro"]),
        "DONE": esc(rnd["done"]),
        "SECTIONS": "".join(sections),
        "TOC": "".join(toc),
        "DOTS": "".join(dots),
        "CONFIG": script_json(page_meta(rnd)),
    })
    title = f"{rnd['game']} picks" if rnd["game"] else rnd["title"]
    head = head_html(title)
    return head + body, standalone(head, body)


def resolve(rnd: dict, docs: dict) -> dict:
    """Join saved picks to the boards: what was picked, with each option's details."""
    boards = []
    for board in rnd["boards"]:
        doc = docs.get(board["section"])
        picks = doc["picks"] if doc else {}
        groups, finished = [], True
        for group in board["groups"]:
            by_value = {o["value"]: o for o in group["options"]}
            raw = picks.get(group["key"])
            values = raw if isinstance(raw, list) else ([raw] if isinstance(raw, str) and raw else [])
            picked = [{"value": v, "name": by_value[v]["name"], "blurb": by_value[v].get("blurb", ""),
                       "spec": by_value[v].get("spec")} for v in values if v in by_value]
            unknown = [v for v in values if v not in by_value]
            tweaks = {}
            for tweak in group["tweaks"]:
                chosen = picks.get(f"{group['key']}.{tweak['key']}")
                tweaks[tweak["key"]] = chosen if chosen in tweak["choices"] else tweak["default"]
            if not picked:
                finished = False
            groups.append({"key": group["key"], "title": group["title"], "mode": group["mode"], "picked": picked,
                           "tweaks": tweaks, "unknown": unknown, "extra": group.get("extra")})
        boards.append({"section": board["section"], "title": board["title"], "question": board["question"],
                       "file": board["file"].name, "finished": finished, "note": doc["note"] if doc else "",
                       "at": doc["at"] if doc else 0, "groups": groups})
    return {"round": rnd["id"], "title": rnd["title"], "game": rnd["game"],
            "complete": all(b["finished"] for b in boards), "boards": boards}


def build_approved(rnd: dict, resolved: dict) -> tuple[str, str]:
    css = (ASSETS / "picker.css").read_text(encoding="utf-8")
    sections = []
    by_section = {b["section"]: b for b in rnd["boards"]}
    for i, rb in enumerate(resolved["boards"]):
        board = by_section[rb["section"]]
        blocks, n = [], 0
        for rg, group in zip(rb["groups"], board["groups"]):
            by_value = {o["value"]: o for o in group["options"]}
            cards = []
            for p in rg["picked"]:
                n += 1
                cards.append(option_html(board, group, by_value[p["value"]], n, picked_view=True))
            tw = " · ".join(f"{esc(t['label'])}: <strong>{esc(rg['tweaks'][t['key']])}</strong>"
                            for t in group["tweaks"])
            body = (f'<fieldset class="{"chips" if group["mode"] == "many" else "opts"}" '
                    f'style="--min: {board["cardWidth"]}px">{"".join(cards)}</fieldset>' if cards
                    else '<p class="not-picked">Not picked yet</p>')
            blocks.append(f'<div class="group"><h3>{esc(group["title"])}</h3>{body}'
                          f'{f"<p class=sub>{tw}</p>" if tw else ""}</div>')
        note = f'<blockquote class="kid-note">“{esc(rb["note"])}”</blockquote>' if rb["note"] else ""
        sections.append(f'<section class="board" id="{esc(rb["section"])}">{board_head(board, i)}'
                        f'{"".join(blocks)}{note}</section>')
    game = f'<p class="game">{esc(rnd["game"])}</p>' if rnd["game"] else ""
    body = (f"<style>{css}</style>\n<div class=\"wrap approved\"><header class=\"intro\">{game}"
            f"<h1>What you picked</h1><p>{esc(rnd['title'])}. These are the specs Claude builds from.</p></header>"
            f"<main class=\"boards\">{''.join(sections)}</main></div>")
    title = f"{rnd['game']} approved picks" if rnd["game"] else f"{rnd['title']}: approved"
    head = head_html(title)
    return head + body, standalone(head, body)


def page_size_check(text: str, problems: Problems, name: str):
    size = len(text.encode("utf-8"))
    if size > PAGE_MAX_BYTES:
        problems.error(name, f"page is {size / 1e6:.1f} MB; artifacts must stay under 16 MB")
    elif size > PAGE_WARN_BYTES:
        problems.warn(name, f"page is {size / 1e6:.1f} MB; it may load slowly on a tablet")


def write_pages(rnd: dict) -> tuple[Path, Path, Problems]:
    fragment, full = build_picker(rnd)
    problems = Problems()
    page_size_check(fragment, problems, "out/picker.html")
    out = rnd["dir"] / "out"
    out.mkdir(exist_ok=True)
    (out / "picker.html").write_text(fragment, encoding="utf-8")
    (out / "picker.standalone.html").write_text(full, encoding="utf-8")
    return out / "picker.html", out / "picker.standalone.html", problems


# ---------------------------------------------------------------------------------------------------------------
# PICKS.md


def quote_note(note: str) -> str:
    return "“" + note.replace("\n", " ").strip() + "”"


def picks_markdown(resolved: dict, source: str) -> str:
    boards = resolved["boards"]
    done = sum(1 for b in boards if b["finished"])
    when = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# Picks: {resolved['title']}", "",
             f"Round `{resolved['round']}`, read from `{source}` on {when}. "
             f"**{done} of {len(boards)} boards finished.**", ""]
    for i, b in enumerate(boards, 1):
        lines.append(f"## {i}. {b['title']}" + ("" if b["finished"] else " (not finished)"))
        lines.append("")
        if b["question"]:
            lines += [f"_{b['question']}_", ""]
        for g in b["groups"]:
            label = f"**{g['title']}**" + (" (tap any)" if g["mode"] == "many" else "")
            if g["picked"]:
                if g["mode"] == "many":
                    shown = ", ".join(f"**{p['name']}**" for p in g["picked"])
                else:
                    p = g["picked"][0]
                    shown = f"**{p['value']} · {p['name']}**" + (f": {p['blurb']}" if p["blurb"] else "")
            else:
                shown = "**not picked yet**"
            tweaks = "".join(f" · {k}: **{v}**" for k, v in g["tweaks"].items())
            lines.append(f"- {label}: {shown}{tweaks}")
            if g["unknown"]:
                lines.append(f"  - Saved values that aren't on the board any more: {', '.join(g['unknown'])}. "
                             "Was the board changed after picking? Ask before using them.")
        if b["note"]:
            lines.append(f"- Note: {quote_note(b['note'])}")
        lines.append("")
    notes = [b for b in boards if b["note"]]
    lines += ["## Notes to check", ""]
    if notes:
        lines += ["Your child's notes can change what a pick means. Read each one with its board. If a note could mean "
                  "two things, ask your child before writing the spec, and record the answer.", ""]
        lines += [f"- **{b['title']}:** {quote_note(b['note'])}" for b in notes]
    else:
        lines.append("No notes this round.")
    unfinished = [b["title"] for b in boards if not b["finished"]]
    if unfinished:
        lines += ["", "## Still to pick", "", *[f"- {t}" for t in unfinished]]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------------------------------------------
# Contact sheet


def sheet_svg(rnd: dict) -> str:
    cell, label_h, cols, pad = 220, 46, 4, 16
    cells = []
    for board in rnd["boards"]:
        for group in board["groups"]:
            for opt in group["options"]:
                cells.append((board, group, opt))
    rows = (len(cells) + cols - 1) // cols
    width = cols * (cell + pad) + pad
    height = rows * (cell + label_h + pad) + pad
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#F3EEFF"/>']
    for i, (board, group, opt) in enumerate(cells):
        x = pad + (i % cols) * (cell + pad)
        y = pad + (i // cols) * (cell + label_h + pad)
        parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="#FFFFFF" stroke="#2B1B4A" '
                     'stroke-width="2"/>')
        if "svg" in opt:
            inner = clean_svg(opt["svg"], f"s{i}")
            inner = re.sub(r"<svg\b([^>]*)>", lambda m: "<svg" + re.sub(r'\s(width|height|x|y)=("[^"]*"|\'[^\']*\')',
                                                                         "", m.group(1)) +
                           f' x="{x + 4}" y="{y + 4}" width="{cell - 8}" height="{cell - 8}">', inner, count=1)
            parts.append(inner)
        else:
            parts.append(f'<image x="{x + 4}" y="{y + 4}" width="{cell - 8}" height="{cell - 8}" '
                         f'href="{image_data_uri(board, opt)}"/>')
        label = f"{board['section']} / {group['key']} / {opt['value']}"
        parts.append(f'<text x="{x}" y="{y + cell + 18}" font-family="Arial, sans-serif" font-size="14" '
                     f'font-weight="bold" fill="#2B1B4A">{esc(label)}</text>')
        parts.append(f'<text x="{x}" y="{y + cell + 36}" font-family="Arial, sans-serif" font-size="13" '
                     f'fill="#4A3B6B">{esc(opt["name"])}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def render_png(svg_path: Path, png_path: Path) -> str | None:
    """Render an SVG to PNG with whatever is installed. Returns the tool used, or None."""
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", "-o", str(png_path), str(svg_path)], check=True)
        return "rsvg-convert"
    if shutil.which("magick"):
        subprocess.run(["magick", str(svg_path), str(png_path)], check=True)
        return "magick"
    if sys.platform == "darwin" and shutil.which("qlmanage"):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["qlmanage", "-t", "-s", "2000", "-o", tmp, str(svg_path)], check=True,
                           capture_output=True)
            made = Path(tmp) / (svg_path.name + ".png")
            if made.exists():
                shutil.move(str(made), png_path)
                return "qlmanage"
    return None


# ---------------------------------------------------------------------------------------------------------------
# The local server


def lan_addresses() -> list[str]:
    addrs = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # no packet is sent; this just picks the outgoing interface
            addrs.append(s.getsockname()[0])
    except OSError:
        pass
    return [a for a in addrs if not a.startswith("127.")]


class PickServer:
    def __init__(self, rnd_dir: Path):
        self.dir = Path(rnd_dir)
        self.lock = threading.Lock()
        self.page = b""
        self.built_at = 0.0
        self.rnd = None
        self.rebuild()

    def sources_mtime(self) -> float:
        files = [self.dir / "round.json", *(self.dir / "boards").glob("*"), ASSETS / "picker.css",
                 ASSETS / "picker.js", ASSETS / "picker.html"]
        return max((f.stat().st_mtime for f in files if f.exists()), default=0.0)

    def rebuild(self):
        rnd, problems = load_round(self.dir)
        if not problems.ok:
            problems.report()
            if self.rnd is None:
                raise SystemExit("Fix the errors above, then run serve again.")
            print("  (keeping the last good page)", file=sys.stderr)
            self.built_at = self.sources_mtime()
            return
        self.rnd = rnd
        _, full = build_picker(rnd)
        self.page = full.encode("utf-8")
        self.built_at = self.sources_mtime()

    def page_bytes(self) -> bytes:
        with self.lock:
            if self.sources_mtime() > self.built_at:
                print("boards changed, rebuilding the page")
                self.rebuild()
            return self.page

    @property
    def picks_path(self) -> Path:
        return self.dir / "picks.json"

    def docs(self) -> dict:
        with self.lock:
            return read_picks_file(self.picks_path)

    def save(self, section: str, doc: dict) -> dict:
        clean = sanitise_doc(doc)
        if not clean["at"]:
            clean["at"] = int(dt.datetime.now().timestamp() * 1000)
        with self.lock:
            docs = read_picks_file(self.picks_path)
            docs[section] = clean
            write_json_atomic(self.picks_path, {"collection": self.rnd["collection"], "docs": docs})
        return clean

    def sections(self) -> set[str]:
        return {b["section"] for b in self.rnd["boards"]}


def make_handler(server: PickServer):
    class Handler(BaseHTTPRequestHandler):
        server_version = "picker/1"

        def log_message(self, fmt, *args):  # quiet: the important events are printed below
            pass

        def send(self, status: int, body: bytes = b"", content_type: str = "application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def send_json(self, status: int, data):
            self.send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"))

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self.send(HTTPStatus.OK, server.page_bytes(), "text/html; charset=utf-8")
            elif path == "/api/picks":
                self.send_json(HTTPStatus.OK, {"collection": server.rnd["collection"], "docs": server.docs()})
            else:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        do_HEAD = do_GET

        def do_PUT(self):
            m = re.fullmatch(r"/api/picks/([A-Za-z0-9_-]{1,40})", self.path.split("?", 1)[0])
            if not m:
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            section = m.group(1)
            if section not in server.sections():
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": f"no board called {section}"})
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                return self.send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "send JSON"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if not 0 < length <= BODY_MAX_BYTES:
                return self.send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "body too large or empty"})
            try:
                doc = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return self.send_json(HTTPStatus.BAD_REQUEST, {"error": "not JSON"})
            if not isinstance(doc, dict):
                return self.send_json(HTTPStatus.BAD_REQUEST, {"error": "send a JSON object"})
            saved = server.save(section, doc)
            print(f"saved {section}: {json.dumps(saved['picks'], ensure_ascii=False)}"
                  + (f"  note: {saved['note']!r}" if saved["note"] else ""))
            self.send_json(HTTPStatus.OK, saved)

    return Handler


# ---------------------------------------------------------------------------------------------------------------
# Commands


def round_dir_arg(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if path.name == "round.json":
        path = path.parent
    if not (path / "round.json").exists():
        raise argparse.ArgumentTypeError(f"no round.json in {path}")
    return path


def load_or_exit(round_dir: Path) -> dict:
    rnd, problems = load_round(round_dir)
    problems.report()
    if not problems.ok:
        print(f"{len(problems.errors)} error(s) in {round_dir}; fix them and run again.", file=sys.stderr)
        sys.exit(1)
    return rnd


def cmd_check(args) -> int:
    rnd, problems = load_round(args.round)
    if problems.ok:
        fragment, _ = build_picker(rnd)
        page_size_check(fragment, problems, "out/picker.html")
    problems.report()
    options = sum(len(g["options"]) for b in rnd["boards"] for g in b["groups"])
    status = "OK" if problems.ok else "FAILED"
    print(f"{status}: {len(rnd['boards'])} board(s), {options} option(s), {len(problems.errors)} error(s), "
          f"{len(problems.warnings)} warning(s)")
    return 0 if problems.ok else 1


def cmd_build(args) -> int:
    rnd = load_or_exit(args.round)
    fragment, full, problems = write_pages(rnd)
    problems.report()
    if not problems.ok:
        return 1
    print(f"wrote {fragment.relative_to(Path.cwd()) if fragment.is_relative_to(Path.cwd()) else fragment} "
          f"({fragment.stat().st_size // 1024} KB): publish this as a Claude artifact with the db capability")
    print(f"wrote {full.name}: open it in a browser, or run `picker.py serve`")
    print(f"picks collection: {rnd['collection']}")
    return 0


def cmd_serve(args) -> int:
    server = PickServer(args.round)
    try:
        httpd = ThreadingHTTPServer((args.host, args.port), make_handler(server))
    except OSError as e:
        if args.port == 0:
            raise
        print(f"Port {args.port} is busy ({e.strerror}), so using a free one instead.")
        httpd = ThreadingHTTPServer((args.host, 0), make_handler(server))
    port = httpd.server_address[1]
    print(f"Picker for “{server.rnd['title']}” is running. Picks save to {server.picks_path}")
    print(f"  On this computer:  http://127.0.0.1:{port}/")
    if args.host in ("0.0.0.0", ""):
        for addr in lan_addresses():
            print(f"  On the tablet:     http://{addr}:{port}/   (same Wi-Fi)")
    print("Press Ctrl-C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0


def docs_from_path(path: Path, collection: str) -> dict:
    """Read picks from a dump of the artifact database.

    Accepts the folder `ArtifactData list` writes with `out_dir` (one `<board>.json` per document, possibly inside a
    `<collection>/` subfolder), a JSON file in any shape `docs_from_any` takes, or the text of a `list` result
    pasted into a file (one JSON row per line).
    """
    if path.is_dir():
        if (path / collection).is_dir():
            path = path / collection
        return {f.stem: sanitise_doc(json.loads(f.read_text(encoding="utf-8"))) for f in sorted(path.glob("*.json"))}
    text = path.read_text(encoding="utf-8")
    try:
        return docs_from_any(json.loads(text))
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return docs_from_any(rows)


def load_docs(args, collection: str) -> tuple[dict, str]:
    if args.source:
        path = Path(args.source).expanduser()
        return docs_from_path(path, collection), path.name
    return read_picks_file(args.round / "picks.json"), "picks.json"


def cmd_read(args) -> int:
    rnd = load_or_exit(args.round)
    docs, source = load_docs(args, rnd["collection"])
    if args.source and args.save:
        write_json_atomic(args.round / "picks.json", {"collection": rnd["collection"], "docs": docs})
        source = f"{source} (saved to picks.json)"
    resolved = resolve(rnd, docs)
    (args.round / "PICKS.md").write_text(picks_markdown(resolved, source), encoding="utf-8")
    write_json_atomic(args.round / "picks.resolved.json", resolved)
    done = sum(1 for b in resolved["boards"] if b["finished"])
    notes = sum(1 for b in resolved["boards"] if b["note"])
    unknown = sum(len(g["unknown"]) for b in resolved["boards"] for g in b["groups"])
    print(f"{done} of {len(resolved['boards'])} boards finished, {notes} note(s) to check"
          + (f", {unknown} saved value(s) no longer on the boards" if unknown else "")
          + f". Wrote PICKS.md and picks.resolved.json in {args.round}")
    if args.strict and not resolved["complete"]:
        return 1
    return 0


def cmd_approved(args) -> int:
    rnd = load_or_exit(args.round)
    docs, _ = load_docs(args, rnd["collection"])
    fragment, full = build_approved(rnd, resolve(rnd, docs))
    out = args.round / "out"
    out.mkdir(exist_ok=True)
    (out / "approved.html").write_text(fragment, encoding="utf-8")
    (out / "approved.standalone.html").write_text(full, encoding="utf-8")
    print(f"wrote {out / 'approved.html'} (publish it, or open approved.standalone.html)")
    return 0


def cmd_sheet(args) -> int:
    rnd = load_or_exit(args.round)
    out = args.round / "out"
    out.mkdir(exist_ok=True)
    svg_path = out / "sheet.svg"
    svg_path.write_text(sheet_svg(rnd), encoding="utf-8")
    png_path = out / "sheet.png"
    try:
        tool = render_png(svg_path, png_path)
    except subprocess.CalledProcessError as e:
        print(f"rendering failed ({e}); open {svg_path} in a browser instead", file=sys.stderr)
        return 1
    if tool:
        print(f"wrote {png_path} with {tool}. Look at it once and fix anything that reads badly.")
    else:
        print(f"wrote {svg_path}. Install librsvg (rsvg-convert) for a PNG, or open the SVG in a browser.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="picker.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, fn, help_text):
        p = sub.add_parser(name, help=help_text, description=help_text)
        p.add_argument("round", type=round_dir_arg, help="the round folder (the one holding round.json)")
        p.set_defaults(fn=fn)
        return p

    add("check", cmd_check, "Validate round.json and every board.")
    add("build", cmd_build, "Build the picker pages into out/.")
    serve = add("serve", cmd_serve, "Serve the picker and save picks to picks.json.")
    serve.add_argument("--host", default="0.0.0.0",
                       help="address to listen on (default: every network, so a tablet on your Wi-Fi can reach it; "
                            "use 127.0.0.1 for this computer only)")
    serve.add_argument("--port", type=int, default=8765, help="port (default 8765; 0 picks a free one)")
    read = add("read", cmd_read, "Write PICKS.md and picks.resolved.json from the saved picks.")
    read.add_argument("--from", dest="source", help="read a dump of the artifact database instead of picks.json")
    read.add_argument("--save", action="store_true", help="with --from, also save what was read as picks.json")
    read.add_argument("--strict", action="store_true", help="exit 1 if any board isn't finished")
    approved = add("approved", cmd_approved, "Build out/approved.html, showing only the picked options.")
    approved.add_argument("--from", dest="source", help="read a dump of the artifact database instead of picks.json")
    add("sheet", cmd_sheet, "Render every option into out/sheet.png.")

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
