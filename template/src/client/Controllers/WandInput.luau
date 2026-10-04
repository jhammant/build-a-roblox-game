-- WandInput: click (or tap the world) to zap where you aim. On touch screens there's also a big ZAP button that aims
-- at the nearest Gloomy. This only tells the server where you aimed; the server decides what happens.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Items = require(Shared.Definitions.Items)
local Palette = require(Shared.Definitions.Palette)
local Bag = require(Shared.Bag)
local Remotes = require(Shared.Remotes)
local Zap = require(Shared.Zap)

local WandInput = {}

local WAND = "Wand"
local GLOOMY_TAG = "Gloomy"
local BUTTON_SIZE = 110 -- pixels: big enough for small thumbs

local player = Players.LocalPlayer
local hasWand = false
local lastZap: number? = nil
local button: TextButton

local function root(): BasePart?
	local character = player.Character
	return character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
end

local function send(aim: Vector3)
	local stats = Items.get(WAND).zap
	local now = os.clock()
	if not hasWand or not Zap.ready(lastZap, now, stats.cooldown) then
		return
	end
	lastZap = now
	Remotes.get("Zap"):FireServer(aim)
end

-- Where a screen point lands in the world (ignoring your own character)
local function worldPoint(screen: Vector2): Vector3?
	local camera = workspace.CurrentCamera
	if not camera then
		return nil
	end
	local ray = camera:ViewportPointToRay(screen.X, screen.Y)
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = { player.Character }
	local range = Items.get(WAND).zap.range * 3
	local result = workspace:Raycast(ray.Origin, ray.Direction * range, params)
	return if result then result.Position else ray.Origin + ray.Direction * range
end

local function zapNearest()
	local me = root()
	if not me then
		return
	end
	local targets = {}
	for _, gloomy in CollectionService:GetTagged(GLOOMY_TAG) do
		if gloomy:IsA("Model") and gloomy.PrimaryPart then
			table.insert(targets, { id = gloomy, position = gloomy.PrimaryPart.Position })
		end
	end
	local target = Zap.nearest(me.Position, targets, Items.get(WAND).zap.range)
	send(if target then target.position else me.Position + me.CFrame.LookVector * 20)
end

local function makeButton()
	local gui = Instance.new("ScreenGui")
	gui.Name = "ZapButton"
	gui.ResetOnSpawn = false
	button = Instance.new("TextButton")
	button.Name = "Zap"
	button.Text = "ZAP!"
	button.Font = Enum.Font.FredokaOne
	button.TextScaled = true
	button.TextColor3 = Palette.Ink
	button.BackgroundColor3 = Palette.Spark
	button.AnchorPoint = Vector2.new(1, 1)
	-- left of Roblox's own jump button, bottom right
	button.Position = UDim2.new(1, -BUTTON_SIZE - 60, 1, -40)
	button.Size = UDim2.fromOffset(BUTTON_SIZE, BUTTON_SIZE)
	button.Visible = false
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0.5, 0)
	corner.Parent = button
	local stroke = Instance.new("UIStroke")
	stroke.Thickness = 4
	stroke.Color = Palette.Ink
	stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	stroke.Parent = button
	button.Activated:Connect(zapNearest)
	button.Parent = gui
	gui.Parent = player:WaitForChild("PlayerGui")
end

local function setItems(snapshot: Bag.Items)
	hasWand = Bag.count(snapshot, WAND) > 0
	button.Visible = hasWand and UserInputService.TouchEnabled
end

function WandInput:Start()
	makeButton()
	Remotes.get("InventoryChanged").OnClientEvent:Connect(setItems)
	task.spawn(function()
		local ok, snapshot = pcall(function()
			return Remotes.get("GetInventory"):InvokeServer()
		end)
		if ok and type(snapshot) == "table" then
			setItems(snapshot)
		end
	end)
	UserInputService.InputBegan:Connect(function(input: InputObject, processed: boolean)
		if processed or input.UserInputType ~= Enum.UserInputType.MouseButton1 then
			return
		end
		local aim = worldPoint(Vector2.new(input.Position.X, input.Position.Y))
		if aim then
			send(aim)
		end
	end)
	UserInputService.TouchTapInWorld:Connect(function(position: Vector2, processed: boolean)
		if processed then
			return
		end
		local aim = worldPoint(position)
		if aim then
			send(aim)
		end
	end)
end

return WandInput
