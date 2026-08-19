FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.12.5

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked

CMD [".venv/bin/uvicorn", "infinite_interns.executor.main:app", "--host", "0.0.0.0", "--port", "8080"]
