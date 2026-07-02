"""Tests for RBAC permissions: Perm catalog, role defaults, decorator."""

from __future__ import annotations

import pytest

from services.permissions import (
    ALL_PERMISSION_KEYS,
    PERMISSIONS_BY_MODULE,
    ROLE_DEFAULT_PERMISSIONS,
    Perm,
    PermissionException,
    require_permission,
)
from utils.exceptions import InventarioException


class TestPermCatalog:
    def test_all_keys_are_strings(self):
        for key in ALL_PERMISSION_KEYS:
            assert isinstance(key, str)
            assert "." in key

    def test_all_keys_have_module_and_action(self):
        for key in ALL_PERMISSION_KEYS:
            parts = key.split(".")
            assert len(parts) == 2

    def test_permissions_by_module_matches_all_keys(self):
        flat = [item["clave"] for module in PERMISSIONS_BY_MODULE.values() for item in module]
        assert sorted(flat) == sorted(ALL_PERMISSION_KEYS)

    def test_permissions_by_module_descriptions_not_empty(self):
        for module, items in PERMISSIONS_BY_MODULE.items():
            for item in items:
                assert item["descripcion"], f"Missing description for {item['clave']}"

    def test_perm_constants_match_keys(self):
        perm_attrs = [v for k, v in vars(Perm).items() if not k.startswith("_")]
        perm_set = set(perm_attrs)
        key_set = set(ALL_PERMISSION_KEYS)
        assert perm_set == key_set, f"Missing: {key_set - perm_set}. Extra: {perm_set - key_set}"


class TestRoleDefaults:
    def test_admin_has_all_permissions(self):
        assert ROLE_DEFAULT_PERMISSIONS["admin"] == set(ALL_PERMISSION_KEYS)

    def test_operador_has_subset(self):
        op_perms = ROLE_DEFAULT_PERMISSIONS["operador"]
        assert len(op_perms) < len(ALL_PERMISSION_KEYS)
        assert Perm.PRODUCTOS_LEER in op_perms
        assert Perm.PRODUCTOS_CREAR in op_perms
        assert Perm.DASHBOARD_VER in op_perms
        # Admin-only permissions not in operador
        assert Perm.USUARIOS_GESTIONAR not in op_perms

    def test_viewer_has_read_only(self):
        viewer_perms = ROLE_DEFAULT_PERMISSIONS["viewer"]
        assert Perm.PRODUCTOS_LEER in viewer_perms
        assert Perm.PRODUCTOS_CREAR not in viewer_perms
        assert Perm.USUARIOS_GESTIONAR not in viewer_perms

    def test_all_roles_exist(self):
        assert set(ROLE_DEFAULT_PERMISSIONS.keys()) == {"admin", "operador", "viewer"}


class TestRequirePermissionDecorator:
    def test_decorator_allows_with_permission(self):
        class FakeController:
            def __init__(self):
                self.current_user_permissions = {Perm.PRODUCTOS_ELIMINAR}
                self.current_user = "admin"

            @require_permission(Perm.PRODUCTOS_ELIMINAR)
            async def delete_product(self):
                return "deleted"

        import asyncio
        ctrl = FakeController()
        result = asyncio.run(ctrl.delete_product())
        assert result == "deleted"

    def test_decorator_raises_without_permission(self):
        class FakeController:
            def __init__(self):
                self.current_user_permissions = {Perm.PRODUCTOS_LEER}
                self.current_user = "viewer"

            @require_permission(Perm.PRODUCTOS_ELIMINAR)
            async def delete_product(self):
                return "deleted"

        import asyncio
        ctrl = FakeController()
        with pytest.raises(PermissionException, match="Sin permiso"):
            asyncio.run(ctrl.delete_product())

    def test_decorator_sync_function(self):
        class FakeController:
            def __init__(self):
                self.current_user_permissions = {Perm.PRODUCTOS_LEER}
                self.current_user = "viewer"

            @require_permission(Perm.PRODUCTOS_LEER)
            def read_product(self):
                return "read"

        ctrl = FakeController()
        assert ctrl.read_product() == "read"

    def test_decorator_sync_raises_without_permission(self):
        class FakeController:
            def __init__(self):
                self.current_user_permissions = set()
                self.current_user = "viewer"

            @require_permission(Perm.PRODUCTOS_LEER)
            def read_product(self):
                return "read"

        ctrl = FakeController()
        with pytest.raises(PermissionException):
            ctrl.read_product()

    def test_permission_exception_inherits(self):
        assert issubclass(PermissionException, InventarioException)
