---
name: safety-check
description: Check a kid's Roblox game against the kit's safety rules before publishing, or whenever the parent asks. Reads the spec, the design specs and the code for content, text and chat, purchases, saved personal data, and names, recordings, account ids or keys in the folder and its git history, then reports in plain words what to change. Never publishes or changes settings. Use for "/safety-check", "is this safe to publish", "check it's kid-safe", "privacy check", or before any /publish.
---

# /safety-check: is it still a kid-safe game?

You're checking a game a parent is building with their child. Report what you find in plain words, sorted by how
much it matters. Don't fix anything without asking, and never publish or change Roblox settings.

Read first: `SPEC.md`, every file in `design/specs/`, `ARCHITECTURE.md`, `CLAUDE.md`, then the code in `src/`.

## 1. Content: does it match what the child chose?

- **Gore and injury:** search `src/` and the specs for blood, gore, wounds, corpses, realistic weapons. Defeated
  things should pop, cheer up or float away, not die realistically.
- **Scary:** list every scary element (jump-scares, chases, dark areas, creepy sounds). Check each one is something
  the child picked (quote the spec line) and that scary things are in an opt-in, signposted place, with a way to turn
  scares off. Check screen shakes and flashes respect `GuiService.ReducedMotionEnabled`.
- **Player against player:** any PvP must be in an area players choose to enter.
- **Anything the child didn't pick:** flag visible features with no spec line behind them.

## 2. Text, chat and contact

- **Free text:** search for `TextBox`, `TextService`, `FilterStringAsync`, `GetNonChatStringForBroadcastAsync`. Any
  text one player types that another can see must go through `TextService` filtering. Prefer pick-from-a-list.
- **Text chat:** check `Config.CHAT_ENABLED` (or whatever switches `TextChatService` off) and say whether chat is on.
- **Voice chat:** it's a Studio setting, not code. Remind the parent to check it's off (File → Experience Settings →
  Communication).
- **Anything else that lets strangers contact players** (friend requests, trading, gifting, notes left in the world).

## 3. Money

Search for `MarketplaceService`, `PromptPurchase`, `PromptProductPurchase`, `PromptGamePassPurchase`, `ProcessReceipt`,
developer products and game passes, and any random reward that costs Robux. The kit's default is **no purchases**. If
any exist, say so plainly and remind the parent to retake the Maturity questionnaire.

## 4. Saved and logged data

- Read the save system's schema. It should hold game progress only (counts, unlocks, choices from lists), nothing
  personal, and support erasing a player's data.
- Search for `print`/`warn` calls or analytics events that include player names or user ids. Counts are fine.

## 5. Names, recordings, ids and keys in the folder

Search the working tree **and the full git history** (`git log -p --all`, `git grep` across revisions) for:

- the child's full name (ask the parent what to search for; don't guess it), their school, their age,
- audio or video recordings and photos that aren't the game's own assets (look at any `.m4a`, `.mp3`, `.wav`,
  `.mov`, `.mp4`, `.jpg`, `.heic` outside the game's asset folders),
- Roblox usernames, user ids, and API key-shaped strings,
- emails, home addresses, private hostnames,
- anything that looks like a secret: `ROBLOX_API_KEY=`, `x-api-key`, long random tokens, `.env` files.

If something is only in git history, say so: removing it means rewriting history, which the parent should decide on.

## 6. The questionnaire

From what the game actually contains, draft the Maturity & Compliance answers (violence, blood, fear, crude humour,
gambling, language, romance, social hangout, free-form creation, paid random items, trading, AI interaction) with a
one-line reason each, and the rating it probably produces. Using AI to build the game doesn't count as AI
interaction. Remind the parent that these are as of October 2026 and to check the live questionnaire.

## Report

```markdown
## Safety check: <date>

**Summary:** <one line: ready to publish / fix these first>

### Fix before publishing
- <issue> (<file:line>) → <what to change>

### Check with your child
- <anything where the game might be scarier or different from what they chose>

### Settings to check in Studio or Creator Hub
- <voice chat, audience, asset privacy, audio permissions>

### Questionnaire (draft)
| Question | Answer | Why |
|---|---|---|

### All clear
- <the checks that passed, briefly>
```

Then ask the parent which fixes they'd like you to make.
