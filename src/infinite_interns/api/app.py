"""Custom HTTP routes mounted beside the LangGraph Agent Server."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
