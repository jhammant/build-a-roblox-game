-- Bus: the server's event bus, so systems can react to each other without requiring each other.
-- Events and their arguments are listed in ARCHITECTURE.md (for example "SparkCollected" and "GloomyCheered").
local Bus = {}

local handlers: { [string]: { (...any) -> () } } = {}

-- Listen for an event. Returns a function that stops listening.
function Bus.on(event: string, handler: (...any) -> ()): () -> ()
	handlers[event] = handlers[event] or {}
	table.insert(handlers[event], handler)
	return function()
		local list = handlers[event]
		local index = list and table.find(list, handler)
		if index then
			table.remove(list, index)
		end
	end
end

-- Each handler runs in its own thread, so one broken listener can't stop the others
function Bus.fire(event: string, ...: any)
	for _, handler in table.clone(handlers[event] or {}) do
		task.spawn(handler, ...)
	end
end

return Bus
