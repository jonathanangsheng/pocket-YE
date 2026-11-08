import html
import logging
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pocket-ye")

LYRICS_FILE = Path(os.getenv("LYRICS_FILE", Path(__file__).parent / "lyrics.txt"))


def load_lyrics() -> list[str]:
    try:
        text = LYRICS_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.warning("Lyrics file not found: %s", LYRICS_FILE)
        return []
    return [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]


def format_lyric(line: str) -> str:
    lyric, _, song = line.partition("|")
    out = html.escape(lyric.strip()).replace(" / ", "\n")
    if song.strip():
        out += f" — <i>{html.escape(song.strip())}</i>"
    return out


def random_lyric() -> str:
    lyrics = load_lyrics()
    return format_lyric(random.choice(lyrics)) if lyrics else "No lyrics configured."


async def now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(random_lyric(), parse_mode=ParseMode.HTML)


def main() -> None:
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("now", now))
    app.run_polling()


if __name__ == "__main__":
    main()
