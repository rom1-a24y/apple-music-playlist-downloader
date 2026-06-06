"""
Apple Music Playlist Downloader – Web Interface
Run:  python app.py
Then open  http://localhost:5000  in your browser.
"""

import json
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, Response, render_template, request

app = Flask(__name__)

# ── active download jobs: job_id -> Queue ──────────────────────────────────
jobs: dict[str, queue.Queue] = {}


# ── ffmpeg detection ────────────────────────────────────────────────────────

def find_ffmpeg() -> str | None:
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        if r.returncode == 0:
            return "ffmpeg"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    winget = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    if winget.exists():
        for exe in winget.glob("**/ffmpeg.exe"):
            return str(exe)
    return None


# ── Apple Music scraping ─────────────────────────────────────────────────────
# Playwright runs in a dedicated subprocess (scrape_helper.py) to avoid any
# asyncio/threading conflict with Flask's server.

SCRAPER = Path(__file__).parent / "scrape_helper.py"


def scrape_playlist(url: str) -> tuple[str, list[dict]]:
    """Return (playlist_name, tracks).  Each track: {position, title, artist}."""
    result = subprocess.run(
        [sys.executable, str(SCRAPER), url],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )
    if result.returncode != 0 and not result.stdout.strip():
        raise RuntimeError(result.stderr.strip() or "scrape_helper a échoué sans message.")

    data = json.loads(result.stdout.strip())
    if not data.get("ok"):
        raise RuntimeError(data.get("error", "Erreur inconnue."))

    return data["name"], data["tracks"]


# ── file helpers ─────────────────────────────────────────────────────────────

def sanitize(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return re.sub(r'\s+', " ", name).strip()


# ── download worker ───────────────────────────────────────────────────────────

def download_worker(job_id: str, url: str, output_base: Path):
    q = jobs[job_id]

    def emit(event_type: str, **kwargs):
        q.put({"type": event_type, **kwargs})

    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        emit("error", message="ffmpeg introuvable. Installez-le avec : winget install --id Gyan.FFmpeg")
        q.put(None)
        return

    emit("log", message="Récupération de la playlist…")
    try:
        playlist_name, tracks = scrape_playlist(url)
    except Exception as e:
        emit("error", message=f"Impossible de lire la playlist : {e}")
        q.put(None)
        return

    if not tracks:
        emit("error", message="Aucun titre trouvé. Vérifiez que la playlist est publique.")
        q.put(None)
        return

    safe_name = sanitize(playlist_name) or "playlist"
    output_dir = output_base / safe_name
    output_dir.mkdir(parents=True, exist_ok=True)

    emit("ready", playlist_name=playlist_name, folder=str(output_dir), tracks=tracks)

    success, failed = 0, []
    total = len(tracks)

    for track in tracks:
        pos = track["position"]
        title = track["title"]
        artist = track["artist"]
        safe_title = sanitize(title)
        safe_artist = sanitize(artist)
        stem = f"{pos:02d} - {safe_title} - {safe_artist}" if safe_artist else f"{pos:02d} - {safe_title}"
        output_mp3 = output_dir / f"{stem}.mp3"

        if output_mp3.exists():
            emit("track_done", position=pos, total=total, title=title, artist=artist, status="skipped")
            success += 1
            continue

        emit("track_start", position=pos, total=total, title=title, artist=artist)

        query = f"{artist} {title}".strip()
        template = str(output_dir / f"{stem}.%(ext)s")
        cmd = [
            sys.executable, "-m", "yt_dlp",
            f"ytsearch1:{query}",
            "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0",
            "--output", template,
            "--no-playlist", "--quiet", "--no-warnings", "--no-progress",
        ]
        if ffmpeg_path != "ffmpeg":
            cmd += ["--ffmpeg-location", str(Path(ffmpeg_path).parent)]

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode == 0 and output_mp3.exists():
                emit("track_done", position=pos, total=total, title=title, artist=artist, status="ok")
                success += 1
            else:
                emit("track_done", position=pos, total=total, title=title, artist=artist, status="failed")
                failed.append(track)
        except subprocess.TimeoutExpired:
            emit("track_done", position=pos, total=total, title=title, artist=artist, status="failed")
            failed.append(track)

        time.sleep(0.8)

    emit("finished", success=success, total=total, failed=failed, folder=str(output_dir))
    q.put(None)  # sentinel – stream ends


# ── Flask routes ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def start_download():
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return {"error": "URL manquante"}, 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = queue.Queue()

    output_base = Path(__file__).parent / "downloads"
    t = threading.Thread(
        target=download_worker,
        args=(job_id, url, output_base),
        daemon=True,
    )
    t.start()
    return {"job_id": job_id}


@app.route("/stream/<job_id>")
def stream(job_id):
    q = jobs.get(job_id)
    if not q:
        return "Job not found", 404

    def generate():
        while True:
            msg = q.get()
            if msg is None:
                yield "data: __END__\n\n"
                break
            yield f"data: {json.dumps(msg)}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})



if __name__ == "__main__":
    import socket
    # Kill any leftover process on port 5000 before starting
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", 5000)) == 0:
            print("WARNING: port 5000 already in use – trying to free it…")
            import subprocess as _sp, sys as _sys
            _sp.run(
                ["powershell", "-Command",
                 "Get-NetTCPConnection -LocalPort 5000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"],
                capture_output=True
            )
            import time as _t; _t.sleep(1)

    print("Ouvre http://localhost:5000 dans ton navigateur")
    app.run(debug=False, threaded=True, port=5000, use_reloader=False)
