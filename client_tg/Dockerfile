FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .

# Установи системные зависимости для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /venv
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# --- Production stage ---
FROM python:3.12-slim

WORKDIR /app

# ⚠️ Установи ТОЛЬКО runtime зависимости (без -dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# venv живёт в /venv — volume mount на /app его не перекроет
COPY --from=builder /venv /venv

ENV PATH="/venv/bin:$PATH"
COPY . .

CMD ["python", "main.py"]