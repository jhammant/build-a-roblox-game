-- harness: a tiny test runner with soft checks, skips and a PASS/FAIL/SKIP summary
local Harness = {}

local SKIP = {} -- sentinel thrown by t.skip
local ABORT = {} -- sentinel thrown by a failed hard assertion (its message is already recorded)
local MAX_PROBLEMS_SHOWN = 25

local function fmt(value: any): string
	if type(value) == "string" then
		return string.format("%q", value)
	elseif type(value) == "table" then
		local parts = {}
		for i, item in value do
			if #parts >= 12 then
				table.insert(parts, "...")
				break
			end
			if type(i) == "number" then
				table.insert(parts, fmt(item))
			else
				table.insert(parts, tostring(i) .. " = " .. fmt(item))
			end
		end
		return "{ " .. table.concat(parts, ", ") .. " }"
	end
	return tostring(value)
end

Harness.fmt = fmt

-- filter: case-insensitive substring of "<suite> <test>"; nil runs everything
function Harness.new(filter: string?): any
	local self = {
		filter = filter and string.lower(filter) or nil,
		results = {}, -- { suite, name, status, problems, notes }
		suite = "(no suite)",
	}

	local current = nil -- the running test's record

	local function addProblem(message: string)
		table.insert(current.problems, message)
	end

	-- Assertions ------------------------------------------------------------------------------------------------------

	-- Soft check: records a problem and keeps going, so data tests can list every bad entry at once
	function self.check(condition: any, message: string): boolean
		if not condition then
			addProblem(message)
		end
		return not not condition
	end

	-- Hard check: records a problem and stops this test
	function self.ok(condition: any, message: string)
		if not condition then
			addProblem(message)
			error(ABORT, 0)
		end
	end

	function self.eq(actual: any, expected: any, message: string?)
		if actual ~= expected then
			addProblem(
				string.format("%sexpected %s, got %s", message and (message .. ": ") or "", fmt(expected), fmt(actual))
			)
			error(ABORT, 0)
		end
	end

	-- Soft equality
	function self.checkEq(actual: any, expected: any, message: string?): boolean
		if actual ~= expected then
			addProblem(
				string.format("%sexpected %s, got %s", message and (message .. ": ") or "", fmt(expected), fmt(actual))
			)
			return false
		end
		return true
	end

	function self.near(actual: number, expected: number, tolerance: number, message: string?)
		if type(actual) ~= "number" or math.abs(actual - expected) > tolerance then
			addProblem(
				string.format(
					"%sexpected %s (±%s), got %s",
					message and (message .. ": ") or "",
					tostring(expected),
					tostring(tolerance),
					tostring(actual)
				)
			)
			error(ABORT, 0)
		end
	end

	function self.contains(haystack: any, needle: string, message: string?)
		if type(haystack) ~= "string" or not string.find(haystack, needle, 1, true) then
			addProblem(
				string.format("%sexpected %s to contain %q", message and (message .. ": ") or "", fmt(haystack), needle)
			)
			error(ABORT, 0)
		end
	end

	function self.fail(message: string)
		addProblem(message)
		error(ABORT, 0)
	end

	-- Stop this test as SKIP (for a module that isn't written yet)
	function self.skip(reason: string)
		current.skipReason = reason
		error(SKIP, 0)
	end

	-- An extra line shown under the test (counts, things still to do)
	function self.note(message: string)
		table.insert(current.notes, message)
	end

	-- Structure -------------------------------------------------------------------------------------------------------

	function self.describe(name: string)
		self.suite = name
	end

	function self.test(name: string, fn: () -> ())
		local label = string.lower(self.suite .. " " .. name)
		if self.filter and not string.find(label, self.filter, 1, true) then
			return
		end
		current = { suite = self.suite, name = name, problems = {}, notes = {}, status = "PASS" }
		local ok, err = xpcall(fn, function(e)
			if e == SKIP or e == ABORT then
				return e
			end
			-- keep the message and the first few stack lines; the rest is harness plumbing
			local lines = string.split(debug.traceback(tostring(e), 2), "\n")
			return table.concat(lines, "\n", 1, math.min(#lines, 6))
		end)
		if not ok then
			if err == SKIP then
				current.status = "SKIP"
			elseif err ~= ABORT then
				table.insert(current.problems, "error: " .. tostring(err))
			end
		end
		if #current.problems > 0 then
			current.status = "FAIL"
		end
		table.insert(self.results, current)
		self.printResult(current)
		current = nil
	end

	-- Output ----------------------------------------------------------------------------------------------------------

	local lastSuite = nil
	function self.printResult(result: any)
		if result.suite ~= lastSuite then
			lastSuite = result.suite
			print("\n" .. result.suite)
		end
		local line = string.format("  %-4s  %s", result.status, result.name)
		if result.status == "SKIP" then
			line ..= "  (" .. tostring(result.skipReason) .. ")"
		end
		print(line)
		for i, problem in result.problems do
			if i > MAX_PROBLEMS_SHOWN then
				print(string.format("          ... and %d more", #result.problems - MAX_PROBLEMS_SHOWN))
				break
			end
			local first = true
			for textLine in string.gmatch(problem, "[^\n]+") do
				print((first and "        - " or "          ") .. textLine)
				first = false
			end
		end
		for _, note in result.notes do
			print("        note: " .. note)
		end
	end

	-- Prints the summary and returns true when nothing failed
	function self.summary(): boolean
		local counts = { PASS = 0, FAIL = 0, SKIP = 0 }
		for _, result in self.results do
			counts[result.status] += 1
		end
		print("\n" .. string.rep("=", 100))
		if counts.FAIL > 0 then
			print("Failures:")
			for _, result in self.results do
				if result.status == "FAIL" then
					print(string.format("  FAIL  %s > %s", result.suite, result.name))
				end
			end
		end
		if counts.SKIP > 0 then
			print("Skipped:")
			for _, result in self.results do
				if result.status == "SKIP" then
					print(string.format("  SKIP  %s > %s: %s", result.suite, result.name, tostring(result.skipReason)))
				end
			end
		end
		print(
			string.format(
				"SUMMARY  %d passed, %d failed, %d skipped (%d tests)",
				counts.PASS,
				counts.FAIL,
				counts.SKIP,
				#self.results
			)
		)
		if #self.results == 0 then
			print("No tests ran" .. (self.filter and (" (nothing matched the filter " .. self.filter .. ")") or ""))
		end
		local passed = counts.FAIL == 0 and #self.results > 0
		print(passed and "RESULT: PASS" or "RESULT: FAIL")
		return passed
	end

	return self
end

return Harness
