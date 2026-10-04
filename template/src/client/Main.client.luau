-- Main (client): starts every controller in order
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))

-- Add new controllers to this list (and to ARCHITECTURE.md)
local ORDER = {
	"Chat",
	"Effects",
	"Hud",
	"WandInput",
}

local controllers = script.Parent:WaitForChild("Controllers")

for _, name in ORDER do
	local module = controllers:FindFirstChild(name)
	if not module then
		warn("[Main] controller missing: " .. name)
		continue
	end
	local ok, controller = pcall(require, module)
	if not ok then
		warn("[Main] failed to load " .. name .. ": " .. tostring(controller))
		continue
	end
	if controller.Start then
		local started, err = xpcall(controller.Start, debug.traceback, controller)
		if not started then
			warn(string.format("[Main] %s:Start failed: %s", name, err))
		end
	end
end

print("[Main] client ready: " .. Config.GAME_NAME)
