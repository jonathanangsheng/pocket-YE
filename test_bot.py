import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test")

import bot


def test_format_lyric_with_song():
    assert bot.format_lyric("a < b | Song") == "a &lt; b — <i>Song</i>"


def test_random_lyric_picks_from_file(tmp_path, monkeypatch):
    lyrics = tmp_path / "lyrics.txt"
    lyrics.write_text("# c\none\ntwo\n", encoding="utf-8")
    monkeypatch.setattr(bot, "LYRICS_FILE", lyrics)
    assert {bot.random_lyric() for _ in range(50)} == {"one", "two"}


def test_random_lyric_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "LYRICS_FILE", tmp_path / "nope.txt")
    assert bot.random_lyric() == "No lyrics configured."
