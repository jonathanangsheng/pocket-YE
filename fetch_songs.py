"""Fetch Ye's song list (titles, albums, Genius URLs) from the Genius API.

Writes songs.json. Lyrics are not returned by the API; this is only the catalog.

Usage: python fetch_songs.py [--artist "Ye"] [--out songs.json]
Requires GENIUS_ACCESS_TOKEN in the environment or .env.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
API = "https://api.genius.com"
# Skip alternate versions; the catalog should list each song once.
SKIP = re.compile(r"\b(remix|demo|snippet|unreleased|live|instrumental|freestyle|cover|"
                  r"tracklist|credits|booklet|discography)\b|\(ft\.|\(feat\.|\(with ", re.I)


def get(path: str, token: str, **params) -> dict:
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)["response"]
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError(f"Genius API kept failing for {path}")


def find_artist_id(name: str, token: str) -> tuple[int, str]:
    hits = get("/search", token, q=name, per_page=10)["hits"]
    for h in hits:
        artist = h["result"]["primary_artist"]
        if artist["name"].lower() == name.lower():
            return artist["id"], artist["name"]
    raise SystemExit(f"No Genius artist named {name!r} found in search results")


def fetch_songs(artist_id: int, token: str) -> list[dict]:
    songs, page = [], 1
    while page:
        resp = get(f"/artists/{artist_id}/songs", token, per_page=50, page=page, sort="popularity")
        for s in resp["songs"]:
            if s["primary_artist"]["id"] != artist_id:  # features on other artists' songs
                continue
            songs.append({
                "id": s["id"],
                "title": s["title"],
                "release_date": s.get("release_date_for_display"),
                "url": s["url"],
            })
        page = resp["next_page"]
    return songs


def dedupe(songs: list[dict]) -> list[dict]:
    seen, out = set(), []
    for s in songs:
        if SKIP.search(s["title"]):
            continue
        key = re.sub(r"[^a-z0-9]", "", s["title"].lower())
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--artist", default="Ye")
    ap.add_argument("--out", default="songs.json")
    args = ap.parse_args()

    token = os.getenv("GENIUS_ACCESS_TOKEN")
    if not token:
        sys.exit("Set GENIUS_ACCESS_TOKEN (create a free client at https://genius.com/api-clients)")

    artist_id, name = find_artist_id(args.artist, token)
    raw = fetch_songs(artist_id, token)
    songs = dedupe(raw)
    Path(args.out).write_text(json.dumps(songs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{name} (id {artist_id}): {len(raw)} songs fetched, {len(songs)} after dedupe -> {args.out}")


if __name__ == "__main__":
    main()
