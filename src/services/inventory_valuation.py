"""Inventory valuation methods (FIFO, LIFO, Average Cost).

Provides cost calculation methods for inventory valuation.
"""

from utils.logger import setup_logger

logger = setup_logger(__name__)


def calcular_costo_fifo(lotes: list[dict], cantidad_solicitada: int) -> tuple[float, int]:
    """Calculate cost using FIFO (First In, First Out).

    Args:
        lots: List of lots sorted by date (oldest first).
        quantity_requested: Quantity to sell/deduct.

    Returns:
        Tuple of (total_cost, remaining_quantity).
    """
    total_cost = 0.0
    remaining = cantidad_solicitada

    for lote in sorted(lotes, key=lambda x: x.get("fecha_fabricacion", "")):
        if remaining <= 0:
            break
        disponible = lote.get("cantidad_actual", 0)
        precio = lote.get("precio", 0)
        take = min(remaining, disponible)
        total_cost += take * precio
        remaining -= take

    return total_cost, remaining


def calcular_costo_lifo(lotes: list[dict], cantidad_solicitada: int) -> tuple[float, int]:
    """Calculate cost using LIFO (Last In, First Out).

    Args:
        lots: List of lots sorted by date (newest first).
        quantity_requested: Quantity to sell/deduct.

    Returns:
        Tuple of (total_cost, remaining_quantity).
    """
    total_cost = 0.0
    remaining = cantidad_solicitada

    for lote in sorted(lotes, key=lambda x: x.get("fecha_fabricacion", ""), reverse=True):
        if remaining <= 0:
            break
        disponible = lote.get("cantidad_actual", 0)
        precio = lote.get("precio", 0)
        take = min(remaining, disponible)
        total_cost += take * precio
        remaining -= take

    return total_cost, remaining


def calcular_costo_promedio(lotes: list[dict], cantidad_solicitada: int) -> tuple[float, int]:
    """Calculate cost using Weighted Average Cost.

    Args:
        lots: List of lots with quantities and prices.
        quantity_requested: Quantity to sell/deduct.

    Returns:
        Tuple of (total_cost, remaining_quantity).
    """
    total_value = sum(lote.get("cantidad_actual", 0) * lote.get("precio", 0) for lote in lotes)
    total_qty = sum(lote.get("cantidad_actual", 0) for lote in lotes)

    if total_qty == 0:
        return 0.0, cantidad_solicitada

    avg_cost = total_value / total_qty
    take = min(cantidad_solicitada, total_qty)
    total_cost = take * avg_cost
    remaining = total_qty - take

    return total_cost, remaining


def calcular_valor_inventario(productos: list[dict], metodo: str = "promedio") -> dict:
    """Calculate total inventory valuation.

    Args:
        products: List of products with quantity and price.
        method: Valuation method ('fifo', 'lifo', 'promedio').

    Returns:
        Dict with total_value, total_quantity, average_cost.
    """
    if not productos:
        return {"total_value": 0, "total_quantity": 0, "average_cost": 0}

    total_qty = sum(p.get("cantidad", 0) for p in productos)

    if metodo == "promedio":
        total_value = sum(p.get("cantidad", 0) * p.get("precio", 0) for p in productos)
    elif metodo == "fifo":
        # For simplicity, use current price (full FIFO requires lot tracking)
        total_value = sum(p.get("cantidad", 0) * p.get("precio", 0) for p in productos)
    elif metodo == "lifo":
        # For simplicity, use current price (full LIFO requires lot tracking)
        total_value = sum(p.get("cantidad", 0) * p.get("precio", 0) for p in productos)
    else:
        total_value = sum(p.get("cantidad", 0) * p.get("precio", 0) for p in productos)

    avg_cost = total_value / total_qty if total_qty > 0 else 0

    return {
        "total_value": total_value,
        "total_quantity": total_qty,
        "average_cost": avg_cost,
        "method": metodo,
    }
