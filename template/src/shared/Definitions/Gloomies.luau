-- Gloomies: the grumpy things you zap. Zap one enough and it cheers up, floats away and drops Sparks.
-- They never hurt anyone. A round of picks changes their looks and numbers here.
local Palette = require(script.Parent.Palette)

local Gloomies = {}

Gloomies.TUNING = {
	MAX = 4, -- how many wander the garden at once
	RESPAWN_SECONDS = 6, -- after one cheers up, a new one arrives this long later
	PAUSE_SECONDS = { 0.5, 2 }, -- they stop for a moment between walks
	CHEER_RISE = 10, -- studs a cheered-up Gloomy floats up before it vanishes
	CHEER_SECONDS = 1.4,
}

-- cheer: zaps needed (each zap adds the wand's power) · speed: studs per second
-- drops: what it leaves behind · weight: how often this kind appears, compared with the others
Gloomies.LIST = {
	{
		id = "Grumpy",
		name = "Gloomy",
		cheer = 3,
		speed = 5,
		weight = 1,
		drops = { item = "Spark", count = 2 },
		look = { size = 4, colour = Palette.Gloomy, cheeredColour = Palette.GloomyCheered, eyes = Palette.Ink },
	},
}

Gloomies.BY_ID = {}
for _, def in Gloomies.LIST do
	Gloomies.BY_ID[def.id] = def
end

return Gloomies
