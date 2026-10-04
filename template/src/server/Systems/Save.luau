-- Save: each player's progress in a DataStore, with retries, a session lock, autosave, migrations and repair.
-- In Studio, or in a place that isn't published, it keeps saves in memory instead, so playtests never touch real data.
--
-- How systems use it:
--   Save.onLoaded(player, fn)  run fn(profile) once their save has loaded
--   Save.get(player)           their profile (a placeholder until loaded; changes to it are not saved)
--   Save.markDirty(player)     after changing the profile, so the next autosave writes it
-- The profile's sections and who owns them are in ARCHITECTURE.md.
local DataStoreService = game:GetService("DataStoreService")
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Items = require(Shared.Definitions.Items)
local Bag = require(Shared.Bag)
local Bus = require(script.Parent.Parent.Bus)

local Save = {}

Save.TUNING = {
	STORE_NAME = "PlayerData",
	KEY_PREFIX = "Player_",
	AUTOSAVE_SECONDS = 60, -- 0 turns autosave off (the tests do this)
	RETRIES = 3, -- tries per DataStore request
	RETRY_WAIT = 2, -- seconds, doubled each retry
	LOCK_SECONDS = 150, -- a lock older than this belongs to a server that crashed, so it's safe to take over
	LOCK_TRIES = 5, -- how many times to wait for another server's lock before taking over anyway
	USE_DATASTORES_IN_STUDIO = false, -- true lets Studio playtests use real saves (only ever on a test copy)
	CLOSE_TIMEOUT = 25, -- seconds BindToClose waits for the last saves (Roblox allows 30)
}

-- Bump SCHEMA_VERSION when the profile's shape changes, and add MIGRATIONS[old] to upgrade old -> old + 1.
-- Never edit a migration that has shipped: players' saves already went through it.
Save.SCHEMA_VERSION = 1

Save.MIGRATIONS = {
	-- 0 -> 1: the first test version kept Sparks as a plain number. This is also the pattern to copy.
	[0] = function(data: any): any
		local items = {}
		if type(data) == "table" and type(data.sparks) == "number" then
			items.Spark = data.sparks
		end
		return { inventory = { items = items }, stats = { cheered = 0 } }
	end,
}

-- A fresh profile. Each section has one owner: inventory -> Inventory, stats -> Gloomies.
function Save.defaultProfile(): { [string]: any }
	return { inventory = { items = {} }, stats = { cheered = 0 } }
end

local function wholeAtLeastZero(value: any): number
	if type(value) ~= "number" or value ~= value or math.abs(value) == math.huge then
		return 0
	end
	return math.max(0, math.floor(value))
end

-- Rebuild a profile from whatever was stored, keeping only valid values. Saves can come back damaged or from an
-- older version of the game, and a bad value must never stop someone playing.
function Save.repair(data: any): { [string]: any }
	local profile = Save.defaultProfile()
	if type(data) ~= "table" then
		return profile
	end
	if type(data.inventory) == "table" then
		profile.inventory.items = Bag.clean(data.inventory.items, Items.BY_ID)
	end
	if type(data.stats) == "table" then
		profile.stats.cheered = wholeAtLeastZero(data.stats.cheered)
	end
	return profile
end

-- Upgrade stored data to the current schema. Returns the data, or nil and an error if a migration failed.
function Save.upgrade(schema: number, data: any): (any, string?)
	while schema < Save.SCHEMA_VERSION do
		local migrate = Save.MIGRATIONS[schema]
		if not migrate then
			return nil, "no migration from schema " .. schema
		end
		local ok, result = pcall(migrate, data)
		if not ok then
			return nil, "migration from schema " .. schema .. " failed: " .. tostring(result)
		end
		data, schema = result, schema + 1
	end
	return data, nil
end

-- Backend: real DataStores, or tables in memory ----------------------------------------------------------------------

local function deepCopy(value: any): any
	if type(value) ~= "table" then
		return value
	end
	local out = {}
	for k, v in value do
		out[k] = deepCopy(v)
	end
	return out
end

local MemoryStore = {}
MemoryStore.__index = MemoryStore

function MemoryStore.new()
	return setmetatable({ values = {} }, MemoryStore)
end

function MemoryStore:UpdateAsync(key: string, transform: (any) -> any): any
	local new = transform(deepCopy(self.values[key]))
	if new ~= nil then
		self.values[key] = deepCopy(new)
	end
	return deepCopy(new)
end

function MemoryStore:RemoveAsync(key: string): any
	local old = self.values[key]
	self.values[key] = nil
	return old
end

local backend = { mode = "none", store = nil :: any }

local function useMemory(reason: string)
	if backend.mode ~= "memory" then
		warn("[Save] Saving to memory only: " .. reason .. ". Progress lasts until this server stops.")
	end
	backend.mode = "memory"
	backend.store = MemoryStore.new()
end

local function chooseBackend()
	if game.GameId == 0 then
		useMemory("this place isn't published, so it has no DataStores")
	elseif RunService:IsStudio() and not Save.TUNING.USE_DATASTORES_IN_STUDIO then
		useMemory("Studio playtests never touch real saves")
	else
		local ok, store = pcall(DataStoreService.GetDataStore, DataStoreService, Save.TUNING.STORE_NAME)
		if ok then
			backend.mode = "datastore"
			backend.store = store
		else
			useMemory("DataStores aren't available (" .. tostring(store) .. ")")
		end
	end
end

-- Call the store with retries. Returns ok and the result (or the last error).
local function call(method: string, ...: any): (boolean, any)
	local wait = Save.TUNING.RETRY_WAIT
	local ok, result
	for attempt = 1, Save.TUNING.RETRIES do
		ok, result = pcall(backend.store[method], backend.store, ...)
		if ok then
			return true, result
		end
		if attempt < Save.TUNING.RETRIES then
			task.wait(wait)
			wait *= 2
		end
	end
	return false, result
end

-- Sessions ----------------------------------------------------------------------------------------------------------

type Session = {
	player: Player,
	key: string,
	profile: { [string]: any },
	loaded: boolean,
	readOnly: boolean, -- true when writing could damage the stored save (it failed to load, or is from a newer game)
	dirty: boolean,
	waiters: { (any) -> () },
}

local JOB_ID = if game.JobId ~= "" then game.JobId else HttpService:GenerateGUID(false)
local sessions: { [Player]: Session } = {}
local started = false

local function now(): number
	return os.time()
end

local function lockIsLive(lock: any): boolean
	return type(lock) == "table"
		and lock.job ~= JOB_ID
		and type(lock.at) == "number"
		and now() - lock.at < Save.TUNING.LOCK_SECONDS
end

local function setState(session: Session, state: string)
	pcall(session.player.SetAttribute, session.player, "SaveState", state)
end

local function finishLoad(session: Session, profile: { [string]: any })
	session.profile = profile
	session.loaded = true
	setState(session, if session.readOnly then "NotSaving" else "Saving")
	local waiters = session.waiters
	session.waiters = {}
	for _, fn in waiters do
		task.spawn(fn, profile)
	end
	Bus.fire("SaveLoaded", session.player, profile)
end

-- Load a save and take its lock. Waits for another server that still holds the lock, then takes over.
local function load(session: Session)
	for attempt = 1, Save.TUNING.LOCK_TRIES do
		local force = attempt == Save.TUNING.LOCK_TRIES
		local busy, newer, loaded = false, false, nil
		local ok, err = call("UpdateAsync", session.key, function(old: any): any
			busy, newer = false, false
			local schema, data
			if old == nil then
				schema, data = Save.SCHEMA_VERSION, Save.defaultProfile()
			elseif type(old) == "table" and type(old.schema) == "number" then
				if old.schema > Save.SCHEMA_VERSION then
					newer, loaded = true, old
					return nil -- saved by a newer version of the game: never touch it
				end
				if lockIsLive(old.lock) and not force then
					busy = true
					return nil
				end
				schema, data = old.schema, old.data
			else
				schema, data = 0, old -- from before saves had a schema
			end
			loaded = { schema = schema, data = data, savedAt = if type(old) == "table" then old.savedAt else nil }
			return { schema = schema, data = data, savedAt = loaded.savedAt, lock = { job = JOB_ID, at = now() } }
		end)
		if not sessions[session.player] then
			-- They left while we were loading: let go of the lock we just took, so their next server needn't wait
			if ok and not busy and not newer then
				call("UpdateAsync", session.key, function(old: any): any
					if type(old) == "table" and type(old.lock) == "table" and old.lock.job == JOB_ID then
						old.lock = nil
						return old
					end
					return nil
				end)
			end
			return
		end
		if not ok then
			warn("[Save] Couldn't load a player's save (" .. tostring(err) .. "). They're playing without saving.")
			session.readOnly = true
			finishLoad(session, Save.defaultProfile())
			return
		end
		if newer then
			warn("[Save] A player's save is from a newer version of the game. They're playing without saving.")
			session.readOnly = true
			finishLoad(session, Save.repair(loaded.data))
			return
		end
		if not busy then
			if force and attempt > 1 then
				warn("[Save] Took over a player's save from a server that didn't let go.")
			end
			local data, upgradeError = Save.upgrade(loaded.schema, loaded.data)
			if upgradeError then
				warn("[Save] Couldn't upgrade a player's save: " .. upgradeError .. ". They're playing without saving.")
				session.readOnly = true
				finishLoad(session, Save.repair(loaded.data))
				return
			end
			session.dirty = loaded.schema < Save.SCHEMA_VERSION
			finishLoad(session, Save.repair(data))
			return
		end
		task.wait(Save.TUNING.RETRY_WAIT * attempt)
	end
end

-- Write a session's profile. `release` lets go of the lock (when the player leaves or the server closes).
local function write(session: Session, release: boolean): boolean
	if session.readOnly or not session.loaded then
		return false
	end
	local data = Save.repair(session.profile)
	local lost = false
	local ok, err = call("UpdateAsync", session.key, function(old: any): any
		lost = type(old) == "table" and lockIsLive(old.lock)
		if lost then
			return nil -- another server took over this save: don't overwrite its newer progress
		end
		return {
			schema = Save.SCHEMA_VERSION,
			data = data,
			savedAt = now(),
			lock = if release then nil else { job = JOB_ID, at = now() },
		}
	end)
	if not ok then
		warn("[Save] Couldn't save a player's progress (" .. tostring(err) .. "). Will try again.")
		return false
	end
	if lost then
		warn("[Save] Another server has a player's save now, so this one stops saving it.")
		session.readOnly = true
		setState(session, "NotSaving")
		return false
	end
	session.dirty = false
	return true
end

local function onPlayerAdded(player: Player)
	if sessions[player] then
		return
	end
	local session: Session = {
		player = player,
		key = Save.TUNING.KEY_PREFIX .. player.UserId,
		profile = Save.defaultProfile(),
		loaded = false,
		readOnly = false,
		dirty = false,
		waiters = {},
	}
	sessions[player] = session
	setState(session, "Loading")
	task.spawn(load, session)
end

local function onPlayerRemoving(player: Player)
	local session = sessions[player]
	if not session then
		return
	end
	write(session, true)
	sessions[player] = nil
end

local function onClose()
	local pending = 0
	for player, session in sessions do
		pending += 1
		task.spawn(function()
			write(session, true)
			sessions[player] = nil
			pending -= 1
		end)
	end
	local closingAt = os.clock()
	while pending > 0 and os.clock() - closingAt < Save.TUNING.CLOSE_TIMEOUT do
		task.wait(0.1)
	end
end

-- API ----------------------------------------------------------------------------------------------------------------

-- Their profile. Until it has loaded this is a placeholder: changes to it are not saved, so wait with onLoaded.
function Save.get(player: Player): { [string]: any }
	local session = sessions[player]
	return if session then session.profile else Save.defaultProfile()
end

function Save.isLoaded(player: Player): boolean
	local session = sessions[player]
	return session ~= nil and session.loaded
end

-- Run fn(profile) once their save has loaded (straight away if it already has). Safe to call from any system's own
-- PlayerAdded handler: Roblox doesn't promise which handler runs first, so this starts their session if need be.
function Save.onLoaded(player: Player, fn: (any) -> ())
	if not sessions[player] and started and player.Parent ~= nil then
		onPlayerAdded(player)
	end
	local session = sessions[player]
	if not session then
		return
	end
	if session.loaded then
		task.spawn(fn, session.profile)
	else
		table.insert(session.waiters, fn)
	end
end

-- Call after changing someone's profile, so the next autosave (or leaving) writes it
function Save.markDirty(player: Player)
	local session = sessions[player]
	if session and session.loaded then
		session.dirty = true
	end
end

-- Write now instead of waiting for the autosave. Returns true if it saved.
function Save.saveNow(player: Player): boolean
	local session = sessions[player]
	return session ~= nil and write(session, false)
end

-- Delete someone's save, for a deletion ("right to be forgotten") request. Returns true if it worked.
function Save.erase(userId: number): (boolean, string?)
	local ok, err = call("RemoveAsync", Save.TUNING.KEY_PREFIX .. userId)
	return ok, if ok then nil else tostring(err)
end

-- "datastore" or "memory"
function Save.mode(): string
	return backend.mode
end

-- One autosave pass: writes every loaded save (which also keeps its lock fresh)
function Save.autosave()
	for _, session in table.clone(sessions) do
		if session.loaded and not session.readOnly then
			write(session, false)
		end
	end
end

function Save:Init()
	chooseBackend()
	game:BindToClose(onClose)
end

function Save:Start()
	started = true
	Players.PlayerAdded:Connect(onPlayerAdded)
	Players.PlayerRemoving:Connect(onPlayerRemoving)
	for _, player in Players:GetPlayers() do
		onPlayerAdded(player)
	end
	if Save.TUNING.AUTOSAVE_SECONDS > 0 then
		task.spawn(function()
			while true do
				task.wait(Save.TUNING.AUTOSAVE_SECONDS)
				Save.autosave()
			end
		end)
	end
end

return Save
