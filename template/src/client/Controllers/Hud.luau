-- Hud: the Sparks counter, the wand badge, the hint line at the top, and short messages from the server
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Items = require(Shared.Definitions.Items)
local Palette = require(Shared.Definitions.Palette)
local Recipes = require(Shared.Definitions.Recipes)
local Bag = require(Shared.Bag)
local Remotes = require(Shared.Remotes)

local Hud = {}

local FONT = Enum.Font.FredokaOne
local SPARK = "Spark"
local WAND = "Wand"

local items: Bag.Items = {}
local gui: ScreenGui
local counter: TextLabel
local badge: TextLabel
local hint: TextLabel
local toast: TextLabel
local toastToken = 0

local function label(props: { [string]: any }): TextLabel
	local l = Instance.new("TextLabel")
	l.BackgroundColor3 = Palette.Panel
	l.TextColor3 = Palette.Ink
	l.Font = FONT
	l.TextScaled = true
	for key, value in props do
		(l :: any)[key] = value
	end
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, 12)
	corner.Parent = l
	local stroke = Instance.new("UIStroke")
	stroke.Thickness = 3
	stroke.Color = Palette.Ink
	stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	stroke.Parent = l
	local pad = Instance.new("UIPadding")
	pad.PaddingLeft = UDim.new(0, 10)
	pad.PaddingRight = UDim.new(0, 10)
	pad.PaddingTop = UDim.new(0, 4)
	pad.PaddingBottom = UDim.new(0, 4)
	pad.Parent = l
	l.Parent = gui
	return l
end

-- How many Sparks the Wand recipe needs (so the hint follows the recipe, whatever the picks make it)
local function sparksNeeded(): number
	for _, recipe in Recipes.LIST do
		if recipe.output.item == WAND then
			for _, input in recipe.inputs do
				if input.item == SPARK then
					return input.count
				end
			end
		end
	end
	return 0
end

local function render()
	local spark = Items.get(SPARK)
	counter.Text = spark.icon .. " " .. Bag.count(items, SPARK)
	local hasWand = Bag.count(items, WAND) > 0
	badge.Visible = hasWand
	badge.Text = Items.get(WAND).icon .. " " .. Items.get(WAND).name
	local need = sparksNeeded() - Bag.count(items, SPARK)
	if hasWand then
		hint.Text = if UserInputService.TouchEnabled then Config.HINTS.zapTouch else Config.HINTS.zap
	elseif need > 0 then
		hint.Text = (string.gsub(Config.HINTS.collect, "{need}", tostring(need)))
	else
		hint.Text = Config.HINTS.craft
	end
end

-- Show a short message for a few seconds
function Hud.toast(text: string)
	toastToken += 1
	local token = toastToken
	toast.Text = text
	toast.Visible = true
	toast.TextTransparency = 0
	task.delay(3, function()
		if token == toastToken then
			TweenService:Create(toast, TweenInfo.new(0.4), { TextTransparency = 1 }):Play()
			task.delay(0.4, function()
				if token == toastToken then
					toast.Visible = false
				end
			end)
		end
	end)
end

function Hud:Start()
	gui = Instance.new("ScreenGui")
	gui.Name = "Hud"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = false
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling

	counter = label({
		Name = "Sparks",
		Size = UDim2.fromOffset(120, 48),
		Position = UDim2.fromOffset(12, 12),
	})
	badge = label({
		Name = "Wand",
		Size = UDim2.fromOffset(180, 40),
		Position = UDim2.fromOffset(12, 68),
		Visible = false,
	})
	hint = label({
		Name = "Hint",
		AnchorPoint = Vector2.new(0.5, 0),
		Size = UDim2.new(0.6, 0, 0, 44),
		Position = UDim2.new(0.5, 0, 0, 12),
		BackgroundColor3 = Palette.Paper,
	})
	local limit = Instance.new("UISizeConstraint")
	limit.MaxSize = Vector2.new(560, 44)
	limit.Parent = hint
	toast = label({
		Name = "Toast",
		AnchorPoint = Vector2.new(0.5, 1),
		Size = UDim2.new(0.6, 0, 0, 44),
		Position = UDim2.new(0.5, 0, 1, -120),
		BackgroundTransparency = 1,
		TextColor3 = Palette.Paper,
		TextStrokeColor3 = Palette.Ink,
		TextStrokeTransparency = 0,
		Visible = false,
	})
	toast:FindFirstChildOfClass("UIStroke"):Destroy()

	gui.Parent = Players.LocalPlayer:WaitForChild("PlayerGui")
	render()

	Remotes.get("InventoryChanged").OnClientEvent:Connect(function(snapshot: Bag.Items)
		items = snapshot
		render()
	end)
	Remotes.get("Notify").OnClientEvent:Connect(Hud.toast)
	task.spawn(function()
		local ok, snapshot = pcall(function()
			return Remotes.get("GetInventory"):InvokeServer()
		end)
		if ok and type(snapshot) == "table" then
			items = snapshot
			render()
		end
	end)
end

return Hud
