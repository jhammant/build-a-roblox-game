-- Remotes: every RemoteEvent and RemoteFunction in the game, by name. The server creates them; clients wait for them.
-- Payloads are listed here and in ARCHITECTURE.md. Add new names here rather than creating remotes anywhere else.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Remotes = {}

Remotes.EVENTS = {
	-- server -> client
	"InventoryChanged", -- (items: { [itemId]: count }) to one player, whenever their items change
	"Notify", -- (text: string) to one player: a short message on screen
	"Collected", -- (itemId: string, position: Vector3) to the collector: a sparkle where they picked it up
	"Zapped", -- (from: Vector3, to: Vector3, hit: boolean) to everyone: draw the zap
	"Cheered", -- (position: Vector3, colour: Color3) to everyone: a Gloomy cheered up
	-- client -> server
	"Zap", -- (aim: Vector3) where the player clicked or tapped; the server decides what it hits
}

Remotes.FUNCTIONS = {
	"GetInventory", -- () -> { [itemId]: count }
}

local FOLDER_NAME = "Remotes"

-- Server only: create the folder and every remote. Main.server calls this once, before any system loads.
function Remotes.setup()
	assert(RunService:IsServer(), "Remotes.setup is server-only")
	local folder = ReplicatedStorage:FindFirstChild(FOLDER_NAME) or Instance.new("Folder")
	folder.Name = FOLDER_NAME
	for _, name in Remotes.EVENTS do
		if not folder:FindFirstChild(name) then
			local remote = Instance.new("RemoteEvent")
			remote.Name = name
			remote.Parent = folder
		end
	end
	for _, name in Remotes.FUNCTIONS do
		if not folder:FindFirstChild(name) then
			local remote = Instance.new("RemoteFunction")
			remote.Name = name
			remote.Parent = folder
		end
	end
	folder.Parent = ReplicatedStorage
end

-- Both sides: a remote by name (clients wait for the server to create it)
function Remotes.get(name: string): any
	assert(table.find(Remotes.EVENTS, name) or table.find(Remotes.FUNCTIONS, name), "Unknown remote: " .. name)
	return ReplicatedStorage:WaitForChild(FOLDER_NAME):WaitForChild(name)
end

return Remotes
