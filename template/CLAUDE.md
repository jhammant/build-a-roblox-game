# A game for a child, built together

This is a Roblox game a child is designing with their parent. **The child decides what's in it.** You build it. The
parent guides, keeps it safe and publishes.

## The child decides

- `design/specs/` holds the specs written from the child's picks. They're the source of truth for how things look and
  behave. `SPEC.md` is the child's description of the whole game, in their words.
- Never redesign anything a spec has settled, and never swap a pick for something easier to build. If a pick is hard,
  build a placeholder, keep the pick on the list, and say so.
- When something is unclear (a note that could mean two things, a gap in the spec, a choice that changes how the game
  feels), stop and ask. The parent will ask the child. Write the answer into the spec.
- If an idea needs the child to choose between looks, suggest a `/pick` round instead of choosing yourself.

## Layout

- `src/server/` → ServerScriptService. `Main.server.luau` starts the systems in `Systems/` in order.
- `src/client/` → StarterPlayerScripts. `Main.client.luau` starts the controllers in `Controllers/`.
- `src/shared/` → ReplicatedStorage.Shared. `Config.luau`, `Remotes.luau`, pure logic (`Bag`, `Craft`, `Zap`),
  `Models.luau` and `Definitions/` (the game's data).
- `ARCHITECTURE.md` is the contract: start order, remotes, Bus events, save sections, tags. **Read it before coding,
  and update it in the same change when you add one of those.**
- `default.project.json` maps the folders into the game. The place file (`*.rbxlx`) only holds what's built by hand in
  Studio; it isn't committed.
- `design/rounds/` holds each round of picks, `design/specs/` the specs written from them, and `design/playtests/`
  the notes from playtests.

## Commands

Tools are pinned in `rokit.toml` (`rokit install` fetches them).

- `rojo serve`: live-sync `src/` into Studio (in Studio: Plugins → Rojo → Connect)
- `lune run tests/run`: the offline tests (about a second). `lune run tests/run save` runs only matching tests
- `selene src`: lint
- `stylua src tests`: format (`stylua --check src tests` to verify)
- `rojo build -o <Name>.rbxlx`: only for a brand-new place file
- `python3 tools/playtest/run.py smoke`: a Studio playtest through the MCP server (`--dry-run` to see the plan first)

## How to build here

- **Contracts first.** Decide the names (remotes, Bus events, save sections, tags, Definitions fields) and write
  them into `ARCHITECTURE.md` before the code.
- **The server is in charge.** The client asks through remotes; the server checks range, cooldowns, counts and types
  on every request. Never trust a number from a client.
- **Content is data.** New items, recipes, Gloomies and colours go in `Definitions/`. Numbers go in `TUNING` or
  `Config`, never inline.
- **One job per module**, named for it, with a one-line header comment saying what it does.
- **Saves:** go through `Save` (`onLoaded`, `get`, `markDirty`). Changing the save's shape needs a schema bump and a
  migration. Never edit a shipped migration.

## Done means tested and played

A change isn't done until all of these pass:

1. `lune run tests/run` (add tests for new logic and data rules)
2. `selene src` and `stylua --check src tests`
3. A playtest in Studio that shows it working: the smoke scenario, plus whatever proves the feature (run Luau on
   the server or client, look at the screen). Lint passing isn't the same as working.

## Studio and its MCP server

`.mcp.json` registers Studio's built-in MCP server (`Roblox_Studio`). It only has tools while Studio is open with
Assistant → … → Manage MCP Servers → "Enable Studio as MCP server" switched on. Use it to read the live game tree,
run Luau, start and stop Play, and take screenshots.

- Keep **one** long-lived `StudioMCP` bridge running for the session. Studio only connects while a bridge is
  listening, and starting several confuses it.
- Running Luau through the MCP gives `require` a **fresh copy** of a module, so a module's live state looks
  unstarted. Read Instances and attributes (for example `workspace.Sparks`, a player's `SaveState`) instead.
- Don't start Play while someone else is testing. The smoke runner refuses to take over a running Play session.
- Save the place (File → Save to File) only when the parent asks: the cloud copy may have things built by hand.

## Keep it kid-safe

- No gore and no blood. Things that are "defeated" cheer up, pop or turn into something nice.
- Scary only where the child asked for it, kept cartoon-scary, signposted, and easy to avoid.
- No free text that other players can see, unless it goes through `TextService` filtering. Names come from lists.
- No purchases, no paid random items, and no pressure to spend.
- Roblox's text chat stays off (`Config.CHAT_ENABLED = false`) unless the parent decides otherwise.
- Family voice recordings and photos are never uploaded or committed. Only finished, mixed sounds go to Roblox.
- Nothing in the game shows the child's full name, age, school or username.

## The parent publishes

Publishing, the Maturity questionnaire, audience settings, asset permissions and API keys are the parent's jobs.
You can prepare the build and the checklist (`/publish`), but never change publishing or account settings yourself,
and never put an API key in a file. Keys live in the computer's keychain.
