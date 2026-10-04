# The parent's guide

This guide walks you through building a Roblox game **with** your child, one phase at a time. You'll work as a team
of three:

- **Your child** is the creative director. They dream the game up, choose how everything looks, play it and say
  what to change.
- **You** are the guide and the scribe. You set things up, ask the questions, write down their answers, keep
  things safe, and do the grown-up jobs like publishing.
- **Claude** (Claude Code) is the builder. It draws the options your child chooses from, writes the code, tests it,
  and explains what it did.

One rule sits above all the others: **your child decides.** Everything visible in the game should trace back to
something they said or picked. When you're not sure what they meant, ask them. Don't guess, and don't let Claude
guess either.

> This kit grew out of **Gun Flower**, a real Roblox game that Clara H. designed and her dad built with Claude Code in
> about a day. Her story is in [`examples/gun-flower/`](../examples/gun-flower/). You'll see her picks and notes
> quoted throughout, because they show how a child's words turn into a game.

## The team, in one table

| | Your child | You | Claude |
|---|---|---|---|
| **Does** | Dreams, picks, plays, gives feedback, names things | Sets up, asks, writes down, checks, publishes | Draws options, builds, tests, explains |
| **Owns** | Every creative choice | Accounts, safety, money (there shouldn't be any), publishing | The code and its tests |
| **Never** | Has to type, install or read code | Overrules a pick because it's harder to build | Picks for your child, or swaps a pick for an easier one |

If something your child picked is hard to build, Claude should make a simple placeholder and keep their pick on the
list. It shouldn't quietly swap in something easier. Tell them it's coming. That's what real studios do.

## The loop

The game grows in rounds. Each round starts from something your child said, and ends with them playing the result.

```text
        ┌──────────────┐
        │  1. Get ready │  (parent, once)
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │  2. Dream it  │  kid talks, parent writes  →  SPEC.md
        └──────┬───────┘
               ▼
   ┌──▶ ┌──────────────┐
   │    │  3. Pick it   │  kid taps A / B / C        →  picks → specs
   │    └──────┬───────┘
   │           ▼
   │    ┌──────────────┐
   │    │  4. Build it  │  Claude builds, parent watches
   │    └──────┬───────┘
   │           ▼
   │    ┌──────────────┐
   └─── │  5. Play it   │  kid plays, parent captures feedback
        └──────┬───────┘
               ▼  (when you're both happy)
        ┌──────────────┐
        │  6. Share it  │  parent only
        └──────────────┘

   7. Keep it safe: the parent's job, at every step
```

## The phases at a glance

| Phase | Who leads | What you end up with | Chapter | Skill |
|---|---|---|---|---|
| 1. Get ready | Parent | Studio, the tools, Claude Code and a game folder, all working | [01-get-ready.md](01-get-ready.md) | none |
| 2. Dream it | Kid (parent writes) | `SPEC.md`, the game in your child's words | [02-dream-it.md](02-dream-it.md) | `/dream` |
| 3. Pick it | Kid | Their picks, and the specs Claude writes from them | [03-pick-it.md](03-pick-it.md) | `/pick` |
| 4. Build it | Claude (parent supervises) | A playable game, tested | [04-build-it.md](04-build-it.md) | `/build` |
| 5. Play it | Kid (parent captures) | Feedback that becomes the next round | [05-play-it.md](05-play-it.md) | `/playtest` |
| 6. Share it | Parent | The game on Roblox, for family and friends | [06-share-it.md](06-share-it.md) | `/publish` |
| 7. Keep it safe | Parent, throughout | A kid-safe game and a kid-safe process | [07-keep-it-safe.md](07-keep-it-safe.md) | `/safety-check` |

There's also an optional chapter for later: [Going faster with several agents](advanced-multi-agent.md). You don't
need it. One Claude session is plenty for a family game.

---

## Phase 1: Get ready (parent, once)

**Goal:** everything installed, one practice run done, and a game folder ready before your child sits down. Setup is
the boring part, so do it without them.

- **Kid:** nothing yet. Maybe ask them to start thinking about what game they'd make.
- **Parent:** install Roblox Studio, the toolchain (Rokit, which fetches Rojo, Selene, StyLua and Lune) and Claude
  Code. Turn on Studio's built-in MCP server so Claude can playtest. Create the game folder from the template and
  check the starter game plays. Sort out accounts: **your account owns the game**, and your child plays on their own.
- **Claude:** helps with setup if you get stuck. Ask it to check the toolchain and run the tests.

**You're done when** the starter game plays in Studio, `lune run tests/run` passes, and Claude can see Studio.

---

## Phase 2: Dream it (kid leads, parent writes it down)

**Goal:** a `SPEC.md` that describes the game in your child's own words.

- **Kid:** talks. What's the game about? What do you do in it? What's the funniest thing that could happen? What's
  scary, and how scary is OK? They can draw too.
- **Parent:** asks the questions and writes down the answers, **in their words**. "Scary, not too much, top hats on
  them" is a better spec than "moderately threatening enemies". A voice memo works well: record the chat, then hand
  Claude the transcript.
- **Claude:** runs the `/dream` interview with you, or turns your notes or transcript into `SPEC.md`. It keeps the
  child's phrases as quotes, fills gaps with sensible defaults (marked as such), and lists what's still undecided as
  things to pick in phase 3.

**Ask your kid:**

- "If your friend played your game for one minute, what would they do?"
- "What do you collect? What do you make with it? What do you use it on?"
- "Who are the bad guys? What happens when you beat one?"
- "Where does it happen? What colour is it?"
- "What's one thing that would make you laugh?"

**You're done when** your child hears `SPEC.md` read back and says "yes, that's my game".

---

## Phase 3: Pick it (the kid chooses)

**Goal:** every visible part of the game chosen by your child, and written down as a spec Claude can build from.

This is the heart of the kit. Claude draws **three options, A, B and C,** for each part of the game (the world, the
hero, the bad guys, the main item…) in the game's real style, so what your child picks is what gets built. You open
the picker page on a tablet. Your child taps a card, can change their mind, and writes notes in the box under each
board. Then Claude reads the picks back and turns them into exact specs: colours, shapes and behaviour.

- **Kid:** taps their favourite for each board, or "tap any" where it lets them pick several. Writes or says notes.
  Their notes count: Clara's "all of them" changed a whole area of Gun Flower.
- **Parent:** opens the picker, reads the options aloud if needed, types notes for them if they'd rather talk, and
  doesn't steer. If they ask "which one do you like?", turn it back: "which one's more *your game*?"
- **Claude:** runs `/pick`. It draws the boards, builds the page, reads the picks, and writes the specs. If a note is
  ambiguous, it asks you to ask your child instead of guessing.

**Rounds.** The first round covers the look of the core game. Later rounds come from playtesting: content (bosses,
bad guys, places), then features (pets, vehicles, rewards…). Each round is triggered by something your child said
while playing.

**You're done when** every board has a pick and Claude has written the spec. You can read it back to your child to
check it.

---

## Phase 4: Build it (Claude builds, parent supervises)

**Goal:** a playable game that does what the spec says, and tests that prove it.

- **Kid:** has a break! Building takes a while. Some kids like watching; most prefer coming back to play.
- **Parent:** tells Claude what to build next (from the spec), watches what it's doing, says no to anything that
  doesn't match a pick, and checks that tests pass before calling something done.
- **Claude:** runs `/build`. It starts from the template's playable loop and changes it to match the spec. It works
  contracts-first (it decides names, events and data before code), keeps the server in charge, puts content in data
  tables, writes tests, and playtests in Studio through the MCP before saying a feature works.

**You're done when** the tests pass, a Studio playtest shows it working, and you've played it yourself for a minute.

---

## Phase 5: Play it and tell us (kid plays, parent captures)

**Goal:** your child plays, and their reactions become the next round.

- **Kid:** plays. Says what's fun, what's boring, what's broken, and what they want next.
- **Parent:** watches more than you talk, and writes down what they say (word for word if you can), what they do
  (where they get stuck, what they keep going back to) and anything that worries you.
- **Claude:** runs `/playtest`. It turns your notes into a list: bugs to fix now, tweaks (too hard, too slow), and
  new ideas. The new ideas become the boards for the next `/pick` round.

**Ask your kid:**

- "What was the best bit?"
- "What was boring, or too hard?"
- "If you could add one thing, what would it be?"
- "Is anything the wrong colour, the wrong size or the wrong speed?"

**You're done when** you have a short list, and your child has chosen what comes next. Then go back to phase 3.

---

## Phase 6: Share it (parent only)

**Goal:** the game on Roblox, so family and friends can play it.

- **Kid:** chooses the name, writes or dictates the description, picks the screenshots, and decides who to invite.
- **Parent:** publishes from **your** account, fills in the Maturity & Compliance questionnaire honestly, sets the
  audience, gives the game permission to use its audio, uploads the thumbnails, and checks the Error Report after
  every publish.
- **Claude:** runs `/publish`. It goes through the checklist with you, gets the build ready, and can publish through
  Open Cloud. Your API key stays in your computer's keychain and never goes in a file.

Roblox's rules for who can play changed a lot in 2025 and 2026. **As of October 2026**, a new public game reaches only
age-checked players aged 16+ and your Trusted Friends until it passes Roblox's Kids & Select evaluation. That's fine
for a family game. The chapter explains what each setting means.

**You're done when** your child has played the published game on their own account, on their own device.

---

## Phase 7: Keep it safe (parent, throughout)

These hold for every phase, not just at the end:

- **Content:** cartoon, not gore. Scary only where your child chose it, and signposted so players can opt in.
- **Text:** no free text players can type, unless it goes through Roblox's `TextService` filtering. Pick names from
  lists.
- **Money:** no purchases.
- **Recordings:** voice memos and family recordings stay on your computer. They don't go in the game, the repo or
  anywhere public.
- **Credit:** credit your child the way you're comfortable with, such as a first name and initial ("Clara H."), not a
  full name, school or age.
- **Accounts:** your child never owns the game, and never handles API keys.

Claude runs `/safety-check` before each publish, and whenever you ask. It reads the spec and the code against these
rules and tells you what it finds.

---

## Pacing it with a child

- **Short sessions work best.** Dream for 20 minutes. Pick for 10–15 minutes. Play for 15–20 minutes. Claude builds in
  between, while your child does something else.
- **Let them see progress quickly.** The template is already playable, so they can run around in "their" game on day
  one, even before it looks like their game.
- **Stop while it's still fun.** You can always pick up a round tomorrow. Everything is saved in the game folder.
- **Celebrate the picks.** When something they chose turns up in the game, show them: "that's your B!"

## When to stop and ask your child

Claude should stop and ask (through you) whenever:

- a note could mean two things ("all of them": all options together, or one of each in different places?),
- the spec and a pick disagree,
- something they picked can't be built as drawn, and there's a choice of how to get close,
- something would change how the game feels (harder, scarier, slower).

Write their answer into the spec, so the next session doesn't ask again.
