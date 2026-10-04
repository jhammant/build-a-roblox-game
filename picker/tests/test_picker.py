"""Tests for picker.py: board checks, page building, saved-picks handling, PICKS.md and the local server.

Run from the repo root: python3 -m unittest discover picker/tests
"""
import copy
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from http.server import ThreadingHTTPServer
from io import StringIO
from pathlib import Path

PICKER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PICKER))
import picker  # noqa: E402

SAMPLE = PICKER / "sample"
GOOD_SVG = "<svg viewBox='0 0 10 10' xmlns='http://www.w3.org/2000/svg'><circle cx='5' cy='5' r='4'/></svg>"


def option(value, svg=GOOD_SVG, **extra):
    return {"value": value, "name": f"Option {value}", "blurb": "", "svg": svg, **extra}


class RoundDir:
    """A throwaway round folder, copied from the sample or written from scratch."""

    def __init__(self, boards=None):
        self.tmp = Path(tempfile.mkdtemp())
        if boards is None:
            shutil.copytree(SAMPLE, self.tmp, dirs_exist_ok=True, ignore=shutil.ignore_patterns("out", "picks*"))
        else:
            (self.tmp / "boards").mkdir()
            (self.tmp / "round.json").write_text(json.dumps({"id": "t1", "title": "Test round"}))
            for name, board in boards.items():
                (self.tmp / "boards" / name).write_text(json.dumps(board))

    def __enter__(self):
        return self.tmp

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp, ignore_errors=True)


def one_board(options, **group):
    return {"title": "Board", "groups": [{"key": "Look", "title": "Look", "mode": "one", "options": options, **group}]}


def problems_for(boards):
    with RoundDir(boards) as d:
        _, problems = picker.load_round(d)
    return problems


class CheckTests(unittest.TestCase):
    def test_sample_round_is_clean(self):
        # Arrange / Act
        rnd, problems = picker.load_round(SAMPLE)
        # Assert
        self.assertEqual(problems.errors, [])
        self.assertEqual(problems.warnings, [])
        self.assertEqual([b["section"] for b in rnd["boards"]], ["wand", "gloomy", "extras"])
        self.assertEqual(rnd["collection"], "picks-00-sample")

    def test_three_options_never_more(self):
        problems = problems_for({"01-a.json": one_board([option(v) for v in "ABCD"])})
        self.assertTrue(any("three, never more" in e for e in problems.errors), problems.errors)

    def test_fewer_than_three_is_a_warning(self):
        problems = problems_for({"01-a.json": one_board([option("A"), option("B")])})
        self.assertEqual(problems.errors, [])
        self.assertTrue(any("usually offer three" in w for w in problems.warnings))

    def test_unsafe_svgs_are_rejected(self):
        bad = {
            "script": "<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
            "event": "<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'></svg>",
            "external href": "<svg xmlns='http://www.w3.org/2000/svg' xmlns:x='http://www.w3.org/1999/xlink'>"
                             "<use x:href='http://example.com/a.svg#x'/></svg>",
            "image": "<svg xmlns='http://www.w3.org/2000/svg'><image href='#a'/></svg>",
            "foreignObject": "<svg xmlns='http://www.w3.org/2000/svg'><foreignObject/></svg>",
            "external url": "<svg xmlns='http://www.w3.org/2000/svg'><rect fill='url(http://x/y)'/></svg>",
            "entity": "<!DOCTYPE svg [<!ENTITY a 'b'>]><svg xmlns='http://www.w3.org/2000/svg'/>",
            "broken xml": "<svg><circle></svg>",
            "not svg": "<div xmlns='http://www.w3.org/1999/xhtml'/>",
        }
        for label, svg in bad.items():
            with self.subTest(label):
                problems = problems_for({"01-a.json": one_board([option("A", svg), option("B"), option("C")])})
                self.assertTrue(problems.errors, f"{label} should be an error")

    def test_internal_references_are_fine(self):
        svg = ("<svg viewBox='0 0 10 10' xmlns='http://www.w3.org/2000/svg'><defs><linearGradient id='g'/></defs>"
               "<rect fill='url(#g)' width='10' height='10'/><use href='#g'/></svg>")
        problems = problems_for({"01-a.json": one_board([option("A", svg), option("B"), option("C")])})
        self.assertEqual(problems.errors, [])

    def test_duplicate_sections_values_and_bad_tweaks(self):
        board = one_board([option("A"), option("A"), option("C")],
                          tweaks=[{"key": "Size", "choices": ["Big", "Small"], "default": "Huge"}])
        problems = problems_for({"01-a.json": board, "02-a.json": board})
        text = "\n".join(problems.errors)
        self.assertIn("used by another board", text)
        self.assertIn("used twice in this group", text)
        self.assertIn("isn't one of the choices", text)

    def test_option_needs_exactly_one_picture(self):
        both = option("A", image="x.png")
        neither = {"value": "B", "name": "B"}
        problems = problems_for({"01-a.json": one_board([both, neither, option("C")])})
        self.assertEqual(sum("exactly one of svg or image" in e for e in problems.errors), 2)

    def test_invalid_json_is_reported_not_raised(self):
        with RoundDir({}) as d:
            (d / "boards" / "01-a.json").write_text("{nope")
            _, problems = picker.load_round(d)
        self.assertTrue(any("isn't valid JSON" in e for e in problems.errors))


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.rnd, _ = picker.load_round(SAMPLE)
        self.fragment, self.full = picker.build_picker(self.rnd)

    def test_artifact_page_is_a_fragment_with_a_title(self):
        self.assertTrue(self.fragment.startswith("<title>Spark Garden picks</title>"))
        self.assertNotIn("<!doctype", self.fragment.lower())
        self.assertTrue(self.full.startswith("<!doctype html>"))
        self.assertIn("viewport-fit=cover", self.full)

    def test_config_lists_every_board_and_group(self):
        raw = self.fragment.split('<script id="picker-config" type="application/json">', 1)[1].split("</script>")[0]
        config = json.loads(raw)
        self.assertEqual(config["collection"], "picks-00-sample")
        self.assertEqual([s["key"] for s in config["sections"]], ["wand", "gloomy", "extras"])
        wand = config["sections"][0]["groups"][0]
        self.assertEqual(wand["names"], {"A": "Star Wand", "B": "Flower Wand", "C": "Bubble Wand"})
        self.assertEqual(wand["tweaks"][0]["default"], "Pink")

    def test_svg_ids_are_unique_across_the_page(self):
        svg = ("<svg viewBox='0 0 10 10' xmlns='http://www.w3.org/2000/svg'><defs><linearGradient id='g'/></defs>"
               "<rect fill='url(#g)' width='10' height='10'/></svg>")
        with RoundDir({"01-a.json": one_board([option("A", svg), option("B", svg), option("C", svg)])}) as d:
            rnd, _ = picker.load_round(d)
            fragment, _ = picker.build_picker(rnd)
        ids = [m for m in __import__("re").findall(r"id='([^']+)'", fragment)]
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), 3)
        for ident in ids:
            self.assertIn(f"url(#{ident})", fragment)

    def test_text_is_escaped(self):
        board = one_board([option("A", name="<b>bold</b>"), option("B"), option("C")])
        board["title"] = "Fish & <chips>"
        with RoundDir({"01-a.json": board}) as d:
            rnd, _ = picker.load_round(d)
            fragment, _ = picker.build_picker(rnd)
        self.assertIn("Fish &amp; &lt;chips&gt;", fragment)
        self.assertNotIn("<b>bold</b>", fragment)

    def test_config_cannot_close_its_script_tag(self):
        board = one_board([option("A", name="</script><script>x"), option("B"), option("C")])
        with RoundDir({"01-a.json": board}) as d:
            rnd, _ = picker.load_round(d)
            fragment, _ = picker.build_picker(rnd)
        config = fragment.split('type="application/json">', 1)[1].split("</script>")[0]
        self.assertIn("<\\/script>", config)


class SavedPicksTests(unittest.TestCase):
    def test_sanitise_clamps_everything(self):
        doc = picker.sanitise_doc({
            "picks": {"Look": "B" * 500, "Many": ["x" * 200] * 100, "Bad": {"nested": 1}, "N": 3},
            "note": "line one\nline two  " + "z" * 1000,
            "at": "yesterday",
        })
        self.assertEqual(len(doc["picks"]["Look"]), picker.PICK_TEXT_MAX)
        self.assertEqual(len(doc["picks"]["Many"]), picker.PICK_LIST_MAX)
        self.assertNotIn("Bad", doc["picks"])
        self.assertNotIn("N", doc["picks"])
        self.assertNotIn("\n", doc["note"])
        self.assertEqual(len(doc["note"]), picker.NOTE_MAX)
        self.assertEqual(doc["at"], 0)

    def test_docs_from_every_supported_shape(self):
        body = {"picks": {"Look": "A"}, "note": "hi", "at": 5}
        shapes = {
            "picks.json": {"collection": "c", "docs": {"wand": body}},
            "plain map": {"wand": body},
            "rows with data": [{"id": "wand", "data": body}],
            "rows with path": [{"path": "picks-00-sample/wand", "data": body}],
            "documents list": {"documents": [{"doc_id": "wand", "data": body}]},
        }
        for label, data in shapes.items():
            with self.subTest(label):
                self.assertEqual(picker.docs_from_any(data), {"wand": {"picks": {"Look": "A"}, "note": "hi", "at": 5}})


class PicksMarkdownTests(unittest.TestCase):
    def test_picks_notes_tweaks_and_gaps_are_all_reported(self):
        # Arrange
        rnd, _ = picker.load_round(SAMPLE)
        docs = {
            "wand": {"picks": {"Look": "B", "Look.Colour": "Sunny gold"}, "note": "all of them!", "at": 1},
            "gloomy": {"picks": {"Look": "D"}, "note": "", "at": 2},
            "extras": {"picks": {"Sounds": ["Boing", "Pop"], "Effects": ["Confetti"]}, "note": "", "at": 3},
        }
        # Act
        resolved = picker.resolve(rnd, docs)
        text = picker.picks_markdown(resolved, "picks.json")
        # Assert
        self.assertFalse(resolved["complete"])
        self.assertIn("**2 of 3 boards finished.**", text)
        self.assertIn("**B · Flower Wand**: A daisy that spins when you zap.", text)
        self.assertIn("Colour: **Sunny gold**", text)
        self.assertIn("**Boing**, **Pop**", text)
        self.assertIn("“all of them!”", text.split("## Notes to check")[1])
        self.assertIn("aren't on the board any more: D", text)
        self.assertIn("## Still to pick", text)
        wand = resolved["boards"][0]["groups"][0]
        self.assertEqual(wand["picked"][0]["spec"]["tip"], "five-petal flower")

    def test_bad_tweak_values_fall_back_to_the_default(self):
        rnd, _ = picker.load_round(SAMPLE)
        resolved = picker.resolve(rnd, {"wand": {"picks": {"Look": "A", "Look.Colour": "Plaid"}, "note": "", "at": 1}})
        self.assertEqual(resolved["boards"][0]["groups"][0]["tweaks"], {"Colour": "Pink"})


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.round = RoundDir()
        self.dir = self.round.__enter__()
        self.server = picker.PickServer(self.dir)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), picker.make_handler(self.server))
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.round.__exit__(None, None, None)

    def request(self, method, path, body=None, content_type="application/json"):
        data = body if isinstance(body, bytes) or body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", content_type)
        try:
            with redirect_stdout(StringIO()), urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read()

    def test_round_trip(self):
        status, page = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"<!doctype html>", page)

        status, body = self.request("PUT", "/api/picks/wand",
                                    {"picks": {"Look": "C", "Look.Colour": "Mint green"}, "note": "bubbles!!",
                                     "at": 1759600000000})
        self.assertEqual(status, 200, body)

        status, body = self.request("GET", "/api/picks")
        self.assertEqual(status, 200)
        docs = json.loads(body)["docs"]
        self.assertEqual(docs["wand"], {"picks": {"Look": "C", "Look.Colour": "Mint green"}, "note": "bubbles!!",
                                        "at": 1759600000000})
        on_disk = json.loads((self.dir / "picks.json").read_text())
        self.assertEqual(on_disk["collection"], "picks-00-sample")
        self.assertEqual(on_disk["docs"]["wand"]["picks"]["Look"], "C")

    def test_rejects_what_it_should(self):
        cases = [
            ("unknown board", "/api/picks/nope", {"picks": {}}, "application/json", 404),
            ("bad path", "/api/picks/../../etc", {"picks": {}}, "application/json", 404),
            ("not JSON type", "/api/picks/wand", b"{}", "text/plain", 415),
            ("not JSON", "/api/picks/wand", b"{nope", "application/json", 400),
            ("not an object", "/api/picks/wand", b"[1]", "application/json", 400),
            ("too big", "/api/picks/wand", b"{" + b" " * (picker.BODY_MAX_BYTES + 1) + b"}", "application/json", 413),
        ]
        for label, path, body, ctype, want in cases:
            with self.subTest(label):
                status, _ = self.request("PUT", path, body, ctype)
                self.assertEqual(status, want)
        self.assertFalse((self.dir / "picks.json").exists())

    def test_server_stamps_a_time_and_sanitises(self):
        status, body = self.request("PUT", "/api/picks/extras", {"picks": {"Sounds": ["Pop", 7]}, "note": 9})
        self.assertEqual(status, 200)
        saved = json.loads(body)
        self.assertEqual(saved["picks"], {"Sounds": ["Pop"]})
        self.assertEqual(saved["note"], "")
        self.assertGreater(saved["at"], 0)


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = picker.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def test_read_writes_both_files_and_strict_fails_when_unfinished(self):
        with RoundDir() as d:
            (d / "picks.json").write_text(json.dumps({"docs": {"wand": {"picks": {"Look": "A"}, "note": "", "at": 1}}}))
            code, out, _ = self.run_cli("read", d)
            self.assertEqual(code, 0)
            self.assertIn("1 of 3 boards finished", out)
            self.assertTrue((d / "PICKS.md").exists())
            resolved = json.loads((d / "picks.resolved.json").read_text())
            self.assertEqual(resolved["boards"][0]["groups"][0]["picked"][0]["name"], "Star Wand")
            code, _, _ = self.run_cli("read", d, "--strict")
            self.assertEqual(code, 1)

    def test_read_from_an_artifact_dump_and_save_it(self):
        with RoundDir() as d:
            dump = d / "dump.json"
            dump.write_text(json.dumps([{"id": "gloomy", "data": {"picks": {"Look": "C"}, "note": "", "at": 1}}]))
            code, out, _ = self.run_cli("read", d, "--from", dump, "--save")
            self.assertEqual(code, 0, out)
            self.assertEqual(json.loads((d / "picks.json").read_text())["docs"]["gloomy"]["picks"], {"Look": "C"})

    def test_read_from_an_artifact_data_out_dir(self):
        # ArtifactData `list` with out_dir writes <out_dir>/<collection>/<doc_id>.json, each the bare document
        with RoundDir() as d:
            folder = d / "dump" / "picks-00-sample"
            folder.mkdir(parents=True)
            (folder / "wand.json").write_text(json.dumps({"at": 1, "note": "big!", "picks": {"Look": "A"}}))
            code, out, _ = self.run_cli("read", d, "--from", d / "dump")
            self.assertEqual(code, 0, out)
            self.assertIn("“big!”", (d / "PICKS.md").read_text())

    def test_read_from_a_pasted_list_result(self):
        pasted = ('1 document from collection "picks-00-sample":\n=== BEGIN ARTIFACT DB 1 ===\n'
                  '{"id":"gloomy","data":{"at":2,"note":"","picks":{"Look":"B"}},"version":1}\n=== END ===\n')
        with RoundDir() as d:
            (d / "pasted.txt").write_text(pasted)
            code, out, _ = self.run_cli("read", d, "--from", d / "pasted.txt")
            self.assertEqual(code, 0, out)
            resolved = json.loads((d / "picks.resolved.json").read_text())
            self.assertEqual(resolved["boards"][1]["groups"][0]["picked"][0]["name"], "Grumpy Blob")

    def test_build_and_approved_write_pages(self):
        with RoundDir() as d:
            (d / "picks.json").write_text(json.dumps({"docs": {"wand": {"picks": {"Look": "B"}, "note": "spin!",
                                                                         "at": 1}}}))
            self.assertEqual(self.run_cli("build", d)[0], 0)
            self.assertEqual(self.run_cli("approved", d)[0], 0)
            approved = (d / "out" / "approved.html").read_text()
            self.assertIn("Flower Wand", approved)
            self.assertNotIn("Star Wand", approved)
            self.assertIn("“spin!”", approved)
            self.assertIn("Not picked yet", approved)

    def test_check_fails_on_a_broken_round(self):
        board = copy.deepcopy(one_board([option(v) for v in "ABCD"]))
        with RoundDir({"01-a.json": board}) as d:
            code, out, err = self.run_cli("check", d)
        self.assertEqual(code, 1)
        self.assertIn("FAILED", out)
        self.assertIn("three, never more", err)


if __name__ == "__main__":
    unittest.main()
