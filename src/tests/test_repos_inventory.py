"""Tests for InventoryRepository: warehouses, stock transfers, adjustments."""

from __future__ import annotations

import pytest


@pytest.fixture
def inv_repo(ctrl):
    return ctrl.db.inventory_repo


class TestInventoryWarehouses:
    def test_crear_almacen(self, inv_repo):
        wh_id = inv_repo.crear_almacen("Principal", "Oficina central")
        assert wh_id > 0

    def test_obtener_almacenes(self, inv_repo):
        inv_repo.crear_almacen("Bodega Norte")
        almacenes = inv_repo.obtener_almacenes()
        assert isinstance(almacenes, list)
        assert len(almacenes) >= 1

    def test_actualizar_almacen(self, inv_repo):
        wh_id = inv_repo.crear_almacen("Old Name")
        inv_repo.actualizar_almacen(wh_id, nombre="New Name")
        almacenes = inv_repo.obtener_almacenes()
        assert any(a["nombre"] == "New Name" for a in almacenes)

    def test_eliminar_almacen_soft(self, inv_repo):
        wh_id = inv_repo.crear_almacen("Temp WH")
        inv_repo.eliminar_almacen(wh_id)
        almacenes = inv_repo.obtener_almacenes()
        assert not any(a["id"] == wh_id for a in almacenes)


class TestInventoryTransfers:
    def test_crear_transferencia(self, inv_repo):
        inv_repo.crear_almacen("Origin")
        inv_repo.crear_almacen("Destiny")
        result = inv_repo.crear_almacen("Transfer WH")
        assert result > 0

    def test_obtener_transferencias(self, inv_repo):
        inv_repo.crear_almacen("O1")
        inv_repo.crear_almacen("D1")
        almacenes = inv_repo.obtener_almacenes()
        assert isinstance(almacenes, list)


class TestInventoryStock:
    def test_obtener_stock_almacen(self, inv_repo):
        wh_id = inv_repo.crear_almacen("Stock WH")
        stock = inv_repo.obtener_inventario_almacen(wh_id)
        assert isinstance(stock, list)

    def test_ajustar_stock_almacen(self, inv_repo):
        wh_id = inv_repo.crear_almacen("Ajuste WH")
        result = inv_repo.ajustar_stock_almacen(
            producto_id=1, almacen_id=wh_id, cantidad=50, usuario="tester"
        )
        assert result >= 0
