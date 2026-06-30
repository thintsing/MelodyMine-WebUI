"""
MelodyMine Web UI — FastAPI Backend
====================================
Provides REST API + WebSocket for the MelodyMine Web UI.

Start:  python server.py          (development)
        uvicorn server:app        (alternative)

API:
  GET    /api/health                    — system readiness check
  POST   /api/download                  — start a download task
  POST   /api/download/{task}/cancel    — cancel a running task
  POST   /api/playlist/info             — resolve playlist URL → track list
  POST   /api/playlist/download         — start a playlist batch download
  WS     /ws/progress/{task}            — real-time progress stream
  GET    /api/downloads                 — list downloaded files + stats
  DELETE /api/downloads/records         — clear all download records (keeps files)
  DELETE /api/downloads/records/{name}  — remove one record (keeps file)
  POST   /api/config                    — save persistent config
  GET    /api/config                    — read persistent config
  GET    /api/config/env                — read env vars for Soulseek creds, proxy, output
  GET    /api/files/{name}              — serve/download a file
  POST   /api/open-folder               — open download dir in file manager
"""

import logging
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn

from melodymine import music_helper
from melodymine.config_manager import (
    DOWNLOADS_DIR, RECORDS_FILE,
    _load_config, _save_config,
    _load_hidden_set, _save_hidden_set,
    _record_lock, get_soulseek_creds,
)
from melodymine.progress import ProgressManager, DownloadCancelled

# ── Audio extensions recognised by the file list ─────────────────────

_AUDIO_EXTS = frozenset({".mp3", ".flac", ".m4a", ".opus", ".ogg", ".wav", ".webm"})

# ── App setup ─────────────────────────────────────────────────────────

_HERE = Path(__file__).resolve().parent

app = FastAPI(
    title="MelodyMine Web UI",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

static_dir = _HERE / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

pm = ProgressManager()


# ── Download Runner ───────────────────────────────────────────────────

def _build_download_params(form_data: dict, output: str = "") -> dict:
    """Reduce copy-paste between single and playlist download params."""
    # Prefer stored config → form value → default
    out_dir = output or ""
    if not out_dir:
        cfg = _load_config()
        out_dir = cfg.get("output_dir", "") or ""
    if not out_dir:
        out_dir = str(DOWNLOADS_DIR)
    return {
        "query": form_data.get("query", "").strip(),
        "platform": form_data.get("platform", "auto"),
        "format": form_data.get("format", "mp3"),
        "output": out_dir,
        "proxy": form_data.get("proxy", ""),
        "bitrate": form_data.get("bitrate", "320k"),
        "index": form_data.get("index", 1),
        "embed_thumbnail": form_data.get("embed_thumbnail", True),
        "no_metadata": form_data.get("no_metadata", False),
        "cookies": form_data.get("cookies", ""),
        "quick": form_data.get("quick", False),
    }


def run_download_in_thread(task_id: str, params: dict) -> None:
    """Execute cmd_download() in a background thread, capturing progress."""
    pm.emit(task_id, "status", "starting")

    try:
        slsk_user, slsk_pass = get_soulseek_creds()

        if pm.is_cancelled(task_id):
            pm.set_result(task_id, {"ok": False, "error": "Cancelled by user"})
            return

        with pm.capture_print(task_id):
            result = music_helper.cmd_download(
                query=params["query"],
                platform=params.get("platform", "auto"),
                fmt=params.get("format", "mp3"),
                output=params.get("output", str(DOWNLOADS_DIR)),
                proxy=params.get("proxy") or None,
                bitrate=params.get("bitrate") or None,
                index=params.get("index", 1),
                embed_thumbnail=params.get("embed_thumbnail", True),
                no_metadata=params.get("no_metadata", False),
                cookies=params.get("cookies") or None,
                quick=params.get("quick", False),
                json_output=True,
                slsk_user=slsk_user,
                slsk_pass=slsk_pass,
            )

        # Post-download: verify file integrity
        if isinstance(result, dict) and result.get("ok"):
            result = music_helper._finalize_download_result(result, params["output"])

        pm.set_result(task_id, result)

    except DownloadCancelled:
        pm.emit(task_id, "status", "cancelled")
        pm.emit(task_id, "log", "[CANCELLED] Download cancelled by user")
        pm.set_result(task_id, {"ok": False, "error": "Cancelled by user"})
    except Exception as e:
        import traceback
        pm.emit(task_id, "log", f"[ERROR] {e}")
        pm.emit(task_id, "log", traceback.format_exc())
        pm.set_result(task_id, {"ok": False, "error": str(e)})


# ── API Routes ────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the Web UI."""
    html_path = static_dir / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return HTMLResponse("<h1>MelodyMine Web UI</h1><p>Frontend not found.</p>", status_code=404)


@app.get("/api/health")
async def health():
    """Check system dependencies."""
    try:
        from melodymine.melodymine_common import find_ffmpeg, check_module
        ffmpeg = find_ffmpeg(None)
        py = sys.executable or "python"

        status = {
            "ffmpeg": bool(ffmpeg),
            "ffmpeg_path": ffmpeg or "",
            "python": sys.version,
            "os": sys.platform,
            "cwd": str(_HERE),
        }
        try:
            status["yt_dlp"] = check_module(py, "yt-dlp")
        except Exception:
            status["yt_dlp"] = False

        return {"ok": True, "status": status}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/download")
async def start_download(
    query: str = Form(...),
    fmt: str = Form("mp3"),
    output: str = Form(""),
    proxy: str = Form(""),
    bitrate: str = Form("320k"),
    index: int = Form(0),
    embed_thumbnail: bool = Form(True),
    no_metadata: bool = Form(False),
    cookies: str = Form(""),
    quick: bool = Form(False),
    platform: str = Form(""),
):
    """Start a download. Returns a task_id for progress tracking."""
    if not query.strip():
        raise HTTPException(400, "Query is required")

    task_id = pm.create_task()

    params = _build_download_params({
        "query": query, "format": fmt, "output": output,
        "proxy": proxy, "bitrate": bitrate, "index": index,
        "embed_thumbnail": embed_thumbnail, "no_metadata": no_metadata,
        "cookies": cookies, "quick": quick, "platform": platform,
    }, output)

    t = threading.Thread(target=run_download_in_thread, args=(task_id, params), daemon=True)
    pm.register_thread(task_id, t)
    t.start()

    return {"ok": True, "task_id": task_id}


@app.post("/api/download/{task_id}/cancel")
async def cancel_download(task_id: str):
    """Cancel a running download task."""
    if pm.cancel(task_id):
        return {"ok": True, "message": f"Task {task_id} cancelled"}
    return {"ok": False, "message": "Task not found or already completed"}


# ── Playlist API ──────────────────────────────────────────────────────

def run_playlist_download_in_thread(task_id: str, params: dict) -> None:
    """Execute cmd_playlist_download() in a background thread."""
    pm.emit(task_id, "status", "resolving")

    try:
        url = params["url"]
        fmt = params.get("format", "mp3")
        output = params.get("output", str(DOWNLOADS_DIR))
        proxy = params.get("proxy", "")
        bitrate = params.get("bitrate", "320k")
        embed_thumbnail = params.get("embed_thumbnail", True)
        no_metadata = params.get("no_metadata", False)
        cookies = params.get("cookies", "")
        quick = params.get("quick", False)
        start_from = params.get("start_from", 0)
        max_tracks = params.get("max_tracks", 0)

        slsk_user, slsk_pass = get_soulseek_creds()

        # Step 1: Resolve playlist
        pm.emit(task_id, "status", "resolving")
        playlist_info = music_helper.resolve_playlist(url)
        if playlist_info is None:
            pm.set_result(task_id, {"ok": False, "error": "Could not resolve playlist"})
            return
        pm.emit(task_id, "playlist_info", playlist_info)

        if pm.is_cancelled(task_id):
            pm.set_result(task_id, {"ok": False, "error": "Cancelled by user"})
            return

        # Step 2: Download tracks one by one
        tracks = playlist_info.get("tracks", [])
        if start_from:
            tracks = tracks[start_from:]
        if max_tracks and max_tracks > 0:
            tracks = tracks[:max_tracks]

        total = len(tracks)
        pm.emit(task_id, "playlist_progress", {
            "current": 0, "total": total, "status": "downloading",
        })

        success_count = 0

        for i, track in enumerate(tracks):
            if pm.is_cancelled(task_id):
                pm.emit(task_id, "log", "[Playlist] Cancelled by user")
                break

            num = i + 1
            query = track.get("query", track.get("title", ""))
            pm.emit(task_id, "playlist_progress", {
                "current": num, "total": total,
                "track": track, "status": "downloading",
            })

            with pm.capture_print(task_id):
                try:
                    result = music_helper.cmd_download(
                        query=query, platform="auto", fmt=fmt,
                        output=output, proxy=proxy or None,
                        bitrate=bitrate or None, index=1,
                        embed_thumbnail=embed_thumbnail,
                        no_metadata=no_metadata,
                        cookies=cookies or None,
                        json_output=False,
                        slsk_user=slsk_user, slsk_pass=slsk_pass,
                        quick=quick,
                    )
                except DownloadCancelled:
                    result = {"ok": False, "error": "Cancelled by user"}
                except Exception as e:
                    result = {"ok": False, "error": str(e)}

            if isinstance(result, dict) and result.get("ok"):
                success_count += 1
                pm.emit(task_id, "playlist_track_result", {
                    "track": track, "ok": True,
                    "file": result.get("file", ""),
                    "current": num, "total": total,
                })
            else:
                err = result.get("error", "unknown") if isinstance(result, dict) else str(result)
                pm.emit(task_id, "playlist_track_result", {
                    "track": track, "ok": False,
                    "error": err,
                    "current": num, "total": total,
                })

        pm.set_result(task_id, {
            "ok": True,
            "playlist_title": playlist_info.get("title", ""),
            "platform": playlist_info.get("platform", ""),
            "total": total,
            "succeeded": success_count,
            "failed": total - success_count,
        })

    except Exception as e:
        import traceback
        pm.emit(task_id, "log", f"[ERROR] {e}")
        pm.emit(task_id, "log", traceback.format_exc())
        pm.set_result(task_id, {"ok": False, "error": str(e)})


@app.post("/api/playlist/info")
async def playlist_info(url: str = Form(...)):
    """Resolve a playlist/album URL and return track list."""
    try:
        info = music_helper.resolve_playlist(url)
        if info is None:
            return {"ok": False, "error": "Could not resolve playlist"}
        return {"ok": True, "playlist": info}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/playlist/download")
async def start_playlist_download(
    url: str = Form(...),
    fmt: str = Form("mp3"),
    output: str = Form(""),
    proxy: str = Form(""),
    bitrate: str = Form("320k"),
    embed_thumbnail: bool = Form(True),
    no_metadata: bool = Form(False),
    cookies: str = Form(""),
    quick: bool = Form(False),
    start_from: int = Form(0),
    max_tracks: int = Form(0),
):
    """Start downloading all tracks from a playlist/album URL."""
    if not url.strip():
        raise HTTPException(400, "Playlist URL is required")

    task_id = pm.create_task()

    params = {
        "url": url.strip(),
        "format": fmt,
        "output": output or str(DOWNLOADS_DIR),
        "proxy": proxy, "bitrate": bitrate,
        "embed_thumbnail": embed_thumbnail,
        "no_metadata": no_metadata, "cookies": cookies,
        "quick": quick,
        "start_from": start_from, "max_tracks": max_tracks,
    }

    t = threading.Thread(target=run_playlist_download_in_thread, args=(task_id, params), daemon=True)
    pm.register_thread(task_id, t)
    t.start()

    return {"ok": True, "task_id": task_id}


@app.get("/api/download/{task_id}/result")
async def get_result(task_id: str):
    """Poll for final result (fallback if WebSocket disconnected)."""
    r = pm.get_result(task_id)
    if r is None:
        return {"ok": False, "done": False}
    return {"ok": r.get("ok", False), "done": True, "result": r}


@app.websocket("/ws/progress/{task_id}")
async def ws_progress(ws: WebSocket, task_id: str):
    """Stream download progress as JSON messages."""
    await ws.accept()
    try:
        for msg in pm.iter_progress(task_id, timeout=600):
            await ws.send_json(msg)
            if msg["type"] == "done":
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logging.warning(f"WS error for {task_id}: {e}")
    finally:
        pm.cleanup(task_id)


@app.get("/api/downloads")
async def list_downloads():
    """List downloaded audio files + stats, excluding hidden records."""
    hidden = _load_hidden_set()
    files = []
    total_size = 0
    if DOWNLOADS_DIR.exists():
        for f in sorted(DOWNLOADS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.suffix.lower() in _AUDIO_EXTS:
                if f.name in hidden:
                    continue
                st = f.stat()
                total_size += st.st_size
                files.append({
                    "name": f.name,
                    "size_mb": round(st.st_size / (1024 * 1024), 1),
                    "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                })
    return {
        "ok": True,
        "files": files[:50],
        "total_files": len(files),
        "total_size_mb": round(total_size / (1024 * 1024), 1),
    }


@app.delete("/api/downloads/records")
async def clear_all_records():
    """Clear all download records (hides everything from list — files kept)."""
    with _record_lock:
        hidden = _load_hidden_set()
        if DOWNLOADS_DIR.exists():
            for f in DOWNLOADS_DIR.iterdir():
                if f.suffix.lower() in _AUDIO_EXTS:
                    hidden.add(f.name)
        _save_hidden_set(hidden)
    return {"ok": True, "hidden_count": len(hidden)}


@app.delete("/api/downloads/records/{name:path}")
async def hide_one_record(name: str):
    """Remove a single file from the list (file kept on disk)."""
    with _record_lock:
        hidden = _load_hidden_set()
        hidden.add(name)
        _save_hidden_set(hidden)
    return {"ok": True, "name": name}


@app.get("/api/files/{name:path}")
async def serve_file(name: str):
    """Serve a downloaded file for preview or download."""
    file_path = (DOWNLOADS_DIR / name).resolve()

    if not str(file_path).startswith(str(DOWNLOADS_DIR.resolve())):
        raise HTTPException(403, "Access denied")

    if not file_path.exists():
        raise HTTPException(404, "File not found")

    return FileResponse(str(file_path), filename=name)


@app.post("/api/open-folder")
async def open_folder():
    """Open the download directory in the system file manager."""
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            os.startfile(str(DOWNLOADS_DIR))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(DOWNLOADS_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(DOWNLOADS_DIR)])
        return {"ok": True, "path": str(DOWNLOADS_DIR)}
    except Exception as e:
        return {"ok": False, "error": str(e), "path": str(DOWNLOADS_DIR)}


@app.get("/api/config")
async def get_config():
    """Return stored config (never expose the actual password)."""
    cfg = _load_config()
    return {
        "soulseek_username": cfg.get("soulseek_username", ""),
        "soulseek_password_set": bool(cfg.get("soulseek_password", "")),
        "output_dir": cfg.get("output_dir", ""),
        "proxy": cfg.get("proxy", ""),
    }


@app.post("/api/config")
async def save_config(
    soulseek_username: str = Form(None),
    soulseek_password: str = Form(None),
    output_dir: str = Form(None),
    proxy: str = Form(None),
):
    """Save persistent config. Fields not sent are left unchanged."""
    updates = {}
    if soulseek_username is not None:
        updates["soulseek_username"] = soulseek_username
    if soulseek_password is not None and soulseek_password:
        updates["soulseek_password"] = soulseek_password
    if output_dir is not None:
        updates["output_dir"] = output_dir
    if proxy is not None:
        updates["proxy"] = proxy
    _save_config(updates)
    return {"ok": True}


@app.get("/api/config/env")
async def env_config():
    """Read environment config for the UI settings panel."""
    cfg = _load_config()
    return {
        "slsk_user": bool(os.getenv("SLSK_USERNAME") or cfg.get("soulseek_username")),
        "slsk_pass_set": bool(os.getenv("SLSK_PASSWORD") or cfg.get("soulseek_password")),
        "all_proxy": os.getenv("ALL_PROXY", "") or cfg.get("proxy", ""),
        "http_proxy": os.getenv("HTTP_PROXY", ""),
        "output_dir": os.getenv("MELODYMINE_OUTPUT", "") or cfg.get("output_dir", ""),
        "stored_user": cfg.get("soulseek_username", ""),
        "stored_pass_set": bool(cfg.get("soulseek_password", "")),
        "stored_output": cfg.get("output_dir", ""),
        "stored_proxy": cfg.get("proxy", ""),
    }


# ── Startup ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(" MelodyMine Web UI — starting...")
    print(f"   Open: http://127.0.0.1:8000")
    print(f"   Docs: http://127.0.0.1:8000/docs")
    print(f"   Downloads: {DOWNLOADS_DIR}")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True, log_level="info")
