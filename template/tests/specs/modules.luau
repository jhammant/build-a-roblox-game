-- modules spec: every file under src/ compiles, and every shared module loads without errors or warnings
local fs = require("@lune/fs")
local luau = require("@lune/luau")

local function luauFiles(dir: string, out: { string }): { string }
	local entries = fs.readDir(dir)
	table.sort(entries)
	for _, entry in entries do
		local full = dir .. "/" .. entry
		if fs.isDir(full) then
			luauFiles(full, out)
		elseif string.match(entry, "%.luau$") then
			table.insert(out, full)
		end
	end
	return out
end

return function(t, ctx)
	t.test("every .luau file under src/ compiles", function()
		local files = luauFiles(ctx.root .. "/src", {})
		for _, path in files do
			local ok, err = pcall(luau.compile, fs.readFile(path))
			t.check(ok, string.sub(path, #ctx.root + 2) .. ": " .. tostring(err))
		end
		t.note(#files .. " files")
	end)

	local loader = ctx.newLoader()
	for _, relPath in loader:modulesIn() do
		t.test(relPath .. " loads cleanly", function()
			local before = #loader.warnings
			local ok, result = pcall(function()
				return loader:require(relPath)
			end)
			t.ok(ok, tostring(result))
			t.check(type(result) == "table", relPath .. " should return a table, got " .. typeof(result))
			for _, warning in loader:warningsSince(before) do
				t.check(false, "warned while loading: " .. warning)
			end
		end)
	end
end
