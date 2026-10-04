-- shim: runs the game's ModuleScripts under Lune, in a fake game tree laid out the way Rojo syncs them:
--   src/shared -> ReplicatedStorage.Shared      src/server -> ServerScriptService
-- Each Loader has its own module cache, so a test that needs fresh state (a new server) makes a new Loader.
local fs = require("@lune/fs")
local luau = require("@lune/luau")
local roblox = require("@lune/roblox")
local task = require("@lune/task")

local Stubs = require("./stubs")

local Shim = {}

-- Roblox datatypes modules may use as globals (Lune provides these)
local DATATYPES = {
	"BrickColor",
	"CFrame",
	"Color3",
	"ColorSequence",
	"ColorSequenceKeypoint",
	"Enum",
	"Font",
	"Instance",
	"NumberRange",
	"NumberSequence",
	"NumberSequenceKeypoint",
	"PhysicalProperties",
	"Ray",
	"Rect",
	"UDim",
	"UDim2",
	"Vector2",
	"Vector3",
}

-- Rojo's file rules: Foo.luau -> ModuleScript, Foo.server.luau -> Script, Foo.client.luau -> LocalScript
local function classify(fileName: string): (string?, string?)
	if string.sub(fileName, -5) ~= ".luau" then
		return nil, nil
	end
	local base = string.sub(fileName, 1, -6)
	if string.sub(base, -7) == ".server" then
		return string.sub(base, 1, -8), "Script"
	elseif string.sub(base, -7) == ".client" then
		return string.sub(base, 1, -8), "LocalScript"
	end
	return base, "ModuleScript"
end

local function newNode(name: string, className: string, parent: any, path: string?): any
	local node = { name = name, className = className, parent = parent, path = path, children = {}, order = {} }
	if parent then
		parent.children[name] = node
		table.insert(parent.order, name)
	end
	return node
end

local function scan(dir: string, node: any)
	local entries = fs.readDir(dir)
	table.sort(entries)
	for _, entry in entries do
		local full = dir .. "/" .. entry
		if fs.isDir(full) then
			scan(full, newNode(entry, "Folder", node, nil))
		else
			local name, className = classify(entry)
			if name and className then
				newNode(name, className, node, full)
			end
		end
	end
end

local function fullName(node: any): string
	local parts = {}
	local current = node
	while current and current.className ~= "DataModel" do
		table.insert(parts, 1, current.name)
		current = current.parent
	end
	return table.concat(parts, ".")
end

local Loader = {}
Loader.__index = Loader

-- options:
--   root       the project folder (the one holding src/)
--   overrides  { ["Remotes"] = "tests/fixtures/Remotes.luau" | false } swaps or removes shared modules
--   side       "server" (default) or "client", for RunService:IsServer()/IsClient()
--   services   fake services to use instead of the stubs ({ DataStoreService = ..., Players = ... })
--   game       properties and methods of `game` ({ GameId = 123, JobId = "job-1", BindToClose = fn })
function Shim.new(options: { [string]: any }): any
	local root = options.root
	assert(type(root) == "string", "Shim.new needs { root = <project root> }")
	local self = setmetatable({
		root = root,
		side = options.side or "server",
		warnings = {}, -- { { module, text } }
		cache = {},
		loading = {},
		proxies = {},
		nodeOf = {},
		gameProps = options.game or {},
	}, Loader)

	self.game = newNode("Game", "DataModel", nil, nil)
	local replicatedStorage = newNode("ReplicatedStorage", "ReplicatedStorage", self.game, nil)
	self.shared = newNode("Shared", "Folder", replicatedStorage, nil)
	scan(root .. "/src/shared", self.shared)
	self.server = newNode("ServerScriptService", "ServerScriptService", self.game, nil)
	scan(root .. "/src/server", self.server)

	for relPath, source in options.overrides or {} do
		self:_override(relPath, source)
	end

	self.workspace = Stubs.workspace()
	self.services = Stubs.services(self.side, self.workspace)
	for name, service in options.services or {} do
		self.services[name] = service
	end
	self.services.ReplicatedStorage = self:_proxy(replicatedStorage)
	self.services.ServerScriptService = self:_proxy(self.server)
	self.env = self:_baseEnv()
	return self
end

local function findIn(start: any, relPath: string): any
	local node = start
	for part in string.gmatch(relPath, "[^/]+") do
		node = node.children[part]
		if not node then
			return nil
		end
	end
	return node
end

function Loader:_override(relPath: string, source: any)
	local parts = string.split(relPath, "/")
	local parent = self.shared
	for i = 1, #parts - 1 do
		parent = parent.children[parts[i]] or newNode(parts[i], "Folder", parent, nil)
	end
	local name = parts[#parts]
	local existing = parent.children[name]
	if source == false then
		if existing then
			parent.children[name] = nil
			table.remove(parent.order, table.find(parent.order, name) :: number)
		end
		return
	end
	local path = self.root .. "/" .. source
	assert(fs.isFile(path), "override file not found: " .. path)
	if existing then
		existing.path = path
		existing.className = "ModuleScript"
	else
		newNode(name, "ModuleScript", parent, path)
	end
end

-- Is there a shared module at this path ("Definitions/Items")?
function Loader:has(relPath: string): boolean
	local node = findIn(self.shared, relPath)
	return node ~= nil and node.className == "ModuleScript"
end

-- Every shared ModuleScript under a folder (or all of them): { "Bag", "Definitions/Items", ... }
function Loader:modulesIn(relDir: string?): { string }
	local start = if relDir then findIn(self.shared, relDir) else self.shared
	local out = {}
	local function walk(node: any, prefix: string)
		for _, name in node.order do
			local child = node.children[name]
			if child then
				local rel = if prefix == "" then name else prefix .. "/" .. name
				if child.className == "ModuleScript" then
					table.insert(out, rel)
				end
				walk(child, rel)
			end
		end
	end
	if start then
		walk(start, relDir or "")
	end
	return out
end

-- require a shared module: loader:require("Definitions/Items")
function Loader:require(relPath: string): any
	local node = findIn(self.shared, relPath)
	if not node or node.className ~= "ModuleScript" then
		error(string.format("src/shared/%s.luau doesn't exist", relPath), 2)
	end
	return self:_load(node)
end

-- require a server module: loader:requireServer("Systems/Save")
function Loader:requireServer(relPath: string): any
	local node = findIn(self.server, relPath)
	if not node or node.className ~= "ModuleScript" then
		error(string.format("src/server/%s.luau doesn't exist", relPath), 2)
	end
	return self:_load(node)
end

-- Warnings recorded since index `from` (default: all), as "[Module] text"
function Loader:warningsSince(from: number?): { string }
	local out = {}
	for i = (from or 0) + 1, #self.warnings do
		local w = self.warnings[i]
		table.insert(out, string.format("[%s] %s", w.module, w.text))
	end
	return out
end

function Loader:_load(node: any): any
	local cached = self.cache[node]
	if cached ~= nil then
		return cached
	end
	local name = fullName(node)
	if self.loading[node] then
		error("Requested module was required recursively: " .. name, 0)
	end
	local env = table.clone(self.env)
	env.script = self:_proxy(node)
	env.warn = function(...)
		local parts = {}
		for i = 1, select("#", ...) do
			table.insert(parts, tostring((select(i, ...))))
		end
		table.insert(self.warnings, { module = name, text = table.concat(parts, " ") })
	end
	local okCompile, chunk = pcall(luau.load, fs.readFile(node.path), { debugName = name, environment = env })
	if not okCompile then
		error(string.format("%s failed to compile: %s", name, tostring(chunk)), 0)
	end
	self.loading[node] = true
	local okRun, result = pcall(chunk)
	self.loading[node] = nil
	if not okRun then
		error(string.format("%s errored while loading: %s", name, tostring(result)), 0)
	end
	if result == nil then
		error(name .. ": module didn't return a value", 0)
	end
	self.cache[node] = result
	return result
end

-- An Instance-like view of a node: .Name, .Parent, children by name, FindFirstChild, WaitForChild...
function Loader:_proxy(node: any): any
	local existing = self.proxies[node]
	if existing then
		return existing
	end
	local loader = self
	local proxy = {}
	local methods = {}

	function methods.FindFirstChild(_, childName: string)
		local child = node.children[childName]
		return child and loader:_proxy(child) or nil
	end

	function methods.WaitForChild(_, childName: string)
		local child = node.children[childName]
		if not child then
			-- Roblox would wait forever; under test, missing means the file isn't written yet
			error(string.format("WaitForChild: %s has no child %q", fullName(node), childName), 2)
		end
		return loader:_proxy(child)
	end

	function methods.GetChildren()
		local out = {}
		for _, childName in node.order do
			if node.children[childName] then
				table.insert(out, loader:_proxy(node.children[childName]))
			end
		end
		return out
	end

	function methods.IsA(_, className: string)
		return className == node.className or className == "Instance"
	end

	function methods.GetFullName()
		return fullName(node)
	end

	function methods.GetService(_, serviceName: string)
		local service = loader.services[serviceName]
		if service == nil then
			error(string.format("test shim: game:GetService(%q) isn't stubbed; add it to stubs.luau", serviceName), 2)
		end
		return service
	end

	setmetatable(proxy, {
		__index = function(_, key)
			if node.className == "DataModel" and loader.gameProps[key] ~= nil then
				return loader.gameProps[key]
			elseif key == "Name" then
				return node.name
			elseif key == "ClassName" then
				return node.className
			elseif key == "Parent" then
				return node.parent and loader:_proxy(node.parent) or nil
			elseif methods[key] then
				return methods[key]
			elseif node.children[key] then
				return loader:_proxy(node.children[key])
			elseif node.className == "DataModel" and key == "GameId" then
				return 0
			elseif node.className == "DataModel" and key == "JobId" then
				return ""
			end
			error(string.format("%s is not a valid member of %s %q", tostring(key), node.className, fullName(node)), 2)
		end,
		__newindex = function(_, key)
			error(string.format("test shim: can't set %s on %s", tostring(key), fullName(node)), 2)
		end,
		__tostring = function()
			return node.name
		end,
	})
	self.proxies[node] = proxy
	self.nodeOf[proxy] = node
	return proxy
end

function Loader:_baseEnv(): { [string]: any }
	local env = {}
	for _, name in DATATYPES do
		local datatype = (roblox :: any)[name]
		if datatype ~= nil then
			env[name] = datatype
		end
	end
	env.Random = Stubs.Random
	env.TweenInfo = Stubs.TweenInfo
	env.RaycastParams = Stubs.RaycastParams
	env.task = task
	env.workspace = self.workspace
	env.game = self:_proxy(self.game)
	env.print = function() end -- keep test output to the results
	env.require = function(target)
		local node = self.nodeOf[target]
		if not node or node.className ~= "ModuleScript" then
			error(
				"test shim: require() only takes ModuleScripts from the fake tree (got " .. tostring(target) .. ")",
				2
			)
		end
		return self:_load(node)
	end
	return env
end

return Shim
