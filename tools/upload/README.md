# Uploading sounds and pictures

`upload.py` turns the sounds and pictures in `assets/` into Roblox asset ids the game can use, through Roblox's Open
Cloud. It checks every file against Roblox's limits first, uploads only what's new or changed, and writes the ids
into `src/shared/AssetIds.luau`, so the code can say:

```lua
local AssetIds = require(ReplicatedStorage.Shared.AssetIds)
sound.SoundId = AssetIds.Audio.Yay
image.Image = AssetIds.Images.WandIcon
```

Everything about Roblox's screens, limits and rules below is **as of October 2026**. Roblox changes these now and
then, so if something doesn't match, trust the screen.

## Before your first upload

1. **Set up publishing first.** Do steps 1 to 3 in `tools/publish/README.md`: the ids file, an API key, and keeping
   the key safe. For uploads, the key also needs the **Assets API** with **Read** and **Write**.
2. **Turn on Asset Privacy** before uploading any pictures: Creator Hub → your name (top right) → **Settings →
   Advanced → Asset Privacy → Opt-in to restrict assets on creation**. Without it, new pictures are **Open Use**,
   which means anyone can use your child's art in their own games, and that can't be undone. It only applies to
   uploads made after you switch it on.
3. **Only upload what you made**, or have the right to use. And keep family voice recordings at home: if a sound has
   your child's voice in it, it's going on a public platform, so think twice.

## Where files go

| Folder | What | Formats |
|---|---|---|
| `assets/audio/` | Sounds and music | `.ogg`, `.mp3`, `.wav`, `.flac` |
| `assets/images/` | Pictures for the game's screens (icons, buttons, stickers) | `.png`, `.jpg`, `.bmp`, `.tga` |

Each file's name becomes its name in the game, so use letters, digits and `_` only, starting with a letter:
`Yay.ogg`, `WandIcon.png`, `Music_Explore.ogg`. Two files can't share a name in the same folder.

## Plan, upload, check

```bash
python3 tools/upload/upload.py plan              # check every file against the limits; sends nothing
python3 tools/upload/upload.py upload            # shows the list, asks you, then uploads
python3 tools/upload/upload.py status --refresh  # later: has moderation approved them?
```

- `upload` is safe to run again. Anything already uploaded is skipped. An upload Roblox was still processing when
  the tool stopped waiting gets collected next time, not sent twice.
- If you change a file, the next `upload` sends it as a **new** asset (Roblox can't replace sounds or pictures in
  place). The new id goes into `AssetIds.luau`, and the old one is kept in `uploaded.json` under `history`.
- Useful options: `--only Yay,Pop` (just these names), `--limit 5` (at most 5 new files this time), `--yes` (don't
  ask), and `--image-type Decal` (pictures as Decals instead of Images).
- Commit `tools/upload/uploaded.json` and `src/shared/AssetIds.luau`. They hold ids, nothing secret.

## Roblox's limits

| | Limit |
|---|---|
| Any file | 20 MB at most |
| Sounds | Up to 7 minutes, 48 kHz or lower, mono, stereo, 3.0 or 5.1 |
| Pictures | Smaller than 8000 × 8000 pixels |
| New sounds through Open Cloud | 10 a month, or 100 once your account is ID-verified |

If you hit the monthly sound limit, Studio's own importer (**Window → Asset Manager → Import**) has a separate,
larger allowance.

## After uploading sounds

- **Moderation.** Roblox checks every new sound and picture. Until it's approved, only you can hear or see it.
  `status --refresh` shows where each one is.
- **Silent for players, fine in Studio?** Studio plays everything because you're signed in as the owner, but players'
  devices may be refused. Open the sound in Creator Hub → **Permissions → Experiences** and give your game **Use**
  permission, even though you own both. Roblox can't undo this grant, which is fine for your own game.
- **Check the Error Report** after the next publish (your game → **Monitoring → Error Report**). "User is not
  authorized to access Asset" means a sound still needs that permission.

## If something goes wrong

| What you see | What to do |
|---|---|
| `401` or `403` | The key: check it has the Assets API with Read and Write, hasn't expired, and allows your current IP address |
| A file marked `ERROR` in `plan` | The line says what's wrong: rename it, shorten it, or export it again |
| "still processing" | Roblox is busy. Run `upload` again later and it picks up where it left off |
| `FAILED` with a moderation message | Roblox rejected the file. Change it and upload again |

## Tests

The tests run against a pretend Roblox on your own computer, so they never upload anything:

```bash
python3 -m unittest discover -s tools/upload/tests
```
