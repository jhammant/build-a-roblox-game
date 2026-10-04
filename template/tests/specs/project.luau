-- project spec: default.project.json sets the place up safely. A place made with `rojo build` otherwise starts on
-- Roblox's legacy chat, which ignores the TextChatService switches and shows chat over the HUD.
local fs = require("@lune/fs")
local serde = require("@lune/serde")

local CHAT_PARTS = { "ChatWindowConfiguration", "ChatInputBarConfiguration", "BubbleChatConfiguration" }

-- Things a log line must never include: they reach the Error Report, and the kit keeps personal data out of logs
local PERSONAL = { "UserId", "%.key%f[%W]", "%.Name%f[%W]", "DisplayName", "session%.key" }

local function luauFiles(dir: string, out: { string }): { string }
	for _, name in fs.readDir(dir) do
		local path = dir .. "/" .. name
		if fs.isDir(path) then
			luauFiles(path, out)
		elseif string.sub(name, -5) == ".luau" then
			table.insert(out, path)
		end
	end
	return out
end

return function(t, ctx)
	t.test("no print or warn includes a player's id, name or save key", function()
		for _, path in luauFiles(ctx.root .. "/src", {}) do
			local lineNo = 0
			for line in string.gmatch(fs.readFile(path) .. "\n", "(.-)\n") do
				lineNo += 1
				local call = string.match(line, "%f[%w](warn%s*%(.*)") or string.match(line, "%f[%w](print%s*%(.*)")
				if call then
					for _, pattern in PERSONAL do
						t.check(
							not string.find(call, pattern),
							string.format("%s:%d logs something personal: %s", path, lineNo, call)
						)
					end
				end
			end
		end
	end)

	t.test("the place uses TextChatService, with chat matching Config.CHAT_ENABLED", function()
		local project = serde.decode("json", fs.readFile(ctx.root .. "/default.project.json"))
		local chat = project.tree.TextChatService
		t.ok(chat ~= nil, "default.project.json has no TextChatService entry")
		t.eq(chat["$properties"] and chat["$properties"].ChatVersion, "TextChatService", "ChatVersion")
		local Config = ctx.need("Config")
		for _, name in CHAT_PARTS do
			local part = chat[name]
			t.check(part ~= nil, name .. " is missing")
			if part then
				t.checkEq(
					part["$properties"] and part["$properties"].Enabled,
					Config.CHAT_ENABLED == true,
					name .. ".Enabled"
				)
			end
		end
	end)
end
