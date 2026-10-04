# 3. Pick it (the kid chooses)

**Who leads:** your child. They choose; Claude draws the options and writes down the result.

**You'll end up with:** your child's picks for every part of the game, and a build spec written from them.

**Time:** 10 to 15 minutes of picking per round. Claude spends longer drawing beforehand and writing up afterwards.

This is the heart of the kit. It's how a child, not the grown-ups or the AI, ends up deciding what the game looks like.

## How it works

1. **Claude draws boards.** A board is one choice, like "your magic wand" or "the bad guys". Each board has **three
   options, A, B and C**, drawn in the game's real style, each with a short name and a one-line description your
   child can read. Some boards say "tap any" instead, for things like sounds or effects where they can pick several.
2. **Your child taps their picks** on a page that works well on a tablet: big cards, a happy sound on every tap, a
   note box under every board, and confetti when everything's picked. They can change their mind as often as they
   like.
3. **Claude reads the picks back** and turns them into an exact spec: colours, shapes, sizes and what each thing does.
4. **Claude builds from that spec** in [phase 4](04-build-it.md). It isn't allowed to swap a pick for something easier.

Here's what the starter round looks like (from [`picker/sample/`](../picker/sample/)):

```text
1  Your magic wand          (pick one)   A Star Wand · B Flower Wand · C Bubble Wand   + stick colour
2  The Gloomies             (pick one)   A Rain Cloud · B Grumpy Blob · C Sulky Sock
3  Extra fun                (tap any)    Sounds: Boing, Pop, Twinkle, Toot
                                         Effects: Sparkles, Confetti, Bubbles, Rainbow trail
```

## Running a round

In the game folder, start Claude and type:

> /pick

Claude will:

1. **Propose the boards** for this round as a short list. Check it's asking about things your child can judge by
   looking. Say OK, or ask for changes.
2. **Draw them**, check them, and look at a contact sheet of every option.
3. **Give you the picker.** It's one of these, depending on your setup:
   - **A Claude link** (an "artifact"). Open it on the tablet while signed in to **your** Claude account. It's private
     to you. Picks save as your child taps, and Claude can read them straight away.
   - **A local address**, like `http://192.168.1.20:8765`. Open it on a tablet on the same Wi-Fi. Picks save to a
     file in your game folder. No accounts needed.
   - **A page to open directly**, as a last resort. When your child's done, tap **Copy picks** at the bottom and
     paste the text to Claude.

## Your job while they pick

- **Hand them the tablet and step back a bit.** Read options aloud if they want, but let them tap.
- **Don't steer.** If they ask "which one do you like?", turn it round: "Which one is more *your* game?"
- **Help with notes.** If they'd rather talk than type, type what they say, word for word.
- **Let them change their mind.** That's built in. The last tap counts.

When they're done, tell Claude:

> Picks are in.

## Notes: the most important part

The note box under every board is where some of the best ideas come from. In Gun Flower:

- "1A with a hand-drawn vibe" turned a choice of logos into polishing Clara's own drawing.
- "C, but every gun is the colour of the flower" became a rule for every weapon in the game.
- "all of them" on the portal arches meant the plaza used every design.

Claude reads every note. If a note could mean two things, it stops and asks you to ask your child, and it offers the
two readings. ("All of them" could mean "use every design, one each" or "combine them into one".) Ask, write down the
answer, and Claude records it in the spec so nobody has to ask again.

If your child skips a board, Claude asks whether they want to finish it or leave it. It never fills a gap itself.

## What you get back

In `design/rounds/<round>/`:

- `PICKS.md`: what was picked, in plain words, with every note quoted exactly.
- `picks.json`: the raw picks (the record of what your child chose).

In `design/specs/`:

- `<round>.md`: the build spec. It starts with a table of the picks and notes in your child's words, then the exact
  details for each thing, how each note was read, and anything that couldn't be built yet.

Claude can also make an **"approved" page** that shows only your child's picks. It's a lovely thing to show them:
"that's your game!"

## Rounds: when to pick again

You don't decide everything at once. Each round is short, and each one comes from playing:

| Round | What it covers | When |
|---|---|---|
| 1 | The look of the core game: the world, the player, the thing you collect, where you make things, what you make, what you use it on | After dreaming |
| 2 | Content: bad guys, bosses, places to explore | When they've played the core loop and want more |
| 3 onwards | Features: pets, vehicles, rewards, a garden, a map… | Whenever playtesting turns up a "can it have…?" |

Gun Flower had three rounds in one day: the core look (8 boards), a boss and its bad guys for each world, then 14
boards of new features. See [`examples/gun-flower/`](../examples/gun-flower/).

## If it goes wrong

| Problem | Fix |
|---|---|
| The page says picks are kept on this screen only | It couldn't reach the artifact database or the local server. Your child can keep picking; you tap **Copy picks** at the end and paste them to Claude |
| The Claude link asks you to sign in | Sign in to your own Claude account on the tablet, or use the local address instead |
| The local address doesn't load on the tablet | Check the tablet is on the same Wi-Fi as the computer, and that Claude's picker server is still running |
| Your child hates all three options | Great feedback. Tell Claude what they said ("none of them, I want it to be a cat"), and it draws a new board |
| Two options look nearly the same | Tell Claude. A board should offer three real alternatives |

**Next:** [4. Build it](04-build-it.md).
