# Publishing new versions of your game

`publish.py` puts a new version of your game live on Roblox without clicking through Studio. It builds the place
from `src/` with Rojo, then sends it to Roblox's Open Cloud, the official way for tools to talk to Roblox.

You publish the **first** version yourself, from Studio (**File → Publish to Roblox**), because that's what creates
the game and its page. This tool does every version after that, and keeps a note of each one in `history.json`.

Everything about Roblox's screens and rules below is **as of October 2026**. Roblox changes its menus now and then,
so if a screen doesn't match, trust the screen.

## 1. Tell the tool which game it is (once)

After your first publish from Studio, find three numbers in Creator Hub (create.roblox.com):

| What | Where to find it |
|---|---|
| **Universe ID** (the game) | **Creations** → hover over your game → **⋯** → **Copy Universe ID** |
| **Place ID** (the start place) | Your game → **Places** → click the start place. It's the number in the address bar: `…/places/<id>/configure` |
| **Your user id** | Open your Roblox profile. It's the number in the address: `roblox.com/users/<id>/profile` |

Then, from the game folder:

```bash
python3 tools/publish/publish.py setup --universe <universe id> --place <place id> --user <your user id>
```

That writes `tools/roblox.json`. It holds only these ids, never the key, so it's fine to commit.
`roblox.example.json` shows what's in it.

## 2. Make an Open Cloud API key (once)

An API key is a password that lets a tool act for your account on Roblox. Make one that can do as little as
possible.

1. In Creator Hub, open **Open Cloud → API Keys** and click **Create API Key**.
2. **Name** it after your game, for example `spark-garden-tools`.
3. Under **Access Permissions**:
   - add **universe-places** (Place Publishing), pick **your game**, and tick **Write**. This is what `publish.py`
     needs.
   - if you'll upload sounds and pictures too, also add the **Assets API** with **Read** and **Write**
     (`tools/upload/README.md`).
4. Under **Security → Accepted IP Addresses**, add your home's current public address as a single address, like
   `203.0.113.7/32`. You can find it with `curl -s https://checkip.amazonaws.com`. Home addresses change now and
   then, so if publishing starts failing with 401 or 403, check this first.
5. Set an **Expiration** about a month away. Keys also stop working on their own after 60 days without use.
6. Click **Save & Generate Key**, then **Copy Key to Clipboard**. Roblox only shows it once.

## 3. Keep the key safe

The key lives only on your computer. Never put it in a file in the game folder, never commit it, and never paste it
into a chat, **including Claude**. Claude never needs to see it: it runs the script, and the script reads the key
itself.

**On a Mac**, store it in the Keychain. The command asks you to paste the key, so it never ends up in your terminal
history. Use the service name `setup` printed (it's also `keychainService` in `tools/roblox.json`):

```bash
security add-generic-password -a "$USER" -s <keychainService> -w
pbcopy < /dev/null   # clear the clipboard afterwards
```

The first time the tool reads it, macOS may ask whether `security` can use it. Click **Allow**. To replace the key
later, run the same command with `-U` added. To remove it: `security delete-generic-password -s <keychainService>`.

**On Windows or Linux** (or for a one-off on a Mac), set it for this terminal session only. It's gone when you close
the window:

```powershell
# PowerShell 7
$env:ROBLOX_API_KEY = Read-Host "Paste the key" -MaskInput
```

```bash
# bash or zsh
read -rs ROBLOX_API_KEY && export ROBLOX_API_KEY
```

If both are set, `ROBLOX_API_KEY` wins. The tool only ever sends the key to Roblox over HTTPS. It never prints,
logs or saves it.

## 4. Publish

**Close any Studio window that has the game open first.** While Studio has it open (Team Create), Roblox refuses new
versions with "409 Server is busy".

```bash
python3 tools/publish/publish.py --dry-run            # build it and show what would happen; sends nothing
python3 tools/publish/publish.py --note "new wand"    # build it, ask you, then publish
python3 tools/publish/publish.py history              # every version published from here
```

The new version is live for new servers straight away. Players already in a server keep the old version until they
rejoin.

## 5. After every publish

- **Check the Error Report** a few minutes later: Creator Hub → your game → **Monitoring → Error Report**. It's the
  only window into errors on players' phones and tablets. Studio can't show you those.
- **Sounds silent for players but fine in Studio?** That's asset permissions. See `tools/upload/README.md`.
- **Added something new** (scarier bits, chat, anything to buy)? Retake the Maturity & Compliance questionnaire
  (your game → **Configure → Questionnaire**) so the game's rating stays honest.

## If something goes wrong

| What you see | What to do |
|---|---|
| `409` "Server is busy" | Close the Studio window that has this game open, then try again |
| `401` or `403` | The key: check it has Place Publishing **Write** for this game, hasn't expired, and allows your current IP address |
| `404` | Check the ids in `tools/roblox.json` against Creator Hub |
| "Can't find Rojo" | Run `rokit install` in the game folder |
| "Not running in a terminal" | Add `--yes`: the tool won't guess when it can't ask you |
| "There's no tools/roblox.json yet" | Do step 1 |

A game owned by a **group** works too: add `--group <group id>` to `setup`. Roblox retired group-owned API keys in
January 2026, so use a key from your own account, and make sure your group role can edit the game.

## Tests

The tests run against a pretend Roblox on your own computer, so they never publish anything:

```bash
python3 -m unittest discover -s tools/publish/tests
```
