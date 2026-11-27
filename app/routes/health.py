"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check: returns {"status": "ok"} when the app is running."""
    return {"status": "ok"}
