"""Store endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.core.database import get_db
from api.app.models.schemas import StoreResponse
from data.scripts.db.models import Store

router = APIRouter()


@router.get("/stores", response_model=list[StoreResponse])
async def list_stores(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Store).order_by(Store.id))
    stores = result.scalars().all()
    return [StoreResponse.model_validate(s) for s in stores]


@router.get("/stores/{store_id}", response_model=StoreResponse)
async def get_store(store_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if store is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Store {store_id} not found")
    return StoreResponse.model_validate(store)
