-- Chat: applies Config.CHAT_ENABLED to Roblox's text chat. The place starts with chat off (default.project.json sets
-- TextChatService's windows to disabled), because nothing in the game needs chat, and turning it off removes a way for
-- strangers to talk to children on public servers. Set CHAT_ENABLED to true to switch it back on for everyone.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TextChatService = game:GetService("TextChatService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))

local Chat = {}

local PARTS = { "ChatWindowConfiguration", "ChatInputBarConfiguration", "BubbleChatConfiguration" }

function Chat:Start()
	local enabled = Config.CHAT_ENABLED == true
	-- These can arrive a moment after the game starts, so wait for them without holding up the other controllers
	for _, name in PARTS do
		task.spawn(function()
			local part = TextChatService:FindFirstChild(name) or TextChatService:WaitForChild(name, 10)
			if part then
				(part :: any).Enabled = enabled
			end
		end)
	end
end

return Chat
