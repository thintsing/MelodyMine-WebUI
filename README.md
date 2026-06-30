# MelodyMine WebUI

[English](./README.md) | [简体中文](./README.zh-CN.md)

A web-based music search & download tool supporting Bilibili, YouTube, Spotify, NetEase Cloud Music, and Soulseek.

## Features

- **Search & Download** — enter a song/artist name or paste a URL to search and download
- **Playlist Support** — paste YouTube / NetEase / Spotify playlist/album URLs, resolve track lists, and batch download with live progress
- **Multi-platform Routing** — Chinese queries auto-route via Soulseek → Bilibili → YouTube; English queries via Soulseek → YouTube
- **WebSocket Progress** — real-time download progress, logs, and results in the browser
- **Built-in Player** — preview downloaded files directly in the UI
- **Soulseek P2P** — optional lossless FLAC downloads via the Soulseek network
- **Config Panel** — set Soulseek credentials, proxy, and output directory from the UI

## Quick Start

### Prerequisites

- Python 3.10+

### Install & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server
python server.py
```

Open **http://127.0.0.1:8000** in your browser.

### First-time Setup

MelodyMine auto-detects and installs missing tools (yt-dlp, ffmpeg, etc.) on first run. You can also run:

```bash
python -m melodymine.music_helper setup
```

## Usage

### Single Song

Type an artist + song name (or paste a URL) in the search box and click Download:

```
周杰伦 稻香
The Weeknd Blinding Lights
https://www.youtube.com/watch?v=...
https://open.spotify.com/track/...
https://music.163.com/song?id=185809
```

### Playlist / Album

Paste a playlist or album URL. The UI auto-detects it and shows a track list. Click **Download All** to batch download with live progress:

- YouTube playlist: `https://www.youtube.com/playlist?list=...`
- NetEase playlist: `https://music.163.com/playlist?id=...`
- NetEase album: `https://music.163.com/album?id=...`
- Spotify playlist: `https://open.spotify.com/playlist/...`
- Spotify album: `https://open.spotify.com/album/...`

### Settings

The settings panel (gear icon) lets you configure:

- **Soulseek credentials** — required for P2P lossless downloads
- **Proxy** — SOCKS5/HTTP proxy for accessing YouTube in restricted networks
- **Output directory** — where downloaded files are saved

## Project Structure

```
melodymine-webui/
├── melodymine/               # Backend music download package
│   ├── music_helper.py       # Download orchestrator
│   ├── melodymine_common.py  # Shared infrastructure
│   ├── bili_client.py        # Bilibili WBI API client
│   ├── netease_client.py     # NetEase Cloud Music API client
│   ├── soulseek_client.py    # Soulseek P2P client
│   ├── ytmusic_client.py     # YouTube Music API client
│   ├── spotify_helper.py     # Spotify/spotDL pipeline
│   ├── metadata.py           # Multi-source metadata enhancement
│   ├── mbrainz_client.py     # MusicBrainz lookup
│   └── cover_client.py       # Cover art downloader
├── static/                   # Frontend (HTML/CSS/JS)
│   └── index.html
├── server.py                 # FastAPI backend
├── run.py                    # Launcher
├── requirements.txt          # Python dependencies
├── LICENSE
├── README.md
└── README.zh-CN.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | System health check |
| POST | `/api/download` | Start a single download |
| POST | `/api/download/{id}/cancel` | Cancel a download task |
| POST | `/api/playlist/info` | Resolve playlist URL |
| POST | `/api/playlist/download` | Batch download playlist |
| WS | `/ws/progress/{id}` | WebSocket progress stream |
| GET | `/api/downloads` | List downloaded files |
| GET/POST | `/api/config` | Read/save settings |
| GET | `/api/files/{name}` | Serve/download a file |
| POST | `/api/open-folder` | Open download folder |

## Disclaimer

MelodyMine is for **personal learning and archival use only**. Downloading copyrighted audio may be illegal in your jurisdiction. Do not distribute, share, or monetize downloaded files. You are solely responsible for complying with local laws and platform terms of service.

## License

MIT. See `LICENSE`.
