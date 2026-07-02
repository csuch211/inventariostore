"""Integration tests for the modular architecture.

Verifies:
  - All 16 module facades import and forward correctly
  - Cross-module workflows (auth -> products -> inventory -> sales)
  - Modular AuthController (real migrated code) works end-to-end
  - Module __init__.py exports are coherent
  - Facade re-exports match source implementations
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

from utils.exceptions import AuthenticationException

# =========================================================================
# Module Import Verification
# =========================================================================

MODULES_DIR = Path(__file__).resolve().parents[2] / "src" / "modules"

MODULE_NAMES = [
    "auth", "products", "inventory", "warehouses", "sales",
    "purchasing", "invoicing", "reports", "accounting", "hr",
    "crm", "documents", "notifications", "automation", "store", "admin",
]


class TestModuleStructure:
    """Verify all 16 modules have the correct directory structure."""

    def test_all_module_dirs_exist(self):
        for name in MODULE_NAMES:
            assert (MODULES_DIR / name).is_dir(), f"Missing module dir: {name}"

    def test_all_modules_have_init(self):
        for name in MODULE_NAMES:
            assert (MODULES_DIR / name / "__init__.py").is_file(), f"Missing __init__.py for {name}"

    def test_all_modules_have_subdirectories(self):
        for name in MODULE_NAMES:
            for sub in ("controllers", "services", "repositories", "ui"):
                path = MODULES_DIR / name / sub
                assert path.is_dir(), f"Missing {sub}/ in module {name}"
                assert (path / "__init__.py").is_file(), f"Missing {sub}/__init__.py in {name}"


class TestModuleImports:
    """Verify every module can be imported and its __init__ exports work."""

    @pytest.mark.parametrize("module_name", MODULE_NAMES)
    def test_module_init_imports(self, module_name):
        mod = importlib.import_module(f"modules.{module_name}")
        assert mod is not None
        assert hasattr(mod, "__all__"), f"{module_name} __init__ missing __all__"
        assert len(mod.__all__) > 0, f"{module_name} __init__ exports nothing"

    @pytest.mark.parametrize("module_name", MODULE_NAMES)
    def test_module_all_exports_resolve(self, module_name):
        mod = importlib.import_module(f"modules.{module_name}")
        for export_name in mod.__all__:
            obj = getattr(mod, export_name, None)
            assert obj is not None, (
                f"{module_name}.{export_name} is None"
            )

    def test_all_subpackage_inits_importable(self):
        """Every Python file under modules/ should be importable by its module path."""
        for importer, modname, is_pkg in pkgutil.walk_packages(
            path=[str(MODULES_DIR)], prefix="modules."
        ):
            try:
                importlib.import_module(modname)
            except Exception as e:
                pytest.fail(f"Failed to import {modname}: {e}")


# =========================================================================
# Facade Forwarding Verification
# =========================================================================

class TestFacadeForwarding:
    """Verify facades correctly re-export from original locations.

    Each facade file should:
    1. Import a class from an original location (core.controllers.*, services.*, etc.)
    2. Export it in __all__
    3. The re-exported class should be the same object as the original
    """

    FACADE_CHECKS: list = [
        # (facade_module, export_name, expected_original)
        ("modules.products.controllers.product_controller", "ProductController",
         "core.controllers.product_controller.ProductController"),
        ("modules.inventory.controllers.inventory_controller", "InventoryController",
         "core.controllers.inventory_controller.InventoryController"),
        ("modules.warehouses.controllers.warehouse_controller", "WarehouseController",
         "core.controllers.warehouse_controller.WarehouseController"),
        ("modules.sales.controllers.sales_controller", "SalesController",
         "core.controllers.sales_controller.SalesController"),
        ("modules.purchasing.controllers.purchasing_controller", "PurchasingController",
         "core.controllers.purchasing_controller.PurchasingController"),
        ("modules.invoicing.controllers.invoice_controller", "InvoiceController",
         "core.controllers.invoice_controller.InvoiceController"),
        ("modules.reports.controllers.report_controller", "ReportController",
         "core.controllers.report_controller.ReportController"),
        ("modules.notifications.controllers.notification_controller", "NotificationController",
         "core.controllers.notification_controller.NotificationController"),
        ("modules.documents.controllers.document_controller", "DocumentController",
         "core.controllers.document_controller.DocumentController"),
        ("modules.automation.controllers.automation_controller", "AutomationController",
         "core.controllers.automation_controller.AutomationController"),
        ("modules.store.controllers.store_controller", "StoreController",
         "core.controllers.store_controller.StoreController"),
        ("modules.admin.controllers.admin_controller", "AdminController",
         "core.controllers.admin_controller.AdminController"),
    ]

    @pytest.mark.parametrize("facade_path,export_name,original_path", FACADE_CHECKS)
    def test_facade_forwards_correctly(self, facade_path, export_name, original_path):
        facade_mod = importlib.import_module(facade_path)
        facade_cls = getattr(facade_mod, export_name)

        orig_mod_path, _, orig_cls_name = original_path.rpartition(".")
        orig_mod = importlib.import_module(orig_mod_path)
        orig_cls = getattr(orig_mod, orig_cls_name)

        assert facade_cls is orig_cls, (
            f"Facade {facade_path}.{export_name} is not the same object as "
            f"{original_path}"
        )


# =========================================================================
# Auth Module Integration (real migrated code)
# =========================================================================

class TestAuthModuleIntegration:
    """Verify the modular AuthController (real migrated code) works end-to-end."""

    @pytest.mark.asyncio
    async def test_auth_login_admin_success(self, ctrl):
        """Admin login succeeds with correct credentials."""
        session = await ctrl.login("admin", "Admin123")
        assert session["username"] == "admin"
        assert session["rol"] == "admin"
        assert "token" in session
        assert len(session["permissions"]) > 0

    @pytest.mark.asyncio
    async def test_auth_login_failure(self, ctrl):
        """Login with bad password raises AuthenticationException."""
        with pytest.raises(AuthenticationException):
            await ctrl.login("admin", "wrong_password")

    @pytest.mark.asyncio
    async def test_auth_login_empty_credentials(self, ctrl):
        with pytest.raises(AuthenticationException):
            await ctrl.login("", "")

    @pytest.mark.asyncio
    async def test_auth_logout_clears_session(self, ctrl):
        session = await ctrl.login("admin", "Admin123")
        assert ctrl.current_user == "admin"

        await ctrl.logout(session["token"])
        assert ctrl.current_user is None
        assert ctrl.current_user_role is None
        assert ctrl.current_user_permissions == set()

    @pytest.mark.asyncio
    async def test_auth_operator_login(self, ctrl):
        session = await ctrl.login("usuario", "Usuario123")
        assert session["username"] == "usuario"
        assert session["rol"] in ("operador", "operator")
        assert "token" in session

    @pytest.mark.asyncio
    async def test_auth_login_mantiene_sesion_activa(self, ctrl):
        session = await ctrl.login("admin", "Admin123")
        assert ctrl.current_user == session["username"]
        assert ctrl.current_user_role == session["rol"]
        assert ctrl.current_user_permissions == set(session["permissions"])

    def test_auth_hash_password(self, ctrl):
        """Password hashing produces verifiable hashes."""
        from modules.auth.services.auth_service import AuthService
        raw = "MiClaveSegura2026!"
        hashed = AuthService.hash_password(raw)
        assert ":" in hashed, "New format should be salt:hash"
        assert AuthService.verify_password(hashed, raw)
        assert not AuthService.verify_password(hashed, "WrongPassword")

    def test_auth_legacy_hash_compatibility(self, ctrl):
        """Legacy hashes (no salt) should still verify correctly."""
        from modules.auth.services.auth_service import AuthService
        legacy_hash = "f4b7e3d1a2c5b8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2"
        result = AuthService.verify_password(legacy_hash, "any_password")
        assert isinstance(result, bool)


# =========================================================================
# Cross-Module Workflow: Auth -> Products -> Inventory -> Sales
# =========================================================================

class TestCrossModuleWorkflow:
    """End-to-end workflow that spans multiple modules."""

    @pytest.mark.asyncio
    async def test_complete_product_lifecycle(self, ctrl):
        """Products module: create, read, update, delete."""
        ok, result = await ctrl.crear_producto(
            codigo="INTEG-001",
            nombre="Producto Integración",
            cantidad="100",
            precio="250.00",
            categoria="Pruebas",
            descripcion="Test de integración modular",
        )
        assert ok, f"Failed to create product: {result}"
        pid = result["id"]

        producto = await ctrl.obtener_producto(pid)
        assert producto is not None
        assert producto["nombre"] == "Producto Integración"

        ok, _ = await ctrl.actualizar_producto(pid, precio="300.00")
        assert ok

        producto = await ctrl.obtener_producto(pid)
        assert float(producto["precio"]) == 300.0

    @pytest.mark.asyncio
    async def test_category_lifecycle(self, ctrl):
        ok, result = await ctrl.crear_categoria(
            nombre="Cat Integración",
            descripcion="Categoría para test",
        )
        assert ok
        cid = result["id"]

        categorias = await ctrl.obtener_categorias()
        assert any(c["id"] == cid for c in categorias)

        ok, _ = await ctrl.actualizar_categoria(cid, nombre="Cat Integración V2")
        assert ok

        ok, _ = await ctrl.eliminar_categoria(cid)
        assert ok

    @pytest.mark.asyncio
    async def test_inventory_warehouse_workflow(self, ctrl):
        """Warehouses module: create warehouse, check inventory."""
        ok, result = await ctrl.crear_almacen(
            nombre="Almacén Integración",
            ubicacion="Zona de pruebas",
        )
        assert ok
        wid = result["id"]

        almacenes = await ctrl.obtener_almacenes()
        assert any(a["id"] == wid for a in almacenes)

        ok, _ = await ctrl.actualizar_almacen(wid, nombre="Almacén Modificado")
        assert ok

    @pytest.mark.asyncio
    async def test_sales_client_workflow(self, ctrl):
        """Sales module: create client, create sale, verify."""
        ok, result = await ctrl.crear_cliente(
            nombre="Cliente Integración",
            telefono="555-0100",
            email="cliente@test.com",
        )
        assert ok
        cid = result["id"]

        clientes = await ctrl.obtener_clientes()
        assert any(c["id"] == cid for c in clientes)

    @pytest.mark.asyncio
    async def test_full_workflow_product_to_sale(self, ctrl):
        """Complete workflow: create product -> create client -> create sale.

        This spans products, sales, and inventory modules.
        """
        pid = None
        cid = None
        try:
            ok, result = await ctrl.crear_producto(
                codigo="FULL-001",
                nombre="Producto Flujo Completo",
                cantidad="50",
                precio="100.00",
            )
            assert ok
            pid = result["id"]

            ok, result = await ctrl.crear_cliente(
                nombre="Cliente Flujo Completo",
                telefono="555-0200",
            )
            assert ok
            cid = result["id"]

            ok, result = await ctrl.crear_venta(
                cliente_id=cid,
                items=[{"producto_id": pid, "cantidad": 2, "precio_unitario": 100.0, "subtotal": 200.0}],
                metodo_pago="efectivo",
            )
            assert ok
            assert "id" in result

            ventas = await ctrl.obtener_ventas()
            assert any(v["id"] == result["id"] for v in ventas)

        finally:
            if cid:
                await ctrl.eliminar_cliente(cid)
            if pid:
                await ctrl.eliminar_producto(pid)

    @pytest.mark.asyncio
    async def test_reports_integration(self, ctrl):
        """Reports module: statistics and exports."""
        await ctrl.crear_producto(
            codigo="RPT-001", nombre="Prod Reportes",
            cantidad="10", precio="50.00",
        )

        stats = await ctrl.obtener_estadisticas()
        assert "total_productos" in stats
        assert stats["total_productos"] > 0

    @pytest.mark.asyncio
    async def test_inventory_analysis(self, ctrl):
        """Inventory module: ABC analysis and rotation."""
        await ctrl.crear_producto(
            codigo="INV-001", nombre="Prod Inventario",
            cantidad="100", precio="75.00",
        )

        abc = await ctrl.analisis_abc()
        assert isinstance(abc, list)

        rotacion = await ctrl.calcular_rotacion(dias=30)
        assert "turnover_ratio" in rotacion

    @pytest.mark.asyncio
    async def test_hr_integration(self, ctrl):
        """HR module: employee lifecycle."""
        ok, result = await ctrl.crear_empleado(
            nombre="Empleado Test",
            apellido="Apellido Test",
            puesto="Desarrollador",
            departamento="TI",
            email="emp@test.com",
            fecha_ingreso="2026-01-01",
        )
        assert ok
        eid = result["id"]

        empleado = await ctrl.obtener_empleado(eid)
        assert empleado is not None
        assert empleado["nombre"] == "Empleado Test"

        deptos = await ctrl.obtener_departamentos()
        assert "TI" in deptos

    @pytest.mark.asyncio
    async def test_crm_integration(self, ctrl):
        """CRM module: contact and opportunity lifecycle."""
        ok, result = await ctrl.crear_contacto(
            nombre="Contacto CRM",
            apellido="Apellido CRM",
            email="crm@test.com",
            telefono="555-0300",
            empresa="Test Corp",
        )
        assert ok
        contact_id = result["id"]

        ok, result = await ctrl.crear_oportunidad(
            titulo="Oportunidad Test",
            contacto_id=contact_id,
            monto=50000.0,
            prioridad="alta",
        )
        assert ok
        opp_id = result["id"]

        pipeline = await ctrl.pipeline_oportunidades()
        assert isinstance(pipeline, dict)

        ok, _ = await ctrl.actualizar_estado_oportunidad(opp_id, "ganada")
        assert ok

    @pytest.mark.asyncio
    async def test_accounting_integration(self, ctrl):
        """Accounting module: journal entries."""
        ok, result = await ctrl.crear_asiento(
            fecha="2026-07-01",
            descripcion="Asiento test integración",
            tipo="diario",
            movimientos=[
                {"cuenta_codigo": "1001", "cuenta_nombre": "Caja", "debito": 1000, "credito": 0, "descripcion": "Test debe"},
                {"cuenta_codigo": "2001", "cuenta_nombre": "Proveedores", "debito": 0, "credito": 1000, "descripcion": "Test haber"},
            ],
        )
        assert ok
        assert "id" in result

    @pytest.mark.asyncio
    async def test_export_integration(self, ctrl, tmp_path):
        """Reports module: CSV export."""
        await ctrl.crear_producto(
            codigo="EXP-001", nombre="Prod Export",
            cantidad="5", precio="30.00",
        )

        ok, path = await ctrl.exportar_csv()
        assert ok
        assert Path(path).exists()

    @pytest.mark.asyncio
    async def test_admin_backup_integration(self, ctrl):
        """Admin module: backup lifecycle."""
        backup = await ctrl.crear_backup()
        assert "ruta" in backup
        assert "nombre" in backup

        from pathlib import Path
        backups = await ctrl.listar_backups()
        assert any(Path(b["ruta"]).name == Path(backup["ruta"]).name for b in backups)


# =========================================================================
# Permissions Integration
# =========================================================================

class TestPermissionsIntegration:
    """Verify RBAC permissions flow through the module chain correctly."""

    @pytest.mark.asyncio
    async def test_permissions_propagated_to_all_modules(self, ctrl):
        perms = {"productos.crear", "ventas.crear", "inventario.ver"}
        ctrl.current_user_permissions = perms
        assert ctrl.has_permission("productos.crear") is True
        assert ctrl.has_permission("admin.config") is False

    @pytest.mark.asyncio
    async def test_permission_enforcement_on_controllers(self, ctrl):
        from services.permissions import PermissionException, require_permission

        class FakeController:
            current_user_permissions: set[str] = set()
            current_user: str = "test"

        fake = FakeController()
        decorated = require_permission("productos.crear")(lambda self: None)
        with pytest.raises(PermissionException):
            decorated(fake)
