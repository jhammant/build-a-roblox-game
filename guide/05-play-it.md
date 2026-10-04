# 5. Play it and tell us (kid plays, parent captures)

**Who leads:** your child plays. You watch and write.

**You'll end up with:** a short list of what to fix, what to tweak and what to add next, in your child's words.

**Time:** 15 to 20 minutes of play, then five minutes with Claude.

This is where the loop closes. What your child does and says while playing becomes the next round of picks.

## Setting it up

- **In Studio** (before you've published): press **Play** and let them take the mouse and keyboard. That's the
  quickest way.
- **On their own device** (after the first private publish in [chapter 6](06-share-it.md)): they open the game from
  the Roblox app on their own account. This is the real test, especially on a tablet or phone.

## Watch more than you talk

The most useful things happen when you say nothing:

- **Where do they go first?** What do they ignore?
- **Where do they get stuck?** Did they understand what to do within the first 30 seconds?
- **What do they keep going back to?** That's the fun bit. Do more of it.
- **What makes them laugh, or groan?**

Resist explaining. If they can't work something out, the game needs to explain it better. Write that down.

## Then ask

- "What was the best bit?"
- "What was boring, or too hard?"
- "Was anything the wrong colour, the wrong size or the wrong speed?"
- "If you could add one thing, what would it be?"

Write their answers word for word.

## Hand it to Claude

In the game folder:

> /playtest

Then paste or type your notes. A voice memo transcript works too. Claude:

1. saves your notes as `design/playtests/<date>.md`, with your child's words kept as quotes,
2. sorts them into **bugs** (it's broken), **tweaks** (it works but it's too fast, too hard, too small), and **new
   ideas**,
3. offers to fix the bugs and tweaks straight away with `/build`,
4. turns the new ideas into a proposed list of boards for the next `/pick` round.

Claude can also run an automatic **smoke test** in Studio: start Play, wait for the game to boot, and report any
errors from the game's scripts. It's a good habit after every build, but it's no substitute for your child playing.

## Bugs, tweaks or ideas?

| Your child says | It's a | What happens |
|---|---|---|
| "I collected a Spark but the number didn't go up" | Bug | Claude fixes it, with a test so it stays fixed |
| "The Gloomies are too fast" | Tweak | Claude changes one number in the Definitions |
| "I want the wand to be purple" | Tweak, but check | A colour they picked is changing, so Claude updates the spec, quoting them |
| "Can there be a dragon?" | New idea | It goes on the list for the next round of picks |
| "This is boring" | A clue | Ask what would make it better. Their answer is usually a new idea |

New ideas go through `/pick`, not straight into code. That keeps your child choosing *how* the dragon looks, not just
*that* there is one.

## When to stop

When you have a short list and your child has chosen what comes next. Go back to
[phase 3](03-pick-it.md) for new ideas, or [phase 4](04-build-it.md) for fixes.

When you're both happy with how it plays, you might be ready to [share it](06-share-it.md).
