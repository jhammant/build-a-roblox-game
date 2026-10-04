-- Sparks: puts Sparks around the garden and drops them where Gloomies cheer up. Walk into one to collect it.
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Items = require(Shared.Definitions.Items)
local Layout = require(Shared.Definitions.World)
local Models = require(Shared.Models)
local Remotes = require(Shared.Remotes)
local Bus = require(script.Parent.Parent.Bus)
local Inventory = require(script.Parent.Inventory)
local World = require(script.Parent.World)

local Sparks = {}

Sparks.TUNING = {
	PICKUP_RANGE = 8, -- studs from the player's middle; anything further is a touch the server doesn't trust
	HOVER = 2, -- studs above the ground
	BOB = 0.6, -- studs up and down
	DROP_SCATTER = 3, -- dropped Sparks land this far apart
	DROP_LIFETIME = 45, -- seconds before an uncollected dropped Spark fades away
}
Sparks.TAG = "Spark"

local rng = Random.new()
local folder: Instance
local inArea = 0 -- Sparks spawned in the Spark area (dropped ones don't count)
local toldFull: { [Player]: boolean } = {}

local function collect(spark: Model, player: Player)
	if spark:GetAttribute("Taken") then
		return
	end
	local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart") :: BasePart?
	if not root or (root.Position - spark:GetPivot().Position).Magnitude > Sparks.TUNING.PICKUP_RANGE then
		return
	end
	local id = spark:GetAttribute("Item") or "Spark"
	if Inventory.add(player, id, 1) == 0 then
		if not toldFull[player] then
			toldFull[player] = true
			Remotes.get("Notify"):FireClient(player, "Your bag is full!")
		end
		return
	end
	spark:SetAttribute("Taken", true)
	Remotes.get("Collected"):FireClient(player, id, spark:GetPivot().Position)
	Bus.fire("SparkCollected", player, 1)
	if spark:GetAttribute("FromArea") then
		inArea -= 1
	end
	spark:Destroy()
end

-- Make one Spark at a ground point. fromArea = it counts towards the Spark area's limit.
function Sparks.spawnAt(ground: Vector3, itemId: string, fromArea: boolean): Model
	local def = Items.get(itemId)
	local at = CFrame.new(ground + Vector3.new(0, Sparks.TUNING.HOVER, 0))
	local spark = Models.spark(def.look, at)
	spark:SetAttribute("Item", itemId)
	spark:SetAttribute("FromArea", fromArea)
	local ball = spark.PrimaryPart :: BasePart
	ball.CanTouch = true
	ball.Touched:Connect(function(hit: BasePart)
		local player = Players:GetPlayerFromCharacter(hit.Parent)
		if player then
			collect(spark, player)
		end
	end)
	spark.Parent = folder
	CollectionService:AddTag(spark, Sparks.TAG)
	local bob = TweenInfo.new(1.2, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true)
	TweenService:Create(ball, bob, { CFrame = at + Vector3.new(0, Sparks.TUNING.BOB, 0) }):Play()
	if fromArea then
		inArea += 1
	end
	return spark
end

-- Scatter dropped items around a point (a cheered-up Gloomy's drops)
function Sparks.drop(position: Vector3, itemId: string, count: number)
	local ground = Vector3.new(position.X, 0, position.Z)
	for i = 1, count do
		local angle = (i / count) * math.pi * 2 + rng:NextNumber() * 0.6
		local offset = Vector3.new(math.cos(angle), 0, math.sin(angle)) * Sparks.TUNING.DROP_SCATTER
		local spark = Sparks.spawnAt(ground + offset, itemId, false)
		task.delay(Sparks.TUNING.DROP_LIFETIME, function()
			if spark.Parent then
				spark:Destroy()
			end
		end)
	end
end

function Sparks:Init()
	folder = workspace:WaitForChild("Sparks")
end

function Sparks:Start()
	local area = Layout.SPARK_AREA
	for _ = 1, area.max do
		Sparks.spawnAt(World.randomPointIn(area, rng), area.item, true)
	end
	task.spawn(function()
		while true do
			task.wait(area.respawnSeconds)
			if inArea < area.max then
				Sparks.spawnAt(World.randomPointIn(area, rng), area.item, true)
			end
		end
	end)
	Bus.on("GloomyCheered", function(_player: Player, position: Vector3, def: any)
		if def.drops and def.drops.count > 0 then
			Sparks.drop(position, def.drops.item, def.drops.count)
		end
	end)
	Bus.on("ItemsChanged", function(player: Player)
		toldFull[player] = nil
	end)
	Players.PlayerRemoving:Connect(function(player)
		toldFull[player] = nil
	end)
end

return Sparks
