import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test")

import bot


def test_format_lyric_with_song():
    assert bot.format_lyric("a < b | Song") == "a &lt; b — <i>Song</i>"


def test_pick_lyric_rotates_without_repeat(tmp_path, monkeypatch):
    lyrics = tmp_path / "lyrics.txt"
    lyrics.write_text("# c\none\ntwo\nthree\n", encoding="utf-8")
    monkeypatch.setattr(bot, "LYRICS_FILE", lyrics)
    monkeypatch.setattr(bot, "DATA_FILE", tmp_path / "data.json")
    assert {bot.pick_lyric() for _ in range(3)} == {"one", "two", "three"}


def test_pick_lyric_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "LYRICS_FILE", tmp_path / "nope.txt")
    assert bot.pick_lyric() == "No lyrics configured."
