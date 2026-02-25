FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc g++ libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY . .

RUN mkdir -p logs models

RUN useradd -m -u 1000 mluser && chown -R mluser:mluser /app
USER mluser

CMD ["uvicorn", "api.routes:app", "--host", "0.0.0.0", "--port", "8000"]