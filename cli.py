"""
Apple Music Playlist Downloader – command line (no web interface).
Run:  python cli.py <apple-music-playlist-url> [output_dir]
Used by the GitHub Actions workflow so the download can be launched from a phone.
"""

import queue
import sys
from pathlib import Path

from app import download_worker, jobs


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python cli.py <url> [output_dir]")
        return 1
    url = sys.argv[1].strip()
    output_base = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "downloads"

    jobs["cli"] = queue.Queue()
    # Runs synchronously; events are queued then printed below
    download_worker("cli", url, output_base)

    exit_code = 0
    while (msg := jobs["cli"].get()) is not None:
        t = msg["type"]
        if t == "log":
            print(msg["message"])
        elif t == "error":
            print(f"ERREUR : {msg['message']}")
            exit_code = 1
        elif t == "ready":
            print(f"Playlist « {msg['playlist_name']} » : {len(msg['tracks'])} titres")
        elif t == "track_done":
            print(f"[{msg['position']:02d}/{msg['total']}] {msg['status']:7} {msg['title']} - {msg['artist']}")
        elif t == "finished":
            print(f"\nTerminé : {msg['success']}/{msg['total']} titres dans {msg['folder']}")
            for f in msg["failed"]:
                print(f"  échec : {f['position']:02d} - {f['title']} - {f['artist']}")
            if msg["success"] == 0:
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
