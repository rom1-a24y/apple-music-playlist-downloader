"""
Standalone scraper – called as a subprocess by app.py.
Prints a JSON object to stdout:
  {"ok": true,  "name": "...", "tracks": [...]}
  {"ok": false, "error": "..."}
"""

import json
import re
import sys

import requests
from playwright.sync_api import sync_playwright


def main(url: str):
    # 1. Load the page in headless Chromium, grab the dev token
    dev_token = None
    playlist_name = "playlist"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_response(r):
            nonlocal dev_token
            if "fetch-proxy.html" in r.url and "devToken=" in r.url:
                m = re.search(r"devToken=([A-Za-z0-9._-]+)", r.url)
                if m:
                    dev_token = m.group(1)

        page.on("response", on_response)
        page.goto(url, wait_until="networkidle", timeout=40_000)

        raw_title = page.title()
        name = re.sub(r"\s*[–-]\s*Apple[\xa0 ]Music.*$", "", raw_title).strip()
        name = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", name).strip()
        if name:
            playlist_name = name

        browser.close()

    if not dev_token:
        print(json.dumps({"ok": False, "error": "Token Apple Music introuvable dans la page."}))
        return

    # 2. Parse storefront + playlist ID from URL
    m = re.search(r"music\.apple\.com/([a-z]{2})/playlist/[^/]+/(pl\.[^?#\s]+)", url)
    if not m:
        print(json.dumps({"ok": False, "error": "URL Apple Music non reconnue."}))
        return
    storefront, playlist_id = m.group(1), m.group(2)

    # 3. Call Apple Music API
    headers = {
        "Authorization": f"Bearer {dev_token}",
        "Origin": "https://music.apple.com",
    }
    api_url = (
        f"https://amp-api.music.apple.com/v1/catalog/{storefront}"
        f"/playlists/{playlist_id}?include=tracks&fields[songs]=name,artistName"
    )

    all_tracks = []
    position = 1

    while api_url:
        resp = requests.get(api_url, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        rel_tracks = (
            data.get("data", [{}])[0]
            .get("relationships", {})
            .get("tracks", {})
        )
        items    = rel_tracks.get("data", [])
        next_rel = rel_tracks.get("next")

        for t in items:
            attrs  = t.get("attributes", {}) if isinstance(t, dict) else {}
            title  = attrs.get("name", "").strip()
            artist = attrs.get("artistName", "").strip()
            if title:
                all_tracks.append({"position": position, "title": title, "artist": artist})
                position += 1

        api_url = f"https://amp-api.music.apple.com{next_rel}" if next_rel else None

    print(json.dumps({"ok": True, "name": playlist_name, "tracks": all_tracks}))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "URL manquante"}))
        sys.exit(1)
    try:
        main(sys.argv[1])
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
