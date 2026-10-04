-- stubs: the bits of the Roblox engine that Lune doesn't have (Signals, Random, TweenInfo, services), just enough
-- for the game's modules to load and run under test
local serde = require("@lune/serde")

local Stubs = {}

-- Signals: Connect/Once/Fire, so modules that hook PlayerAdded or Heartbeat at load time don't crash ----------------

local Signal = {}
Signal.__index = Signal

function Signal.new()
	return setmetatable({ handlers = {} }, Signal)
end

function Signal:Connect(fn)
	local handlers = self.handlers
	table.insert(handlers, fn)
	return {
		Connected = true,
		Disconnect = function(connection)
			connection.Connected = false
			local index = table.find(handlers, fn)
			if index then
				table.remove(handlers, index)
			end
		end,
	}
end

Signal.Once = Signal.Connect

function Signal:Fire(...)
	for _, fn in table.clone(self.handlers) do
		fn(...)
	end
end

function Signal:Wait()
	error("test stub: Signal:Wait() would block forever outside Roblox", 2)
end

Stubs.Signal = Signal

-- Random: a seeded xorshift32, so seeded runs repeat (the numbers differ from Roblox's) -------------------------------

local Random = {}
Random.__index = Random

local TWO_32 = 4294967296

local function xorshift(x: number): number
	x = bit32.bxor(x, bit32.lshift(x, 13))
	x = bit32.bxor(x, bit32.rshift(x, 17))
	return bit32.bxor(x, bit32.lshift(x, 5))
end

function Random.new(seed: number?)
	local x = bit32.bxor(math.floor(math.abs(seed or (os.clock() * 1e6 + os.time()))) % TWO_32, 0x9E3779B9)
	if x == 0 then
		x = 0x2545F491
	end
	for _ = 1, 8 do
		x = xorshift(x)
	end
	return setmetatable({ _state = x }, Random)
end

function Random:_next(): number
	self._state = xorshift(self._state)
	return self._state / TWO_32
end

function Random:NextNumber(min: number?, max: number?): number
	local lo, hi = min or 0, max or 1
	return lo + (hi - lo) * self:_next()
end

function Random:NextInteger(min: number, max: number): number
	if max < min then
		error(string.format("invalid argument #2 to 'NextInteger' (max %d < min %d)", max, min), 2)
	end
	return min + math.floor(self:_next() * (max - min + 1))
end

Stubs.Random = Random

-- Plain records outside Roblox ----------------------------------------------------------------------------------------

Stubs.TweenInfo = {
	new = function(time, style, direction, repeatCount, reverses, delayTime)
		return {
			Time = time or 1,
			EasingStyle = style,
			EasingDirection = direction,
			RepeatCount = repeatCount or 0,
			Reverses = reverses or false,
			DelayTime = delayTime or 0,
		}
	end,
}

Stubs.RaycastParams = {
	new = function()
		return { FilterType = nil, FilterDescendantsInstances = {}, IgnoreWater = false }
	end,
}

-- Services ------------------------------------------------------------------------------------------------------------

function Stubs.services(side: string, workspaceStub: any): { [string]: any }
	local services = {}

	services.TweenService = {
		Create = function(_, instance, _info, props)
			local tween = { Completed = Signal.new() }
			function tween.Play()
				for key, value in props do
					pcall(function()
						instance[key] = value
					end)
				end
				tween.Completed:Fire("Completed")
			end
			function tween.Cancel() end
			return tween
		end,
	}

	local guidCount = 0
	services.HttpService = {
		GenerateGUID = function(_, wrap: boolean?)
			guidCount += 1
			local id = string.format("00000000-0000-4000-8000-%012d", guidCount)
			return if wrap == false then id else "{" .. id .. "}"
		end,
		JSONEncode = function(_, value)
			return serde.encode("json", value)
		end,
		JSONDecode = function(_, text)
			return serde.decode("json", text)
		end,
	}

	services.RunService = {
		IsServer = function()
			return side == "server"
		end,
		IsClient = function()
			return side == "client"
		end,
		IsStudio = function()
			return true
		end,
		Heartbeat = Signal.new(),
		RenderStepped = Signal.new(),
	}

	services.Players = {
		LocalPlayer = nil,
		GetPlayers = function()
			return {}
		end,
		GetPlayerFromCharacter = function()
			return nil
		end,
		PlayerAdded = Signal.new(),
		PlayerRemoving = Signal.new(),
	}

	services.CollectionService = {
		GetTagged = function()
			return {}
		end,
		HasTag = function()
			return false
		end,
		AddTag = function() end,
		GetInstanceAddedSignal = function()
			return Signal.new()
		end,
	}

	services.Debris = { AddItem = function() end }
	services.Workspace = workspaceStub
	return services
end

-- workspace: nothing in it, and every raycast misses
function Stubs.workspace()
	return {
		Name = "Workspace",
		ClassName = "Workspace",
		Gravity = 196.2,
		CurrentCamera = nil,
		Raycast = function()
			return nil
		end,
		FindFirstChild = function()
			return nil
		end,
		WaitForChild = function(_, name)
			error("test stub: workspace has no " .. tostring(name), 2)
		end,
		GetChildren = function()
			return {}
		end,
	}
end

return Stubs
