"""Tests for AccountingController."""

from __future__ import annotations

import pytest

from services.permissions import Perm, PermissionException


class TestAccountingController:
    @pytest.mark.asyncio
    async def test_crear_asiento_success(self, ctrl):
        ctrl.current_user_permissions.add(Perm.CONTABILIDAD_ASIENTOS)
        success, result = await ctrl.crear_asiento(
            fecha="2025-01-15",
            descripcion="Venta contable",
            tipo="venta",
            movimientos=[
                {"cuenta_codigo": "1101", "cuenta_nombre": "Caja", "debito": 1000, "credito": 0},
                {"cuenta_codigo": "4101", "cuenta_nombre": "Ventas", "debito": 0, "credito": 1000},
            ],
        )
        assert success is True
        assert "id" in result

    @pytest.mark.asyncio
    async def test_crear_asiento_unbalanced(self, ctrl):
        ctrl.current_user_permissions.add(Perm.CONTABILIDAD_ASIENTOS)
        success, _result = await ctrl.crear_asiento(
            fecha="2025-01-15",
            descripcion="Unbalanced",
            tipo="ajuste",
            movimientos=[
                {"cuenta_codigo": "1101", "cuenta_nombre": "Caja", "debito": 1000, "credito": 0},
                {"cuenta_codigo": "4101", "cuenta_nombre": "Ventas", "debito": 0, "credito": 500},
            ],
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_obtener_asiento(self, ctrl):
        ctrl.current_user_permissions.add(Perm.CONTABILIDAD_LEER)
        result = await ctrl.obtener_asiento(1)
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_listar_asientos(self, ctrl):
        ctrl.current_user_permissions.add(Perm.CONTABILIDAD_LEER)
        result = await ctrl.obtener_asientos()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_permission_denied(self, ctrl):
        ctrl.current_user_permissions = set()
        with pytest.raises(PermissionException, match="Sin permiso"):
            await ctrl.crear_asiento(
                fecha="2025-01-15", descripcion="X", tipo="venta", movimientos=[]
            )
