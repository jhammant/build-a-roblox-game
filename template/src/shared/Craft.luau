-- Craft: can this player make a recipe, what's missing, and making it. Pure, so it's tested offline.
local Bag = require(script.Parent.Bag)

local Craft = {}

export type Result = {
	ok: boolean,
	missing: { { item: string, count: number } }, -- what's still needed, and how many more
	full: boolean, -- true when they can't hold any more of what it makes (a tool they already have)
}

function Craft.check(items: Bag.Items, recipe: any, known: { [string]: any }): Result
	local missing = {}
	for _, input in recipe.inputs do
		local short = input.count - Bag.count(items, input.item)
		if short > 0 then
			table.insert(missing, { item = input.item, count = short })
		end
	end
	local output = known[recipe.output.item]
	local full = output == nil or Bag.count(items, recipe.output.item) + recipe.output.count > output.maxStack
	return { ok = #missing == 0 and not full, missing = missing, full = full }
end

-- What to tell the player when they can't make it: "You need 2 more Sparks."
function Craft.explain(result: Result, recipe: any, known: { [string]: any }): string
	if result.full then
		local output = known[recipe.output.item]
		return "You already have " .. (if output then "a " .. output.name else "that") .. "."
	end
	local parts = {}
	for _, need in result.missing do
		local def = known[need.item]
		local name = if def == nil then need.item elseif need.count == 1 then def.name else def.plural
		table.insert(parts, need.count .. " more " .. name)
	end
	return "You need " .. table.concat(parts, " and ") .. "."
end

-- Use up the inputs and add the output. Returns true, or false and the reason.
function Craft.make(items: Bag.Items, recipe: any, known: { [string]: any }): (boolean, string?)
	local result = Craft.check(items, recipe, known)
	if not result.ok then
		return false, Craft.explain(result, recipe, known)
	end
	for _, input in recipe.inputs do
		Bag.take(items, input.item, input.count)
	end
	Bag.add(items, recipe.output.item, recipe.output.count, known[recipe.output.item].maxStack)
	return true, nil
end

-- Which recipe a station should make for this player: the first one they can make now. If there isn't one, the
-- first one they could still make later (so we can say what's missing). nil when they've made everything here.
function Craft.pick(items: Bag.Items, recipes: { any }, station: string, known: { [string]: any }): (any, Result?)
	local fallback, fallbackResult = nil, nil
	for _, recipe in recipes do
		if recipe.station == station then
			local result = Craft.check(items, recipe, known)
			if result.ok then
				return recipe, result
			elseif not result.full and fallback == nil then
				fallback, fallbackResult = recipe, result
			end
		end
	end
	return fallback, fallbackResult
end

return Craft
