"""MelodyMine — Multi-platform music download backend.

Provides search and download capabilities across:
  - Bilibili (WBI API)
  - YouTube / YouTube Music
  - Spotify (via spotDL)
  - NetEase Cloud Music
  - Soulseek P2P network

WebUI modules:
  - :mod:`melodymine.config_manager` — persistent config + records
  - :mod:`melodymine.progress` — thread-safe progress queue
"""

from melodymine import music_helper  # noqa: F401
