# The picker contract

A **round** is one sitting of picks: a few boards your child taps through on a tablet. Each **board** is one JSON
file. Adding a board means adding one more file. `picker.py` checks the files, builds the tap-to-pick page, saves the
picks, and reads them back for Claude.

This is the format Gun Flower's third round settled on, when several art agents each drew one board in parallel and a
generator stitched the page together. It's written so Claude (or several Claudes) can draw boards without touching any
code.

## A round on disk

```text
design/rounds/01-look/
├── round.json          the round: title, intro, where picks are saved
├── boards/
│   ├── 01-hero.json    one board per file, shown in filename order
│   ├── 02-world.json
│   └── 03-extras.json
├── picks.json          the picks (local backend), or a dump of the artifact database
├── PICKS.md            what `picker.py read` writes: every pick and note, in plain words
├── picks.resolved.json the same picks, joined to each option's details, for the spec writer
└── out/                built pages (rebuild any time)
    ├── picker.html             publish this as a Claude artifact
    ├── picker.standalone.html  open this, or let `picker.py serve` serve it
    ├── approved.html           "what you picked", once picks are in
    └── sheet.png               a contact sheet of every option, for Claude to look at
```

## `round.json`

```json
{
  "id": "01-look",
  "title": "Pick your game's look",
  "intro": "Tap your favourite in each box. You can change your mind as often as you like.",
  "game": "Spark Garden",
  "collection": "picks-01-look",
  "done": "Tell Claude “picks are in” and it will start building."
}
```

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Short id for the round. Letters, digits, `-` and `_` |
| `title` | yes | The big heading on the page |
| `intro` | no | One or two sentences your child reads first |
| `game` | no | The game's name, shown above the title |
| `collection` | no | Where the artifact database keeps the picks. Defaults to `picks-<id>` |
| `done` | no | What the page says when every board is picked |

## A board

```json
{
  "section": "hero",
  "title": "Your hero",
  "question": "Who do you play as?",
  "cardWidth": 220,
  "groups": [
    {
      "key": "Look",
      "title": "Hero look",
      "subtitle": "one short line under the title",
      "mode": "one",
      "tweaks": [
        { "key": "Colour", "label": "Which colour?", "choices": ["Pink", "Blue", "Gold"], "default": "Pink" }
      ],
      "options": [
        {
          "value": "A",
          "name": "Star Fox",
          "blurb": "A speedy fox with a star on its tail.",
          "svg": "<svg viewBox='0 0 240 240' xmlns='http://www.w3.org/2000/svg'>…</svg>",
          "spec": { "body": "#FF9F1C", "outline": "#2B1B4A", "size_studs": 5 }
        }
      ]
    }
  ]
}
```

**Board fields**

| Field | Required | Meaning |
|---|---|---|
| `section` | no | The board's id. Defaults to the filename without its number (`01-hero.json` → `hero`) |
| `title` | yes | The board's heading |
| `question` | no | The question your child answers, under the heading |
| `cardWidth` | no | Smallest card width in pixels. Defaults to 220 for A/B/C cards and 110 for chips |
| `groups` | yes | One or more choices on this board |

**Group fields**

| Field | Required | Meaning |
|---|---|---|
| `key` | yes | The choice's id, unique on the board |
| `title` | yes | What's being chosen |
| `subtitle` | no | One short extra line |
| `mode` | no | `"one"` (pick one of A, B, C) or `"many"` (tap any). Defaults to `"one"` |
| `tweaks` | no | Dropdowns that adjust the pick (a colour, a size, which two flowers make it). Each has `key`, `label`, `choices` and `default` |
| `extra` | no | Anything else the spec writer should know about this choice. Passed through untouched |
| `options` | yes | The options |

**Option fields**

| Field | Required | Meaning |
|---|---|---|
| `value` | yes | `"A"`, `"B"` or `"C"` in `one` mode. A short id (`"Sparkles"`) in `many` mode |
| `name` | yes | A short name a child can read. 32 characters at most |
| `blurb` | no | One line saying what it is. 100 characters at most. Shown on A/B/C cards |
| `svg` | one of | The drawing, inline (see the art rules below) |
| `image` | one of | Or a PNG, JPEG, WebP or SVG file, as a path relative to the board file. Embedded in the page |
| `spec` | no | The exact details behind the drawing (colours, sizes, behaviour), so the spec writer doesn't have to guess them from the picture |

## The rules `picker.py check` enforces

These are errors, and the page won't build until they're fixed:

- **Three options, never more.** A `one` group has at most three options. Fewer than three is allowed, with a
  warning. A `many` group has 2 to 16 options.
- Every `value`, `key` and `section` is unique where it needs to be, and uses only letters, digits, `-` and `_`.
- Every option has a `name` and exactly one of `svg` or `image`.
- Every SVG parses as XML, has an `<svg>` root, and is **self-contained and inert**: no `<script>`, no
  `<foreignObject>`, no `<image>`, no `on…=` event attributes, no `javascript:` and no links outside the drawing
  (`href` may only point at `#an-id` inside it). Ids inside an SVG are fine, because the builder prefixes them.
- Every tweak has 2 to 30 choices, and its `default` is one of them.

These are warnings (the page still builds):

- a name over 32 characters, or a blurb over 100,
- an SVG without a `viewBox`,
- a page over 8 MB (it's an error over 15 MB).

## The art rules (for whoever draws the boards)

- **Draw it in the game's real style.** What your child picks is what gets built, so the picture has to match what
  the game can actually look like. Use the colours, outline weight and shapes the game uses.
- **Kid-safe by construction.** No gore, no weapons that look real, nothing frightening unless your child asked for
  scary, and then only "scary, not too much".
- **Three real alternatives.** Make A, B and C different ideas, not three shades of one idea. If one option is
  obviously the "right" answer, the board isn't doing its job.
- **No text inside drawings** unless the text is the design (a logo). If you need letters, draw them as paths or use
  `font-family="Arial Rounded MT Bold, Arial, sans-serif" font-weight="bold"`.
- **Fill in `spec`.** Record the exact colours and sizes you drew, so picks become specs without guesswork.
- Check your drawings: `picker.py sheet <round>` renders every option into `out/sheet.png`. Look at it once and fix
  anything that reads badly.

## Where picks are saved

Each board's picks are one document:

```json
{
  "picks": { "Look": "B", "Look.Colour": "Gold", "Sounds": ["Boing", "Pop"] },
  "note": "make it sparkly!!",
  "at": 1759600000000
}
```

- `picks[<group>]` is `"A"`/`"B"`/`"C"` (or the option's value) in `one` mode, or a list of values in `many` mode.
- `picks["<group>.<tweak>"]` is the chosen tweak.
- `note` is whatever your child typed in the board's note box, up to 300 characters.
- `at` is when it was saved, in milliseconds since 1970.

There are three backends. The page picks the first one that works:

1. **Claude artifact database.** Publish `out/picker.html` as a Claude artifact with the `db` capability. Each board
   is saved to `<collection>/<section>`. Claude reads them back with `ArtifactData` (`list` on the collection).
2. **Local server.** `picker.py serve <round>` serves the page on your home network and saves picks to
   `picks.json`. Open the address it prints on the tablet. No accounts needed.
3. **Copy and paste.** If neither works (say, the file opened directly), the page keeps the picks in that browser
   and shows a **Copy picks** button. Paste the text to Claude.

`picks.json` has the same shape whichever backend filled it:

```json
{ "collection": "picks-01-look", "docs": { "hero": { "picks": {}, "note": "", "at": 0 } } }
```

## Reading picks back

`picker.py read <round>` checks every pick against the boards and writes:

- `PICKS.md`: each board, what was picked (letter, name and blurb), the tweaks, and the note, quoted exactly. Boards
  that aren't finished are flagged. Every note is listed again at the end, under **Notes to check**, because notes
  can change what a pick means.
- `picks.resolved.json`: the same, with each option's `spec` and `extra` attached, for writing the build spec.

Use `--from <file>` to read a dump of the artifact database instead of `picks.json`.
