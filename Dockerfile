FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py lyrics.txt ./
ENV DATA_FILE=/data/data.json
VOLUME /data
CMD ["python", "bot.py"]
