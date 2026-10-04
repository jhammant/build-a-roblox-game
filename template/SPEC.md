# Spark Garden: game spec

_This is the starter game's spec. When your child dreams up their own game, `/dream` replaces this file with theirs,
in their words. Until then, it describes what the template does._

## The game in one line

Collect Sparks, make a Magic Wand, and zap the grumpy Gloomies until they cheer up.

## The loop

> Collect Sparks → take 3 to the Workbench → make a Magic Wand → zap Gloomies → they cheer up, float away and drop
> more Sparks → collect those too.

It should make sense within 30 seconds of joining. The hint line at the top of the screen says what to do next.

## Things in the game

| Thing | What it does | Where its look comes from |
|---|---|---|
| Sparks | Glowing balls in the garden. Walk into one to collect it | `Definitions/Items` (Spark) |
| Workbench | Press Make with 3 Sparks to get a Magic Wand | `Definitions/World`, `Definitions/Recipes` |
| Magic Wand | Click (or tap ZAP) to zap where you aim | `Definitions/Items` (Wand) |
| Gloomies | Grumpy blobs that wander about. Three zaps cheer one up | `Definitions/Gloomies` |

## Feel

Bright, friendly and a bit silly. Nothing hurts you. Gloomies are grumpy, not scary, and cheering them up feels good:
a burst of colour, and they float away.

## Saving

Your Sparks and your wand are saved between visits (once the game is published).

## Not decided yet

Everything that's a placeholder: the look of the wand, the Gloomies, the Sparks and the garden. The first `/pick`
round is where your child chooses them.

## Rounds
