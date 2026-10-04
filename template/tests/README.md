# Tests

Two kinds, for two jobs:

| | What it checks | Needs Studio? | Command |
|---|---|---|---|
| `tests/` (Lune) | The data, the pure logic, the models, and the real Save and Inventory systems against a pretend DataStore | No | `lune run tests/run` |
| `tools/playtest/` | The real game in Studio: it starts, builds the garden, and our scripts log no errors | Yes, and it **starts Play** | `python3 tools/playtest/run.py smoke` |

Run the Lune tests after every change. They take about a second.

```bash
lune run tests/run          # everything
lune run tests/run save     # only tests whose "<suite> <name>" contains "save"
```

Each test prints `PASS`, `FAIL` or `SKIP`, then there's a summary, and the exit code is 1 if anything failed. Data
tests use soft checks, so one failure lists every bad entry at once.

## What's covered

| Spec | Checks |
|---|---|
| `modules` | Every file under `src/` compiles; every shared module loads without errors or warnings |
| `definitions` | Colours are colours, item ids are unique, recipes use real items, Gloomies drop real items, everything is on the map, and every recipe's ingredients can be found in the game |
| `bag`, `craft`, `zap` | The pure logic: adding and taking items, cleaning saved items, making recipes and explaining what's missing, what a zap hits, range and cooldown |
| `models` | Every placeholder model builds from the real looks, has a PrimaryPart and stays under the part budget |
| `save` | The real Save system: round trips between two servers, migrations, repairing damaged data, Studio's in-memory mode, session locks (waiting, taking over, stale locks), never overwriting a newer save, surviving an outage, saving on shutdown, and erasing |
| `inventory` | The real Inventory with Save: adding, limits, crafting, telling the client, and refusing changes before the save loads |

## How it works

`lib/shim.luau` builds a pretend game tree laid out the way Rojo syncs `src/` (`ReplicatedStorage.Shared`,
`ServerScriptService`) and runs the real modules in it, with Roblox's datatypes from Lune and stubs for the services
Lune doesn't have (`lib/stubs.luau`). `lib/fakes.luau` adds a pretend DataStoreService (which refuses what Roblox
refuses: NaN, mixed tables and so on), a pretend Players service, and `Fakes.server(ctx, options)`, a whole pretend
server. `fixtures/Remotes.luau` stands in for the real remotes and records what the server sends.

## Adding a test

Add a `t.test(...)` to the right file in `specs/`, or add a new spec file to `SPECS` in `run.luau`.

```lua
t.test("every Gloomy drops something", function()
	local Gloomies = ctx.need("Definitions/Gloomies") -- SKIPs if the file isn't written yet
	for _, def in Gloomies.LIST do
		t.check(def.drops.count > 0, def.id .. " drops nothing") -- soft: keeps going
	end
end)
```

Helpers: `t.check`, `t.checkEq` (soft), `t.ok`, `t.eq`, `t.near`, `t.contains`, `t.fail` (stop the test),
`t.skip(reason)`, `t.note(text)`.

## Studio playtests

`tools/playtest/run.py` drives Studio through its MCP server. **A real run starts and stops Play**, so only run it
when nobody else is using Studio.

```bash
python3 tools/playtest/run.py --list            # the scenarios
python3 tools/playtest/run.py smoke --dry-run   # the MCP calls it would make; sends nothing
python3 tools/playtest/run.py smoke             # run it (starts Play!)
```

`smoke` checks that Studio isn't already playing, starts Play, waits for `[Main] server ready` and
`[Main] client ready`, lets the game run for a few seconds, checks the garden was built, fails on any error from our
scripts, and stops Play. Exit codes: 0 pass, 1 fail, 2 setup problem (no Studio connected, for example).

A scenario is a JSON file in `tools/playtest/scenarios/` with `steps` and `cleanup`. The steps are
`check_edit_mode`, `start_play`, `stop_play`, `sleep`, `wait_for_logs`, `collect_errors`, `execute_luau` (with an
optional `expect`) and `screenshot`. The MCP client is `tools/playtest/studio_client.py`; set `STUDIO_MCP` if Studio's
`StudioMCP` program isn't in the usual macOS place. The client is only tested on a Mac.
