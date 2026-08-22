FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY *.py ./

ENV WHATSAPP_API_BASE_URL=http://whatsapp-bridge:8090/api
ENV MESSAGES_DB_PATH=/app/store/messages.db

# Invoke the synced venv's interpreter directly (rather than `uv run`) so no
# writable HOME/cache dir is needed at runtime -- the container may run as an
# arbitrary non-root UID (see docker-compose.yml).
CMD ["/app/.venv/bin/python", "main.py"]
