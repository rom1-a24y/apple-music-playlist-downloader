"""
Apple Music Playlist Downloader – command line (no web interface).
Run:  python cli.py <apple-music-playlist-url> [output_dir] [positions]
  positions: optional, e.g. "1,3,6-7" to download only those tracks.
Used by the GitHub Actions workflow so the download can be launched from a phone.
"""

import queue
import sys
import threading
from pathlib import Path

from app import download_worker, jobs


def parse_positions(text: str) -> set[int]:
    result = set()
    for part in text.replace(" ", ",").split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            result.update(range(int(a), int(b) + 1))
        elif part.strip():
            result.add(int(part))
    return result


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python cli.py <url> [output_dir] [positions]")
        return 1
    url = sys.argv[1].strip()
    output_base = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "downloads"
    only = parse_positions(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].strip() else None

    jobs["cli"] = queue.Queue()
    threading.Thread(target=download_worker, args=("cli", url, output_base, only), daemon=True).start()

    exit_code = 0
    while (msg := jobs["cli"].get()) is not None:
        t = msg["type"]
        if t == "log":
            print(msg["message"], flush=True)
        elif t == "error":
            print(f"ERREUR : {msg['message']}", flush=True)
            exit_code = 1
        elif t == "ready":
            n = len(only) if only else len(msg["tracks"])
            print(f"Playlist « {msg['playlist_name']} » : {n} titre(s) à télécharger", flush=True)
        elif t == "track_done":
            src = f" [{msg['source']}]" if msg.get("source") else ""
            print(f"[{msg['position']:02d}/{msg['total']}] {msg['status']:7} "
                  f"{msg['title']} - {msg['artist']}{src}", flush=True)
            for err in msg.get("errors", []):
                print(f"           {err}", flush=True)
        elif t == "finished":
            print(f"\nTerminé : {msg['success']}/{msg['total']} titres dans {msg['folder']}")
            for f in msg["failed"]:
                print(f"  échec : {f['position']:02d} - {f['title']} - {f['artist']}")
            if msg["success"] == 0:
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
