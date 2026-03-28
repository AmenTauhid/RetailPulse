"""Conversational AI service using Claude API with tool use.

The LLM never generates data — it calls tools that query the real database,
then synthesizes a natural language answer grounded in the returned data.
"""

import json
import logging
from datetime import date, timedelta

import anthropic
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.core.config import get_settings
from data.scripts.db.models import (
    Category,
    DailyAggregate,
    Holiday,
    Store,
    WeatherDaily,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are RetailPulse AI, a retail demand intelligence assistant for a Canadian \
retail chain (similar to Canadian Tire). You help store managers and \
merchandising teams make data-driven stocking and planning decisions.

RULES:
- Only reference data returned by your tool calls. Never invent or guess numbers.
- If no relevant data is available, say so honestly.
- Keep answers concise and actionable — these are busy retail professionals.
- When citing data, mention the store name and category, not just IDs.
- Use Canadian English and context (provinces, Canadian holidays, etc.).
- Format numbers clearly (e.g., "12 units/day" not "12.000000").

You have access to tools that query the real database. Use them to answer questions about:
- Demand forecasts and historical sales
- Weather impact on product categories
- Upcoming holidays and their effect on demand
- Anomalies (unexpected demand spikes or drops)
- Store and category comparisons"""

TOOLS = [
    {
        "name": "get_historical_demand",
        "description": "Get daily demand data for a specific store and product category over a date range. Returns total quantity sold, revenue, and transaction count per day.",
        "input_schema": {
            "type": "object",
            "properties": {
                "store_id": {"type": "integer", "description": "Store ID (1-10)"},
                "category_id": {"type": "integer", "description": "Category ID (1-14)"},
                "start_date": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD). Defaults to 30 days ago.",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD). Defaults to 2025-12-31.",
                },
            },
            "required": ["store_id", "category_id"],
        },
    },
    {
        "name": "get_stores",
        "description": "List all retail stores with their city, province, and type. Use this to look up store IDs.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_categories",
        "description": "List all product categories with their department and seasonal info. Use this to look up category IDs.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_weather",
        "description": "Get recent weather data for a store location. Returns temperature, precipitation, snowfall.",
        "input_schema": {
            "type": "object",
            "properties": {
                "store_id": {"type": "integer", "description": "Store ID (1-10)"},
                "days": {
                    "type": "integer",
                    "description": "Number of recent days to fetch. Default 7.",
                },
            },
            "required": ["store_id"],
        },
    },
    {
        "name": "get_upcoming_holidays",
        "description": "Get upcoming Canadian holidays within a date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_demand_comparison",
        "description": "Compare average daily demand for a category across two stores over a date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "store_id_a": {"type": "integer", "description": "First store ID"},
                "store_id_b": {"type": "integer", "description": "Second store ID"},
                "category_id": {"type": "integer", "description": "Category ID"},
                "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
            },
            "required": ["store_id_a", "store_id_b", "category_id"],
        },
    },
    {
        "name": "get_top_categories",
        "description": "Get the top-selling or fastest-growing categories for a store over a recent period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "store_id": {"type": "integer", "description": "Store ID"},
                "days": {"type": "integer", "description": "Lookback period in days. Default 14."},
                "metric": {
                    "type": "string",
                    "enum": ["volume", "growth"],
                    "description": "'volume' for highest sales, 'growth' for biggest increase vs prior period. Default 'volume'.",
                },
            },
            "required": ["store_id"],
        },
    },
    {
        "name": "get_weather_impact",
        "description": "Show how temperature ranges correlate with demand for a specific category at a store.",
        "input_schema": {
            "type": "object",
            "properties": {
                "store_id": {"type": "integer", "description": "Store ID"},
                "category_id": {"type": "integer", "description": "Category ID"},
            },
            "required": ["store_id", "category_id"],
        },
    },
]


def _execute_tool(tool_name: str, tool_input: dict, session: Session) -> str:
    """Execute a tool call against the database and return JSON result."""

    if tool_name == "get_stores":
        rows = session.execute(select(Store).order_by(Store.id)).scalars().all()
        return json.dumps(
            [
                {
                    "id": s.id,
                    "name": s.name,
                    "city": s.city,
                    "province": s.province,
                    "type": s.store_type,
                }
                for s in rows
            ]
        )

    elif tool_name == "get_categories":
        rows = session.execute(select(Category).order_by(Category.id)).scalars().all()
        return json.dumps(
            [
                {
                    "id": c.id,
                    "name": c.name,
                    "department": c.department,
                    "is_seasonal": c.is_seasonal,
                    "peak_season": c.peak_season,
                }
                for c in rows
            ]
        )

    elif tool_name == "get_historical_demand":
        store_id = tool_input["store_id"]
        category_id = tool_input["category_id"]
        start = tool_input.get("start_date", str(date(2025, 12, 1)))
        end = tool_input.get("end_date", "2025-12-31")

        rows = (
            session.execute(
                select(DailyAggregate)
                .where(
                    DailyAggregate.store_id == store_id,
                    DailyAggregate.category_id == category_id,
                    DailyAggregate.date >= start,
                    DailyAggregate.date <= end,
                )
                .order_by(DailyAggregate.date)
            )
            .scalars()
            .all()
        )

        store = session.execute(select(Store).where(Store.id == store_id)).scalar_one_or_none()
        cat = session.execute(
            select(Category).where(Category.id == category_id)
        ).scalar_one_or_none()

        data = [
            {
                "date": str(r.date),
                "quantity": r.total_quantity,
                "revenue": float(r.total_revenue),
                "transactions": r.transaction_count,
            }
            for r in rows
        ]
        total_qty = sum(d["quantity"] for d in data)
        avg_qty = round(total_qty / len(data), 1) if data else 0

        return json.dumps(
            {
                "store": store.name if store else f"Store {store_id}",
                "category": cat.name if cat else f"Category {category_id}",
                "period": f"{start} to {end}",
                "days_with_data": len(data),
                "total_quantity": total_qty,
                "avg_daily_quantity": avg_qty,
                "total_revenue": round(sum(d["revenue"] for d in data), 2),
                "recent_days": data[-7:] if len(data) > 7 else data,
            }
        )

    elif tool_name == "get_weather":
        store_id = tool_input["store_id"]
        days = tool_input.get("days", 7)

        rows = (
            session.execute(
                select(WeatherDaily)
                .where(WeatherDaily.store_id == store_id)
                .order_by(WeatherDaily.date.desc())
                .limit(days)
            )
            .scalars()
            .all()
        )

        store = session.execute(select(Store).where(Store.id == store_id)).scalar_one_or_none()

        return json.dumps(
            {
                "store": store.name if store else f"Store {store_id}",
                "city": store.city if store else "Unknown",
                "data": [
                    {
                        "date": str(w.date),
                        "temp_high": float(w.temp_high_c or 0),
                        "temp_low": float(w.temp_low_c or 0),
                        "temp_mean": float(w.temp_mean_c or 0),
                        "snowfall_cm": float(w.snowfall_cm or 0),
                        "precipitation_mm": float(w.precipitation_mm or 0),
                        "description": w.weather_description or "",
                    }
                    for w in rows
                ],
            }
        )

    elif tool_name == "get_upcoming_holidays":
        start = tool_input["start_date"]
        end = tool_input["end_date"]

        rows = (
            session.execute(
                select(Holiday)
                .where(Holiday.date >= start, Holiday.date <= end)
                .order_by(Holiday.date)
            )
            .scalars()
            .all()
        )

        return json.dumps(
            [
                {"date": str(h.date), "name": h.name, "province": h.province_code or "National"}
                for h in rows
            ]
        )

    elif tool_name == "get_demand_comparison":
        sid_a = tool_input["store_id_a"]
        sid_b = tool_input["store_id_b"]
        cid = tool_input["category_id"]
        start = tool_input.get("start_date", str(date(2025, 6, 1)))
        end = tool_input.get("end_date", "2025-8-31")

        def avg_demand(sid):
            result = session.execute(
                select(func.avg(DailyAggregate.total_quantity)).where(
                    DailyAggregate.store_id == sid,
                    DailyAggregate.category_id == cid,
                    DailyAggregate.date >= start,
                    DailyAggregate.date <= end,
                )
            ).scalar()
            return round(float(result or 0), 2)

        store_a = session.execute(select(Store).where(Store.id == sid_a)).scalar_one_or_none()
        store_b = session.execute(select(Store).where(Store.id == sid_b)).scalar_one_or_none()
        cat = session.execute(select(Category).where(Category.id == cid)).scalar_one_or_none()

        avg_a = avg_demand(sid_a)
        avg_b = avg_demand(sid_b)

        return json.dumps(
            {
                "category": cat.name if cat else f"Category {cid}",
                "period": f"{start} to {end}",
                "store_a": {
                    "name": store_a.name if store_a else f"Store {sid_a}",
                    "avg_daily_qty": avg_a,
                },
                "store_b": {
                    "name": store_b.name if store_b else f"Store {sid_b}",
                    "avg_daily_qty": avg_b,
                },
                "difference_pct": round(((avg_a - avg_b) / avg_b * 100) if avg_b else 0, 1),
            }
        )

    elif tool_name == "get_top_categories":
        store_id = tool_input["store_id"]
        days = tool_input.get("days", 14)
        metric = tool_input.get("metric", "volume")
        end_date = date(2025, 12, 31)
        start_date = end_date - timedelta(days=days)
        prev_start = start_date - timedelta(days=days)

        store = session.execute(select(Store).where(Store.id == store_id)).scalar_one_or_none()

        # Current period
        current = session.execute(
            select(
                DailyAggregate.category_id,
                func.avg(DailyAggregate.total_quantity).label("avg_qty"),
            )
            .where(
                DailyAggregate.store_id == store_id,
                DailyAggregate.date >= str(start_date),
                DailyAggregate.date <= str(end_date),
            )
            .group_by(DailyAggregate.category_id)
        ).all()

        # Previous period (for growth)
        previous = {}
        if metric == "growth":
            prev_rows = session.execute(
                select(
                    DailyAggregate.category_id,
                    func.avg(DailyAggregate.total_quantity).label("avg_qty"),
                )
                .where(
                    DailyAggregate.store_id == store_id,
                    DailyAggregate.date >= str(prev_start),
                    DailyAggregate.date < str(start_date),
                )
                .group_by(DailyAggregate.category_id)
            ).all()
            previous = {r[0]: float(r[1]) for r in prev_rows}

        cats = {c.id: c.name for c in session.execute(select(Category)).scalars().all()}

        results = []
        for row in current:
            cat_id = row[0]
            avg = float(row[1])
            entry = {"category": cats.get(cat_id, f"Cat {cat_id}"), "avg_daily_qty": round(avg, 1)}
            if metric == "growth" and cat_id in previous and previous[cat_id] > 0:
                entry["growth_pct"] = round((avg - previous[cat_id]) / previous[cat_id] * 100, 1)
            results.append(entry)

        if metric == "growth":
            results = [r for r in results if "growth_pct" in r]
            results.sort(key=lambda r: r["growth_pct"], reverse=True)
        else:
            results.sort(key=lambda r: r["avg_daily_qty"], reverse=True)

        return json.dumps(
            {
                "store": store.name if store else f"Store {store_id}",
                "period": f"{start_date} to {end_date}",
                "metric": metric,
                "categories": results[:10],
            }
        )

    elif tool_name == "get_weather_impact":
        store_id = tool_input["store_id"]
        category_id = tool_input["category_id"]

        rows = session.execute(
            select(
                WeatherDaily.temp_mean_c,
                DailyAggregate.total_quantity,
            )
            .join(
                WeatherDaily,
                (
                    (DailyAggregate.store_id == WeatherDaily.store_id)
                    & (DailyAggregate.date == WeatherDaily.date)
                ),
            )
            .where(
                DailyAggregate.store_id == store_id,
                DailyAggregate.category_id == category_id,
            )
        ).all()

        store = session.execute(select(Store).where(Store.id == store_id)).scalar_one_or_none()
        cat = session.execute(
            select(Category).where(Category.id == category_id)
        ).scalar_one_or_none()

        buckets: dict[str, list[int]] = {}
        for temp, qty in rows:
            t = float(temp) if temp else 0
            if t < -10:
                tr = "below -10C"
            elif t < 0:
                tr = "-10C to 0C"
            elif t < 10:
                tr = "0C to 10C"
            elif t < 20:
                tr = "10C to 20C"
            else:
                tr = "above 20C"
            buckets.setdefault(tr, []).append(qty)

        return json.dumps(
            {
                "store": store.name if store else f"Store {store_id}",
                "category": cat.name if cat else f"Category {category_id}",
                "temperature_impact": {
                    tr: {"avg_daily_qty": round(sum(q) / len(q), 1), "sample_days": len(q)}
                    for tr, q in sorted(buckets.items())
                },
            }
        )

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def chat(user_message: str, conversation_history: list[dict], session: Session) -> dict:
    """Process a chat message using Claude with tool use.

    Args:
        user_message: The user's question.
        conversation_history: Prior messages in the conversation.
        session: Sync SQLAlchemy session for tool execution.

    Returns:
        Dict with 'response' (text), 'tools_used' (list of tool names called).
    """
    settings = get_settings()
    api_key = settings.anthropic_api_key

    if not api_key or api_key == "your_key_here":
        return {
            "response": "The Anthropic API key is not configured. Please add your key to the .env file as ANTHROPIC_API_KEY.",
            "tools_used": [],
        }

    client = anthropic.Anthropic(api_key=api_key)

    messages = [*conversation_history, {"role": "user", "content": user_message}]
    tools_used = []

    # Tool use loop — Claude may call multiple tools before responding
    max_iterations = 5
    for _ in range(max_iterations):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Process all tool calls in the response
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tools_used.append(tool_name)

                    logger.info("Tool call: %s(%s)", tool_name, json.dumps(tool_input)[:200])

                    try:
                        result = _execute_tool(tool_name, tool_input, session)
                    except Exception as e:
                        logger.error("Tool execution error: %s", e)
                        result = json.dumps({"error": str(e)})

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            messages.append({"role": "user", "content": tool_results})
        else:
            # Claude is done — extract the text response
            text_parts = [block.text for block in response.content if hasattr(block, "text")]
            return {
                "response": "\n".join(text_parts),
                "tools_used": tools_used,
            }

    return {
        "response": "I wasn't able to complete the analysis. Please try rephrasing your question.",
        "tools_used": tools_used,
    }
