# MelodyMine WebUI

[English](./README.md) | [简体中文](./README.zh-CN.md)

基于 Web 的音乐搜索与下载工具，支持 Bilibili、YouTube、Spotify、网易云音乐、Soulseek 多平台音源。

## 功能特性

- **搜索下载** — 输入歌曲名/歌手名或粘贴链接即可搜索下载
- **歌单支持** — 粘贴 YouTube / 网易云 / Spotify 歌单/专辑链接，解析曲目列表，批量下载并实时展示进度
- **多平台路由** — 中文搜索自动走 Soulseek → Bilibili → YouTube，英文搜索走 Soulseek → YouTube
- **WebSocket 实时推送** — 浏览器端实时展示下载进度、日志和结果
- **内置播放器** — 下载完成后可直接在界面中试听
- **Soulseek P2P** — 可选通过 Soulseek 网络下载无损 FLAC
- **配置面板** — 在界面中设置 Soulseek 账号、代理和下载目录

## 快速开始

### 环境要求

- Python 3.10+

### 安装运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
python server.py
```

浏览器打开 **http://127.0.0.1:8000** 即可使用。

### 首次配置

首次运行时 MelodyMine 会自动检测并安装缺失工具（yt-dlp、ffmpeg 等）。也可以手动执行：

```bash
python -m melodymine.music_helper setup
```

## 使用方式

### 单曲下载

在搜索框中输入歌曲名或粘贴链接，点击下载：

```
周杰伦 稻香
The Weeknd Blinding Lights
https://www.youtube.com/watch?v=...
https://open.spotify.com/track/...
https://music.163.com/song?id=185809
```

### 歌单 / 专辑下载

粘贴歌单或专辑链接，界面会自动识别并展示曲目列表。点击**下载全部**即可批量下载：

- YouTube 歌单：`https://www.youtube.com/playlist?list=...`
- 网易云歌单：`https://music.163.com/playlist?id=...`
- 网易云专辑：`https://music.163.com/album?id=...`
- Spotify 歌单：`https://open.spotify.com/playlist/...`
- Spotify 专辑：`https://open.spotify.com/album/...`

### 设置面板

右上角齿轮图标进入设置，可配置：

- **Soulseek 账号** — P2P 无损下载所需
- **代理** — SOCKS5/HTTP 代理，用于受限网络环境访问 YouTube
- **下载目录** — 文件保存路径

## 项目结构

```
melodymine-webui/
├── melodymine/               # 后端音乐下载包
│   ├── music_helper.py       # 下载编排核心
│   ├── melodymine_common.py  # 共享基础设施
│   ├── bili_client.py        # B站 WBI API
│   ├── netease_client.py     # 网易云音乐 API
│   ├── soulseek_client.py    # Soulseek P2P
│   ├── ytmusic_client.py     # YouTube Music API
│   ├── spotify_helper.py     # Spotify/spotDL 下载
│   ├── metadata.py           # 多源元数据增强
│   ├── mbrainz_client.py     # MusicBrainz 查询
│   └── cover_client.py       # 封面下载
├── static/                   # 前端 (HTML/CSS/JS)
│   └── index.html
├── server.py                 # FastAPI 后端
├── run.py                    # 启动入口
├── requirements.txt          # Python 依赖
├── LICENSE
└── README.md
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 系统健康检查 |
| POST | `/api/download` | 启动单曲下载 |
| POST | `/api/download/{id}/cancel` | 取消下载任务 |
| POST | `/api/playlist/info` | 解析歌单 URL |
| POST | `/api/playlist/download` | 批量下载歌单 |
| WS | `/ws/progress/{id}` | WebSocket 实时进度 |
| GET | `/api/downloads` | 列出已下载文件 |
| GET/POST | `/api/config` | 读取/保存设置 |
| GET | `/api/files/{name}` | 播放/下载文件 |
| POST | `/api/open-folder` | 打开下载目录 |

## 免责声明

MelodyMine 仅供**个人学习和存档**使用。下载受版权保护的音频文件可能违反当地法律。请勿分发、分享或商用下载的文件。使用者须自行遵守所在地法律法规及各平台服务条款。

## 许可证

MIT，详见 `LICENSE` 文件。
