---
name: playtest
description: Turn a child's playtest into the next steps for their Roblox game. Save the parent's notes with the child's words quoted, sort them into bugs, tweaks and new ideas, offer to fix bugs and tweaks with /build, and turn new ideas into the next /pick round's boards. Can also run an automatic Studio smoke test. Use for "/playtest", "we just played it", "here's what my kid said", "smoke test the game", or "what should we do next".
---

# /playtest: what the child said becomes what happens next

The parent watched their child play and wrote down what they did and said. Your job is to keep the child's words,
sort them, and turn them into the next round, without deciding for the child.

## 1. Collect the notes

Ask the parent for their notes: pasted text, a file, or a voice-memo transcript. If they haven't got any yet, give them
the four questions to ask their child:

- "What was the best bit?"
- "What was boring, or too hard?"
- "Was anything the wrong colour, the wrong size or the wrong speed?"
- "If you could add one thing, what would it be?"

Also ask what they *saw*: where the child went first, where they got stuck, what they kept going back to.

## 2. Save them

Write `design/playtests/<YYYY-MM-DD>.md`:

```markdown
# Playtest: <date>

Played <in Studio / on a tablet / on a phone>, about <n> minutes.

## What they said
- "<their words, exactly>"

## What the parent saw
- <observations>

## Bugs (it's broken)
- <bug> (from: "<quote>" / seen by the parent)

## Tweaks (it works, but…)
- <tweak> → <the number or Definition it touches>

## New ideas (for the next /pick round)
- <idea> (from: "<quote>")

## Questions to ask the child
- <anything ambiguous>
```

Keep personal details out (no full names, schools, ages).

## 3. Sort carefully

- **Bug:** something doesn't work as the spec says. Fix it with `/build`, with a test so it stays fixed.
- **Tweak:** a number, size, speed or difficulty. Find the Definition or `Config` value it touches. If the tweak
  changes something the child **picked** (a colour, a look), update the spec, quoting what they said now.
- **New idea:** anything new to see or do ("can there be a dragon?"). Don't build it. It becomes a board for the next
  `/pick` round, so the child chooses *how* it looks, not just *that* it exists.
- **"It's boring"** is a clue, not a task. Suggest the parent ask "what would make it more fun?" and record the answer.
- If something could be a bug or a design choice ("the Gloomies run away"), ask.

## 4. Offer the next step

Summarise in a few lines, then offer:

1. fix the bugs and tweaks now with `/build`,
2. a draft list of boards for the next `/pick` round, one per new idea,
3. nothing yet, if the child is happy and wants to play more.

The parent and child choose.

## Smoke test (any time)

To check the game boots cleanly in Studio without a child at the keyboard:

```bash
python3 tools/playtest/run.py smoke --dry-run   # show what it would do
python3 tools/playtest/run.py smoke             # start Play, wait for ready, report errors, stop Play
```

It needs Studio open with the MCP server on and Rojo connected, and it starts and stops Play, so only run it when
nobody is playing in Studio. A pass means the game booted with no errors from its own scripts. It doesn't mean the
game is fun; only the child can tell you that.
