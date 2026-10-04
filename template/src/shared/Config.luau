-- Config: game-wide settings. Each system's own numbers live in its Definitions module instead
local Config = {}

Config.GAME_NAME = "Spark Garden"
Config.DEBUG = false -- true prints extra logs from systems

-- Player
Config.WALK_SPEED = 18 -- a little faster than Roblox's 16, so exploring feels zippy
Config.JUMP_POWER = 50

-- Roblox's own text chat. Off by default: nothing in the game needs it, and it's one less way for strangers to talk
-- to children. Turn it on only once you've thought about who will play.
Config.CHAT_ENABLED = false

-- Workspace folders created by Main.server, each owned by one system
Config.FOLDERS = { "World", "Sparks", "Gloomies", "Effects" }

-- The hint line at the top of the screen. {need} becomes the number of Sparks still needed for a Wand.
Config.HINTS = {
	collect = "Collect Sparks! You need {need} more for a Wand.",
	craft = "You have enough Sparks. Take them to the Workbench!",
	zap = "Click a Gloomy to zap it and cheer it up!",
	zapTouch = "Walk up to a Gloomy and tap ZAP!",
}

return Config
