# MelodyMine

Download music from Bilibili, YouTube, and Spotify URLs with automatic search, audio conversion, metadata cleanup, and cross-platform dependency setup.

MelodyMine can be used as a standalone CLI or as a file-based skill for AI assistants such as WorkBuddy, OpenClaw, and Hermes.

## Features

- Bilibili for Chinese music queries, using direct WBI search plus `yt-dlp`.
- YouTube for English and international music queries.
- Spotify URL downloads through spotDL.
- Automatic setup for Python packages and ffmpeg fallback via `imageio-ffmpeg`.
- Metadata cleanup with title, artist, album, cover, and `Artist - Title` renaming.
- Proxy and cookies support for restricted networks or YouTube bot checks.

## Quick Start

From the repository or skill root:

```bash
python scripts/music_helper.py setup
python scripts/music_helper.py download "周杰伦 稻香"
python scripts/music_helper.py download "The Weeknd Blinding Lights"
```

The only hard prerequisite is Python 3.10+. `setup` installs the Python packages MelodyMine needs.

## Common Commands

Download a Chinese song. Auto mode prefers Bilibili:

```bash
python scripts/music_helper.py download "周杰伦 稻香"
```

Download an English song. Auto mode prefers YouTube:

```bash
python scripts/music_helper.py download "The Weeknd Blinding Lights"
```

Download from a Spotify URL:

```bash
python scripts/music_helper.py download "https://open.spotify.com/track/..."
```

Search without downloading:

```bash
python scripts/music_helper.py search "周杰伦 稻香"
python scripts/music_helper.py search "The Weeknd" --platform youtube
```

Force a platform:

```bash
python scripts/music_helper.py download "周杰伦 稻香" --platform bilibili
python scripts/music_helper.py download "The Weeknd Blinding Lights" --platform youtube
```

Choose format, bitrate, output folder, or search result:

```bash
python scripts/music_helper.py download "周杰伦 稻香" --format flac --bitrate 320K
python scripts/music_helper.py download "稻香" --index 2
python scripts/music_helper.py download "Artist Song" --output "D:\Music"
```

Use a proxy for YouTube when direct access fails:

```bash
python scripts/music_helper.py download "The Weeknd Blinding Lights" --proxy socks5://HOST:PORT
```

Use cookies when YouTube asks for sign-in or bot confirmation:

```bash
python scripts/music_helper.py download "Artist Song" --cookies "D:\path\cookies.txt"
```

Check dependencies:

```bash
python scripts/music_helper.py check
```

## CLI Options

```text
python scripts/music_helper.py download "query" [options]

Options:
  --platform {auto,bilibili,youtube}  Default: auto
  --format {mp3,flac,m4a,opus,wav,vorbis}
  --output PATH
  --proxy URL                         e.g. socks5://host:port
  --cookies PATH                      cookies.txt for YouTube checks
  --bitrate RATE                      e.g. 320K
  --index N                           1-based search result index
  --no-thumbnail
  --no-metadata
```

## Platform Routing

| Input | Default Route | Notes |
| --- | --- | --- |
| Chinese query | Bilibili | No proxy expected. Falls back to YouTube if needed. |
| English or non-Chinese query | YouTube | Try direct first; add proxy after network failure. |
| Spotify URL | spotDL | Auto-installs spotDL on first use if possible. |

## Advanced Spotify Operations

Use `scripts/spotify_helper.py` for playlist sync, metadata-only saves, URL resolution, or metadata updates:

```bash
python scripts/spotify_helper.py sync "https://open.spotify.com/playlist/..." --save-file playlist.spotdl
python scripts/spotify_helper.py save "https://open.spotify.com/album/..." --save-file album.spotdl
python scripts/spotify_helper.py url "Artist - Song"
python scripts/spotify_helper.py meta "D:\Music\song.mp3"
```

See `references/usage.md` for spotDL option details and `references/config.md` for spotDL configuration fields.

## Install As An AI Skill

Copy this folder to your assistant's skills directory:

| Platform | Example path |
| --- | --- |
| WorkBuddy | `~/.workbuddy/skills/melodymine/` |
| OpenClaw | `~/.openclaw/skills/melodymine/` |
| Hermes | `~/.hermes/skills/melodymine/` |
| Custom | Any directory your assistant scans for file-based skills |

Then restart the assistant and ask naturally:

```text
下载周杰伦的稻香
Download Blinding Lights by The Weeknd
下载这个 https://open.spotify.com/track/...
```

The assistant should read `SKILL.md`, run setup if needed, execute the download command, and report the saved path.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| No Python found | Install Python 3.10+ from python.org, then rerun setup. |
| Bilibili `412 Precondition Failed` | Retry after a few seconds; the helper already retries once. |
| YouTube timeout | Retry with `--proxy socks5://HOST:PORT` if you have a proxy. |
| YouTube asks for sign-in or bot confirmation | Export YouTube cookies to cookies.txt and pass `--cookies PATH`. |
| Spotify `KeyError: 'uri'` | Search by song name instead of Spotify URL, or use `spotify_helper.py --use-official-api` when appropriate. |
| Metadata is wrong | Retry with a more exact `Artist Song` query or add `--no-metadata`. |

## File Structure

```text
MelodyMine/
├── SKILL.md
├── README.md
├── scripts/
│   ├── music_helper.py       # Main setup/search/download helper
│   ├── spotify_helper.py     # Advanced spotDL operations
│   └── requirements.txt
└── references/
    ├── usage.md              # spotDL CLI reference
    └── config.md             # spotDL config reference
```

## License

MIT. See `LICENSE`.
