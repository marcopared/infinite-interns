FROM python:3.13-slim

RUN pip install --no-cache-dir uv==0.12.5
WORKDIR /app
COPY pyproject.toml uv.lock README.md langgraph.json ./
COPY src ./src
RUN uv sync --dev --locked

CMD [".venv/bin/langgraph", "dev", "--host", "0.0.0.0", "--port", "2024", "--no-browser"]
