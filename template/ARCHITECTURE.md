# Architecture: the contracts

Read this before writing code. It fixes the shared pieces (start order, remotes, events, the save, tags and data) so
that every change fits with the rest. When you add one of these, add it here in the same change.

The rules behind it:

- **The server is in charge.** Collecting, crafting, zapping and saving all happen on the server. The client only
  asks (through remotes) and shows things. The server checks every request: range, cooldown, counts and types.
- **Content is data.** Items, recipes, Gloomies, colours and the layout are tables in `src/shared/Definitions/`.
  A round of picks changes those tables, not the code. Numbers live in a module's `TUNING` or `Config`, never inline.
- **Logic that can be pure is pure.** `Bag`, `Craft` and `Zap` in `src/shared/` make no Roblox calls, so the Lune
  tests check them in a second.

## Folders

| Folder | Becomes | What's in it |
|---|---|---|
| `src/server/` | ServerScriptService | `Main.server.luau`, `Bus.luau`, `Systems/` |
| `src/client/` | StarterPlayerScripts | `Main.client.luau`, `Controllers/` |
| `src/shared/` | ReplicatedStorage.Shared | `Config`, `Remotes`, `Bag`, `Craft`, `Zap`, `Models`, `Definitions/` |

## Start order

`Main.server` creates the remotes and the workspace folders (`Config.FOLDERS`), then requires each system in
`ORDER` and calls `Init` on all of them, then `Start` on all of them. Characters are held back until then
(`CharacterAutoLoads = false`), so nobody spawns into an empty place. A system that errors is logged and skipped;
the rest keep running. When everything has started it prints `[Main] server ready: <game name>`.

| # | System | Owns | Others may call |
|---|---|---|---|
| 1 | `World` | The ground, path, spawn, Workbench and flowers (built in `Init`) | `World.randomPointIn(area, rng)`, `World.TAGS` |
| 2 | `Save` | Every player's profile in a DataStore | `get`, `isLoaded`, `onLoaded`, `markDirty`, `saveNow`, `erase`, `mode` |
| 3 | `Inventory` | `profile.inventory` | `count`, `add`, `take`, `craft`, `snapshot` |
| 4 | `Sparks` | Spark pickups in `workspace.Sparks` | `spawnAt(ground, itemId, fromArea)`, `drop(position, itemId, count)` |
| 5 | `Gloomies` | Gloomies in `workspace.Gloomies`, and `profile.stats` | `targets()`, `hit(id, player, power)`, `spawnOne()` |
| 6 | `Crafting` | The Make prompt on every CraftPoint | `use(player, point)` |
| 7 | `Wands` | The wand in your hand, and checking every zap | `equip(player)` |

A system may call the systems above it in this table, and listen to any Bus event. Only `Inventory` changes items;
only `Gloomies` changes `stats`.

`Main.client` starts the controllers in its own `ORDER` and prints `[Main] client ready: <game name>`:

| Controller | What it does |
|---|---|
| `Chat` | Turns Roblox's text chat off unless `Config.CHAT_ENABLED` is true |
| `Effects` | Sparkles when you collect, the zap line, the cheer burst, a celebration when you make something (from `InventoryChanged`). Looks only |
| `Hud` | The Sparks counter, the wand badge, the hint line and short messages (`Notify`) |
| `WandInput` | Click or tap to zap; a big ZAP button on touch screens. Sends `Zap` |

## Remotes

All of them are listed in `src/shared/Remotes.luau`. The server creates them; `Remotes.get(name)` finds one.

| Remote | Direction | Payload | Server checks |
|---|---|---|---|
| `InventoryChanged` | server → one player | `items: { [itemId]: count }` | |
| `Notify` | server → one player | `text: string` | |
| `Collected` | server → one player | `itemId: string, position: Vector3` | |
| `Zapped` | server → everyone | `from: Vector3, to: Vector3, hit: boolean` | |
| `Cheered` | server → everyone | `position: Vector3, colour: Color3` | |
| `Zap` | client → server | `aim: Vector3` | a real Vector3, owns a wand, cooldown, range, what's near the aim |
| `GetInventory` | client → server (function) | returns `{ [itemId]: count }` | only their own items |

Crafting has no remote: it uses a ProximityPrompt, which the server hears directly, and the server checks the
distance again.

## Bus events (server only)

`Bus.fire(event, ...)` runs every listener in its own thread; `Bus.on(event, fn)` returns a function that stops
listening.

| Event | Arguments | Fired by | Heard by |
|---|---|---|---|
| `SaveLoaded` | `player, profile` | Save | (anything that sets up per-player state) |
| `ItemsChanged` | `player, items` | Inventory | Wands (put the wand in their hand), Sparks |
| `SparkCollected` | `player, amount` | Sparks | |
| `ItemCrafted` | `player, recipeId, itemId` | Crafting | |
| `GloomyCheered` | `player, position, def` | Gloomies | Sparks (drops) |

## The save

One DataStore (`PlayerData`), one key per player (`Player_<UserId>`), written only with `UpdateAsync`. A record is
`{ schema, data, savedAt, lock }`.

| Section | Shape | Owner |
|---|---|---|
| `inventory.items` | `{ [itemId]: count }`, only known items, 1 to `maxStack` | Inventory |
| `stats.cheered` | whole number ≥ 0 | Gloomies |

- **Loading** takes a lock (`{ job, at }`), so two servers never write the same save. If another server holds a fresh
  lock it waits and retries, then takes over. A lock older than `LOCK_SECONDS` is from a crashed server and is taken
  at once.
- **Schema.** `Save.SCHEMA_VERSION` is the current shape. To change the shape, bump it and add
  `Save.MIGRATIONS[old]` (old → old + 1). Never edit a migration that has shipped. A save from a newer version of
  the game is never written by an older server.
- **Repair.** Everything loaded goes through `Save.repair`, which keeps only valid values. A damaged save never stops
  anyone playing.
- **When it writes:** autosave every `AUTOSAVE_SECONDS`, when a player leaves, and on shutdown (`BindToClose`).
  If loading failed, it never writes, so an outage can't wipe progress.
- **In Studio** (and in a place that isn't published) it saves to memory only, warns once, and never touches real
  data. `Save.TUNING.USE_DATASTORES_IN_STUDIO` changes that, and should only ever be used on a test copy.
- **Deleting** a player's data on request: `Save.erase(userId)`.

To add a section: add it to `Save.defaultProfile`, teach `Save.repair` to check it, bump the schema with a migration
if old saves need it, give it one owner, and list it in the table above.

## Tags and attributes

| Tag | On | Attributes | Used by |
|---|---|---|---|
| `CraftPoint` | the Workbench (or anything you build by hand and tag) | `Station` (`"Workbench"`) | Crafting |
| `Spark` | each Spark pickup | `Item`, `FromArea`, `Taken` | Sparks, Effects |
| `Gloomy` | each Gloomy | `GloomyId` | WandInput (touch aiming) |

Players get a `SaveState` attribute: `Loading`, `Saving` or `NotSaving`.

## Definitions (what the picks change)

| Module | What's in it | What a pick usually changes |
|---|---|---|
| `Palette` | Every colour, by name | The colours |
| `Items` | Sparks and the Wand: names, icons, `maxStack`, `look`, the wand's `zap` numbers | Looks, names, the wand's power |
| `Recipes` | What the Workbench makes, from what | Costs, new things to make |
| `Gloomies` | Kinds of Gloomy, how many zaps cheer them up, what they drop, `TUNING` | Looks, numbers, new kinds |
| `World` | Where everything goes | The layout |

`Models` builds the placeholder models from these looks out of plain parts. When a pick changes a shape, change
`Models` too, and keep each model under the part budget in `tests/specs/models.luau`.

## Testing

- `lune run tests/run` checks the data, the pure logic, the models and the real Save and Inventory systems against a
  pretend DataStore, in about a second. See `tests/README.md`.
- `python3 tools/playtest/run.py smoke` plays the game in Studio through the MCP server and fails on any error from
  our scripts. It starts Play, so only run it when nobody else is using Studio.
