-- Main (server): creates the remotes and workspace folders, then starts every system in order
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Remotes = require(Shared.Remotes)

-- Hold characters back until the world exists, so nobody spawns into an empty place
Players.CharacterAutoLoads = false

Remotes.setup()

for _, name in Config.FOLDERS do
	if not workspace:FindFirstChild(name) then
		local folder = Instance.new("Folder")
		folder.Name = name
		folder.Parent = workspace
	end
end

-- The start order. A system can use any system above it. World builds the ground first; Save comes before anything
-- that keeps progress. Add new systems to this list (and to ARCHITECTURE.md).
local ORDER = {
	"World",
	"Save",
	"Inventory",
	"Sparks",
	"Gloomies",
	"Crafting",
	"Wands",
}

local systems = {}
for _, name in ORDER do
	local module = script.Parent.Systems:FindFirstChild(name)
	if not module then
		warn("[Main] system missing: " .. name)
		continue
	end
	local ok, system = pcall(require, module)
	if ok then
		table.insert(systems, { name = name, system = system })
	else
		warn("[Main] failed to load " .. name .. ": " .. tostring(system))
	end
end

-- A broken system logs loudly but doesn't stop the rest of the game
local function run(phase: string)
	for _, entry in systems do
		local fn = entry.system[phase]
		if fn then
			local ok, err = xpcall(fn, debug.traceback, entry.system)
			if not ok then
				warn(string.format("[Main] %s:%s failed: %s", entry.name, phase, err))
			end
		end
	end
end

run("Init")
run("Start")

local function onCharacter(character: Model)
	local humanoid = character:WaitForChild("Humanoid") :: Humanoid
	humanoid.WalkSpeed = Config.WALK_SPEED
	humanoid.UseJumpPower = true
	humanoid.JumpPower = Config.JUMP_POWER
end

Players.PlayerAdded:Connect(function(player)
	player.CharacterAdded:Connect(onCharacter)
end)
Players.CharacterAutoLoads = true

-- Anyone who joined while the world was being built gets their character now
for _, player in Players:GetPlayers() do
	player.CharacterAdded:Connect(onCharacter)
	if not player.Character then
		task.spawn(player.LoadCharacter, player)
	end
end

print("[Main] server ready: " .. Config.GAME_NAME)
