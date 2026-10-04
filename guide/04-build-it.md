# 4. Build it (Claude builds, parent supervises)

**Who leads:** Claude, with you watching and saying yes or no.

**You'll end up with:** a playable game that matches your child's picks, with tests that prove the important bits work.

**Time:** anything from twenty minutes to a few hours, depending on the round. Your child doesn't need to be there.

## How Claude builds

The template isn't just a starter game. It's set up so Claude can build safely and you can check its work:

- **The code lives in files**, and Rojo syncs it into Studio. That means every change is saved in git and can be
  undone, checked with a linter and tested outside Studio.
- **Contracts first.** Before writing code, Claude updates `ARCHITECTURE.md`: the names of the messages between the
  players' devices and the server, the events systems use to talk to each other, and what gets saved. Deciding
  these first is what keeps a growing game tidy.
- **The server is in charge.** Collecting, crafting, damage and saving happen on Roblox's server, never on the
  player's device. The device asks; the server checks (is the player close enough? do they have enough Sparks?) and
  decides. That stops cheating and a whole class of bugs.
- **Content is data.** Items, recipes, bad guys and colours live in tables in `src/shared/Definitions/`. Changing a
  colour your child picked is a one-line edit, not a hunt through code.
- **Tests run in seconds** without Studio (`lune run tests/run`), and Claude adds tests for each new feature.
- **Real playtests** through Studio's MCP server: Claude starts Play, checks the game booted without errors, looks
  at the result and stops Play. A feature isn't done until a playtest shows it working.

## Running a build

In the game folder:

> /build

Claude reads the newest spec in `design/specs/`, proposes a short plan (what it'll change, in what order), and waits
for your OK. Then it builds one piece at a time, and for each piece:

1. updates the contracts if needed,
2. changes the Definitions and code,
3. adds or updates tests and runs them,
4. checks the code with Selene and StyLua,
5. playtests in Studio,
6. commits the change with a clear message.

It tells you when something from the spec can't be built yet and what placeholder it used instead.

## Your job: supervise, don't author

You don't need to read the code. You do need to keep Claude honest. Good questions to ask:

- "Which line of the spec does this come from?"
- "Did that pass the tests *and* a playtest?"
- "Show me a screenshot of it in the game."
- "Is that what my child picked, or something easier?"
- "What did you leave as a placeholder?"

Say **no** to anything that changes a pick, adds something your child didn't ask for, or makes the game scarier,
harder or more grown-up than they chose. Claude will change course.

## Before you call a round done

- [ ] `lune run tests/run` passes.
- [ ] `selene src` and `stylua --check src` are clean.
- [ ] Claude has playtested it in Studio and shown you.
- [ ] **You've played it yourself** for a minute or two. Does it match the spec? Is anything broken or confusing?
- [ ] Everything is committed (`git status` is clean).

Then go and get your child for [phase 5](05-play-it.md).

## Things that trip people up

- **Edit code in files, not in Studio.** Rojo overwrites scripts in Studio with the files on disk. Anything typed into
  a script inside Studio is lost.
- **Hand-built things live in the place file.** The template builds its whole world from code, so place files
  aren't committed (`.gitignore` leaves out `*.rbxlx`). If you or your child build something by hand in Studio (a
  house, some trees), it's saved only in the place file, not in `src/`. Save it (**File → Save to File**), and if
  you want it in git, take `*.rbxlx` out of `.gitignore` and commit it. Never run `rojo build -o` over a place file
  that has hand-built things in it: it replaces the whole file.
- **Studio needs to be open** for Claude's playtests. If Claude says it can't reach Studio, check Studio is open with
  the MCP server switched on ([chapter 1](01-get-ready.md#connect-claude-to-studio)).
- **Studio saves are pretend.** In Studio the game keeps saves in memory only, so progress resets every time you
  press Play. That's expected. Real saving starts once the game is published.
- **One Studio, one game.** If you have another game open in Studio, close it, or tell Claude which window to use.

## Keeping it affordable

One Claude session is plenty for a family game, and it's what this guide assumes. If you want to try several agents
building in parallel, see [Going faster with several agents](advanced-multi-agent.md). It's quicker but uses a lot
more of your Claude plan.

**Next:** [5. Play it](05-play-it.md).
