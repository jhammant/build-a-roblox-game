-- zap spec: what a zap hits, range, cooldown, and refusing junk from clients
local roblox = require("@lune/roblox")
local Vector3 = roblox.Vector3

return function(t, ctx)
	local Zap = ctx.need("Zap")
	local stats = { range = 60, hitRadius = 6, cooldown = 0.35, power = 1 }
	local origin = Vector3.new(0, 0, 0)

	t.test("hits the target nearest the aim point", function()
		local targets = {
			{ id = "near", position = Vector3.new(20, 0, 0) },
			{ id = "nearer", position = Vector3.new(22, 0, 1) },
		}
		local target = Zap.pickTarget(origin, Vector3.new(22, 0, 0), targets, stats)
		t.eq(target and target.id, "nearer")
	end)

	t.test("misses when the aim is too far from every target", function()
		local targets = { { id = "a", position = Vector3.new(20, 0, 0) } }
		t.eq(Zap.pickTarget(origin, Vector3.new(20, 0, 10), targets, stats), nil)
	end)

	t.test("can't hit anything out of range, even when aimed at", function()
		local targets = { { id = "far", position = Vector3.new(100, 0, 0) } }
		t.eq(Zap.pickTarget(origin, Vector3.new(100, 0, 0), targets, stats), nil)
	end)

	t.test("clampAim pulls a far aim back to the wand's range", function()
		local aim = Zap.clampAim(origin, Vector3.new(200, 0, 0), 60)
		t.near(aim.X, 60, 1e-6, "clamped x")
		local close = Zap.clampAim(origin, Vector3.new(10, 0, 0), 60)
		t.near(close.X, 10, 1e-6, "close aims are left alone")
	end)

	t.test("nearest finds the closest target in range", function()
		local targets = {
			{ id = "a", position = Vector3.new(30, 0, 0) },
			{ id = "b", position = Vector3.new(0, 0, 12) },
			{ id = "c", position = Vector3.new(500, 0, 0) },
		}
		t.eq((Zap.nearest(origin, targets, 60) or {}).id, "b")
		t.eq(Zap.nearest(origin, { targets[3] }, 60), nil, "nothing in range")
	end)

	t.test("ready waits for the cooldown", function()
		t.eq(Zap.ready(nil, 10, 0.35), true, "first zap")
		t.eq(Zap.ready(10, 10.2, 0.35), false, "too soon")
		t.eq(Zap.ready(10, 10.4, 0.35), true, "after the cooldown")
	end)

	t.test("validAim refuses anything that isn't a real point", function()
		t.eq(Zap.validAim(Vector3.new(1, 2, 3)), true, "a point")
		t.eq(Zap.validAim("aim"), false, "text")
		t.eq(Zap.validAim(nil), false, "nothing")
		t.eq(Zap.validAim({ X = 1, Y = 2, Z = 3 }), false, "a table pretending")
		t.eq(Zap.validAim(Vector3.new(0 / 0, 0, 0)), false, "NaN")
		t.eq(Zap.validAim(Vector3.new(math.huge, 0, 0)), false, "infinity")
	end)
end
