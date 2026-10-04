-- Zap: what a zap hits. Pure maths, so it's tested offline. The server uses it to check every zap; the client uses
-- `nearest` to aim the touch-screen ZAP button.
local Zap = {}

export type Target = { id: any, position: Vector3 }
export type Stats = { range: number, hitRadius: number, cooldown: number, power: number }

-- A zap can't reach further than the wand's range: pull a far-away aim point back towards the player
function Zap.clampAim(origin: Vector3, aim: Vector3, range: number): Vector3
	local offset = aim - origin
	if offset.Magnitude <= range then
		return aim
	end
	return origin + offset.Unit * range
end

-- The target closest to the aim point, if it's within hitRadius of the aim and within range of the player
function Zap.pickTarget(origin: Vector3, aim: Vector3, targets: { Target }, stats: Stats): Target?
	local best, bestDistance = nil, math.huge
	for _, target in targets do
		local fromPlayer = (target.position - origin).Magnitude
		local fromAim = (target.position - aim).Magnitude
		if fromPlayer <= stats.range and fromAim <= stats.hitRadius and fromAim < bestDistance then
			best, bestDistance = target, fromAim
		end
	end
	return best
end

-- The target closest to the player, within range
function Zap.nearest(origin: Vector3, targets: { Target }, range: number): Target?
	local best, bestDistance = nil, math.huge
	for _, target in targets do
		local distance = (target.position - origin).Magnitude
		if distance <= range and distance < bestDistance then
			best, bestDistance = target, distance
		end
	end
	return best
end

-- Has the cooldown passed since the last zap?
function Zap.ready(lastAt: number?, now: number, cooldown: number): boolean
	return lastAt == nil or now - lastAt >= cooldown
end

-- Is this a usable aim point from a client? (Remote arguments can be anything.)
function Zap.validAim(aim: any): boolean
	if typeof(aim) ~= "Vector3" then
		return false
	end
	for _, axis in { aim.X, aim.Y, aim.Z } do
		if axis ~= axis or math.abs(axis) == math.huge then
			return false
		end
	end
	return true
end

return Zap
