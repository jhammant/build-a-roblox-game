-- World: where everything goes. The ground's top is at y = 0; areas are rectangles on the ground (size X by Z).
local Palette = require(script.Parent.Palette)

local World = {}

World.GROUND = { size = Vector3.new(180, 4, 180), colour = Palette.Grass }

World.SPAWN = Vector3.new(0, 0, 40)

World.WORKBENCH = {
	position = Vector3.new(0, 0, 16),
	station = "Workbench",
	top = Palette.Wood,
	legs = Palette.WoodDark,
}

-- Sparks appear here, up to `max` at once, one every `respawnSeconds`
World.SPARK_AREA = {
	item = "Spark",
	centre = Vector3.new(-34, 0, 4),
	size = Vector2.new(50, 56),
	max = 10,
	respawnSeconds = 4,
}

-- Gloomies wander in here
World.GLOOMY_AREA = {
	centre = Vector3.new(34, 0, -14),
	size = Vector2.new(56, 56),
}

-- A path from the spawn to the Workbench, and some flowers to make it look like a garden
World.PATH = { from = Vector3.new(0, 0, 40), to = Vector3.new(0, 0, 16), width = 6, colour = Palette.Path }

World.FLOWERS = {
	Vector3.new(-8, 0, 30),
	Vector3.new(8, 0, 28),
	Vector3.new(-12, 0, 20),
	Vector3.new(12, 0, 22),
	Vector3.new(-6, 0, 48),
	Vector3.new(7, 0, 50),
	Vector3.new(-60, 0, 40),
	Vector3.new(60, 0, 40),
	Vector3.new(-60, 0, -50),
	Vector3.new(0, 0, -60),
}

return World
