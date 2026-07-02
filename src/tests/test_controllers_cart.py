"""Tests for CartController."""

from __future__ import annotations

import pytest


class TestCartController:
    @pytest.mark.asyncio
    async def test_obtener_o_crear_carrito(self, ctrl):
        ctrl.current_user = "testuser"
        result = await ctrl.obtener_o_crear_carrito()
        assert "id" in result
        assert result["estado"] == "activo"

    @pytest.mark.asyncio
    async def test_agregar_item(self, ctrl):
        _, product = await ctrl.crear_producto(
            codigo="CART-CTRL", nombre="Cart Item", cantidad="10", precio="5.0"
        )
        ctrl.current_user = "buyer"
        await ctrl.obtener_o_crear_carrito()
        success = await ctrl.agregar_al_carrito(product["id"], 2, 5.0)
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_items(self, ctrl):
        ctrl.current_user = "viewer"
        cart = await ctrl.obtener_o_crear_carrito()
        items = await ctrl.obtener_items_carrito(cart["id"])
        assert isinstance(items, list)

    @pytest.mark.asyncio
    async def test_eliminar_item(self, ctrl):
        _, product = await ctrl.crear_producto(
            codigo="CART-DEL", nombre="Del Item", cantidad="5", precio="3.0"
        )
        ctrl.current_user = "deleter"
        cart = await ctrl.obtener_o_crear_carrito()
        add_ok = await ctrl.agregar_al_carrito(product["id"], 1, 3.0)
        assert add_ok is True
        items = await ctrl.obtener_items_carrito(cart["id"])
        assert len(items) > 0
        success = await ctrl.eliminar_item_carrito(items[0]["id"])
        assert success is True

    @pytest.mark.asyncio
    async def test_cerrar_carrito(self, ctrl):
        ctrl.current_user = "closer"
        cart = await ctrl.obtener_o_crear_carrito()
        success = await ctrl.marcar_carrito_convertido(cart["id"])
        assert success is True
