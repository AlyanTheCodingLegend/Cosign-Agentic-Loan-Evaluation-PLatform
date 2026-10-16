"""FastAPI app and route registration."""

from fastapi import FastAPI

app = FastAPI(title="Loan Approval Agent")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}
