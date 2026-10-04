-- fakes: a pretend DataStoreService and Players service, so server systems (Save, Inventory) run under test
local serde = require("@lune/serde")
local task = require("@lune/task")

local Stubs = require("./stubs")
local Signal = Stubs.Signal

local Fakes = {}

-- DataStores ----------------------------------------------------------------------------------------------------------

-- What Roblox refuses to store: NaN or infinity, functions, invalid UTF-8, mixed or gappy tables
local function strictCheck(value: any, path: string)
	local kind = type(value)
	if kind == "number" then
		if value ~= value or math.abs(value) == math.huge then
			error("104: Cannot store " .. tostring(value) .. " at " .. path)
		end
	elseif kind == "string" then
		if utf8.len(value) == nil then
			error("104: Cannot store invalid UTF-8 at " .. path)
		end
	elseif kind == "table" then
		local count, numbers, strings, maxIndex = 0, 0, 0, 0
		for key in value do
			count += 1
			if type(key) == "number" and key >= 1 and key % 1 == 0 then
				numbers += 1
				maxIndex = math.max(maxIndex, key)
			elseif type(key) == "string" then
				strings += 1
			else
				error("104: Cannot store a " .. type(key) .. " key at " .. path)
			end
		end
		if numbers > 0 and strings > 0 then
			error("104: Cannot store a mixed table at " .. path)
		end
		if numbers > 0 and maxIndex ~= count then
			error("104: Cannot store an array with gaps at " .. path)
		end
		for key, item in value do
			strictCheck(item, path .. "." .. tostring(key))
		end
	elseif kind ~= "boolean" then
		error("104: Cannot store " .. kind .. " at " .. path)
	end
end

local OUTAGE = "502: API Services rejected request with error. HTTP 500 (Internal Server Error)"

local function newStore(): any
	-- values are kept as JSON text, like the real thing, so nothing shares tables with the game
	local store = { values = {}, calls = 0, writes = 0, failNext = 0, delay = 0 }

	local function begin()
		store.calls += 1
		if store.delay > 0 then
			task.wait(store.delay)
		end
		if store.failNext > 0 then
			store.failNext -= 1
			error(OUTAGE)
		end
	end

	function store:UpdateAsync(key: string, transform: (any) -> any): any
		begin()
		local raw = self.values[key]
		local new = transform(if raw then serde.decode("json", raw) else nil)
		if new == nil then
			return nil
		end
		strictCheck(new, key)
		self.values[key] = serde.encode("json", new)
		self.writes += 1
		return serde.decode("json", self.values[key])
	end

	function store:GetAsync(key: string): any
		begin()
		local raw = self.values[key]
		return if raw then serde.decode("json", raw) else nil
	end

	function store:RemoveAsync(key: string): any
		begin()
		local raw = self.values[key]
		self.values[key] = nil
		return if raw then serde.decode("json", raw) else nil
	end

	-- For tests: read or write a value without counting it as a request
	function store:read(key: string): any
		local raw = self.values[key]
		return if raw then serde.decode("json", raw) else nil
	end

	function store:put(key: string, value: any)
		self.values[key] = serde.encode("json", value)
	end

	return store
end

-- One service can be shared by two fake servers, to test what happens between them
function Fakes.dataStoreService(): any
	local service = { stores = {} }
	function service:GetDataStore(name: string)
		self.stores[name] = self.stores[name] or newStore()
		return self.stores[name]
	end
	return service
end

-- Players -------------------------------------------------------------------------------------------------------------

function Fakes.players(): any
	local Players = { Name = "Players", PlayerAdded = Signal.new(), PlayerRemoving = Signal.new(), list = {} }
	Players.LocalPlayer = nil

	function Players:GetPlayers()
		return table.clone(self.list)
	end

	function Players:GetPlayerFromCharacter(character)
		for _, player in self.list do
			if player.Character == character then
				return player
			end
		end
		return nil
	end

	-- A player joins (fires PlayerAdded)
	function Players.join(userId: number): any
		local attributes = {}
		local player = {
			UserId = userId,
			Name = "Player" .. userId,
			Parent = Players,
			Character = nil,
			CharacterAdded = Signal.new(),
			CharacterAppearanceLoaded = Signal.new(),
		}
		function player:SetAttribute(key: string, value: any)
			attributes[key] = value
		end
		function player:GetAttribute(key: string): any
			return attributes[key]
		end
		table.insert(Players.list, player)
		Players.PlayerAdded:Fire(player)
		return player
	end

	-- A player leaves (fires PlayerRemoving)
	function Players.leave(player: any)
		local index = table.find(Players.list, player)
		if index then
			table.remove(Players.list, index)
		end
		Players.PlayerRemoving:Fire(player)
		player.Parent = nil
	end

	return Players
end

-- A whole fake server: a Loader with fake DataStores and Players, plus the BindToClose handlers it registered.
-- options: dataStores (share one between servers), gameId (0 = unpublished), studio, jobId, overrides
function Fakes.server(ctx: any, options: { [string]: any }?): any
	local opts = options or {}
	local server = {
		dataStores = opts.dataStores or Fakes.dataStoreService(),
		players = Fakes.players(),
		closeHandlers = {},
	}
	server.loader = ctx.newLoader({
		services = { DataStoreService = server.dataStores, Players = server.players },
		game = {
			GameId = if opts.gameId ~= nil then opts.gameId else 123,
			JobId = opts.jobId or "job-1",
			BindToClose = function(_, fn)
				table.insert(server.closeHandlers, fn)
			end,
		},
		overrides = opts.overrides,
	})
	server.loader.services.RunService.IsStudio = function()
		return opts.studio == true
	end
	function server.store(): any
		return server.dataStores:GetDataStore("PlayerData")
	end
	function server.close()
		for _, fn in server.closeHandlers do
			fn()
		end
	end
	return server
end

return Fakes
