"""Tests for StoreRepository: store config, products, orders."""

from __future__ import annotations

import pytest


@pytest.fixture
def store_repo(ctrl):
    return ctrl.db.store_repo


@pytest.fixture
def store_product_id(ctrl, store_repo):
    """Create a product and sync it to store."""
    prod = ctrl.db.product_repo.crear_producto(
        codigo="STORE-PROD", nombre="Store Product", cantidad=10, precio=25.0
    )
    store_repo.sincronizar_producto(prod["id"], visible=True, destacado=True)
    return prod["id"]


class TestStoreConfig:
    def test_guardar_y_obtener_config(self, store_repo):
        store_repo.guardar_config("store_name", "Mi Tienda")
        store_repo.guardar_config("currency", "MXN")
        config = store_repo.obtener_config()
        assert config.get("store_name") == "Mi Tienda"
        assert config.get("currency") == "MXN"

    def test_guardar_config_overwrite(self, store_repo):
        store_repo.guardar_config("key", "val1")
        store_repo.guardar_config("key", "val2")
        config = store_repo.obtener_config()
        assert config["key"] == "val2"


class TestStoreProducts:
    def test_sincronizar_producto(self, store_repo):
        result = store_repo.sincronizar_producto(
            producto_id=1, visible=True, descripcion_larga="Test"
        )
        assert result > 0

    def test_listar_productos_tienda(self, store_repo, store_product_id):
        productos = store_repo.listar_productos_tienda()
        assert isinstance(productos, list)
        assert len(productos) >= 1

    def test_listar_solo_visibles(self, store_repo):
        store_repo.sincronizar_producto(1, visible=False)
        store_repo.sincronizar_producto(2, visible=True)
        productos = store_repo.listar_productos_tienda(solo_visibles=True)
        assert all(p["visible"] == 1 for p in productos)

    def test_eliminar_producto_tienda(self, store_repo):
        store_repo.sincronizar_producto(99, visible=True)
        result = store_repo.eliminar_producto_tienda(99)
        assert result is None  # No actual product 99, but should not crash


class TestStoreOrders:
    def test_crear_pedido(self, store_repo):
        result = store_repo.crear_pedido(
            cliente_nombre="Comprador",
            cliente_email="buyer@test.com",
            cliente_telefono="555-0000",
            direccion_envio="Calle 123",
            notas="Sin notas",
            items=[{"producto_id": 1, "cantidad": 2, "precio_unitario": 25.0, "subtotal": 50.0}],
            total=50.0,
        )
        assert result > 0

    def test_obtener_pedidos(self, store_repo):
        store_repo.crear_pedido("A", "a@b.com", "555-0001", "Dir 1", "notas", 10, [{"producto_id": 1, "cantidad": 1, "precio_unitario": 10, "subtotal": 10}])
        pedidos = store_repo.obtener_pedidos()
        assert isinstance(pedidos, list)
        assert len(pedidos) >= 1

    def test_actualizar_estado_pedido(self, store_repo):
        created = store_repo.crear_pedido("B", "b@b.com", "555-0002", "Dir 2", "notas", 10, [{"producto_id": 1, "cantidad": 1, "precio_unitario": 10, "subtotal": 10}])
        store_repo.actualizar_estado_pedido(created, "enviado")
        pedidos = store_repo.obtener_pedidos()
        assert any(p["id"] == created and p["estado"] == "enviado" for p in pedidos)
