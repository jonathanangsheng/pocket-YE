import os
from datetime import date

import pytest

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test")

import bot


def test_format_lyric_with_song():
    assert bot.format_lyric("a < b | Song") == "a &lt; b — <i>Song</i>"


@pytest.fixture
def lyric_files(tmp_path, monkeypatch):
    lyrics = tmp_path / "lyrics.txt"
    lyrics.write_text("# c\none\ntwo\nthree\n", encoding="utf-8")
    monkeypatch.setattr(bot, "LYRICS_FILE", lyrics)
    monkeypatch.setattr(bot, "DATA_FILE", tmp_path / "data.json")
    return lyrics


def test_daily_lyric_is_stable_within_a_day(lyric_files):
    day = date(2026, 1, 1)
    first = bot.daily_lyric("UTC", day)
    assert all(bot.daily_lyric("UTC", day) == first for _ in range(5))


def test_daily_lyric_rotates_without_repeat(lyric_files):
    days = [date(2026, 1, d) for d in (1, 2, 3)]
    assert {bot.daily_lyric("UTC", d) for d in days} == {"one", "two", "three"}


def test_daily_lyric_chat_a_day_behind_keeps_its_lyric(lyric_files):
    behind, ahead = date(2026, 1, 1), date(2026, 1, 2)
    expected = bot.daily_lyric("UTC", behind)
    bot.daily_lyric("UTC", ahead)
    assert bot.daily_lyric("UTC", behind) == expected


def test_daily_lyric_prunes_old_days(lyric_files):
    for d in range(1, 8):
        bot.daily_lyric("UTC", date(2026, 1, d))
    assert len(bot.load_data()["daily"]) == 3


def test_daily_lyric_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "LYRICS_FILE", tmp_path / "nope.txt")
    assert bot.daily_lyric("UTC", date(2026, 1, 1)) == "No lyrics configured."
