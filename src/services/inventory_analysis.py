"""Inventory analysis: ABC analysis, turnover, aging, stockout risk."""

from utils.logger import setup_logger

logger = setup_logger(__name__)


def analisis_abc(productos: list[dict]) -> list[dict]:
    """ABC analysis based on revenue contribution.

    Args:
        products: List of products with quantity, price, and optionally sales data.

    Returns:
        List of products with ABC classification:
        - A: Top 80% of revenue (high value)
        - B: Next 15% of revenue (medium value)
        - C: Bottom 5% of revenue (low value)
    """
    if not productos:
        return []

    # Calculate revenue for each product
    for p in productos:
        p["_revenue"] = p.get("cantidad", 0) * p.get("precio", 0)

    # Sort by revenue descending
    sorted_products = sorted(productos, key=lambda x: x["_revenue"], reverse=True)
    total_revenue = sum(p["_revenue"] for p in sorted_products)

    if total_revenue == 0:
        for p in sorted_products:
            p["abc_class"] = "C"
        return sorted_products

    # Assign ABC classes
    cumulative = 0
    for p in sorted_products:
        cumulative += p["_revenue"]
        pct = (cumulative / total_revenue) * 100

        if pct <= 80:
            p["abc_class"] = "A"
        elif pct <= 95:
            p["abc_class"] = "B"
        else:
            p["abc_class"] = "C"

    return sorted_products


def calcular_rotacion_inventario(productos: list[dict], ventas_periodo: list[dict]) -> dict:
    """Calculate inventory turnover ratio.

    Args:
        products: Current inventory.
        sales: Sales in the period.

    Returns:
        Dict with turnover_ratio, days_of_supply, stockout_risk.
    """
    if not productos:
        return {"turnover_ratio": 0, "days_of_supply": 0, "stockout_risk": "low"}

    total_stock = sum(p.get("cantidad", 0) for p in productos)
    total_cost = sum(p.get("cantidad", 0) * p.get("precio", 0) for p in productos)

    # Calculate COGS from sales
    cogs = sum(
        s.get("cantidad", 0) * s.get("precio_unitario", 0)
        for s in ventas_periodo
    )

    # Turnover ratio = COGS / Average Inventory Value
    avg_inventory = total_cost  # Simplified: use current value
    turnover_ratio = cogs / avg_inventory if avg_inventory > 0 else 0

    # Days of supply = (Average Inventory / COGS) * 365
    days_of_supply = (avg_inventory / cogs * 365) if cogs > 0 else 999

    # Stockout risk based on days of supply
    if days_of_supply < 30:
        stockout_risk = "high"
    elif days_of_supply < 90:
        stockout_risk = "medium"
    else:
        stockout_risk = "low"

    return {
        "turnover_ratio": round(turnover_ratio, 2),
        "days_of_supply": round(days_of_supply, 1),
        "stockout_risk": stockout_risk,
        "total_stock": total_stock,
        "total_value": total_cost,
        "cogs": cogs,
    }


def analisis_envejecimiento(productos: list[dict]) -> list[dict]:
    """Analyze inventory aging based on last movement date.

    Args:
        products: List of products with last_moved_at or creado_en.

    Returns:
        List of products with aging classification:
        - fresh: moved in last 30 days
        - aging: moved 30-90 days ago
        - old: moved 90+ days ago
        - stagnant: never moved
    """
    from datetime import datetime, timedelta

    now = datetime.now()
    result = []

    for p in productos:
        last_moved = p.get("last_moved_at") or p.get("creado_en")
        if not last_moved:
            aging = "stagnant"
        else:
            try:
                moved_date = datetime.fromisoformat(last_moved)
                days_since = (now - moved_date).days
                if days_since <= 30:
                    aging = "fresh"
                elif days_since <= 90:
                    aging = "aging"
                else:
                    aging = "old"
            except (ValueError, TypeError):
                aging = "stagnant"

        result.append({**p, "aging_class": aging})

    return result


def calcular_riesgo_agotamiento(productos: list[dict]) -> list[dict]:
    """Calculate stockout risk for each product.

    Args:
        products: List of products with quantity, stock_min, and optionally
                  daily_sales (average sales per day).

    Returns:
        List of products with days_until_stockout and risk_level.
    """
    result = []

    for p in productos:
        qty = p.get("cantidad", 0)
        stock_min = p.get("stock_min", 0)
        daily_sales = p.get("daily_sales", 1)  # Default to 1 if not provided

        if daily_sales <= 0:
            days_until_stockout = 999
        else:
            days_until_stockout = qty / daily_sales

        if qty == 0:
            risk_level = "critical"
        elif qty <= stock_min:
            risk_level = "high"
        elif days_until_stockout < 14:
            risk_level = "medium"
        else:
            risk_level = "low"

        result.append({
            **p,
            "days_until_stockout": round(days_until_stockout, 1),
            "risk_level": risk_level,
        })

    return result
