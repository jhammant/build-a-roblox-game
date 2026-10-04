-- World: builds the garden (ground, path, spawn, Workbench, flowers) from Definitions/World.
-- Anything already in the place counts: a hand-built part tagged CraftPoint is used instead of a new Workbench,
-- and a Baseplate is used instead of new ground.
local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Layout = require(Shared.Definitions.World)
local Palette = require(Shared.Definitions.Palette)
local Models = require(Shared.Models)

local World = {}

World.TAGS = { CraftPoint = "CraftPoint" }

local function groundPart(name: string, size: Vector3, position: Vector3, colour: Color3, parent: Instance)
	local p = Instance.new("Part")
	p.Name = name
	p.Anchored = true
	p.Size = size
	p.Position = position
	p.Color = colour
	p.Material = Enum.Material.SmoothPlastic
	p.TopSurface = Enum.SurfaceType.Smooth
	p.Parent = parent
	return p
end

local function buildGround(folder: Instance)
	if workspace:FindFirstChild("Baseplate") then
		return
	end
	local size = Layout.GROUND.size
	groundPart("Ground", size, Vector3.new(0, -size.Y / 2, 0), Layout.GROUND.colour, folder)
	-- The path sits a hair above the ground so the two never flicker
	local path = Layout.PATH
	local length = (path.to - path.from).Magnitude
	local p = groundPart("Path", Vector3.new(path.width, 0.2, length), Vector3.zero, path.colour, folder)
	p.CanCollide = false
	p.CFrame = CFrame.lookAt((path.from + path.to) / 2, path.to) + Vector3.new(0, 0.1, 0)
end

local function buildSpawn(folder: Instance)
	if workspace:FindFirstChildWhichIsA("SpawnLocation", true) then
		return
	end
	local spawn = Instance.new("SpawnLocation")
	spawn.Name = "Spawn"
	spawn.Anchored = true
	spawn.Neutral = true
	spawn.Duration = 0 -- no force field: nothing in the garden can hurt you
	spawn.Size = Vector3.new(8, 0.4, 8)
	spawn.Position = Layout.SPAWN + Vector3.new(0, 0.2, 0)
	spawn.Color = Palette.Path
	spawn.Material = Enum.Material.SmoothPlastic
	spawn.TopSurface = Enum.SurfaceType.Smooth
	spawn.Parent = folder
end

local function buildWorkbench(folder: Instance)
	if #CollectionService:GetTagged(World.TAGS.CraftPoint) > 0 then
		return
	end
	local bench = Layout.WORKBENCH
	local model = Models.workbench(bench, CFrame.new(bench.position))
	model:SetAttribute("Station", bench.station)
	model.Parent = folder

	local sign = Instance.new("BillboardGui")
	sign.Name = "Sign"
	sign.Size = UDim2.fromOffset(200, 40)
	sign.StudsOffset = Vector3.new(0, 3, 0)
	sign.AlwaysOnTop = false
	sign.Adornee = model.PrimaryPart
	local label = Instance.new("TextLabel")
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundTransparency = 1
	label.Text = bench.station
	label.TextScaled = true
	label.Font = Enum.Font.FredokaOne
	label.TextColor3 = Palette.Paper
	label.TextStrokeColor3 = Palette.Ink
	label.TextStrokeTransparency = 0
	label.Parent = sign
	sign.Parent = model

	CollectionService:AddTag(model, World.TAGS.CraftPoint)
end

local function buildFlowers(folder: Instance)
	for i, position in Layout.FLOWERS do
		local colour = Palette.Flowers[(i - 1) % #Palette.Flowers + 1]
		Models.flower(colour, Palette.Stem, CFrame.new(position)).Parent = folder
	end
end

function World:Init()
	local folder = workspace:WaitForChild("World")
	buildGround(folder)
	buildSpawn(folder)
	buildWorkbench(folder)
	buildFlowers(folder)
end

-- A random point on the ground inside an area ({ centre, size }), using `rng`
function World.randomPointIn(area: any, rng: Random): Vector3
	local x = area.centre.X + (rng:NextNumber() - 0.5) * area.size.X
	local z = area.centre.Z + (rng:NextNumber() - 0.5) * area.size.Y
	return Vector3.new(x, area.centre.Y, z)
end

return World
