# pocket-YE
A telegram bot that sends a daily YE lyric

## Setup
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set `TELEGRAM_BOT_TOKEN` (from @BotFather).
3. Add lyrics to `lyrics.txt`, one per line, optionally `lyric | song`. Lines starting with `#` are ignored.
4. `python bot.py`

## Commands
| Command | Description |
| --- | --- |
| `/start` | Subscribe the chat to the daily lyric |
| `/stop` | Unsubscribe |
| `/now` | Show today's lyric immediately (same one as the daily send) |
| `/settime HH:MM` | Set this chat's daily send time |
| `/timezone Area/City` | Set this chat's timezone, e.g. `Asia/Singapore` |
| `/add lyric \| song` | Append a lyric (admins only, private chat) |

## Configuration
Set in `.env`:

| Variable | Description |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Required bot token |
| `DAILY_TIME` / `TIMEZONE` | Defaults for new subscribers (`09:00`, `UTC`) |
| `ADMIN_IDS` | Comma-separated user IDs allowed to use `/add` |
| `ALLOWED_CHATS` | Comma-separated chat IDs; empty allows all |
| `WEBHOOK_URL` / `WEBHOOK_SECRET` / `PORT` | Set `WEBHOOK_URL` to use webhook mode instead of polling |

Subscriptions and lyric rotation are stored in `data.json`. One lyric is drawn per calendar date (in each chat's timezone) and shared by every chat and `/now` that day. Lyrics are drawn in shuffled order without repeats until all have been used.

## Docker
```
docker build -t pocket-ye .
docker run -d --env-file .env -v pocket-ye-data:/data pocket-ye
```

## Tests
`pytest`
