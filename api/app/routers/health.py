"""Health check endpoint."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/v1/health")
async def health_check(request: Request):
    return {
        "status": "healthy",
        "model_loaded": request.app.state.model is not None,
    }
