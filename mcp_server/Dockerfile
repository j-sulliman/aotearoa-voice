FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
      "mcp>=1.2.0" \
      "starlette>=0.37.0" \
      "uvicorn[standard]>=0.30.0"

COPY tools/ ./tools/
COPY data/ ./data/
COPY server.py ./

EXPOSE 8001

CMD ["python", "server.py"]
