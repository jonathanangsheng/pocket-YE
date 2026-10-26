import html
import json
import logging
import os
import random
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import Forbidden
from telegram.ext import Application, CommandHandler, ContextTypes, filters

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pocket-ye")

BASE = Path(__file__).parent
LYRICS_FILE = Path(os.getenv("LYRICS_FILE", BASE / "lyrics.txt"))
DATA_FILE = Path(os.getenv("DATA_FILE", BASE / "data.json"))
DEFAULT_TIME = os.getenv("DAILY_TIME", "09:00")
DEFAULT_TZ = os.getenv("TIMEZONE", "UTC")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
ALLOWED_CHATS = {int(x) for x in os.getenv("ALLOWED_CHATS", "").split(",") if x.strip()}


def load_lyrics() -> list[str]:
    try:
        text = LYRICS_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.warning("Lyrics file not found: %s", LYRICS_FILE)
        return []
    return [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]


def format_lyric(line: str) -> str:
    lyric, _, song = line.partition("|")
    out = html.escape(lyric.strip())
    if song.strip():
        out += f" — <i>{html.escape(song.strip())}</i>"
    return out


def load_data() -> dict:
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"subs": {}, "remaining": []}


def save_data(data: dict) -> None:
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(DATA_FILE)


def daily_lyric(tz: str, today: date | None = None) -> str:
    """The lyric for `today` in `tz`. Drawn once per date, then shared by every chat and /now."""
    lyrics = load_lyrics()
    if not lyrics:
        return "No lyrics configured."
    day = (today or datetime.now(ZoneInfo(tz)).date()).isoformat()
    data = load_data()
    daily = data.setdefault("daily", {})
    if day not in daily:
        remaining = [l for l in data.get("remaining", []) if l in lyrics]
        if not remaining:
            remaining = lyrics[:]
            random.shuffle(remaining)
        daily[day] = remaining.pop()
        data["remaining"] = remaining
        for old in sorted(daily)[:-3]:  # chats in other timezones may still be a day behind
            del daily[old]
        save_data(data)
    return format_lyric(daily[day])


def chat_tz(chat_id: int) -> str:
    return load_data()["subs"].get(str(chat_id), {}).get("tz", DEFAULT_TZ)


def schedule(app_or_ctx, chat_id: int, hhmm: str, tz: str) -> None:
    jq = app_or_ctx.job_queue
    for job in jq.get_jobs_by_name(str(chat_id)):
        job.schedule_removal()
    jq.run_daily(
        send_daily,
        time.fromisoformat(hhmm).replace(tzinfo=ZoneInfo(tz)),
        chat_id=chat_id,
        name=str(chat_id),
    )


def allowed(update: Update) -> bool:
    return not ALLOWED_CHATS or update.effective_chat.id in ALLOWED_CHATS


def is_admin(update: Update) -> bool:
    return update.effective_user.id in ADMIN_IDS


def unsubscribe(context, chat_id: int) -> None:
    for job in context.job_queue.get_jobs_by_name(str(chat_id)):
        job.schedule_removal()
    data = load_data()
    if data["subs"].pop(str(chat_id), None) is not None:
        save_data(data)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    chat_id = update.effective_chat.id
    data = load_data()
    sub = data["subs"].setdefault(str(chat_id), {"time": DEFAULT_TIME, "tz": DEFAULT_TZ})
    save_data(data)
    schedule(context, chat_id, sub["time"], sub["tz"])
    await update.message.reply_text(
        f"Subscribed. Daily lyric at {sub['time']} {sub['tz']}.\n"
        "/settime HH:MM, /timezone Area/City, /now, /stop"
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    unsubscribe(context, update.effective_chat.id)
    await update.message.reply_text("Unsubscribed.")


async def update_sub(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, value: str) -> None:
    data = load_data()
    sub = data["subs"].get(str(update.effective_chat.id))
    if not sub:
        await update.message.reply_text("Send /start first.")
        return
    sub[key] = value
    save_data(data)
    schedule(context, update.effective_chat.id, sub["time"], sub["tz"])
    await update.message.reply_text(f"Daily lyric at {sub['time']} {sub['tz']}.")


async def settime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        value = time.fromisoformat(context.args[0]).strftime("%H:%M")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /settime HH:MM")
        return
    await update_sub(update, context, "time", value)


async def timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        name = context.args[0]
        ZoneInfo(name)
    except (IndexError, ZoneInfoNotFoundError, ValueError):
        await update.message.reply_text("Usage: /timezone Area/City (e.g. Asia/Singapore)")
        return
    await update_sub(update, context, "tz", name)


async def now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if allowed(update):
        tz = chat_tz(update.effective_chat.id)
        await update.message.reply_text(daily_lyric(tz), parse_mode=ParseMode.HTML)


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return
    line = " ".join(context.args).replace("\n", " ").strip()
    if not line:
        await update.message.reply_text("Usage: /add lyric | song")
        return
    with LYRICS_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    await update.message.reply_text("Added.")


async def send_daily(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.chat_id
    try:
        await context.bot.send_message(chat_id, daily_lyric(chat_tz(chat_id)), parse_mode=ParseMode.HTML)
    except Forbidden:
        log.info("Chat %s blocked the bot; unsubscribing", chat_id)
        unsubscribe(context, chat_id)


async def restore(app: Application) -> None:
    for chat_id, sub in load_data()["subs"].items():
        schedule(app, int(chat_id), sub["time"], sub["tz"])


def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).post_init(restore).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("now", now))
    app.add_handler(CommandHandler("settime", settime))
    app.add_handler(CommandHandler("timezone", timezone))
    app.add_handler(CommandHandler("add", add, filters=filters.ChatType.PRIVATE))

    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", "8080")),
            url_path=token,
            webhook_url=f"{webhook_url.rstrip('/')}/{token}",
            secret_token=os.getenv("WEBHOOK_SECRET") or None,
        )
    else:
        app.run_polling()


if __name__ == "__main__":
    main()
