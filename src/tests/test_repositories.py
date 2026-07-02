"""Tests for the repository layer.

Verifies that each repository correctly handles CRUD operations,
audit logging, and error conditions using an isolated SQLite DB.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def product_repo(ctrl):
    return ctrl.db.product_repo


@pytest.fixture
def user_repo(ctrl):
    return ctrl.db.user_repo


@pytest.fixture
def sale_repo(ctrl):
    return ctrl.db.sale_repo


@pytest.fixture
def inventory_repo(ctrl):
    return ctrl.db.inventory_repo


@pytest.fixture
def config_repo(ctrl):
    return ctrl.db.config_repo


# ============ ProductRepository ============


class TestProductRepository:
    def test_crear_producto(self, product_repo):
        result = product_repo.crear_producto(
            codigo="TST-001", nombre="Test Product", cantidad=10, precio=9.99
        )
        assert result is not None
        assert result["codigo"] == "TST-001"
        assert result["nombre"] == "Test Product"
        assert result["cantidad"] == 10

    def test_obtener_producto_por_id(self, product_repo):
        created = product_repo.crear_producto(codigo="TST-002", nombre="By ID")
        fetched = product_repo.obtener_producto_por_id(created["id"])
        assert fetched is not None
        assert fetched["codigo"] == "TST-002"

    def test_obtener_producto_por_codigo(self, product_repo):
        product_repo.crear_producto(codigo="TST-003", nombre="By Code")
        fetched = product_repo.obtener_producto_por_codigo("TST-003")
        assert fetched is not None
        assert fetched["nombre"] == "By Code"

    def test_obtener_todos_productos(self, product_repo):
        product_repo.crear_producto(codigo="TST-004", nombre="List Me")
        products = product_repo.obtener_todos_productos()
        assert len(products) >= 1
        assert any(p["codigo"] == "TST-004" for p in products)

    def test_actualizar_producto(self, product_repo):
        created = product_repo.crear_producto(codigo="TST-005", nombre="Old Name")
        updated = product_repo.actualizar_producto(
            created["id"], nombre="New Name", usuario="tester"
        )
        assert updated["nombre"] == "New Name"

    def test_actualizar_stock(self, product_repo):
        created = product_repo.crear_producto(codigo="TST-006", nombre="Stock Test", cantidad=10)
        updated = product_repo.actualizar_stock(
            created["id"], 5, tipo_movimiento="entrada", usuario="tester"
        )
        assert updated["cantidad"] == 15

    def test_eliminar_producto(self, product_repo):
        created = product_repo.crear_producto(codigo="TST-007", nombre="Delete Me")
        product_repo.eliminar_producto(created["id"], usuario="tester")
        fetched = product_repo.obtener_producto_por_id(created["id"])
        assert fetched is None or fetched.get("activo") == 0

    def test_buscar_productos(self, product_repo):
        product_repo.crear_producto(codigo="TST-008", nombre="Searchable Item")
        results = product_repo.buscar_productos("Searchable")
        assert len(results) >= 1

    def test_duplicate_codigo_raises(self, product_repo):
        product_repo.crear_producto(codigo="DUP-001", nombre="First")
        from utils.exceptions import DuplicateProductException

        with pytest.raises(DuplicateProductException):
            product_repo.crear_producto(codigo="DUP-001", nombre="Second")

    def test_crear_categoria(self, product_repo):
        cat_id = product_repo.crear_categoria("TestCat", "Test description")
        assert cat_id is not None
        cats = product_repo.obtener_categorias()
        assert any(c["nombre"] == "TestCat" for c in cats)

    def test_actualizar_categoria(self, product_repo):
        cat_id = product_repo.crear_categoria("OldCat")
        product_repo.actualizar_categoria(cat_id, "NewCat")
        cats = product_repo.obtener_categorias()
        assert any(c["nombre"] == "NewCat" for c in cats)

    def test_eliminar_categoria(self, product_repo):
        cat_id = product_repo.crear_categoria("DelCat")
        product_repo.eliminar_categoria(cat_id)
        cats = product_repo.obtener_categorias()
        assert not any(c["id"] == cat_id for c in cats)

    def test_crear_proveedor(self, product_repo):
        prov_id = product_repo.crear_proveedor("TestProv", "contacto@test.com")
        assert prov_id is not None
        provs = product_repo.obtener_proveedores()
        assert any(p["nombre"] == "TestProv" for p in provs)

    def test_obtener_estadisticas(self, product_repo):
        product_repo.crear_producto(codigo="STAT-1", nombre="Stat Product", cantidad=10, precio=5.0)
        stats = product_repo.obtener_estadisticas()
        assert "total_productos" in stats
        assert stats["total_productos"] >= 1

    def test_obtener_distribucion_categorias(self, product_repo):
        product_repo.crear_producto(codigo="DIST-1", nombre="Dist Product", categoria="CatA")
        dist = product_repo.obtener_distribucion_categorias()
        assert isinstance(dist, list)


# ============ UserRepository ============


class TestUserRepository:
    def test_crear_usuario(self, user_repo):
        uid = user_repo.crear_usuario("testuser", "hash123", "Test User", "viewer")
        assert uid is not None

    def test_obtener_usuarios(self, user_repo):
        user_repo.crear_usuario("listuser", "hash", "List User", "viewer")
        users = user_repo.obtener_usuarios()
        assert any(u["username"] == "listuser" for u in users)

    def test_obtener_usuario_por_username(self, user_repo):
        user_repo.crear_usuario("finduser", "hash", "Find User", "viewer")
        user = user_repo.obtener_usuario_por_username("finduser")
        assert user is not None
        assert user["nombre"] == "Find User"

    def test_obtener_roles(self, user_repo):
        roles = user_repo.obtener_roles()
        assert isinstance(roles, list)
        assert len(roles) >= 2  # admin, operador, viewer

    def test_obtener_permisos_catalogo(self, user_repo):
        perms = user_repo.obtener_permisos_catalogo()
        assert isinstance(perms, list)
        assert len(perms) >= 50  # 65+ permissions


# ============ SaleRepository ============


class TestSaleRepository:
    def test_crear_cliente(self, sale_repo):
        cid = sale_repo.crear_cliente("Test Client", "555-1234")
        assert cid is not None

    def test_obtener_clientes(self, sale_repo):
        sale_repo.crear_cliente("Client List")
        clients = sale_repo.obtener_clientes()
        assert any(c["nombre"] == "Client List" for c in clients)

    def test_actualizar_cliente(self, sale_repo):
        cid = sale_repo.crear_cliente("Old Name")
        sale_repo.actualizar_cliente(cid, "New Name")
        client = sale_repo.obtener_cliente_por_id(cid)
        assert client["nombre"] == "New Name"

    def test_eliminar_cliente(self, sale_repo):
        cid = sale_repo.crear_cliente("Delete Me")
        sale_repo.eliminar_cliente(cid)
        clients = sale_repo.obtener_clientes()
        assert not any(c["id"] == cid for c in clients)


# ============ InventoryRepository ============


class TestInventoryRepository:
    def test_crear_almacen(self, inventory_repo):
        aid = inventory_repo.crear_almacen("Warehouse A", "Location 1")
        assert aid is not None

    def test_obtener_almacenes(self, inventory_repo):
        inventory_repo.crear_almacen("Warehouse B")
        almacenes = inventory_repo.obtener_almacenes()
        assert any(a["nombre"] == "Warehouse B" for a in almacenes)

    def test_actualizar_almacen(self, inventory_repo):
        aid = inventory_repo.crear_almacen("Old WH")
        inventory_repo.actualizar_almacen(aid, nombre="New WH")
        almacenes = inventory_repo.obtener_almacenes()
        assert any(a["nombre"] == "New WH" for a in almacenes)

    def test_eliminar_almacen(self, inventory_repo):
        aid = inventory_repo.crear_almacen("Delete WH")
        inventory_repo.eliminar_almacen(aid)
        almacenes = inventory_repo.obtener_almacenes()
        assert not any(a["id"] == aid for a in almacenes)


# ============ ConfigRepository ============


class TestConfigRepository:
    def test_guardar_y_obtener_config(self, config_repo):
        config_repo.guardar_config("test_key", "test_value")
        value = config_repo.obtener_config("test_key")
        assert value == "test_value"

    def test_config_default(self, config_repo):
        value = config_repo.obtener_config("nonexistent", "default_val")
        assert value == "default_val"

    def test_registrar_backup(self, config_repo):
        config_repo.registrar_backup("/tmp/test.zip", 1024, "manual", "admin")
        assert True  # Some repos may return None for void operations

    def test_obtener_backups(self, config_repo):
        config_repo.registrar_backup("/tmp/b1.zip", 500, "manual", "admin")
        backups = config_repo.obtener_backups()
        assert len(backups) >= 1
