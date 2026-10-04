---
name: pick
description: Run a round of picks for a kid's Roblox game. Draw three options (A, B, C) for each part of the game in its real style, put them on a tap-to-pick page the child uses on a tablet, read their picks and notes back, and write them up as exact build specs. Use for "/pick", "let's do a picking round", "make some boards", "picks are in", "what did they pick", "turn the picks into specs", or when playtest feedback turns into a new round.
---

# /pick: the child chooses, Claude draws and writes it down

This is the heart of the kit. Your job is to give the child real choices and to record exactly what they chose. You
are not the designer. **The child decides.**

- Never pick for the child, and never let the parent's preference stand in for theirs.
- Never swap a pick for something easier to build. If a pick is hard, build a placeholder and say so in the spec.
- Their words are the spec. Quote their notes exactly. When a note could mean two things, stop and ask (through the
  parent) instead of guessing.

The tools are in `tools/picker/`. The data format is in `tools/picker/CONTRACT.md`. Read it before drawing anything.

## 1. Plan the round with the parent

Read, in this order: `SPEC.md` (the dream), `design/specs/` (everything already approved, so you don't ask again),
and the latest playtest notes in `design/playtests/` (where this round's ideas usually come from).

Then propose the round to the parent in a short list: one line per board, saying what's being chosen and whether
it's pick-one (A/B/C) or tap-any. Wait for their OK before drawing.

- **3 to 8 boards per round.** A child stays happy for about 10 to 15 minutes of picking.
- **Round 1** is the look of the core game: the world, the player's look or outfit, the thing you collect, where you
  make things, what you make, and what you use it on. Later rounds come from playtesting: content (bad guys, places,
  bosses), then features (pets, vehicles, rewards, a shop with no real money).
- Only ask what the child can answer by looking. "Which flower gun?" is a good board. "Which damage formula?" isn't.
  Decide technical details yourself and write them into the spec.

## 2. Draw the boards

Make the round folder and `round.json` (see the contract), then one JSON file per board in `boards/`, named
`01-<section>.json`, `02-…` in the order the child will see them. Write each file from Python with
`json.dump(data, f, ensure_ascii=False, indent=2)` so the SVG strings are escaped correctly.

How to draw:

- **In the game's real style.** What the child picks is what gets built. Draw things that can be made from Roblox
  parts (blocks, balls, cylinders, wedges) in flat, bright colours with a thick dark outline, unless `design/specs/`
  has already set a different style. Then follow that style exactly.
- **Three real alternatives.** A, B and C should be different ideas, not three colours of one idea. Colour can be a
  `tweak` (a dropdown) instead of a whole option.
- **Short names a child can read**, and a one-line blurb that says what it does, not just what it looks like.
- **Kid-safe by construction.** No gore, nothing realistic that hurts, no real weapons. Scary only if the child asked
  for scary, and then cartoon scary.
- **Fill in `spec`** with the exact colours (hex), sizes (in studs; a player is about 5 studs tall) and behaviour you
  drew, so the spec you write later doesn't have to guess.
- No text inside drawings unless the text is the design.

Then check and look:

```bash
python3 tools/picker/picker.py check design/rounds/<round>
python3 tools/picker/picker.py sheet design/rounds/<round>
```

Fix every error from `check`. Read `out/sheet.png` once, fix anything that reads badly (too small, too similar, off
style), and move on. Don't loop on polish.

## 3. Give the child the picker

Build the page:

```bash
python3 tools/picker/picker.py build design/rounds/<round>
```

Then pick a backend, in this order:

1. **Claude artifact** (best: picks save as they tap, from any device). If you have the `Artifact` tool, publish
   `design/rounds/<round>/out/picker.html` with `capabilities: {"db": {}}`. Give the parent the link. They open it
   on the tablet **signed in to their own Claude account** (the artifact is private to them). Say that the first tap
   may ask them to allow saving.
2. **Local server** (no accounts). Run `python3 tools/picker/picker.py serve design/rounds/<round>` in the
   background and give the parent the "On the tablet" address it prints. The tablet must be on the same Wi-Fi. Picks
   save to `design/rounds/<round>/picks.json`.
3. **Copy and paste** (last resort). The parent opens `out/picker.standalone.html`, the child picks, and the parent
   taps **Copy picks** and pastes the text to you.

Tell the parent what to say to the child, for example: "Claude has drawn some ideas for your game. Tap the one you
like best in each box. You can change your mind, and you can type ideas in the boxes." Then **wait**. Don't poll or
read picks until the parent says they're in.

## 4. Read the picks back

- **Artifact:** list the collection named in `round.json` (default `picks-<id>`) with `ArtifactData`, using
  `out_dir: design/rounds/<round>/dump`, then run
  `python3 tools/picker/picker.py read design/rounds/<round> --from design/rounds/<round>/dump --save`.
  (`--save` keeps a copy as `picks.json`, so the round's record lives in the repo.)
- **Local server:** `python3 tools/picker/picker.py read design/rounds/<round>`. Stop the server afterwards.
- **Pasted text:** save it to `design/rounds/<round>/pasted.txt`, then write the picks yourself in the `picks.json`
  shape from the contract, and run `read`.

Read `PICKS.md`. Anything **not picked yet**? Ask the parent whether the child wants to finish or skip it. Never fill
a gap yourself.

## 5. Check the notes

Every note is listed under **Notes to check**. For each one, decide what it changes:

- **Clear** ("make it pink", "bigger"): apply it, and say how in the spec.
- **Could mean two things**: stop and ask. Give the parent the readings to put to the child, for example: Gun Flower's
  "all of them" on the portal arches could mean "use every arch design, one per world" or "combine them into one
  arch". Write down the answer.
- **A new idea** ("can it have a pet?"): don't build it now. Add it to the next round's list in the spec.

## 6. Write the spec

Write `design/specs/<round>.md`. It's the source of truth the builder follows. Use this shape:

```markdown
# <Round title>: build spec

Picked by <child's first name> on <date>. Do not redesign anything here. If something can't be built yet, build a
placeholder and list it under "Not built yet". Never swap a pick for an easier one.

## The picks, in their words

| Board | Pick | Their note |
|---|---|---|
| Your magic wand | B · Flower Wand, stick Sunny gold | "make it spin and sparkle!!" |

## Your magic wand: B, Flower Wand

- **Shape:** <the parts it's made of, with sizes in studs>
- **Colours:** <every colour as hex or RGB, and which part it goes on>
- **Behaviour:** <what it does, numbers that matter>
- **Sounds and effects:** <from the extras board, if picked>
- **From their note:** "make it spin and sparkle!!" → the flower head spins once per zap; sparkles on every zap.

## How we read the notes

- "<note>": <what we did with it, and whether the child confirmed it>

## Not built yet

- <anything placeholdered, and why>

## Ideas for next round

- <new ideas from notes>
```

Be exact. "Pink" isn't a spec; `#FF6FB5` on the stick is. Copy colours and sizes from each option's `spec` in
`picks.resolved.json`.

## 7. Show the child what they chose

```bash
python3 tools/picker/picker.py approved design/rounds/<round> [--from <dump>]
```

Publish `out/approved.html` as an artifact (no capabilities needed), or open `out/approved.standalone.html`. It shows
only their picks and notes. It's a nice moment ("that's your game!"), and the builder can check against it.

## 8. Wrap up

- Add the round to the **Rounds** list at the bottom of `SPEC.md`, with a link to its spec.
- Commit the round folder (`round.json`, `boards/`, `picks.json`, `PICKS.md`, `picks.resolved.json`) and the spec.
  Leave `out/` and `dump/` out; they're rebuilt any time.
- Tell the parent what's next: usually `/build` from the new spec.
