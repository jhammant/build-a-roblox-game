# 1. Get ready (parent, once)

**Who leads:** you. Do this without your child: it's the boring part, and you want the first thing they see to be a
game that works.

**You'll end up with:** Roblox Studio, the build tools and Claude Code installed, a game folder made from the starter
template, and the starter game running in Studio.

**Time:** about an hour the first time.

> These steps were written and tested on a Mac. Roblox Studio, the build tools and Claude Code all run on Windows too,
> and we note the Windows differences we know about, but the kit hasn't been tested end to end on Windows yet.

## What you need

- A Mac or Windows computer that runs Roblox Studio.
- A **Roblox account for you**. This is the account that will own the game.
- Your child's own Roblox account, for playing. (See [Accounts](#accounts) below.)
- A **Claude** plan that includes Claude Code (Pro, Max, Team or Enterprise; the free plan doesn't).
- A tablet for picking is nice but optional. Any browser works.

## Accounts

Roblox puts the responsibility for a game on whoever owns it: age checks, moderation notices, the questionnaire and
any data-deletion requests. That's an adult's job.

- **Your account owns the game.** Your child never owns it.
- **Your child plays on their own account**, from their own device if they like. Later (in
  [chapter 6](06-share-it.md)) you can add them as an editor so they can play the private game.
- **Link your accounts** with Roblox's parental controls. Since April 2026, a linked parent automatically becomes
  their child's Trusted Friend, which makes testing together much easier.
- **Turn on 2-Step Verification** on your account now. You'll need it to share the game later.

## Install the tools

### 1. Roblox Studio

Download it from the Roblox Creator Hub and sign in with **your** account.

### 2. Rokit (the toolchain manager)

Rokit installs the exact versions of the four tools the game uses: **Rojo** (syncs code files into Studio),
**Selene** (checks the code), **StyLua** (tidies the code) and **Lune** (runs the tests outside Studio).

On a Mac:

```bash
curl -sSf https://raw.githubusercontent.com/rojo-rbx/rokit/main/scripts/install.sh | bash
```

On Windows (PowerShell):

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/rojo-rbx/rokit/main/scripts/install.ps1 | Invoke-Expression
```

Close the terminal and open a new one afterwards.

### 3. Claude Code

On a Mac:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

On Windows (PowerShell):

```powershell
irm https://claude.ai/install.ps1 | iex
```

Run `claude --version` in a new terminal to check it worked. The first time you run `claude`, it opens your browser to
sign in.

### 4. Python 3

The picker and the publishing tools are small Python scripts with no extra packages. Macs with the developer tools
have Python 3 already (`python3 --version`). On Windows, install it from python.org and tick "Add to PATH".

## Make your game folder

Get the kit, then make a folder for your game from the template:

```bash
git clone https://github.com/jhammant/build-a-roblox-game.git
cd build-a-roblox-game
python3 new-game.py ~/Games/our-game
```

That copies the starter game, the Claude skills (`/dream`, `/pick`, `/build`, `/playtest`, `/publish`,
`/safety-check`) and the picker into the new folder, and makes it a git repository so every change can be undone.

Then, in the new folder:

```bash
cd ~/Games/our-game
rokit install
rojo plugin install
```

`rokit install` fetches the pinned tools. The first time, it asks whether you trust each tool: answer yes (they're
the standard Roblox community tools, pinned to exact versions in `rokit.toml`). `rojo plugin install` adds the Rojo
button to Studio.

## See the starter game run

The template is already a tiny playable game called **Spark Garden**: collect Sparks, make a Wand at the Workbench,
and zap the grumpy Gloomies until they cheer up. Your child's picks will turn it into their own game.

1. Build a fresh place file and open it in Studio:

   ```bash
   rojo build -o Game.rbxlx
   open Game.rbxlx
   ```

   (On Windows, double-click `Game.rbxlx` instead of running `open`.)

2. Start syncing the code into Studio. Leave this running in its own terminal:

   ```bash
   rojo serve
   ```

3. In Studio, open the **Plugins** tab, click **Rojo**, then **Connect**.
4. Press **Play**. Walk around, collect three Sparks, go to the Workbench, and zap a Gloomy.

If something doesn't work, that's exactly what Claude is for. Start it in the game folder (next step) and describe
what happened.

## Connect Claude to Studio

Claude can play-test the game for real through Studio's built-in MCP server, which lets it start Play, run code in
the game and take screenshots.

1. In Studio, open **Assistant**, then **… → Manage MCP Servers**, and switch on **Enable Studio as MCP server**.
   (Studio's Assistant settings also have a **Quick connect** list. If Claude Code is in it, switch it on there.)
2. The game folder already has a `.mcp.json` that tells Claude Code where Studio's MCP server is. On Windows, open
   `.mcp.json` and change the command to `cmd.exe /c %LOCALAPPDATA%\Roblox\mcp.bat`, which is where Roblox puts it
   on Windows.
3. Start Claude Code in the game folder and approve the Studio server when it asks:

   ```bash
   claude
   ```

4. Ask it to check everything:

   > Check the setup: run the tests and the linter, and see if you can reach Studio.

You're done when Claude reports the tests pass and it can see Studio.

## Ground rules, before your child joins

Agree these with yourself first, then share the ones that matter with your child:

- **They decide what the game is.** You and Claude help. You won't change their picks.
- **They never type personal information** into the game, the picker or Claude: no full name, school, address or age.
- **Scary stuff only if they want it**, and only "scary, not too much".
- **Claude is a computer program, not a person.** It's very good at building, and it can be wrong. You check its work.
- **You do the grown-up jobs**: accounts, publishing, money (there won't be any) and anything that goes online.

More on all of this in [chapter 7](07-keep-it-safe.md).

**Next:** [2. Dream it](02-dream-it.md).
