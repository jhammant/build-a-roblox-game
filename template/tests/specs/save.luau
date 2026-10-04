-- save spec: the real Save system on a pretend server with pretend DataStores. Each test is a fresh server; a test
-- that needs two servers shares one DataStore between them, like Roblox does.
local task = require("@lune/task")

local Fakes = require("../lib/fakes")

local KEY = "Player_"

-- Start Save on a fake server, with waits and autosave turned off so tests run instantly
local function startSave(server: any, tweak: { [string]: any }?): any
	local Save = server.loader:requireServer("Systems/Save")
	Save.TUNING.AUTOSAVE_SECONDS = 0
	Save.TUNING.RETRY_WAIT = 0
	for key, value in tweak or {} do
		Save.TUNING[key] = value
	end
	Save:Init()
	Save:Start()
	return Save
end

-- Let spawned loads and retries run
local function settle()
	for _ = 1, 20 do
		task.wait()
	end
end

local function warningsMatching(server: any, text: string): number
	local n = 0
	for _, warning in server.loader:warningsSince(0) do
		if string.find(warning, text, 1, true) then
			n += 1
		end
	end
	return n
end

return function(t, ctx)
	t.test("a new player starts empty, and leaving saves their progress and lets go of the lock", function()
		local server = Fakes.server(ctx)
		local Save = startSave(server)
		local player = server.players.join(1)
		settle()
		t.eq(Save.isLoaded(player), true, "loaded")
		t.eq(Save.mode(), "datastore", "a published server uses DataStores")
		t.eq(next(Save.get(player).inventory.items), nil, "starts with an empty bag")
		Save.get(player).inventory.items.Spark = 5
		Save.markDirty(player)
		server.players.leave(player)
		local record = server.store():read(KEY .. 1)
		t.ok(record ~= nil, "nothing was written")
		t.eq(record.schema, Save.SCHEMA_VERSION, "schema")
		t.eq(record.data.inventory.items.Spark, 5, "Sparks saved")
		t.eq(record.lock, nil, "lock released on leaving")
	end)

	t.test("a second server loads what the first one saved", function()
		local stores = Fakes.dataStoreService()
		local first = Fakes.server(ctx, { dataStores = stores, jobId = "job-A" })
		local SaveA = startSave(first)
		local player = first.players.join(2)
		settle()
		SaveA.get(player).inventory.items.Spark = 3
		SaveA.get(player).inventory.items.Wand = 1
		SaveA.get(player).stats.cheered = 4
		SaveA.markDirty(player)
		first.players.leave(player)

		local second = Fakes.server(ctx, { dataStores = stores, jobId = "job-B" })
		local SaveB = startSave(second)
		local again = second.players.join(2)
		settle()
		local profile = SaveB.get(again)
		t.eq(profile.inventory.items.Spark, 3, "Sparks")
		t.eq(profile.inventory.items.Wand, 1, "Wand")
		t.eq(profile.stats.cheered, 4, "cheered count")
	end)

	t.test("an old save is migrated to the current schema", function()
		local server = Fakes.server(ctx)
		server.store():put(KEY .. 3, { sparks = 4 }) -- a schema-0 save: Sparks as a plain number
		local Save = startSave(server)
		local player = server.players.join(3)
		settle()
		t.eq(Save.get(player).inventory.items.Spark, 4, "Sparks carried over")
		server.players.leave(player)
		local record = server.store():read(KEY .. 3)
		t.eq(record.schema, Save.SCHEMA_VERSION, "written back at the current schema")
		t.eq(record.data.sparks, nil, "the old field is gone")
	end)

	t.test("damaged data is repaired, not trusted", function()
		local server = Fakes.server(ctx)
		server.store():put(KEY .. 4, {
			schema = 1,
			data = {
				inventory = { items = { Spark = -3, Wand = 7, Banana = 2 } },
				stats = { cheered = "lots" },
			},
		})
		local Save = startSave(server)
		local player = server.players.join(4)
		settle()
		local profile = Save.get(player)
		t.eq(profile.inventory.items.Spark, nil, "negative Sparks dropped")
		t.eq(profile.inventory.items.Wand, 1, "Wand capped at maxStack")
		t.eq(profile.inventory.items.Banana, nil, "unknown item dropped")
		t.eq(profile.stats.cheered, 0, "a bad number becomes 0")
	end)

	t.test("repair survives anything", function()
		local Save = Fakes.server(ctx).loader:requireServer("Systems/Save")
		for _, junk in { nil, 7, "text", true, { inventory = "x" }, { inventory = { items = { 1, 2, 3 } } } } do
			local profile = Save.repair(junk)
			t.check(type(profile.inventory.items) == "table", "inventory.items for " .. tostring(junk))
			t.check(profile.stats.cheered == 0, "stats.cheered for " .. tostring(junk))
		end
	end)

	t.test("Studio keeps saves in memory and says so once", function()
		local server = Fakes.server(ctx, { studio = true })
		local Save = startSave(server)
		local player = server.players.join(5)
		settle()
		t.eq(Save.mode(), "memory", "mode")
		t.eq(Save.isLoaded(player), true, "still loads")
		Save.get(player).inventory.items.Spark = 2
		Save.markDirty(player)
		server.players.leave(player)
		t.eq(server.store().calls, 0, "never touched the DataStore")
		t.eq(warningsMatching(server, "Saving to memory only"), 1, "one warning")
	end)

	t.test("an unpublished place keeps saves in memory too", function()
		local server = Fakes.server(ctx, { gameId = 0 })
		local Save = startSave(server)
		t.eq(Save.mode(), "memory", "mode")
		t.contains(server.loader:warningsSince(0)[1] or "", "isn't published")
	end)

	t.test("waits for another server's lock, then takes over", function()
		local server = Fakes.server(ctx)
		server.store():put(KEY .. 6, {
			schema = 1,
			data = { inventory = { items = { Spark = 9 } }, stats = { cheered = 0 } },
			lock = { job = "another-server", at = os.time() },
		})
		local Save = startSave(server, { LOCK_TRIES = 3 })
		local player = server.players.join(6)
		settle()
		t.eq(Save.isLoaded(player), true, "loaded in the end")
		t.eq(Save.get(player).inventory.items.Spark, 9, "with the stored progress")
		t.eq(server.store():read(KEY .. 6).lock.job, "job-1", "now holds the lock")
		t.eq(warningsMatching(server, "Took over"), 1, "said it took over")
	end)

	t.test("a stale lock from a crashed server is taken straight away", function()
		local server = Fakes.server(ctx)
		server.store():put(KEY .. 7, {
			schema = 1,
			data = { inventory = { items = { Spark = 1 } }, stats = { cheered = 0 } },
			lock = { job = "crashed-server", at = os.time() - 100000 },
		})
		local Save = startSave(server)
		local player = server.players.join(7)
		settle()
		t.eq(Save.isLoaded(player), true, "loaded")
		t.eq(warningsMatching(server, "Took over"), 0, "no takeover needed")
	end)

	t.test("a save from a newer version of the game is never overwritten", function()
		local server = Fakes.server(ctx)
		local future = { schema = 99, data = { inventory = { items = { Spark = 50 } } }, extra = "keep me" }
		server.store():put(KEY .. 8, future)
		local Save = startSave(server)
		local player = server.players.join(8)
		settle()
		t.eq(Save.isLoaded(player), true, "you can still play")
		t.eq(Save.get(player).inventory.items.Spark, 50, "with what it could read")
		Save.markDirty(player)
		server.players.leave(player)
		local record = server.store():read(KEY .. 8)
		t.eq(record.schema, 99, "schema untouched")
		t.eq(record.extra, "keep me", "nothing rewritten")
	end)

	t.test("a DataStore outage never wipes a save", function()
		local server = Fakes.server(ctx)
		server.store():put(KEY .. 9, { schema = 1, data = { inventory = { items = { Spark = 8 } }, stats = {} } })
		server.store().failNext = 100
		local Save = startSave(server)
		local player = server.players.join(9)
		settle()
		t.eq(Save.isLoaded(player), true, "you can still play")
		Save.get(player).inventory.items.Spark = 0
		Save.markDirty(player)
		server.store().failNext = 0
		server.players.leave(player)
		t.eq(server.store():read(KEY .. 9).data.inventory.items.Spark, 8, "the stored Sparks are safe")
	end)

	t.test("shutting down saves everyone and releases their locks", function()
		local server = Fakes.server(ctx)
		local Save = startSave(server)
		local a = server.players.join(10)
		local b = server.players.join(11)
		settle()
		Save.get(a).inventory.items.Spark = 1
		Save.get(b).inventory.items.Spark = 2
		server.close()
		t.eq(server.store():read(KEY .. 10).data.inventory.items.Spark, 1, "first player saved")
		t.eq(server.store():read(KEY .. 11).data.inventory.items.Spark, 2, "second player saved")
		t.eq(server.store():read(KEY .. 11).lock, nil, "locks released")
	end)

	t.test("onLoaded runs once the save is in, and erase deletes it", function()
		local server = Fakes.server(ctx)
		local Save = startSave(server)
		local player = server.players.join(12)
		local seen = nil
		Save.onLoaded(player, function(profile)
			seen = profile
		end)
		settle()
		t.ok(seen ~= nil, "onLoaded didn't run")
		t.eq(seen, Save.get(player), "it gets the live profile")
		server.players.leave(player)
		t.ok(server.store():read(KEY .. 12) ~= nil, "saved on leaving")
		local ok = Save.erase(12)
		t.eq(ok, true, "erase worked")
		t.eq(server.store():read(KEY .. 12), nil, "the save is gone")
	end)
end
