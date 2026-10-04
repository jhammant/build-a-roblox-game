-- Gloomies: grumpy blobs that wander the garden. Zap one enough and it cheers up, floats away and drops Sparks;
-- a new one arrives a little later. They never hurt anyone.
local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Defs = require(Shared.Definitions.Gloomies)
local Layout = require(Shared.Definitions.World)
local Models = require(Shared.Models)
local Remotes = require(Shared.Remotes)
local Bus = require(script.Parent.Parent.Bus)
local Save = require(script.Parent.Save)
local World = require(script.Parent.World)

local Gloomies = {}

Gloomies.TAG = "Gloomy"

type Gloomy = {
	id: number,
	def: any,
	model: Model,
	position: Vector3, -- ground point under it
	target: Vector3,
	pauseUntil: number,
	cheer: number, -- zaps so far, counting up to def.cheer
	cheering: boolean,
	bobOffset: number,
}

local rng = Random.new()
local folder: Instance
local active: { [number]: Gloomy } = {}
local nextId = 0

local function pickDef(): any
	local total = 0
	for _, def in Defs.LIST do
		total += def.weight
	end
	local roll = rng:NextNumber() * total
	for _, def in Defs.LIST do
		roll -= def.weight
		if roll <= 0 then
			return def
		end
	end
	return Defs.LIST[#Defs.LIST]
end

local function bodyCFrame(g: Gloomy, facing: Vector3, t: number): CFrame
	local lift = g.def.look.size / 2 + math.abs(math.sin(t * 6 + g.bobOffset)) * 0.4
	local at = g.position + Vector3.new(0, lift, 0)
	if (facing - g.position).Magnitude < 0.01 then
		return CFrame.new(at)
	end
	return CFrame.lookAt(at, Vector3.new(facing.X, at.Y, facing.Z))
end

function Gloomies.spawnOne()
	nextId += 1
	local def = pickDef()
	local position = World.randomPointIn(Layout.GLOOMY_AREA, rng)
	local g: Gloomy = {
		id = nextId,
		def = def,
		model = nil :: any,
		position = position,
		target = World.randomPointIn(Layout.GLOOMY_AREA, rng),
		pauseUntil = 0,
		cheer = 0,
		cheering = false,
		bobOffset = rng:NextNumber() * math.pi,
	}
	g.model = Models.gloomy(def.look, bodyCFrame(g, g.target, 0))
	g.model:SetAttribute("GloomyId", g.id)
	g.model.Parent = folder
	CollectionService:AddTag(g.model, Gloomies.TAG)
	active[g.id] = g
end

-- Where every Gloomy that can still be zapped is: { { id, position } }
function Gloomies.targets(): { { id: number, position: Vector3 } }
	local out = {}
	for id, g in active do
		if not g.cheering then
			table.insert(out, { id = id, position = g.model:GetPivot().Position })
		end
	end
	return out
end

local function cheerUp(g: Gloomy, player: Player)
	g.cheering = true
	local position = g.model:GetPivot().Position
	for _, p in g.model:GetDescendants() do
		if p:IsA("BasePart") and p.Name == "Body" then
			p.Color = g.def.look.cheeredColour
		elseif p:IsA("BasePart") and p.Name == "Brow" then
			p:Destroy() -- no more frown
		end
	end
	Remotes.get("Cheered"):FireAllClients(position, g.def.look.cheeredColour)
	Bus.fire("GloomyCheered", player, position, g.def)

	local profile = Save.get(player)
	if Save.isLoaded(player) then
		profile.stats.cheered += 1
		Save.markDirty(player)
	end

	local rise = TweenInfo.new(Defs.TUNING.CHEER_SECONDS, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
	for _, p in g.model:GetDescendants() do
		if p:IsA("BasePart") then
			TweenService:Create(p, rise, {
				CFrame = p.CFrame + Vector3.new(0, Defs.TUNING.CHEER_RISE, 0),
				Transparency = 1,
			}):Play()
		end
	end
	task.delay(Defs.TUNING.CHEER_SECONDS, function()
		active[g.id] = nil
		g.model:Destroy()
	end)
	task.delay(Defs.TUNING.RESPAWN_SECONDS, Gloomies.spawnOne)
end

-- A zap landed on Gloomy `id`. Returns true if it cheered up.
function Gloomies.hit(id: number, player: Player, power: number): boolean
	local g = active[id]
	if not g or g.cheering then
		return false
	end
	g.cheer += power
	if g.cheer >= g.def.cheer then
		cheerUp(g, player)
		return true
	end
	return false
end

local function step(dt: number)
	local t = os.clock()
	for _, g in active do
		if g.cheering or not g.model.Parent then
			continue
		end
		if t >= g.pauseUntil then
			local offset = Vector3.new(g.target.X - g.position.X, 0, g.target.Z - g.position.Z)
			local stepLength = g.def.speed * dt
			if offset.Magnitude <= stepLength then
				g.position = g.target
				g.target = World.randomPointIn(Layout.GLOOMY_AREA, rng)
				local pause = Defs.TUNING.PAUSE_SECONDS
				g.pauseUntil = t + rng:NextNumber(pause[1], pause[2])
			else
				g.position += offset.Unit * stepLength
			end
		end
		g.model:PivotTo(bodyCFrame(g, g.target, t))
	end
end

function Gloomies:Init()
	folder = workspace:WaitForChild("Gloomies")
end

function Gloomies:Start()
	for _ = 1, Defs.TUNING.MAX do
		Gloomies.spawnOne()
	end
	RunService.Heartbeat:Connect(step)
end

return Gloomies
