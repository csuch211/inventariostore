"""Tests for CartRepository: carts, items, checkout."""

from __future__ import annotations

import pytest


@pytest.fixture
def cart_repo(ctrl):
    return ctrl.db.cart_repo


@pytest.fixture(scope="session")
def product_id(seeded_ctrl):
    """Create a product for cart tests."""
    p = seeded_ctrl.db.product_repo.crear_producto(
        codigo="CART-PROD", nombre="Cart Product", cantidad=20, precio=10.0
    )
    return p["id"]


class TestCartRepository:
    def test_crear_carrito(self, cart_repo):
        cart_id = cart_repo.crear_carrito("testuser")
        assert cart_id > 0

    def test_obtener_carrito_activo(self, cart_repo):
        cart_repo.crear_carrito("user1")
        cart = cart_repo.obtener_carrito_activo("user1")
        assert cart is not None
        assert cart["estado"] == "activo"

    def test_obtener_o_crear_carrito_existing(self, cart_repo):
        cart_repo.crear_carrito("user2")
        cart = cart_repo.obtener_o_crear_carrito("user2")
        assert cart["estado"] == "activo"

    def test_obtener_o_crear_carrito_new(self, cart_repo):
        cart = cart_repo.obtener_o_crear_carrito("newuser")
        assert cart["id"] > 0
        assert cart["estado"] == "activo"

    def test_agregar_item(self, cart_repo, product_id):
        cart_id = cart_repo.crear_carrito("buyer")
        item_id = cart_repo.agregar_item(cart_id, product_id, 2, 10.0)
        assert item_id is not None

    def test_agregar_item_existing_increases_qty(self, cart_repo, product_id):
        cart_id = cart_repo.crear_carrito("buyer2")
        cart_repo.agregar_item(cart_id, product_id, 2, 10.0)
        cart_repo.agregar_item(cart_id, product_id, 3, 10.0)
        items = cart_repo.obtener_items(cart_id)
        assert len(items) == 1
        assert items[0]["cantidad"] == 5

    def test_obtener_items(self, cart_repo, product_id):
        cart_id = cart_repo.crear_carrito("items_user")
        cart_repo.agregar_item(cart_id, product_id, 1, 10.0)
        items = cart_repo.obtener_items(cart_id)
        assert len(items) == 1
        assert items[0]["producto_id"] == product_id

    def test_eliminar_item(self, cart_repo, product_id):
        cart_id = cart_repo.crear_carrito("del_user")
        item_id = cart_repo.agregar_item(cart_id, product_id, 1, 10.0)
        cart_repo.eliminar_item(item_id)
        items = cart_repo.obtener_items(cart_id)
        assert len(items) == 0

    def test_actualizar_cantidad_item(self, cart_repo, product_id):
        cart_id = cart_repo.crear_carrito("qty_user")
        item_id = cart_repo.agregar_item(cart_id, product_id, 1, 10.0)
        cart_repo.actualizar_cantidad(item_id, 5)
        items = cart_repo.obtener_items(cart_id)
        assert items[0]["cantidad"] == 5

    def test_cerrar_carrito(self, cart_repo):
        cart_id = cart_repo.crear_carrito("close_user")
        cart_repo.marcar_convertido(cart_id)
        cart = cart_repo.obtener_carrito_activo("close_user")
        assert cart is None

    def test_carrito_con_cliente(self, cart_repo):
        cart_id = cart_repo.crear_carrito("client_user", cliente_id=1)
        assert cart_id > 0
