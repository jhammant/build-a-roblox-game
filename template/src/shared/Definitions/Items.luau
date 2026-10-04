-- Items: everything a player can carry. A round of picks changes the looks and numbers here, not the code.
local Palette = require(script.Parent.Palette)

local Items = {}

-- kind: "resource" (you collect and spend it) or "tool" (you keep it and use it)
-- maxStack: the most of this item one player can hold
-- look: how its placeholder model is built (see Shared/Models)
Items.LIST = {
	{
		id = "Spark",
		name = "Spark",
		plural = "Sparks",
		icon = "✨",
		kind = "resource",
		maxStack = 99,
		look = { size = 1.6, colour = Palette.Spark, glow = true },
	},
	{
		id = "Wand",
		name = "Magic Wand",
		plural = "Magic Wands",
		icon = "⭐",
		kind = "tool",
		maxStack = 1,
		look = { length = 2.6, thickness = 0.3, stick = Palette.WandStick, tip = Palette.WandTip, tipSize = 0.8 },
		-- power: cheer per zap · cooldown: seconds between zaps · range: studs from the player
		-- hitRadius: how close to a Gloomy a click must land to hit it
		zap = { power = 1, cooldown = 0.35, range = 60, hitRadius = 6 },
	},
}

Items.BY_ID = {}
for _, def in Items.LIST do
	Items.BY_ID[def.id] = def
end

function Items.get(id: string): any
	return Items.BY_ID[id]
end

return Items
