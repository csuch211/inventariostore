"""Tests for domain controllers.

Verifies that each domain controller correctly delegates to repositories
and handles business logic properly.
"""

from __future__ import annotations

import pytest
from services.permissions import Perm


# ============ ProductController ============


class TestProductController:
    @pytest.mark.asyncio
    async def test_crear_producto(self, ctrl):
        success, product = await ctrl.crear_producto(
            codigo="PC-001", nombre="Test Product", cantidad="10", precio="9.99"
        )
        assert success is True
        assert product["codigo"] == "PC-001"

    @pytest.mark.asyncio
    async def test_obtener_todos_productos(self, ctrl):
        await ctrl.crear_producto(
            codigo="PC-002", nombre="List Product", cantidad="5", precio="5.0"
        )
        products = await ctrl.obtener_todos_productos()
        assert len(products) >= 1

    @pytest.mark.asyncio
    async def test_buscar_productos(self, ctrl):
        await ctrl.crear_producto(
            codigo="PC-003", nombre="Searchable Product", cantidad="1", precio="1.0"
        )
        results = await ctrl.buscar_productos("Searchable")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_obtener_categorias(self, ctrl):
        cats = await ctrl.obtener_categorias()
        assert isinstance(cats, list)

    @pytest.mark.asyncio
    async def test_obtener_proveedores(self, ctrl):
        provs = await ctrl.obtener_proveedores()
        assert isinstance(provs, list)

    @pytest.mark.asyncio
    async def test_obtener_estadisticas(self, ctrl):
        stats = await ctrl.obtener_estadisticas()
        assert "total_productos" in stats


# ============ SalesController ============


class TestSalesController:
    @pytest.mark.asyncio
    async def test_obtener_clientes(self, ctrl):
        clients = await ctrl.obtener_clientes()
        assert isinstance(clients, list)

    @pytest.mark.asyncio
    async def test_obtener_ventas(self, ctrl):
        sales = await ctrl.obtener_ventas()
        assert isinstance(sales, list)


# ============ WarehouseController ============


class TestWarehouseController:
    @pytest.mark.asyncio
    async def test_obtener_almacenes(self, ctrl):
        almacenes = await ctrl.obtener_almacenes()
        assert isinstance(almacenes, list)

    @pytest.mark.asyncio
    async def test_obtener_alertas_stock(self, ctrl):
        alerts = await ctrl.obtener_alertas_stock()
        assert isinstance(alerts, list)


# ============ ReportController ============


class TestReportController:
    @pytest.mark.asyncio
    async def test_obtener_distribucion_categorias(self, ctrl):
        dist = await ctrl.obtener_distribucion_categorias()
        assert isinstance(dist, list)

    @pytest.mark.asyncio
    async def test_obtener_top_productos_stock(self, ctrl):
        top = await ctrl.obtener_top_productos_stock(limit=5)
        assert isinstance(top, list)

    @pytest.mark.asyncio
    async def test_exportar_csv(self, ctrl):
        await ctrl.crear_producto(
            codigo="EXP-1", nombre="Export Product", cantidad="5", precio="10.0"
        )
        success, path = await ctrl.exportar_csv()
        assert success is True

    @pytest.mark.asyncio
    async def test_exportar_json(self, ctrl):
        await ctrl.crear_producto(
            codigo="EXP-2", nombre="Export JSON Product", cantidad="3", precio="7.5"
        )
        success, path = await ctrl.exportar_json()
        assert success is True


# ============ AdminController ============


class TestAdminController:
    @pytest.mark.asyncio
    async def test_obtener_usuarios_con_roles(self, ctrl):
        users = await ctrl.obtener_usuarios_con_roles()
        assert isinstance(users, list)
        assert len(users) >= 2  # admin + usuario

    @pytest.mark.asyncio
    async def test_obtener_roles(self, ctrl):
        roles = await ctrl.obtener_roles()
        assert isinstance(roles, list)
        assert len(roles) >= 2

    @pytest.mark.asyncio
    async def test_obtener_permisos_catalogo(self, ctrl):
        perms = await ctrl.obtener_permisos_catalogo()
        assert isinstance(perms, list)
        assert len(perms) >= 50


# ============ Phase1Controller ============


class TestPhase1Controller:
    @pytest.mark.asyncio
    async def test_obtener_kpis_dashboard(self, ctrl):
        kpis = await ctrl.obtener_kpis_dashboard()
        assert isinstance(kpis, dict)

    @pytest.mark.asyncio
    async def test_crear_lote(self, ctrl):
        success, product = await ctrl.crear_producto(
            codigo="LOT-001", nombre="Lote Product", cantidad="10", precio="5.0"
        )
        assert success is True
        success, lote = await ctrl.crear_lote(product["id"], "LOT-001-A", 10)
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_lotes(self, ctrl):
        lotes = await ctrl.obtener_lotes()
        assert isinstance(lotes, list)

    @pytest.mark.asyncio
    async def test_crear_lista_precio(self, ctrl):
        success, lista = await ctrl.crear_lista_precio("Mayoreo", "Precios de mayoreo")
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_impuestos(self, ctrl):
        impuestos = await ctrl.obtener_impuestos()
        assert isinstance(impuestos, list)


# ============ Phase3Controller ============


class TestPhase3Controller:
    @pytest.mark.asyncio
    async def test_obtener_variantes(self, ctrl):
        variantes = await ctrl.obtener_variantes()
        assert isinstance(variantes, list)

    @pytest.mark.asyncio
    async def test_obtener_plantillas_reporte(self, ctrl):
        plantillas = await ctrl.obtener_plantillas_reporte()
        assert isinstance(plantillas, list)

    @pytest.mark.asyncio
    async def test_obtener_idiomas_disponibles(self, ctrl):
        idiomas = await ctrl.obtener_idiomas_disponibles()
        assert isinstance(idiomas, list)
        assert len(idiomas) >= 2  # es + en

    @pytest.mark.asyncio
    async def test_obtener_jobs_push(self, ctrl):
        jobs = await ctrl.obtener_jobs_push()
        assert isinstance(jobs, list)


# ============ Facade (InventarioController) ============


class TestInventarioControllerFacade:
    @pytest.mark.asyncio
    async def test_login_sets_permissions(self, ctrl):
        await ctrl.login("admin", "Admin123")
        assert ctrl.current_user == "admin"
        assert len(ctrl.current_user_permissions) > 0

    @pytest.mark.asyncio
    async def test_permission_check(self, ctrl):
        assert ctrl.has_permission(Perm.DASHBOARD_VER)
        assert ctrl.has_permission(Perm.PRODUCTOS_LEER)

    @pytest.mark.asyncio
    async def test_no_permission_check(self, ctrl):
        ctrl.current_user_permissions = set()
        assert not ctrl.has_permission(Perm.DASHBOARD_VER)

    @pytest.mark.asyncio
    async def test_sync_children_on_permissions_change(self, ctrl):
        ctrl.current_user_permissions = {Perm.DASHBOARD_VER}
        assert Perm.DASHBOARD_VER in ctrl._phase1.current_user_permissions
        assert Perm.DASHBOARD_VER in ctrl._products.current_user_permissions
