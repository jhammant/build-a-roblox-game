-- Crafting: every CraftPoint (the Workbench) gets a "Make" prompt. Using it makes the first recipe you can afford,
-- or tells you what you still need. The server checks everything; the client only presses the prompt.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Items = require(Shared.Definitions.Items)
local Recipes = require(Shared.Definitions.Recipes)
local Craft = require(Shared.Craft)
local Remotes = require(Shared.Remotes)
local Bus = require(script.Parent.Parent.Bus)
local Inventory = require(script.Parent.Inventory)
local World = require(script.Parent.World)

local Crafting = {}

Crafting.TUNING = {
	RANGE = 10, -- studs: how close you must be to use a CraftPoint
	COOLDOWN = 0.5, -- seconds between uses, per player
}

local lastUse: { [Player]: number } = {}

local function notify(player: Player, text: string)
	Remotes.get("Notify"):FireClient(player, text)
end

local function primaryOf(point: Instance): BasePart?
	if point:IsA("BasePart") then
		return point
	elseif point:IsA("Model") then
		return point.PrimaryPart or point:FindFirstChildWhichIsA("BasePart")
	end
	return nil
end

-- Someone pressed Make at a CraftPoint
function Crafting.use(player: Player, point: Instance)
	local now = os.clock()
	if lastUse[player] and now - lastUse[player] < Crafting.TUNING.COOLDOWN then
		return
	end
	lastUse[player] = now
	local part = primaryOf(point)
	local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart") :: BasePart?
	if not part or not root or (root.Position - part.Position).Magnitude > Crafting.TUNING.RANGE + 4 then
		return
	end
	local station = point:GetAttribute("Station") or "Workbench"
	local items = Inventory.snapshot(player)
	local recipe, result = Craft.pick(items, Recipes.LIST, station, Items.BY_ID)
	if not recipe then
		notify(player, "You've made everything the " .. station .. " can make!")
		return
	end
	if not (result :: Craft.Result).ok then
		notify(player, Craft.explain(result :: Craft.Result, recipe, Items.BY_ID))
		return
	end
	local ok, reason = Inventory.craft(player, recipe)
	if ok then
		notify(player, "You made a " .. Items.get(recipe.output.item).name .. "!")
		Bus.fire("ItemCrafted", player, recipe.id, recipe.output.item)
	elseif reason then
		notify(player, reason)
	end
end

local function setUp(point: Instance)
	local part = primaryOf(point)
	if not part or part:FindFirstChild("CraftPrompt") then
		return
	end
	local prompt = Instance.new("ProximityPrompt")
	prompt.Name = "CraftPrompt"
	prompt.ActionText = "Make"
	prompt.ObjectText = point:GetAttribute("Station") or "Workbench"
	prompt.HoldDuration = 0
	prompt.RequiresLineOfSight = false
	prompt.MaxActivationDistance = Crafting.TUNING.RANGE
	prompt.Triggered:Connect(function(player)
		Crafting.use(player, point)
	end)
	prompt.Parent = part
end

function Crafting:Start()
	for _, point in CollectionService:GetTagged(World.TAGS.CraftPoint) do
		setUp(point)
	end
	CollectionService:GetInstanceAddedSignal(World.TAGS.CraftPoint):Connect(setUp)
	Players.PlayerRemoving:Connect(function(player)
		lastUse[player] = nil
	end)
end

return Crafting
