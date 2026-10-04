-- craft spec: checking, explaining and making recipes, with made-up items so tuning the real ones can't break it
return function(t, ctx)
	local Craft = ctx.need("Craft")
	local known = {
		Spark = { name = "Spark", plural = "Sparks", maxStack = 99 },
		Leaf = { name = "Leaf", plural = "Leaves", maxStack = 99 },
		Wand = { name = "Magic Wand", plural = "Magic Wands", maxStack = 1 },
		Hat = { name = "Hat", plural = "Hats", maxStack = 1 },
	}
	local wand = {
		id = "MagicWand",
		station = "Workbench",
		inputs = { { item = "Spark", count = 3 } },
		output = { item = "Wand", count = 1 },
	}
	local hat = {
		id = "Hat",
		station = "Workbench",
		inputs = { { item = "Spark", count = 2 }, { item = "Leaf", count = 1 } },
		output = { item = "Hat", count = 1 },
	}
	local elsewhere = {
		id = "Elsewhere",
		station = "Cauldron",
		inputs = { { item = "Spark", count = 1 } },
		output = { item = "Hat", count = 1 },
	}

	t.test("check lists what's missing", function()
		local result = Craft.check({ Spark = 1 }, hat, known)
		t.eq(result.ok, false)
		t.eq(#result.missing, 2, "missing count")
		t.eq(result.missing[1].item, "Spark")
		t.eq(result.missing[1].count, 1)
		t.eq(result.missing[2].item, "Leaf")
	end)

	t.test("explain reads like a sentence", function()
		t.eq(Craft.explain(Craft.check({ Spark = 1 }, wand, known), wand, known), "You need 2 more Sparks.")
		t.eq(Craft.explain(Craft.check({ Spark = 2 }, wand, known), wand, known), "You need 1 more Spark.")
		t.eq(Craft.explain(Craft.check({}, hat, known), hat, known), "You need 2 more Sparks and 1 more Leaf.")
		t.eq(
			Craft.explain(Craft.check({ Spark = 9, Wand = 1 }, wand, known), wand, known),
			"You already have a Magic Wand."
		)
	end)

	t.test("make uses up the inputs and adds the output", function()
		local items = { Spark = 5 }
		local ok, reason = Craft.make(items, wand, known)
		t.eq(ok, true, tostring(reason))
		t.eq(items.Spark, 2, "Sparks left")
		t.eq(items.Wand, 1, "Wand made")
		local again, why = Craft.make(items, wand, known)
		t.eq(again, false, "can't make a second Wand")
		t.contains(why, "already have")
		t.eq(items.Spark, 2, "nothing used up on a failed make")
	end)

	t.test("pick chooses what you can make now, then what you could make next", function()
		local recipes = { wand, hat, elsewhere }
		local recipe, result = Craft.pick({ Spark = 3 }, recipes, "Workbench", known)
		t.eq(recipe and recipe.id, "MagicWand", "can make the wand")
		t.eq(result and result.ok, true)
		recipe, result = Craft.pick({ Spark = 2, Wand = 1 }, recipes, "Workbench", known)
		t.eq(recipe and recipe.id, "Hat", "the next thing to make")
		t.eq(result and result.ok, false, "but not yet")
		recipe = Craft.pick({ Wand = 1, Hat = 1 }, recipes, "Workbench", known)
		t.eq(recipe, nil, "everything here is made")
		recipe = Craft.pick({ Spark = 1 }, recipes, "Cauldron", known)
		t.eq(recipe and recipe.id, "Elsewhere", "each station has its own recipes")
	end)

	t.test("the real Wand recipe works with the real items", function()
		local Items = ctx.need("Definitions/Items")
		local Recipes = ctx.need("Definitions/Recipes")
		local recipe = Recipes.BY_ID.MagicWand
		t.ok(recipe ~= nil, "there's no MagicWand recipe")
		local items = { Spark = recipe.inputs[1].count }
		t.eq((Craft.make(items, recipe, Items.BY_ID)), true, "making the wand from exactly enough Sparks")
		t.eq(items.Wand, 1)
	end)
end
