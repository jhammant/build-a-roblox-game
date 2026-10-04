-- run: the game's offline tests. `lune run tests/run [filter]` from the project folder; exits 1 if anything fails.
local fs = require("@lune/fs")
local process = require("@lune/process")

local Harness = require("./lib/harness")
local Shim = require("./lib/shim")

-- The project folder: the one above tests/ (works from any working directory), else the working directory
local function findRoot(): string
	local source = debug.info(1, "s")
	local dir = string.match(source, "^(.*)[/\\]tests[/\\]run") or ""
	if dir ~= "" and string.sub(dir, 1, 1) ~= "/" and not string.match(dir, "^%a:") then
		dir = process.cwd .. dir
	end
	if dir ~= "" and fs.isDir(dir .. "/src/shared") then
		return dir
	end
	return (string.gsub(process.cwd, "[/\\]$", ""))
end

local root = findRoot()
if not fs.isDir(root .. "/src/shared") then
	print("can't find src/shared under " .. root .. "; run this from the game's folder")
	process.exit(2)
end

local filter = process.args[1]
local t = Harness.new(filter)

-- Shared by every spec
local ctx = { root = root }

-- A fresh fake game (its own module cache). Options are documented in lib/shim.luau.
function ctx.newLoader(options: { [string]: any }?): any
	local opts = table.clone(options or {})
	opts.root = root
	return Shim.new(opts)
end

ctx.loader = ctx.newLoader()

-- Load a shared module for a test, or SKIP the test if its file isn't written yet (a file that errors FAILs)
function ctx.need(relPath: string): any
	if not ctx.loader:has(relPath) then
		t.skip(string.format("src/shared/%s.luau isn't written yet", relPath))
	end
	local ok, result = pcall(function()
		return ctx.loader:require(relPath)
	end)
	if not ok then
		t.fail("couldn't load " .. relPath .. ": " .. tostring(result))
	end
	return result
end

local SPECS = {
	{ name = "modules", run = require("./specs/modules") },
	{ name = "definitions", run = require("./specs/definitions") },
	{ name = "bag", run = require("./specs/bag") },
	{ name = "craft", run = require("./specs/craft") },
	{ name = "zap", run = require("./specs/zap") },
	{ name = "models", run = require("./specs/models") },
	{ name = "save", run = require("./specs/save") },
	{ name = "inventory", run = require("./specs/inventory") },
	{ name = "project", run = require("./specs/project") },
}

print(string.format("Tests (project %s)%s", root, if filter then "  filter: " .. filter else ""))
for _, spec in SPECS do
	t.describe(spec.name)
	local ok, err = pcall(spec.run, t, ctx)
	if not ok then
		t.test("(spec setup)", function()
			t.fail("spec crashed: " .. tostring(err))
		end)
	end
end

local passed = t.summary()
process.exit(if passed then 0 else 1)
