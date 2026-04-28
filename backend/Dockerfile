FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps: ffmpeg is handy if we ever transcode locally; libstdc++ is
# pulled in by httpx's HTTP/2 stack on slim images.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
      "fastapi>=0.110.0" \
      "uvicorn[standard]>=0.30.0" \
      "python-multipart>=0.0.9" \
      "anthropic>=0.39.0" \
      "openai>=1.40.0" \
      "httpx>=0.27.0" \
      "mcp>=1.2.0" \
      "slowapi>=0.1.9"

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
