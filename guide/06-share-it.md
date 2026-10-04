# 6. Share it (parent only)

**Who leads:** you. Your child chooses the name, the description and the screenshots; you do everything that touches
accounts and settings.

**You'll end up with:** the game published on Roblox, playable by your child on their own account, and by family and
friends when you're ready.

**Time:** an hour for the first publish and settings. Later publishes take a few minutes.

> **Roblox's rules here changed several times in 2025 and 2026.** Everything below is as of **October 2026**,
> checked against Roblox's creator documentation (links at the end). If a screen doesn't match, trust the screen and
> the linked docs.

## Who can play, in one minute

- **Private** means editors only: you, plus your child if you add them as an editor. Playtesters can't join a
  private game.
- **Limited** (playtesters or your Roblox friends) and **Public** both need, first: an account in good standing that
  is at least 2 days old, an **age check** on your account (facial age estimation or ID), and the **Maturity &
  Compliance questionnaire**.
- **Even then**, a new game only reaches **age-checked players aged 16+ and your Trusted Friends**. Children use
  Roblox Kids (ages 5 to 8) or Roblox Select (ages 9 to 15), and a game reaches them only after it passes Roblox's
  **Kids & Select** evaluation. That needs ID verification, 2-Step Verification, either two months of Premium or a
  refundable 1,000 Robux fee, and 250 highly engaged age-checked 16+ players within 60 days.

**What that means for a family game:** playing it with your own child is easy. Playing it with their friends is
possible but takes some setting up (see [stage 3](#testing-in-stages)). Reaching children generally is a big
deliberate step for later, and many family games never take it. That's fine.

## Before the first publish

- [ ] The build is finished and committed, tests pass, and you've played it.
- [ ] `/safety-check` is clean ([chapter 7](07-keep-it-safe.md)).
- [ ] 2-Step Verification is on, and you've done the age check on your account.
- [ ] **Asset Privacy is on**: Creator Hub → your name → **Settings → Advanced → Asset Privacy → "Opt-in to restrict
  assets on creation"**. Without it, images and meshes you upload are **Open Use**, which means anyone can reuse your
  child's art, and that can't be undone. It only applies to uploads made after you switch it on.
- [ ] Your child has chosen the name and helped write the description.

## The first publish (it stays private)

1. Open the game in Studio with Rojo connected, so Studio has the latest code.
2. **File → Publish to Roblox**. Owner: **your account**. Devices: **Computer, Phone and Tablet** (leave console and VR
   off for now).
3. Click **Create**. New games start **Private**.

Then ask Claude:

> /publish

Claude walks you through the settings below, and records the game's ids in the game folder so later updates can be
published from the command line (using an Open Cloud API key kept in your computer's keychain, never in a file).

## Settings to check after the first publish

| Setting | Where | Suggested | Why |
|---|---|---|---|
| Audience | Creator Hub → Configure → Settings → Audience | Private for now | Test before anyone else plays |
| Voice chat | Studio → File → Experience Settings → Communication | Off | It's on by default for new games. A kids' game doesn't need it |
| Text chat | Already off in the template (`default.project.json`, and `Config.CHAT_ENABLED` in code) | Off | Nothing in the game needs chat, and it removes a stranger-contact route |
| Server size | Configure → Places → start place → Access | 8 | Enough for family and friends |
| Avatar | Studio → File → Avatar Settings | R15, Player Choice | Kids like their own avatars |
| Strong language | Audience → Communication Settings | Off (the default) | It's a kids' game |
| Genre | Configure → Settings | Whatever fits | It can only be changed every 3 months |

## The Maturity & Compliance questionnaire

Creator Hub → your game → **Configure → Questionnaire**. Answer honestly for the **most intense thing a player can
meet** in the game. Getting it wrong can get the game's label removed, which makes it unplayable.

For a typical cartoon game made with this kit (silly bad guys, no blood, no chat, no purchases), expect:

- **Violence:** yes, if players zap or fight things, even cartoon things. Usually **Mild** ("unrealistic depictions…
  bodies disappearing the moment their health reaches zero").
- **Fear:** yes if anything is creepy-looking or there are jump-scares. Still **Mild** unless there's realistic gore.
- **Everything else** (blood, crude humour, gambling, strong language, romance, social hangout, free-form user
  creation, paid random items, trading, AI characters players talk to): usually **no**. Using AI to *build* the game
  doesn't count as AI interaction.

That usually comes out as a **Mild** rating, which is allowed for both Roblox Kids and Roblox Select. **Retake the
questionnaire** whenever the game changes in a way it asks about: scarier bad guys, purchases, chat or trading.

## Audio and images: the permission trap

This one caught us out. Sounds you upload are private to your account. Studio plays them fine (it loads them as you),
but players' devices may not: Gun Flower's live game logged "Failed to load sound: User is not authorized to access
Asset" thousands of times, and the iPad had sound effects but no music.

**The fix:** for each restricted audio asset, open it in Creator Hub → **Permissions → Experiences** and grant your
game **Use** permission, even though you own both. Grants can't be undone.

**Check the Error Report after every publish** (Creator Hub → your game → **Monitoring → Error Report**). It's the only
window into errors on players' devices.

## Testing in stages

| Stage | Who can play | You need first | How |
|---|---|---|---|
| 1. Private | You, and your child as an editor | Just publishing | Add your child: Studio → **Collaborate** → find them → **Edit**. You must be Roblox friends. They play from their own device by opening the game link |
| 2. Limited → Playtesters | Age-checked 16+ playtesters, or your Trusted Friends | Your age check and the questionnaire | Studio → Collaborate → add them with **Play**, then Audience → Limited → Playtesters |
| 3. Limited → Friends | Your Roblox friends, with the same 16+ / Trusted Friends limit | Same as stage 2 | Audience → Limited → Friends |
| 4. Public | Age-checked 16+ players and your Trusted Friends, until Kids & Select | Same as stage 2 | Audience → Public. Tick **Exclude from Recommendations** to keep it quiet |

**Your child's friends.** Until the game passes Kids & Select, an under-16 friend can only play if they're **your**
Trusted Friend, and a Trusted Friend request from an under-13 needs their parent's approval. That's a link between you
and someone else's child, so only do it with their parent's agreement. Alternatives: the friend's parent plays with
the child watching, or you wait.

**Team Create across ages.** If your child is an editor, Studio's collaboration rules group people by age, and an
adult and a young child can't edit together unless they're Trusted Friends (automatic once your accounts are linked)
or the child's parental controls allow it. Even if Team Create is blocked, your child keeps Edit permission, so they
can still **play** the private game. If they do join Team Create, they should build and decorate, not edit scripts:
Rojo owns the scripts.

## Later publishes

Every later publish is either **File → Publish to Roblox** in Studio, or:

> /publish

which builds the place from your files and publishes it through Open Cloud. Two gotchas:

- **Close Studio's window for the game first.** Open Cloud refuses to publish ("409 Server is busy") while a Studio
  window has the published game open.
- **Once the game is Limited or Public, every publish has to meet the publishing requirements again.**

## The game page

Let your child choose the name and help write the description. Keep it honest: say what you do in the game, and say
"No purchases" if that's true. Thumbnails are 16:9 (1920 × 1080 is ideal), the icon is a 512 × 512 square, and every
image is moderated. Leave scary moments out of the thumbnails. One more gotcha: Creator Hub's upload progress stalls
when its browser tab is in the background, so keep the tab visible while thumbnails upload.

**Credit your child** the way you're comfortable with. A first name and initial ("Designed by Clara H.") is plenty.
Don't put their full name, username, age or school on the page, in the credits, in the thumbnails, or in the
"Song Artist" field of uploaded music.

## Going public to children (later, if ever)

Kids & Select needs ID verification, 2-Step Verification, two consecutive months of Premium **or** a refundable 1,000
Robux fee, and **250 unique plays by highly engaged, age-checked 16+ players within 60 days**. For most family games,
the 250 players is the real hurdle. It may never happen, and the game can stay a family-and-friends game. Track it
under **Audience → Reach**.

## Sources (Roblox creator docs, read October 2026)

- Publishing, audience and requirements: <https://create.roblox.com/docs/production/publishing/publish-games-and-places>
- Roblox Kids and Select: <https://create.roblox.com/docs/production/publishing/kids-and-select>
- Content maturity and the questionnaire: <https://create.roblox.com/docs/production/promotion/content-maturity>
- Collaboration and Team Create age rules: <https://create.roblox.com/docs/projects/collaboration>
- Asset privacy: <https://create.roblox.com/docs/projects/assets/privacy>
- Audio assets: <https://create.roblox.com/docs/audio/assets>
- Voice chat: <https://create.roblox.com/docs/chat/voice-chat>
- Text chat: <https://create.roblox.com/docs/chat/in-experience-text-chat>
- Icons: <https://create.roblox.com/docs/production/publishing/experience-icons>
- Thumbnails: <https://create.roblox.com/docs/production/publishing/thumbnails>
- Error Report: <https://create.roblox.com/docs/production/analytics/error-report>
- Roblox newsroom, *Expanding Trusted Friends* (April 2026): <https://about.roblox.com/newsroom/2026/04/expanding-trusted-friends>
- Parental controls: <https://about.roblox.com/parental-controls>

**Next:** [7. Keep it safe](07-keep-it-safe.md).
