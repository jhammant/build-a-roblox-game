-- Bag: pure maths on a player's item counts ({ [itemId]: count }). No Roblox calls, so it's tested offline.
local Bag = {}

export type Items = { [string]: number }

function Bag.count(items: Items, id: string): number
	local n = items[id]
	return if type(n) == "number" then n else 0
end

-- Add up to `amount`, never going over `maxStack`. Returns how many were actually added.
function Bag.add(items: Items, id: string, amount: number, maxStack: number?): number
	if amount <= 0 then
		return 0
	end
	local have = Bag.count(items, id)
	local room = math.max(0, (maxStack or math.huge) - have)
	local added = math.min(amount, room)
	if added > 0 then
		items[id] = have + added
	end
	return added
end

-- Take exactly `amount`, or nothing at all. Returns true when it was taken.
function Bag.take(items: Items, id: string, amount: number): boolean
	local have = Bag.count(items, id)
	if amount < 0 or have < amount then
		return false
	end
	local left = have - amount
	items[id] = if left > 0 then left else nil
	return true
end

-- A clean copy for saving or loading: only known items, as whole numbers from 1 to that item's maxStack.
-- `known` is Items.BY_ID. Anything else (unknown ids, text, NaN, negatives) is dropped.
function Bag.clean(items: any, known: { [string]: any }): Items
	local out = {}
	if type(items) ~= "table" then
		return out
	end
	for id, n in items do
		local def = if type(id) == "string" then known[id] else nil
		if def and type(n) == "number" and n == n and n < math.huge then
			local whole = math.clamp(math.floor(n), 0, def.maxStack)
			if whole > 0 then
				out[id] = whole
			end
		end
	end
	return out
end

return Bag
