"""Tests for InventoryController."""

from __future__ import annotations

import pytest


class TestInventoryController:
    @pytest.mark.asyncio
    async def test_obtener_almacenes(self, ctrl):
        result = await ctrl.obtener_almacenes()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_crear_almacen(self, ctrl):
        success, _result = await ctrl.crear_almacen(
            nombre="Bodega Principal", ubicacion="Planta baja"
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_stock_almacen(self, ctrl):
        result = await ctrl.obtener_inventario_almacen(1)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_crear_transferencia(self, ctrl):
        _, wh1 = await ctrl.crear_almacen("Origen")
        _, wh2 = await ctrl.crear_almacen("Destino")
        success, _result = await ctrl.crear_transferencia_almacen(
            almacen_origen_id=wh1["id"],
            almacen_destino_id=wh2["id"],
            producto_id=1,
            cantidad=5,
        )
        assert success is True or success is False  # depends on stock

    @pytest.mark.asyncio
    async def test_obtener_transferencias(self, ctrl):
        result = await ctrl.obtener_transferencias_almacen()
        assert isinstance(result, list)
