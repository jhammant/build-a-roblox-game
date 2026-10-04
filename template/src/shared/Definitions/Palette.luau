-- Palette: every colour in the game, by name. Picks change these values; models and UI read them from here.
local Palette = {}

-- Outlines and text
Palette.Ink = Color3.fromRGB(43, 27, 74)
Palette.Paper = Color3.fromRGB(255, 246, 224)

-- The garden
Palette.Grass = Color3.fromRGB(63, 194, 94)
Palette.Path = Color3.fromRGB(244, 214, 160)
Palette.Wood = Color3.fromRGB(176, 116, 64)
Palette.WoodDark = Color3.fromRGB(122, 78, 44)
Palette.Stem = Color3.fromRGB(46, 158, 74)
-- Never the Spark yellow: anything you can collect has to stand out from the decoration
Palette.Flowers = {
	Color3.fromRGB(255, 111, 181),
	Color3.fromRGB(51, 181, 255),
	Color3.fromRGB(255, 77, 94),
	Color3.fromRGB(168, 119, 255),
}

-- Things you collect, make and zap
Palette.Spark = Color3.fromRGB(255, 212, 71)
Palette.WandStick = Color3.fromRGB(255, 111, 181)
Palette.WandTip = Color3.fromRGB(255, 212, 71)
Palette.Gloomy = Color3.fromRGB(150, 140, 175)
Palette.GloomyCheered = Color3.fromRGB(255, 159, 28)
Palette.Zap = Color3.fromRGB(255, 240, 150)

-- Screen
Palette.Panel = Color3.fromRGB(255, 255, 255)
Palette.Accent = Color3.fromRGB(255, 79, 163)

return Palette
