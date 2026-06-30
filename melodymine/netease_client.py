#!/usr/bin/env python3
"""NetEase Cloud Music API client — search + song detail, stdlib only."""

import json
import sys
import urllib.request
import urllib.error
import urllib.parse

from melodymine.melodymine_common import BILI_UA as UA


def search(query, limit=3, timeout=10):
    """Search NetEase for songs by query string.

    Returns list of dicts: {title, artist, album, duration, pic_url}
    or empty list on failure.
    """
    data = urllib.parse.urlencode({"s": query, "type": 1, "limit": limit, "offset": 0}).encode()
    req = urllib.request.Request(
        "https://music.163.com/api/search/get",
        data=data,
    )
    req.add_header("User-Agent", UA)
    req.add_header("Referer", "https://music.163.com")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []

    if body.get("code") != 200:
        return []

    results = []
    for song in body.get("result", {}).get("songs", []):
        artists = ", ".join(a["name"] for a in song.get("artists", []))
        album = song.get("album", {})
        results.append({
            "title": song.get("name", ""),
            "artist": artists,
            "album": album.get("name", ""),
            "duration": song.get("duration", 0),
            "pic_url": album.get("picUrl", ""),
        })
    return results


def detail(song_id, timeout=10):
    """Get song detail by NetEase song ID.

    Returns dict: {title, artist, album} or None on failure.
    """
    data = urllib.parse.urlencode({"ids": f"[{song_id}]", "limit": 1, "offset": 0}).encode()
    req = urllib.request.Request(
        "https://music.163.com/api/song/detail/",
        data=data,
    )
    req.add_header("User-Agent", UA)
    req.add_header("Referer", "https://music.163.com")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    if body.get("code") != 200 or not body.get("songs"):
        return None

    song = body["songs"][0]
    artists = ", ".join(a["name"] for a in song.get("artists", []))
    return {
        "title": song.get("name", ""),
        "artist": artists,
        "album": song.get("album", {}).get("name", ""),
    }


def playlist_detail(playlist_id, timeout=15):
    """Get NetEase playlist detail + track list.

    Returns dict: {title, creator, track_count, tracks: [{id, title, artist, album}]}
    or None on failure.
    """
    req = urllib.request.Request(
        f"https://music.163.com/api/playlist/detail?id={playlist_id}",
    )
    req.add_header("User-Agent", UA)
    req.add_header("Referer", "https://music.163.com")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    if body.get("code") != 200 or not body.get("result"):
        return None

    pl = body["result"]
    tracks = []
    for t in pl.get("tracks", []):
        artists = ", ".join(a["name"] for a in t.get("artists", []))
        album = t.get("al", {}) if isinstance(t.get("al"), dict) else t.get("album", {})
        tracks.append({
            "id": str(t["id"]),
            "title": t.get("name", ""),
            "artist": artists,
            "album": album.get("name", "") if isinstance(album, dict) else "",
        })

    creator = pl.get("creator", {})
    return {
        "platform": "netease",
        "type": "playlist",
        "id": str(playlist_id),
        "title": pl.get("name", ""),
        "creator": creator.get("nickname", ""),
        "description": pl.get("description", "")[:200],
        "cover": pl.get("coverImgUrl", ""),
        "track_count": pl.get("trackCount", 0),
        "play_count": pl.get("playCount", 0),
        "tracks": tracks,
    }


def album_detail(album_id, timeout=15):
    """Get NetEase album detail + track list.

    Returns dict: {title, artist, track_count, tracks: [{id, title, artist, album}]}
    or None on failure.
    """
    req = urllib.request.Request(
        f"https://music.163.com/api/album/{album_id}",
    )
    req.add_header("User-Agent", UA)
    req.add_header("Referer", "https://music.163.com")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    if body.get("code") != 200 or not body.get("album"):
        return None

    al = body["album"]
    artist_name = al.get("artist", {}).get("name", "") if isinstance(al.get("artist"), dict) else ""
    tracks = []
    for t in al.get("songs", []):
        artists = ", ".join(a["name"] for a in t.get("artists", []))
        tracks.append({
            "id": str(t["id"]),
            "title": t.get("name", ""),
            "artist": artists,
            "album": al.get("name", ""),
        })

    return {
        "platform": "netease",
        "type": "album",
        "id": str(album_id),
        "title": al.get("name", ""),
        "creator": artist_name,
        "description": al.get("description", "")[:200] if al.get("description") else "",
        "cover": al.get("picUrl", ""),
        "track_count": al.get("size", 0),
        "play_count": 0,
        "tracks": tracks,
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "search" and len(sys.argv) >= 3:
        q = sys.argv[2]
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        print(json.dumps(search(q, limit=n), ensure_ascii=False))
    elif cmd == "detail" and len(sys.argv) >= 3:
        sid = sys.argv[2]
        print(json.dumps(detail(sid), ensure_ascii=False))
    elif cmd == "playlist" and len(sys.argv) >= 3:
        pid = sys.argv[2]
        print(json.dumps(playlist_detail(pid), ensure_ascii=False))
    elif cmd == "album" and len(sys.argv) >= 3:
        aid = sys.argv[2]
        print(json.dumps(album_detail(aid), ensure_ascii=False))
    else:
        print("Usage: python netease_client.py search <query> [limit]")
        print("       python netease_client.py detail <song_id>")
        print("       python netease_client.py playlist <playlist_id>")
        print("       python netease_client.py album <album_id>")
        sys.exit(1)
