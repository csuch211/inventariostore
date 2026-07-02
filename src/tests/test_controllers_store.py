"""Tests for StoreController."""

from __future__ import annotations

import pytest


class TestStoreController:
    @pytest.mark.asyncio
    async def test_obtener_config_tienda(self, ctrl):
        result = await ctrl.obtener_config_tienda()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_guardar_config_tienda(self, ctrl):
        success = await ctrl.guardar_config_tienda("store_name", "Mi Tienda")
        assert success is True

    @pytest.mark.asyncio
    async def test_listar_productos_tienda(self, ctrl):
        result = await ctrl.listar_productos_tienda()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_sincronizar_producto_tienda(self, ctrl):
        _, product = await ctrl.crear_producto(
            codigo="TIENDA-1", nombre="Prod Tienda", cantidad="5", precio="15.0"
        )
        success = await ctrl.sincronizar_producto(
            producto_id=product["id"], visible=True
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_crear_pedido_tienda(self, ctrl):
        success, _result = await ctrl.crear_pedido_tienda(
            cliente_nombre="Comprador",
            cliente_email="buyer@test.com",
            cliente_telefono="555-0000",
            direccion_envio="Calle 123",
            notas="Sin notas",
            items=[{"producto_id": 1, "cantidad": 1, "precio_unitario": 10, "subtotal": 10}],
            total=10.0,
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_pedidos_tienda(self, ctrl):
        result = await ctrl.obtener_pedidos_tienda()
        assert isinstance(result, list)
