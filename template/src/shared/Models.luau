-- Models: builds the placeholder models from Definitions looks, out of plain Roblox parts. When the picks say what
-- something looks like, change its look data first; only change a builder here when the shape itself changes.
-- Every builder takes a CFrame to build at and returns the new Model (not parented), with a PrimaryPart.
local Models = {}

local function part(props: { [string]: any }): BasePart
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.Material = Enum.Material.SmoothPlastic
	for key, value in props do
		(p :: any)[key] = value
	end
	return p
end

local function model(name: string, parts: { BasePart }, primary: BasePart): Model
	local m = Instance.new("Model")
	m.Name = name
	for _, p in parts do
		p.Parent = m
	end
	m.PrimaryPart = primary
	return m
end

-- A Spark: a glowing ball. `at` is its centre.
function Models.spark(look: any, at: CFrame): Model
	local ball = part({
		Name = "Ball",
		Shape = Enum.PartType.Ball,
		Size = Vector3.one * look.size,
		Color = look.colour,
		Material = if look.glow then Enum.Material.Neon else Enum.Material.SmoothPlastic,
		CFrame = at,
	})
	if look.glow then
		local light = Instance.new("PointLight")
		light.Color = look.colour
		light.Range = 8
		light.Brightness = 1
		light.Parent = ball
	end
	return model("Spark", { ball }, ball)
end

-- A wand: a stick with a ball on the end. `at` is the grip (bottom of the stick), pointing along its -Z axis.
-- Parts are unanchored and welded to the stick, so it can be welded into a hand.
function Models.wand(look: any, at: CFrame): Model
	local stick = part({
		Name = "Stick",
		Shape = Enum.PartType.Cylinder,
		Size = Vector3.new(look.length, look.thickness, look.thickness),
		Color = look.stick,
		-- a Cylinder's length runs along its X axis; turn it to run along -Z
		CFrame = at * CFrame.new(0, 0, -look.length / 2) * CFrame.Angles(0, math.rad(90), 0),
	})
	local tip = part({
		Name = "Tip",
		Shape = Enum.PartType.Ball,
		Size = Vector3.one * look.tipSize,
		Color = look.tip,
		Material = Enum.Material.Neon,
		CFrame = at * CFrame.new(0, 0, -look.length),
	})
	local tipAttachment = Instance.new("Attachment")
	tipAttachment.Name = "TipAttachment"
	tipAttachment.Parent = tip
	for _, p in { stick, tip } do
		p.Anchored = false
		p.Massless = true
	end
	local weld = Instance.new("WeldConstraint")
	weld.Part0 = stick
	weld.Part1 = tip
	weld.Parent = stick
	return model("Wand", { stick, tip }, stick)
end

-- A Gloomy: a round body with two small eyes and a frowning brow. `at` is the centre of its body.
function Models.gloomy(look: any, at: CFrame): Model
	local size = look.size
	local body = part({
		Name = "Body",
		Shape = Enum.PartType.Ball,
		Size = Vector3.one * size,
		Color = look.colour,
		CFrame = at,
	})
	local parts = { body }
	for _, side in { -1, 1 } do
		table.insert(
			parts,
			part({
				Name = "Eye",
				Shape = Enum.PartType.Ball,
				Size = Vector3.one * size * 0.14,
				Color = look.eyes,
				CFrame = at * CFrame.new(side * size * 0.16, size * 0.1, -size * 0.45),
			})
		)
		table.insert(
			parts,
			part({
				Name = "Brow",
				Size = Vector3.new(size * 0.22, size * 0.05, size * 0.05),
				Color = look.eyes,
				CFrame = at
					* CFrame.new(side * size * 0.16, size * 0.22, -size * 0.44)
					* CFrame.Angles(0, 0, math.rad(side * 18)),
			})
		)
	end
	return model("Gloomy", parts, body)
end

-- A workbench: a wooden top on four legs. `at` is the ground point under its centre.
function Models.workbench(look: any, at: CFrame): Model
	local top = part({
		Name = "Top",
		Size = Vector3.new(8, 0.8, 4),
		Color = look.top,
		CanCollide = true,
		CFrame = at * CFrame.new(0, 3.4, 0),
	})
	local parts = { top }
	for _, x in { -3.4, 3.4 } do
		for _, z in { -1.4, 1.4 } do
			table.insert(
				parts,
				part({
					Name = "Leg",
					Size = Vector3.new(0.6, 3, 0.6),
					Color = look.legs,
					CanCollide = true,
					CFrame = at * CFrame.new(x, 1.5, z),
				})
			)
		end
	end
	return model("Workbench", parts, top)
end

-- A flower: a stem and a round head. `at` is the ground point it grows from.
function Models.flower(colour: Color3, stem: Color3, at: CFrame): Model
	local stalk = part({
		Name = "Stem",
		Size = Vector3.new(0.3, 2, 0.3),
		Color = stem,
		CFrame = at * CFrame.new(0, 1, 0),
	})
	local head = part({
		Name = "Head",
		Shape = Enum.PartType.Ball,
		Size = Vector3.one * 1.4,
		Color = colour,
		CFrame = at * CFrame.new(0, 2.3, 0),
	})
	return model("Flower", { stalk, head }, stalk)
end

return Models
