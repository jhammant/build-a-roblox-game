-- Recipes: what you can make, where, and from what. Add a recipe here and the Workbench can make it.
local Recipes = {}

-- station: which kind of CraftPoint makes it (the CraftPoint's "Station" attribute)
-- inputs: items used up · output: the item you get
Recipes.LIST = {
	{
		id = "MagicWand",
		name = "Magic Wand",
		station = "Workbench",
		inputs = { { item = "Spark", count = 3 } },
		output = { item = "Wand", count = 1 },
	},
}

Recipes.BY_ID = {}
for _, recipe in Recipes.LIST do
	Recipes.BY_ID[recipe.id] = recipe
end

return Recipes
