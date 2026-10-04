# Spark Garden

This is your child's game folder. It starts as **Spark Garden**, a tiny game that already works: collect Sparks,
take three to the Workbench to make a Magic Wand, and zap the grumpy Gloomies until they cheer up and float away,
dropping more Sparks. Everything about it is meant to change. Your child's picks will turn it into their own game.

It's a game for Roblox, made with Claude Code. It isn't made or endorsed by Roblox.

## What's in here

| | |
|---|---|
| `SPEC.md` | The game, in your child's words. `/dream` writes it |
| `design/` | Each round of picks (`rounds/`), the specs Claude writes from them (`specs/`) and playtest notes (`playtests/`) |
| `src/` | The game's code. Claude writes this |
| `tests/` | Checks that run in about a second, without Studio |
| `tools/playtest/` | Lets Claude play the game in Studio to check it works |
| `CLAUDE.md` | The rules Claude follows here (your child decides, keep it safe) |
| `ARCHITECTURE.md` | How the code fits together, for Claude and anyone curious |

## First run

You need Roblox Studio, Rokit and Claude Code installed (the guide's "Get ready" chapter walks through them). Then,
in this folder:

```bash
rokit install            # fetch the exact tool versions this game uses (say yes when it asks to trust each tool)
rojo plugin install      # add the Rojo button to Studio
rojo build -o Game.rbxlx # make a fresh place file (only the first time)
```

1. Open `Game.rbxlx` in Roblox Studio.
2. Back in the terminal, run `rojo serve`. In Studio, click **Plugins → Rojo → Connect**. Now Studio shows whatever
   is in `src/`, and updates as Claude changes it.
3. Press **Play**. You should land in a garden with Sparks to collect and Gloomies wandering about.

## Checking it works

```bash
lune run tests/run          # the offline checks
selene src                  # lint
stylua --check src tests    # formatting
```

To let Claude playtest in Studio, turn on Studio's MCP server (**Assistant → … → Manage MCP Servers → Enable Studio
as MCP server**). `.mcp.json` already tells Claude Code where to find it on a Mac. On Windows, Roblox's docs give
the command as `cmd.exe /c %LOCALAPPDATA%\Roblox\mcp.bat`: put that in `.mcp.json` (and in the `STUDIO_MCP` setting
the playtest tool reads). The playtest tool itself has only been tested on a Mac.

## Saving progress

While you're testing in Studio, progress is kept in memory only and forgotten when you stop. That's on purpose, so
tests never touch real saves. Once the game is published, it saves each player's Sparks and wand to Roblox.

## Keeping it safe

- Text chat is switched off (`Config.CHAT_ENABLED` in `src/shared/Config.luau`).
- There's nothing to buy.
- Keep family voice recordings out of this folder. `recordings/` is ignored by git, just in case.
