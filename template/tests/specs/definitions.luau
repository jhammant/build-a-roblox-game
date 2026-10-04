-- definitions spec: the game's data fits together (recipes use real items, numbers make sense, places are on the map)
-- These are the checks that catch a typo after a round of picks changes Definitions.
local roblox = require("@lune/roblox")
local Vector3 = roblox.Vector3

local function isColour(value: any): boolean
	return typeof(value) == "Color3"
end

local function wholeAtLeast(value: any, min: number): boolean
	return type(value) == "number" and value == math.floor(value) and value >= min
end

local function inside(area: any, point: Vector3, ground: Vector3): boolean
	return math.abs(point.X) <= ground.X / 2
		and math.abs(point.Z) <= ground.Z / 2
		and (
			area == nil
			or (
				math.abs(point.X - area.centre.X) <= area.size.X / 2
				and math.abs(point.Z - area.centre.Z) <= area.size.Y / 2
			)
		)
end

return function(t, ctx)
	t.test("no decoration shares a colour with something you collect", function()
		local Palette = ctx.need("Definitions/Palette")
		for i, colour in Palette.Flowers do
			t.check(colour ~= Palette.Spark, "Palette.Flowers[" .. i .. "] is the same colour as a Spark")
		end
	end)

	t.test("every Palette entry is a colour", function()
		local Palette = ctx.need("Definitions/Palette")
		for name, value in Palette do
			if type(value) == "table" then
				for i, colour in value do
					t.check(isColour(colour), "Palette." .. name .. "[" .. i .. "] isn't a Color3")
				end
			else
				t.check(isColour(value), "Palette." .. name .. " isn't a Color3")
			end
		end
	end)

	t.test("items have unique ids, names, icons and sensible numbers", function()
		local Items = ctx.need("Definitions/Items")
		local seen = {}
		for i, def in Items.LIST do
			local where = "Items.LIST[" .. i .. "] (" .. tostring(def.id) .. ")"
			t.check(
				type(def.id) == "string" and string.match(def.id, "^%u%w*$") ~= nil,
				where .. ": id must be PascalCase"
			)
			t.check(not seen[def.id], where .. ": id used twice")
			seen[def.id] = true
			t.check(type(def.name) == "string" and def.name ~= "", where .. ": name missing")
			t.check(type(def.plural) == "string" and def.plural ~= "", where .. ": plural missing")
			t.check(type(def.icon) == "string" and def.icon ~= "", where .. ": icon missing")
			t.check(def.kind == "resource" or def.kind == "tool", where .. ": kind must be resource or tool")
			t.check(wholeAtLeast(def.maxStack, 1), where .. ": maxStack must be a whole number of at least 1")
			t.check(type(def.look) == "table", where .. ": look missing")
			t.check(Items.BY_ID[def.id] == def, where .. ": missing from BY_ID")
		end
	end)

	t.test("the wand has zap numbers and a look", function()
		local Items = ctx.need("Definitions/Items")
		local wand = Items.get("Wand")
		t.ok(wand ~= nil, "there's no Wand item")
		t.eq(wand.kind, "tool", "Wand kind")
		for _, key in { "power", "cooldown", "range", "hitRadius" } do
			t.check(type(wand.zap[key]) == "number" and wand.zap[key] > 0, "Wand.zap." .. key .. " must be above 0")
		end
		for _, key in { "stick", "tip" } do
			t.check(isColour(wand.look[key]), "Wand.look." .. key .. " must be a Color3")
		end
		t.check(isColour(Items.get("Spark").look.colour), "Spark.look.colour must be a Color3")
	end)

	t.test("recipes use real items and make something you can hold", function()
		local Items = ctx.need("Definitions/Items")
		local Recipes = ctx.need("Definitions/Recipes")
		local seen = {}
		for i, recipe in Recipes.LIST do
			local where = "Recipes.LIST[" .. i .. "] (" .. tostring(recipe.id) .. ")"
			t.check(not seen[recipe.id], where .. ": id used twice")
			seen[recipe.id] = true
			t.check(type(recipe.station) == "string" and recipe.station ~= "", where .. ": station missing")
			t.check(type(recipe.inputs) == "table" and #recipe.inputs > 0, where .. ": no inputs")
			for _, input in recipe.inputs or {} do
				t.check(Items.get(input.item) ~= nil, where .. ": input " .. tostring(input.item) .. " isn't an item")
				t.check(wholeAtLeast(input.count, 1), where .. ": input counts must be whole numbers of at least 1")
				local def = Items.get(input.item)
				if def then
					t.check(
						input.count <= def.maxStack,
						where .. ": needs more " .. input.item .. " than anyone can carry"
					)
				end
			end
			local output = Items.get(recipe.output.item)
			t.check(output ~= nil, where .. ": output " .. tostring(recipe.output.item) .. " isn't an item")
			t.check(wholeAtLeast(recipe.output.count, 1), where .. ": output count must be at least 1")
			if output then
				t.check(recipe.output.count <= output.maxStack, where .. ": makes more than anyone can carry")
			end
		end
	end)

	t.test("gloomies have looks, cheer and drops that exist", function()
		local Items = ctx.need("Definitions/Items")
		local Gloomies = ctx.need("Definitions/Gloomies")
		t.check(wholeAtLeast(Gloomies.TUNING.MAX, 1), "TUNING.MAX must be at least 1")
		t.check(Gloomies.TUNING.RESPAWN_SECONDS > 0, "TUNING.RESPAWN_SECONDS must be above 0")
		t.check(#Gloomies.LIST > 0, "no Gloomies")
		for i, def in Gloomies.LIST do
			local where = "Gloomies.LIST[" .. i .. "] (" .. tostring(def.id) .. ")"
			t.check(wholeAtLeast(def.cheer, 1), where .. ": cheer must be a whole number of at least 1")
			t.check(type(def.speed) == "number" and def.speed > 0, where .. ": speed must be above 0")
			t.check(type(def.weight) == "number" and def.weight > 0, where .. ": weight must be above 0")
			t.check(
				Items.get(def.drops.item) ~= nil,
				where .. ": drops " .. tostring(def.drops.item) .. " isn't an item"
			)
			t.check(wholeAtLeast(def.drops.count, 0), where .. ": drops.count must be a whole number")
			t.check(type(def.look.size) == "number" and def.look.size > 0, where .. ": look.size must be above 0")
			for _, key in { "colour", "cheeredColour", "eyes" } do
				t.check(isColour(def.look[key]), where .. ": look." .. key .. " must be a Color3")
			end
		end
	end)

	t.test("everything in the world is on the ground", function()
		local World = ctx.need("Definitions/World")
		local ground = World.GROUND.size
		t.check(inside(nil, World.SPAWN, ground), "SPAWN is off the ground")
		t.check(inside(nil, World.WORKBENCH.position, ground), "WORKBENCH is off the ground")
		for _, name in { "SPARK_AREA", "GLOOMY_AREA" } do
			local area = World[name]
			for _, corner in
				{ Vector3.new(-1, 0, -1), Vector3.new(1, 0, 1), Vector3.new(-1, 0, 1), Vector3.new(1, 0, -1) }
			do
				local point = area.centre + Vector3.new(corner.X * area.size.X / 2, 0, corner.Z * area.size.Y / 2)
				t.check(inside(nil, point, ground), name .. " runs off the ground")
			end
		end
		for i, position in World.FLOWERS do
			t.check(inside(nil, position, ground), "FLOWERS[" .. i .. "] is off the ground")
		end
		t.check(inside(World.SPARK_AREA, World.SPARK_AREA.centre, ground), "SPARK_AREA centre")
	end)

	t.test("you can always get what the first tool needs", function()
		-- Every recipe input must come from somewhere: the Spark area, or what Gloomies drop
		local Recipes = ctx.need("Definitions/Recipes")
		local World = ctx.need("Definitions/World")
		local Gloomies = ctx.need("Definitions/Gloomies")
		local sources = { [World.SPARK_AREA.item] = true }
		for _, def in Gloomies.LIST do
			sources[def.drops.item] = true
		end
		for _, recipe in Recipes.LIST do
			for _, input in recipe.inputs do
				t.check(
					sources[input.item],
					recipe.id .. " needs " .. input.item .. ", but nothing in the game gives it"
				)
			end
		end
	end)

	t.test("config has a name, folders and every hint", function()
		local Config = ctx.need("Config")
		t.check(type(Config.GAME_NAME) == "string" and Config.GAME_NAME ~= "", "GAME_NAME missing")
		t.check(type(Config.CHAT_ENABLED) == "boolean", "CHAT_ENABLED must be true or false")
		local seen = {}
		for _, name in Config.FOLDERS do
			t.check(not seen[name], "folder " .. name .. " listed twice")
			seen[name] = true
		end
		for _, key in { "collect", "craft", "zap", "zapTouch" } do
			t.check(type(Config.HINTS[key]) == "string" and Config.HINTS[key] ~= "", "HINTS." .. key .. " missing")
		end
		t.contains(Config.HINTS.collect, "{need}", "HINTS.collect")
	end)
end
