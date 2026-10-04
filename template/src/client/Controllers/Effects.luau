-- Effects: the sparkles, zaps, cheering bursts and the celebration when you make something. Only looks:
-- nothing here changes the game.
local Debris = game:GetService("Debris")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Palette = require(Shared.Definitions.Palette)
local Recipes = require(Shared.Definitions.Recipes)
local Remotes = require(Shared.Remotes)

local Effects = {}

-- Roblox's built-in sparkle texture: no upload or asset permission needed
local SPARKLE = "rbxasset://textures/particles/sparkles_main.dds"

local folder: Instance

-- A burst of particles at a point, cleaned up after a couple of seconds
function Effects.burst(position: Vector3, colours: { Color3 }, count: number, speed: number)
	local anchor = Instance.new("Part")
	anchor.Anchored = true
	anchor.CanCollide = false
	anchor.CanQuery = false
	anchor.CanTouch = false
	anchor.Transparency = 1
	anchor.Size = Vector3.one
	anchor.Position = position
	anchor.Parent = folder
	local keypoints = {}
	for i, colour in colours do
		table.insert(keypoints, ColorSequenceKeypoint.new((i - 1) / math.max(1, #colours - 1), colour))
	end
	if #keypoints == 1 then
		table.insert(keypoints, ColorSequenceKeypoint.new(1, colours[1]))
	end
	local emitter = Instance.new("ParticleEmitter")
	emitter.Texture = SPARKLE
	emitter.Color = ColorSequence.new(keypoints)
	emitter.Size = NumberSequence.new(0.8, 0)
	emitter.Lifetime = NumberRange.new(0.6, 1.2)
	emitter.Speed = NumberRange.new(speed * 0.5, speed)
	emitter.SpreadAngle = Vector2.new(180, 180)
	emitter.LightEmission = 0.6
	emitter.Rate = 0
	emitter.Parent = anchor
	emitter:Emit(count)
	Debris:AddItem(anchor, 2)
end

-- A bright line from the wand to where the zap landed, fading out
function Effects.zap(from: Vector3, to: Vector3, hit: boolean)
	local length = (to - from).Magnitude
	if length < 0.1 then
		return
	end
	local beam = Instance.new("Part")
	beam.Anchored = true
	beam.CanCollide = false
	beam.CanQuery = false
	beam.CanTouch = false
	beam.Material = Enum.Material.Neon
	beam.Color = Palette.Zap
	beam.Size = Vector3.new(0.25, 0.25, length)
	beam.CFrame = CFrame.lookAt((from + to) / 2, to)
	beam.Parent = folder
	TweenService:Create(beam, TweenInfo.new(0.25), { Transparency = 1, Size = Vector3.new(0.05, 0.05, length) }):Play()
	Debris:AddItem(beam, 0.3)
	if hit then
		Effects.burst(to, { Palette.Zap, Palette.Spark }, 12, 8)
	end
end

function Effects:Start()
	folder = workspace:WaitForChild("Effects")
	Remotes.get("Collected").OnClientEvent:Connect(function(_itemId: string, position: Vector3)
		Effects.burst(position, { Palette.Spark }, 16, 6)
	end)
	Remotes.get("Zapped").OnClientEvent:Connect(Effects.zap)
	Remotes.get("Cheered").OnClientEvent:Connect(function(position: Vector3, colour: Color3)
		Effects.burst(position, { colour, Palette.Spark, Palette.Accent }, 40, 14)
	end)

	-- Making something is a big moment, so celebrate when anything a recipe makes goes up
	local made = {}
	for _, recipe in Recipes.LIST do
		made[recipe.output.item] = true
	end
	local before: { [string]: number }? = nil
	Remotes.get("InventoryChanged").OnClientEvent:Connect(function(items: { [string]: number })
		if before then
			for itemId in made do
				if (items[itemId] or 0) > (before[itemId] or 0) then
					local root = Players.LocalPlayer.Character
						and Players.LocalPlayer.Character:FindFirstChild("HumanoidRootPart") :: BasePart?
					if root then
						Effects.burst(
							root.Position + Vector3.new(0, 2, 0),
							{ Palette.WandTip, Palette.WandStick, Palette.Accent },
							50,
							16
						)
					end
				end
			end
		end
		before = table.clone(items)
	end)
end

return Effects
