-- models spec: every placeholder model builds from the real looks, with a PrimaryPart and a sensible part count
-- (Lune builds real Instances offline, so this catches a bad property name or a missing look field.)
local roblox = require("@lune/roblox")
local CFrame = roblox.CFrame

local PART_BUDGET = 40 -- placeholders should stay light; real models come later from the picks

local function countParts(model: any): number
	local n = 0
	for _, child in model:GetDescendants() do
		if child:IsA("BasePart") then
			n += 1
		end
	end
	return n
end

return function(t, ctx)
	local function build(label: string, fn: () -> any)
		t.test(label, function()
			local Models = ctx.need("Models")
			local ok, model = pcall(fn, Models)
			t.ok(ok, "building it errored: " .. tostring(model))
			t.eq(model.ClassName, "Model", "returns a Model")
			t.ok(model.PrimaryPart ~= nil, "has a PrimaryPart")
			local parts = countParts(model)
			t.check(parts >= 1 and parts <= PART_BUDGET, "has " .. parts .. " parts (budget " .. PART_BUDGET .. ")")
		end)
	end

	build("a Spark builds", function(Models)
		return Models.spark(ctx.need("Definitions/Items").get("Spark").look, CFrame.new(0, 2, 0))
	end)

	build("a Wand builds, with a tip to zap from", function(Models)
		local wand = Models.wand(ctx.need("Definitions/Items").get("Wand").look, CFrame.new())
		t.check(wand:FindFirstChild("Tip") ~= nil, "no Tip part")
		t.check(wand.PrimaryPart.Anchored == false, "a wand must be unanchored so it can be welded to a hand")
		return wand
	end)

	build("every kind of Gloomy builds", function(Models)
		local last
		for _, def in ctx.need("Definitions/Gloomies").LIST do
			last = Models.gloomy(def.look, CFrame.new(0, def.look.size / 2, 0))
			t.check(last.PrimaryPart.Name == "Body", def.id .. ": the PrimaryPart should be the Body")
		end
		return last
	end)

	build("the Workbench builds", function(Models)
		return Models.workbench(ctx.need("Definitions/World").WORKBENCH, CFrame.new())
	end)

	build("a flower builds", function(Models)
		local Palette = ctx.need("Definitions/Palette")
		return Models.flower(Palette.Flowers[1], Palette.Stem, CFrame.new())
	end)
end
