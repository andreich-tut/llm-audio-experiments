FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y ffmpeg curl redis-tools && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/docker/docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s CMD pgrep -f "python bot.py" || exit 1

CMD ["/app/docker/docker-entrypoint.sh"]
