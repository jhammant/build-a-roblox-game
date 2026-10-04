-- inventory spec: the real Inventory system with the real Save on a pretend server
local task = require("@lune/task")

local Fakes = require("../lib/fakes")

local function newServer(ctx: any): any
	local server = Fakes.server(ctx, { overrides = { Remotes = "tests/fixtures/Remotes.luau" } })
	local Save = server.loader:requireServer("Systems/Save")
	Save.TUNING.AUTOSAVE_SECONDS = 0
	Save.TUNING.RETRY_WAIT = 0
	local Inventory = server.loader:requireServer("Systems/Inventory")
	Save:Init()
	Save:Start()
	Inventory:Start()
	server.Save = Save
	server.Inventory = Inventory
	server.Remotes = server.loader:require("Remotes")
	return server
end

local function settle()
	for _ = 1, 20 do
		task.wait()
	end
end

return function(t, ctx)
	t.test("adding items saves them and tells the player's screen", function()
		local server = newServer(ctx)
		local player = server.players.join(1)
		settle()
		t.eq(server.Inventory.add(player, "Spark", 2), 2, "added")
		local sent = server.Remotes.last("InventoryChanged")
		t.ok(sent ~= nil, "InventoryChanged wasn't sent")
		t.eq(sent.player, player, "sent to the right player")
		t.eq(sent.args[1].Spark, 2, "with the new count")
		server.players.leave(player)
		t.eq(server.store():read("Player_1").data.inventory.items.Spark, 2, "saved")
	end)

	t.test("a tool stops at one, and unknown items are refused", function()
		local server = newServer(ctx)
		local player = server.players.join(2)
		settle()
		t.eq(server.Inventory.add(player, "Wand", 3), 1, "only one wand")
		t.eq(server.Inventory.add(player, "Banana", 1), 0, "no such item")
	end)

	t.test("crafting a wand uses the Sparks", function()
		local server = newServer(ctx)
		local player = server.players.join(3)
		settle()
		local Recipes = server.loader:require("Definitions/Recipes")
		local ok, reason = server.Inventory.craft(player, Recipes.BY_ID.MagicWand)
		t.eq(ok, false, "can't craft with nothing")
		t.contains(reason, "You need")
		server.Inventory.add(player, "Spark", 4)
		ok = server.Inventory.craft(player, Recipes.BY_ID.MagicWand)
		t.eq(ok, true, "crafted")
		t.eq(server.Inventory.count(player, "Spark"), 1, "Sparks left")
		t.eq(server.Inventory.count(player, "Wand"), 1, "has a wand")
	end)

	t.test("nothing changes before the save has loaded", function()
		local server = Fakes.server(ctx, { overrides = { Remotes = "tests/fixtures/Remotes.luau" } })
		local Save = server.loader:requireServer("Systems/Save")
		Save.TUNING.AUTOSAVE_SECONDS = 0
		local Inventory = server.loader:requireServer("Systems/Inventory")
		-- Save isn't started, so no save ever loads for this player
		local player = server.players.join(4)
		t.eq(Inventory.add(player, "Spark", 1), 0, "refused while loading")
		t.eq(Inventory.take(player, "Spark", 1), false, "take refused while loading")
	end)
end
