"""Compute daily aggregates from transaction data for ML consumption."""

from collections import defaultdict
from decimal import Decimal

from data.scripts.db.models import DailyAggregate, Product, Transaction


def generate_aggregates(
    transactions: list[Transaction],
    products: list[Product],
) -> list[DailyAggregate]:
    """Aggregate transactions by (store_id, category_id, date).

    Args:
        transactions: List of Transaction ORM objects.
        products: List of Product ORM objects (to map product_id -> category_id).

    Returns:
        List of DailyAggregate ORM objects.
    """
    product_category = {p.id: p.category_id for p in products}

    # Accumulate: key = (store_id, category_id, date)
    agg: dict[tuple, dict] = defaultdict(lambda: {
        "total_quantity": 0,
        "total_revenue": Decimal("0.00"),
        "transaction_count": 0,
    })

    for txn in transactions:
        cat_id = product_category.get(txn.product_id)
        if cat_id is None:
            continue
        key = (txn.store_id, cat_id, txn.transaction_date)
        agg[key]["total_quantity"] += txn.quantity
        agg[key]["total_revenue"] += txn.total_amount
        agg[key]["transaction_count"] += 1

    aggregates: list[DailyAggregate] = []
    for (store_id, category_id, dt), vals in agg.items():
        avg_basket = (
            vals["total_revenue"] / vals["transaction_count"]
            if vals["transaction_count"] > 0
            else Decimal("0.00")
        )
        aggregates.append(
            DailyAggregate(
                store_id=store_id,
                category_id=category_id,
                date=dt,
                total_quantity=vals["total_quantity"],
                total_revenue=vals["total_revenue"],
                transaction_count=vals["transaction_count"],
                avg_basket_size=round(avg_basket, 2),
            )
        )

    return aggregates
