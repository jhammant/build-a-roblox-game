-- Inventory: each player's items (Sparks, the Wand). Kept in their save; tells their screen whenever it changes.
-- Other systems change items only through this module.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Items = require(Shared.Definitions.Items)
local Bag = require(Shared.Bag)
local Craft = require(Shared.Craft)
local Remotes = require(Shared.Remotes)
local Bus = require(script.Parent.Parent.Bus)
local Save = require(script.Parent.Save)

local Inventory = {}

local function itemsOf(player: Player): Bag.Items
	return Save.get(player).inventory.items
end

-- A copy of their items, safe to send to the client
function Inventory.snapshot(player: Player): Bag.Items
	return table.clone(itemsOf(player))
end

-- Tell everything that cares: their screen, the save and other systems
local function changed(player: Player)
	Save.markDirty(player)
	local snapshot = Inventory.snapshot(player)
	Remotes.get("InventoryChanged"):FireClient(player, snapshot)
	Bus.fire("ItemsChanged", player, snapshot)
end

function Inventory.count(player: Player, id: string): number
	return Bag.count(itemsOf(player), id)
end

-- Add items. Returns how many were added: 0 before their save has loaded, or when they can't carry any more.
function Inventory.add(player: Player, id: string, amount: number): number
	local def = Items.get(id)
	if not def or not Save.isLoaded(player) then
		return 0
	end
	local added = Bag.add(itemsOf(player), id, amount, def.maxStack)
	if added > 0 then
		changed(player)
	end
	return added
end

-- Take items. Returns true only if they had enough (then all of them are taken).
function Inventory.take(player: Player, id: string, amount: number): boolean
	if not Save.isLoaded(player) then
		return false
	end
	local taken = Bag.take(itemsOf(player), id, amount)
	if taken then
		changed(player)
	end
	return taken
end

-- Make a recipe from their items. Returns true, or false and a message for the player.
function Inventory.craft(player: Player, recipe: any): (boolean, string?)
	if not Save.isLoaded(player) then
		return false, "Just a moment, your bag is still loading."
	end
	local ok, reason = Craft.make(itemsOf(player), recipe, Items.BY_ID)
	if ok then
		changed(player)
	end
	return ok, reason
end

function Inventory:Start()
	Remotes.get("GetInventory").OnServerInvoke = function(player: Player)
		return Inventory.snapshot(player)
	end
	local function onPlayer(player: Player)
		Save.onLoaded(player, function()
			Remotes.get("InventoryChanged"):FireClient(player, Inventory.snapshot(player))
			Bus.fire("ItemsChanged", player, Inventory.snapshot(player))
		end)
	end
	Players.PlayerAdded:Connect(onPlayer)
	for _, player in Players:GetPlayers() do
		onPlayer(player)
	end
end

return Inventory
