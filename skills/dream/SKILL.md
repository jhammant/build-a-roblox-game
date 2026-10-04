---
name: dream
description: Turn a child's game idea into SPEC.md, in their own words. Interview the child through the parent, or turn the parent's notes, a voice-memo transcript or a photo of a drawing into a spec with the core loop, the child's key phrases quoted, defaults clearly marked, and a "To pick" list for the first picking round. Use for "/dream", "let's dream up the game", "here are my kid's ideas", "turn this transcript into a spec", or "start the spec".
---

# /dream: the game, in the child's words

You're helping a parent write down their child's game. The child is the designer. The parent is the scribe. You turn
what they say into `SPEC.md` without making it yours.

## Ground rules

- **Keep the child's words.** Quote their phrases exactly, even odd ones ("scary, not too much, top hats on them").
  Those quotes are what later rounds build from.
- **Don't improve the idea.** If something sounds impossible or strange, write it down anyway and note that the first
  version will be simple.
- **Mark your own additions.** Anything you fill in is a *default*, labelled as one, so the parent can check it.
- **Ask, don't assume.** If an answer could mean two things, ask the parent to ask the child.
- **No personal details.** If the notes include the child's full name, age, school or address, leave them out of
  `SPEC.md`. A first name is fine.
- **Kid-safe.** If an idea is gory or frightening, don't refuse it outright. Ask the parent to check with the child
  ("scary like a ghost train, or scary like a nightmare?"), and write down a cartoon version.

## 1. Find out what you're working from

Ask the parent which of these they have:

1. **Notes or a transcript.** Ask them to paste it, or give you the file path.
2. **A drawing.** Ask for a photo; look at it and describe what you see back to them to check.
3. **Nothing yet: interview.** You'll ask questions; the parent reads them to the child and types the answers word
   for word.

Read `SPEC.md` first. If it's still the template's starter (Spark Garden), you're replacing it. If it's already
theirs, you're adding to it: keep everything already there.

## 2. Interview (if needed)

Ask a few questions at a time, in plain words a child understands. Start wide, then narrow. Stop when you have the
core loop and a handful of vivid details; don't exhaust a child.

- The big idea: "What's your game about?" "If your friend played it for one minute, what would they do?"
- The loop: "What do you collect?" "What do you make with it?" "What do you use it on, and what happens then?"
- The world: "Where does it happen? What colour is it?" "Is there anywhere secret?"
- The characters: "Who are you?" "Who are the bad guys? Funny, scary or both? How scary is OK?" "What happens when
  you beat one?"
- The feeling: "Should it feel exciting, cosy, silly or spooky?" "What would make you play it again tomorrow?"

If they're stuck, offer two silly options. Never offer your own idea as the answer.

## 3. Write SPEC.md

Use this shape. Keep it short: one or two pages.

```markdown
# <Game name>: game spec

Designed by <child's first name>, with <parent, e.g. "their dad">. Written <date> from <an interview / notes / a
voice memo>. Quotes are <first name>'s own words.

## The idea

<Two or three sentences in plain words, quoting the child where you can.>

## The loop

<One line: collect → make → use → reward → explore further, in the game's own terms.>

It should make sense within about 30 seconds of joining.

## The world

## The player

## The bad guys (or the challenge)

## What makes it fun

<Their words: the funny bits, the feelings, what would make them come back.>

## Keeping it kid-safe

<How scary is OK, in their words. No gore, no purchases, no free text. Anything else they or the parent said.>

## Defaults (Claude filled these in; check them)

- <each assumption you made, one line each>

## To pick

<Everything visible that's still undecided, as board ideas for the first /pick round: one line each, saying what's
being chosen. These are questions for the child, not decisions for you.>

## Rounds

<Left empty. /pick adds a line per round, linking its spec in design/specs/.>
```

## 4. Map it onto the template

The template is a working game with a collect → craft → use loop (Sparks → Wand at the Workbench → zap Gloomies). Add
a short section to `SPEC.md` called **How the starter game becomes this one**, saying which template piece becomes
which part of their game (for example, "Sparks → flowers; Workbench → the magic stream; Wand → flower gun; Gloomies →
eyeless monsters"). Keep it a table. That tells `/build` what to rename and reshape, and tells the parent how close
the starting point already is.

## 5. Read it back

Summarise `SPEC.md` for the parent in a few short sentences a child would understand, and ask them to read it to
their child: "Is that your game? Is anything wrong or missing?" Change it until the child says yes. Then commit
`SPEC.md`.

## 6. Next

Tell the parent the next step is `/pick`, and that its first round will come from the **To pick** list.
