---
name: build
description: Build the next piece of a kid's Roblox game from its approved specs. Plan from design/specs, update the contracts in ARCHITECTURE.md first, change Definitions and code with the server in charge, add tests, run Lune, Selene and StyLua, playtest in Studio through the MCP, and commit, one piece at a time, never swapping a child's pick for something easier. Use for "/build", "build the spec", "build round 2", "make the changes", "fix these playtest bugs", or after picks are written up.
---

# /build: build what the child picked

You're building a game a child designed. Their picks, written up in `design/specs/`, are the source of truth. Read
`CLAUDE.md` and `ARCHITECTURE.md` before you change anything.

## Rules

- **Build what was picked.** Never redesign an approved pick, and never swap it for something easier. If something
  can't be built yet, build a clear placeholder and record it under "Not built yet" in the spec.
- **Don't add what wasn't asked for.** New ideas go on the next `/pick` round's list, not into code.
- **When the spec is unclear, ask** the parent (who'll ask the child). Don't guess at anything visible.
- **Kid-safe always.** No gore, no purchases, no unfiltered free text; scary only where the spec says so.
- **Done means tested and playtested**, not just written.

## 1. Plan

Find what to build: the newest spec in `design/specs/` that has unbuilt items, or the playtest list the parent gave
you. Propose a short plan to the parent, one line per piece, in the order you'll build them (core loop changes first,
then content, then polish). Say what each piece changes that the child will see. Wait for their OK.

## 2. For each piece

1. **Contracts first.** If the piece adds remotes, Bus events, save fields, tags or Definitions tables, update
   `ARCHITECTURE.md` before writing code.
2. **Data before code.** Put colours, sizes, speeds, counts and recipes in `src/shared/Definitions/` or `Config.luau`,
   copied exactly from the spec (hex colours, sizes in studs).
3. **Server in charge.** The client asks through a remote; the server checks range, cooldowns and counts, then acts.
   Never trust a number the client sends.
4. **Tests.** Add or update specs in `tests/specs/` for the logic and data you changed (recipes reference real items,
   numbers are in range, the pure logic does what the spec says). Keep game logic in `src/shared` modules where Lune
   can test it.
5. **Check:**

   ```bash
   lune run tests/run
   selene src
   stylua src && stylua --check src tests
   ```

6. **Playtest in Studio** through the Roblox Studio MCP: make sure Rojo is connected (`rojo serve` running and the
   plugin connected), start Play, wait for the server and client "ready" lines, check the console for errors from
   the game's scripts, look at the thing you built (a screenshot, or Luau that inspects the live Instances), then
   stop Play. `python3 tools/playtest/run.py smoke` runs the boot-and-errors part for you.
   - `require` through the MCP returns a fresh copy of a module, so it can't see live state. Inspect Instances
     instead (for example `workspace.Gloomies:GetChildren()`).
   - If Studio isn't reachable, say so and ask the parent to open it; don't mark the piece done.
7. **Commit** with a Conventional Commit message that says what the child will notice, for example
   `feat(wand): flower wand from round 1 pick B`.

## 3. Report

Tell the parent, in plain words:

- what's new that their child will see, and which pick or note it came from,
- what you tested and how (test counts, the playtest result),
- anything left as a placeholder, and why,
- what's next (usually: get your child to play it, then `/playtest`).

## Things to watch

- **Never run `rojo build -o` over the place file** if it has anything built by hand in Studio; it replaces the file.
  Build to a scratch path when you need a build check.
- **Edit scripts in `src/`, never inside Studio**: Rojo overwrites Studio's copies.
- **Studio saves are in memory.** DataStores don't work in an unpublished place, so progress resets each Play. Test
  save logic with the Lune fake DataStore instead.
- **One job per module**, named for it, with a one-line header comment. Follow the patterns already in `src/`.
- If a change would make the game scarier, harder or more grown-up than the spec, stop and ask.
