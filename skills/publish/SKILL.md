---
name: publish
description: Walk a parent through publishing their kid's Roblox game, and publish new versions through Open Cloud once it exists. Runs the safety check, the build checks and the settings checklist, records the game's ids, and publishes only when the parent says so. Use for "/publish", "publish the game", "put the new version live", "share it with family".
disable-model-invocation: true
---

# /publish: the parent's job, with Claude's help

Publishing puts the game where other people can play it, so **the parent decides every step**. You prepare, check
and explain. You never publish, upload or change a Roblox setting without the parent saying yes to that specific
action, in this conversation.

Read `guide/06-share-it.md` from the kit if it's available, or rely on the facts below. They're **as of October
2026**: Roblox changes its rules often, so if the parent says a screen looks different, trust the screen.

## Never

- Never ask for, read out, or accept an API key in the chat. If the parent pastes one, tell them to revoke it in
  Creator Hub and make a new one. The tools read the key themselves, from the macOS Keychain or the
  `ROBLOX_API_KEY` environment variable.
- Never make the child the owner, or suggest putting their name, age, username or school on the game page.
- Never mark a game Public or change its audience yourself. That's a Creator Hub setting the parent changes.

## 1. Is it ready?

1. Run `/safety-check` (or follow its steps) and show the parent the result. Stop if anything is in "Fix before
   publishing".
2. Run the checks, and build to a scratch file (never over a place file with hand-built work in it):

   ```bash
   lune run tests/run
   selene src
   stylua --check src tests
   rojo build -o /tmp/publish-check.rbxlx
   ```

3. Check `git status` is clean, so the published version matches a commit.

## 2. First publish (in Studio)

If `tools/roblox.json` doesn't exist, the game hasn't been published yet. The first publish happens in Studio,
because that's what creates the game:

1. Open the place in Studio with Rojo connected (`rojo serve`, then Plugins → Rojo → Connect), so Studio has the
   latest code.
2. **File → Publish to Roblox.** Creator: the parent's own account. Devices: Computer, Phone, Tablet. Click
   **Create**. It starts **Private** (editors only).
3. Ask the parent for the three ids (`tools/publish/README.md` says where each one is in Creator Hub), then record
   them:

   ```bash
   python3 tools/publish/publish.py setup --universe <universe id> --place <place id> --user <their user id>
   ```

   `tools/roblox.json` holds ids only, no secrets, and is fine to commit.

## 3. The settings checklist

Go through these with the parent, one at a time, and tick them off in your reply:

- [ ] 2-Step Verification on, and the age check done on their account (needed for anything beyond Private).
- [ ] **Asset Privacy** on before uploading any images or meshes (Creator Hub → their name → Settings → Advanced).
- [ ] Voice chat **off** (Studio → File → Experience Settings → Communication). It's on by default.
- [ ] Text chat: the template turns it off in code (`Config.CHAT_ENABLED`). Confirm it's still off.
- [ ] Server size about 8; avatar R15 with Player Choice.
- [ ] The **Maturity & Compliance questionnaire** answered honestly. Offer the draft answers from `/safety-check`.
- [ ] The name, description, icon (512 × 512) and thumbnails (1920 × 1080) chosen by the child. "No purchases" in
      the description if true. Credit as a first name and initial at most.
- [ ] Their child added as an editor (Studio → Collaborate), so they can play the private game on their own account.

## 4. Sounds and images

If the game has its own audio or images in `assets/`, upload them with the tools (parent's say-so each time):

```bash
python3 tools/upload/upload.py plan      # checks every file, sends nothing
python3 tools/upload/upload.py upload    # asks, then uploads and writes src/shared/AssetIds.luau
python3 tools/upload/upload.py status --refresh
```

Then remind the parent about the trap Gun Flower hit: **each restricted audio asset may need the game granted Use
permission** (Creator Hub → the asset → Permissions → Experiences), even though they own both. Studio plays it anyway,
so only players' devices show the problem.

## 5. Later publishes (Open Cloud)

Once `tools/roblox.json` exists, new versions can go out from the command line:

```bash
python3 tools/publish/publish.py --dry-run               # builds and says what would happen; sends nothing
python3 tools/publish/publish.py --note "<what changed>" # builds, asks, publishes
```

- Show the parent the dry run first, and publish only when they say yes.
- **Close any Studio window that has the game open first.** Open Cloud answers "409 Server is busy" otherwise.
- The API key needs place-publishing permission only for this. `tools/publish/README.md` explains how to make one
  with an IP allow-list and an expiry, and how to store it.

## 6. After every publish

- Ask the parent to play it on the child's device and account.
- Remind them to open Creator Hub → the game → **Monitoring → Error Report** after a few minutes of real play. It's
  the only place errors on players' devices show up.
- Record what was published (the tool keeps `tools/publish/history.json`) and commit.

## Sharing beyond the family (explain, don't do)

As of October 2026: Private is editors only. Limited (playtesters or friends) and Public need the owner's age check
and the questionnaire, and even then reach only age-checked players aged 16+ and the owner's Trusted Friends until
the game passes Roblox's Kids & Select evaluation (ID verification, 2-Step Verification, two months of Premium or a
refundable 1,000 Robux fee, and 250 highly engaged 16+ players within 60 days). Testing with the child's friends means
a Trusted Friend link with someone else's child, so only with that parent's agreement. Lay out the options; the
parent chooses.
