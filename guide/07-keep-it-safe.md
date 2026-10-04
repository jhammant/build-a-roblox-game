# 7. Keep it safe (parent, throughout)

**Who leads:** you, at every step. Claude helps by checking.

This isn't a last step. These rules apply from the first dream to the hundredth publish. Claude's `/safety-check`
skill reads the spec and the code against them and tells you what it finds. Run it before every publish, and any time
you're unsure.

## In the game

**Content**

- Cartoon, not gore. No blood, no realistic injuries. Defeated things pop, cheer up, turn into flowers, float away.
- Scary only where your child chose it, and "scary, not too much". Put scary things in one clearly signposted place,
  and give players a way to opt out (a "No scares" switch, or an arch that says "Spooky! Brave explorers only").
- Respect Roblox's **Reduce Motion** setting for screen shakes and flashes.
- PvP (players fighting each other), if your child wants it, only in an arena players choose to enter.

**Text**

- No free text that other players can see, unless it goes through Roblox's `TextService` filtering. Easier still:
  let players pick names from a list.
- The template switches Roblox's text chat off. Keep it off unless the game needs it.
- Voice chat off (Studio → File → Experience Settings → Communication). It's on by default for new games.

**Money**

- **No purchases.** No game passes, no developer products, no paid random items ("loot boxes", eggs, spins). Say
  "No purchases" in the description.
- If you ever change that, it's a family decision, cosmetic items only, with no pressure tactics (no countdowns, no
  "last chance"), and you retake the questionnaire first.

**Saved data**

- Save game progress only: counts, unlocks, choices from lists. No personal information.
- Roblox sends "right to be forgotten" requests when a player deletes their account. The template's save system has
  an `erase` function for those.

## Around the game

**Recordings and photos**

- Voice memos, family recordings and photos of drawings stay on your computer. They don't go in the game folder, the
  game, or anywhere public. If you'd like your child's voice or drawing *in* the game, that's a deliberate decision:
  a short cheer is low-risk; anything identifying isn't.

**Credit**

- First name and initial, at most: "Designed by Clara H.". Never a full name, username, age or school, in the game, on
  the game page, in thumbnails, or in the "Song Artist" field of uploaded audio.

**Accounts**

- Your account owns the game. Your child never owns it, never handles API keys and never needs your password.
- Turn on 2-Step Verification on your account.
- Link your account to your child's with Roblox's parental controls.

**Keys and secrets**

- Open Cloud API keys live in your computer's keychain (on a Mac) or an environment variable you set for one session,
  never in a file, never in git and never pasted into a chat. Give each key only the permissions it needs, an IP
  allow-list and an expiry date.

**Sharing**

- Testing with your child's friends means a Trusted Friend link between you and someone else's child. Only do it with
  that parent's agreement ([chapter 6](06-share-it.md#testing-in-stages)).
- If you make your game folder public on GitHub, check it first: no names, no recordings, no keys. Claude's
  `/safety-check` includes a scan for these.

## Working with Claude, safely

- **You approve what goes online.** Claude can prepare a publish, but you decide when it happens. The `/publish` skill
  only runs when you ask for it.
- **Check its work.** Claude is very capable and sometimes wrong. Play the game yourself before your child does.
- **Your child talks to you, not to Claude directly**, unless you're sitting with them. Their words go through you
  into the spec. That keeps personal details out and keeps you in the loop.

## The `/safety-check` skill

In the game folder:

> /safety-check

Claude reads `SPEC.md`, the specs in `design/specs/` and the code, and reports, in plain words:

- content that could be scarier, gorier or more grown-up than your child chose,
- free text that isn't filtered, chat or voice settings, and anything that could let strangers contact players,
- purchases, paid random items or pressure tactics,
- personal data being saved, logged or shown,
- names, recordings, photos, account ids or keys in the folder or its git history,
- the questionnaire answers the game probably needs, so you can check yours still match.

It tells you what to change; it doesn't publish anything or change settings itself.
