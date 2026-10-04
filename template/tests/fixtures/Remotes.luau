-- Remotes (test fixture): stands in for src/shared/Remotes.luau and records what the server sends to clients
local Remotes = { sent = {} }

local remotes = {}

function Remotes.get(name: string): any
	local remote = remotes[name]
	if not remote then
		remote = { Name = name }
		function remote:FireClient(player: any, ...: any)
			table.insert(Remotes.sent, { name = name, player = player, args = table.pack(...) })
		end
		function remote:FireAllClients(...: any)
			table.insert(Remotes.sent, { name = name, args = table.pack(...) })
		end
		remotes[name] = remote
	end
	return remote
end

-- The last thing sent on a remote, or nil
function Remotes.last(name: string): any
	for i = #Remotes.sent, 1, -1 do
		if Remotes.sent[i].name == name then
			return Remotes.sent[i]
		end
	end
	return nil
end

return Remotes
