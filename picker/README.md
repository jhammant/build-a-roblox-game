# picker

The tap-to-pick page your child uses to choose what goes in their game. Claude draws three options for each part of
the game, `picker.py` turns them into a page that works on a tablet, and the picks come back as plain words Claude
can build from.

It's one Python file with no dependencies (Python 3.9 or later). In a game folder made from the template, it lives
at `tools/picker/`, and the `/pick` skill drives it.

```bash
python3 picker.py check  sample   # are the boards valid?
python3 picker.py sheet  sample   # out/sheet.png: every option on one image
python3 picker.py build  sample   # out/picker.html (artifact) and out/picker.standalone.html
python3 picker.py serve  sample   # serve it to a tablet on your Wi-Fi; picks save to picks.json
python3 picker.py read   sample   # PICKS.md and picks.resolved.json from the saved picks
python3 picker.py approved sample # out/approved.html: only what was picked
```

- [`CONTRACT.md`](CONTRACT.md) is the format: one JSON file per board, three options per choice, and where the
  picks are saved.
- [`sample/`](sample/) is a tiny three-board round for a game called Spark Garden, matching the template's starter
  game. Try it with `serve`.
- The page saves picks to whichever of these works first: a Claude artifact's database, the local `serve` server,
  or the browser it's open in (with a **Copy picks** button).

Tests:

```bash
python3 -m unittest discover -s picker/tests
```
