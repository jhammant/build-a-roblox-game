-- Wands: puts the wand in your hand once you've made one, and checks every zap (cooldown, range, what it hits).
-- The client only says where you aimed; this decides the rest.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Items = require(Shared.Definitions.Items)
local Models = require(Shared.Models)
local Remotes = require(Shared.Remotes)
local Zap = require(Shared.Zap)
local Bus = require(script.Parent.Parent.Bus)
local Inventory = require(script.Parent.Inventory)
local Gloomies = require(script.Parent.Gloomies)

local Wands = {}

Wands.ITEM = "Wand"

local lastZap: { [Player]: number } = {}

local function handOf(character: Model): BasePart?
	return (character:FindFirstChild("RightHand") or character:FindFirstChild("Right Arm")) :: BasePart?
end

-- Put a wand in their hand if they own one and aren't holding it yet
function Wands.equip(player: Player)
	local character = player.Character
	if not character or character:FindFirstChild("Wand") or Inventory.count(player, Wands.ITEM) < 1 then
		return
	end
	local hand = handOf(character)
	if not hand then
		return
	end
	local def = Items.get(Wands.ITEM)
	-- grip at the bottom of the hand; the wand points the way the hand faces (forwards)
	local grip = hand.CFrame * CFrame.new(0, -hand.Size.Y / 2, 0)
	local wand = Models.wand(def.look, grip)
	local weld = Instance.new("WeldConstraint")
	weld.Part0 = hand
	weld.Part1 = wand.PrimaryPart
	weld.Parent = wand.PrimaryPart
	wand.Parent = character
end

local function tipOf(character: Model, fallback: Vector3): Vector3
	local wand = character:FindFirstChild("Wand")
	local tip = wand and wand:FindFirstChild("Tip") :: BasePart?
	return if tip then tip.Position else fallback
end

local function onZap(player: Player, aim: any)
	local def = Items.get(Wands.ITEM)
	local stats = def.zap
	local now = os.clock()
	if not Zap.validAim(aim) or not Zap.ready(lastZap[player], now, stats.cooldown) then
		return
	end
	if Inventory.count(player, Wands.ITEM) < 1 then
		return
	end
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
	if not root then
		return
	end
	lastZap[player] = now
	local origin = root.Position
	local clamped = Zap.clampAim(origin, aim, stats.range)
	local target = Zap.pickTarget(origin, clamped, Gloomies.targets(), stats)
	local to = if target then target.position else clamped
	Remotes.get("Zapped"):FireAllClients(tipOf(character, origin), to, target ~= nil)
	if target then
		Gloomies.hit(target.id, player, stats.power)
	end
end

function Wands:Start()
	Remotes.get("Zap").OnServerEvent:Connect(onZap)
	Bus.on("ItemsChanged", function(player: Player)
		Wands.equip(player)
	end)
	local function onPlayer(player: Player)
		player.CharacterAppearanceLoaded:Connect(function()
			Wands.equip(player)
		end)
	end
	Players.PlayerAdded:Connect(onPlayer)
	for _, player in Players:GetPlayers() do
		onPlayer(player)
	end
	Players.PlayerRemoving:Connect(function(player)
		lastZap[player] = nil
	end)
end

return Wands
