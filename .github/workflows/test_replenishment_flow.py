"""
Tests for the product replenishment flow, from suggesting reorders to
creating purchase orders.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.controllers.product_controller import ProductController
from core.schemas import ProductData
from services.permissions import Perm


@pytest.fixture
def product_controller_with_mocks(ctrl) -> ProductController:
    """Provides a ProductController with mocked dependencies for replenishment tests."""
    # Mock repositories to isolate controller logic
    ctrl.db.product_repo = MagicMock()
    ctrl.db.purchase_order_repo = MagicMock()
    return ProductController(
        db=ctrl.db,
        user_repo=ctrl.db.user_repo,
        current_user="test_user",
        current_user_permissions={Perm.PRODUCTOS_LEER, Perm.ORDENES_COMPRA_CREAR},
    )


@pytest.mark.asyncio
async def test_replenishment_suggestion_and_order_creation(product_controller_with_mocks):
    """
    Verify that the replenishment flow works end-to-end:
    1. A product with low stock is correctly identified for reordering.
    2. A purchase order is created for that product from the suggestion.
    """
    # --- Arrange ---
    controller = product_controller_with_mocks

    # Mock a product that is below its minimum stock level
    low_stock_product = ProductData(
        id=101,
        nombre="Producto Bajo Stock",
        codigo="LOW-001",
        cantidad=5,
        stock_minimo=10,
        proveedor_id=202,
        proveedor_nombre="Proveedor Fiable",
    )

    # Configure the mock product repo to return our low-stock product
    controller.db.product_repo.obtener_productos_bajo_stock.return_value = [low_stock_product]

    # Mock the purchase order repo to verify it's called later
    controller.db.purchase_order_repo.crear_orden_compra = AsyncMock()

    # --- Act: Part 1 - Get replenishment suggestions ---
    suggestions = await controller.sugerir_reabastecimiento()

    # --- Assert: Part 1 ---
    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion["producto_id"] == low_stock_product.id
    assert suggestion["cantidad_sugerida"] == 5  # (stock_minimo - cantidad)

    # --- Act: Part 2 - Create purchase orders from suggestions ---
    await controller.crear_ordenes_desde_sugerencias(suggestions)

    # --- Assert: Part 2 ---
    # Verify that the purchase order creation method was called with the correct data
    order_repo_mock = controller.db.purchase_order_repo
    order_repo_mock.crear_orden_compra.assert_called_once()
    call_args, call_kwargs = order_repo_mock.crear_orden_compra.call_args

    assert call_kwargs["proveedor_id"] == low_stock_product.proveedor_id
    assert len(call_kwargs["items"]) == 1
    assert call_kwargs["items"][0]["producto_id"] == low_stock_product.id
    assert call_kwargs["items"][0]["cantidad"] == 5