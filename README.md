# Build a Roblox game, together

**Your kid designs it. Claude builds it. You keep it safe.**

A free, open-source kit that walks a parent through building a real Roblox game **with** their child, using
[Claude Code](https://code.claude.com). It's written for parents, and it works as a team of three:

| | Does | Never |
|---|---|---|
| **Your child** | Dreams the game up, picks how everything looks, plays it, says what's next | Has to type, install anything or read code |
| **You** | Set things up, ask the questions, write down the answers, keep it safe, publish | Overrule a pick because it's harder to build |
| **Claude** | Draws the options, writes the code, tests it, explains what it did | Picks for your child, or swaps a pick for something easier |

The one rule above all others: **your child decides.** Everything you can see in the finished game traces back to
something they said or tapped.

## How it works

1. **[Get ready](guide/01-get-ready.md)** (parent, once). Install Roblox Studio, the build tools and Claude Code, and
   make a game folder from the starter template. The starter is already a tiny playable game.
2. **[Dream it](guide/02-dream-it.md)** (kid talks, parent writes). `/dream` turns your child's ideas into a spec, in
   their own words.
3. **[Pick it](guide/03-pick-it.md)** (kid chooses). `/pick` draws three options for each part of the game. Your child
   taps their favourites on a tablet, with a note box on every board. Their picks become exact build specs.
4. **[Build it](guide/04-build-it.md)** (Claude builds, parent supervises). `/build` builds from the specs, with tests
   and real playtests in Roblox Studio.
5. **[Play it](guide/05-play-it.md)** (kid plays, parent captures). `/playtest` turns what they say into fixes and the
   next round of picks.
6. **[Share it](guide/06-share-it.md)** (parent only). `/publish` walks you through Roblox's publishing rules (as of
   October 2026) and puts new versions live.
7. **[Keep it safe](guide/07-keep-it-safe.md)** (parent, throughout). `/safety-check` before every publish.

Then go round again: pick, build, play, pick. **Start with [the parent's guide](guide/README.md).**

## Quick start

After installing Roblox Studio, [Rokit](https://github.com/rojo-rbx/rokit) and Claude Code
([chapter 1](guide/01-get-ready.md) has every command):

```bash
git clone https://github.com/jhammant/build-a-roblox-game.git
cd build-a-roblox-game
python3 new-game.py ~/Games/our-game

cd ~/Games/our-game
rokit install
rojo plugin install
rojo build -o Game.rbxlx     # open this in Roblox Studio
rojo serve                   # then Plugins → Rojo → Connect, and press Play
```

Then, in another terminal in the same folder, start Claude Code and dream:

```bash
claude
```

```text
/dream
```

## What's in the kit

| Folder | What it is |
|---|---|
| [`guide/`](guide/) | The parent's guide: one chapter per phase, with who does what and questions to ask your child |
| [`template/`](template/) | The starter game: collect Sparks, craft a Wand, cheer up the Gloomies. Set up so Claude can build safely: contracts first, the server in charge, data-driven content, Lune tests and a Studio playtest runner |
| [`skills/`](skills/) | The Claude Code skills: `/dream`, `/pick`, `/build`, `/playtest`, `/publish`, `/safety-check` |
| [`picker/`](picker/) | The tap-to-pick page: one JSON file per board, three options per choice, picks saved to a Claude artifact or your own computer |
| [`tools/`](tools/) | Publishing and asset uploads through Roblox Open Cloud, with the API key kept in your keychain |
| [`examples/gun-flower/`](examples/gun-flower/) | The worked example: how Clara H. designed Gun Flower, pick by pick |
| [`site/`](site/) | The landing page |
| [`new-game.py`](new-game.py) | Makes a game folder from all of the above |

## Where this came from

The kit grew out of **Gun Flower**, a real Roblox game that Clara H. designed and her dad built with Claude Code in
about a day. She described it out loud, picked every look from boards of three options on an iPad, and her notes
("scary, not too much, top hats on them", "C, but every gun is the colour of the flower", "all of them") shaped the
whole game. [Read her story](examples/gun-flower/).

## Safety, in short

Your account owns the game; your child plays on their own. Cartoon, not gore. Scary only where your child chose it.
No purchases. Chat off, and no free text without Roblox's filtering. Family recordings stay at home. API keys stay in
your keychain. [Chapter 7](guide/07-keep-it-safe.md) has the details.

## Running the kit's own tests

```bash
python3 -m unittest discover -s picker/tests
python3 -m unittest discover -s tools/publish/tests
python3 -m unittest discover -s tools/upload/tests
python3 -m unittest discover -s tests
cd template && lune run tests/run && selene src && stylua --check src tests
```

## Licence and trademarks

The code is MIT ([LICENSE](LICENSE)). The guide and the art are CC BY 4.0 ([LICENSE-DOCS.md](LICENSE-DOCS.md)): share and adapt them freely, with credit.

This is an independent project. It isn't made, endorsed or sponsored by Roblox Corporation or Anthropic. Roblox is a
trademark of Roblox Corporation.
