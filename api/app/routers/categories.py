"""Category endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.core.database import get_db
from api.app.models.schemas import CategoryResponse, ProductResponse
from data.scripts.db.models import Category, Product

router = APIRouter()


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.id))
    categories = result.scalars().all()
    return [CategoryResponse.model_validate(c) for c in categories]


@router.get("/categories/{category_id}/products", response_model=list[ProductResponse])
async def list_products_by_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.category_id == category_id).order_by(Product.id)
    )
    products = result.scalars().all()
    return [ProductResponse.model_validate(p) for p in products]
