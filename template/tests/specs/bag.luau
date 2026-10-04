-- bag spec: adding, taking and cleaning item counts
return function(t, ctx)
	local Bag = ctx.need("Bag")

	t.test("count is 0 for anything you don't have", function()
		t.eq(Bag.count({}, "Spark"), 0)
		t.eq(Bag.count({ Spark = 4 }, "Spark"), 4)
	end)

	t.test("add stops at maxStack and says how many it added", function()
		local items = { Spark = 97 }
		t.eq(Bag.add(items, "Spark", 5, 99), 2, "added")
		t.eq(items.Spark, 99)
		t.eq(Bag.add(items, "Spark", 1, 99), 0, "added when full")
		t.eq(Bag.add(items, "Wand", 0, 1), 0, "adding nothing")
		t.eq(items.Wand, nil, "adding nothing leaves no entry")
	end)

	t.test("take is all or nothing", function()
		local items = { Spark = 3 }
		t.eq(Bag.take(items, "Spark", 4), false, "taking too many")
		t.eq(items.Spark, 3, "nothing taken")
		t.eq(Bag.take(items, "Spark", 3), true, "taking exactly")
		t.eq(items.Spark, nil, "an empty count is removed")
		t.eq(Bag.take(items, "Spark", -1), false, "negative amounts")
	end)

	t.test("clean keeps only known items as whole numbers within maxStack", function()
		local known = { Spark = { maxStack = 99 }, Wand = { maxStack = 1 } }
		local cleaned = Bag.clean({
			Spark = 12.7,
			Wand = 5,
			Banana = 3,
			[7] = 1,
			Other = "x",
		}, known)
		t.eq(cleaned.Spark, 12, "Spark rounded down")
		t.eq(cleaned.Wand, 1, "Wand capped at maxStack")
		t.eq(cleaned.Banana, nil, "unknown item dropped")
		t.eq(cleaned[7], nil, "number key dropped")
		local nan = 0 / 0
		local weird = Bag.clean({ Spark = nan, Wand = -2 }, known)
		t.eq(next(weird), nil, "NaN and negatives dropped")
		t.eq(next(Bag.clean("not a table", known)), nil, "junk gives an empty bag")
	end)
end
