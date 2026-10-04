# Gun Flower: the spec

**Designed by Clara H., with her dad.** She talked the game through with a voice assistant on 3 October 2026, and
the conversation was written up as this spec. The recording stayed at home. This is a trimmed copy of the spec
Claude built from, with her ideas and phrases kept as they were.

It's here to show what a phase 2 spec can look like. Yours can be much shorter. Half a page in your child's words
is plenty to start.

---

## The core idea

Gun Flower is a colourful open-world adventure. The player explores a strange, psychedelic world, first on foot and
later on horseback. It should feel colourful, funny, slightly chaotic, magical and immediately fun for a child.

> Explore → find flowers → collect flowers → take them to the magical stream → create flower guns → fight monsters →
> monsters become flowers → collect better flowers → create more powerful guns → explore further.

That loop is the heart of the game. A player should understand it within about 30 seconds of joining.

## World

Bright and slightly psychedelic: oversized flowers, rolling hills, forests, rainbow colours, unusual trees, glowing
plants, sparkles, strange colourful skies and streams running through it all. Playful, not realistic.

**The Gun Flower Stream** is a magical rainbow stream. You bring flowers to it, and it turns them into weapons. It
should be obviously exciting: rainbow water, bubbles, floating flowers and magical sounds. You spawn close to it.

## Flowers

Different coloured flowers grow all over the world. You walk up to one and collect it: it disappears with a little
burst and a satisfying sound, and your count goes up. Start with a few colours (pink, blue, yellow, purple, red) that
are easy to tell apart from a distance.

Later the flowers become real species, starting with the 50 in our flower spotting book (daisy, bluebell, foxglove,
poppy, cowslip…), each with a colour, a rarity and a magic property that changes the guns. Finding a new one should
feel like *"Wait! What's THAT flower?!"*

## Crafting

At the stream you turn flowers into a gun:

```text
THE GUN FLOWER STREAM
Choose what to make:
[BUBBLE GUN]   [CONFETTI GUN]
(show the flowers required)
```

The flowers leave your inventory and drop into the stream, the stream does something magical, and the gun appears in
your hands. It should feel rewarding.

1. **Bubble Gun.** Fires big colourful bubbles that pop on hits. Funny, not violent. A basic monster takes about 10
   hits.
2. **Confetti Gun.** Stronger. Fires confetti bursts with a silly celebratory sound. About 5 hits.

## Monsters

Clara's key idea: **they have no eyes.** Weird and slightly creepy in concept, but the tone is silly fun, not horror:
colourful blob and plant creatures with strange mouths, bouncy movement and silly noises. They wander, notice you,
chase you, and you escape or beat them.

**When a monster is defeated, it turns into a flower of its own colour.** POP! A flower appears where it stood, ready
to collect. Flowers → guns → monsters → better flowers → better guns.

## Celebrations

How you win decides the celebration. A Bubble Gun win makes bubbles rain down around you. A Confetti Gun win rains
confetti. Deliberately over the top, even for ordinary monsters.

## Horses

Like the horses in Horse Life: walk up, climb on, ride, explore faster. Later (added the same day):

- You choose and customise your own horse at the very start: coat, mane, other fun options, and a name picked from a
  list.
- Feeding it certain flowers gives it powers, like **flying**.

## Keeping it right for kids

- Combat is extremely simple: click to fire on a computer, a big FIRE button on a tablet.
- No gore and no realistic weapons. These are ridiculous magical flower-powered blasters.
- Scary only in one place: a Mystery Area at the far end of the map, and "scary, not too much".

## Getting started in the game

Spawn somewhere beautiful, with flowers nearby and the stream in view. Then simple prompts, one at a time:

1. 🌸 PICK A FLOWER!
2. 🌈 TAKE IT TO THE MAGIC STREAM!
3. 🔫 MAKE YOUR FIRST FLOWER GUN!
4. 👾 FIND A MONSTER!
5. 💥 BLAST IT!
6. 🌸 IT TURNED INTO A FLOWER!

After that, stop hand-holding and let the player explore.

## The first map

A small, polished area, not an enormous empty world:

```text
                MYSTERY AREA
                     |
              MONSTER FOREST
                     |
    FLOWER FIELD — RAINBOW STREAM
                     |
                PLAYER SPAWN
                     |
                 HORSE AREA
```

## The design rule

When choosing between something technically impressive and something Clara will immediately find funny or fun,
**choose the second one.** The feeling to aim for: *"I found a weird flower. I wonder what ridiculous gun I can make
with it?"*

## For the builder

These lines were for Claude, not Clara, but they're why the game could grow quickly:

- The server is in charge of inventory, crafting, damage and rewards. Never trust the client.
- Flowers, recipes, monsters and weapons are data tables, so adding more is a data job, not new code.
- Build in small playable steps: spawn, world, collect a flower, see it in the inventory, craft a Bubble Gun, fire
  it, meet a monster, beat it, watch it turn into a flower, and so on. Keep the game runnable at every step.
- Don't wait for custom models. Build from simple shapes, but make it look coherent and fun, not like a grey-box test.
