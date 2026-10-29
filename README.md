# pocket-YE
A telegram bot that replies to `/now` with a random YE lyric

## Setup
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set `TELEGRAM_BOT_TOKEN` (from @BotFather).
3. Add lyrics to `lyrics.txt`, one per line, optionally `lyric | song`. Lines starting with `#` are ignored.
4. `python bot.py`

## Docker
```
docker build -t pocket-ye .
docker run -d --env-file .env pocket-ye
```

## Tests
`pytest`
