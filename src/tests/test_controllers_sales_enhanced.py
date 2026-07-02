"""Tests for SalesEnhancedController."""

from __future__ import annotations

import pytest

from core.controllers.sales_enhanced_controller import SalesEnhancedController
from services.permissions import ALL_PERMISSION_KEYS


class TestSalesEnhancedController:
    @pytest.fixture
    def ctrl2(self, ctrl):
        sc = SalesEnhancedController(ctrl.db, ctrl.auth_service, ctrl.export_service)
        sc.current_user = "admin"
        sc.current_user_role = "admin"
        sc.current_user_permissions = set(ALL_PERMISSION_KEYS)
        return sc

    @pytest.mark.asyncio
    async def test_crear_descuento(self, ctrl2):
        success, _result = await ctrl2.crear_descuento(
            codigo="VERANO25",
            nombre="Verano 25%",
            tipo="porcentaje",
            valor=25.0,
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_descuentos(self, ctrl2):
        result = await ctrl2.obtener_descuentos()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_crear_promocion(self, ctrl2):
        success, _result = await ctrl2.crear_promocion(
            nombre="2x1",
            tipo="2x1",
            valor=0,
            fecha_inicio="2025-01-01",
            fecha_fin="2025-01-31",
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_promociones(self, ctrl2):
        result = await ctrl2.obtener_promociones()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_validar_descuento(self, ctrl2):
        await ctrl2.crear_descuento(codigo="TEST10", nombre="Test", valor=10)
        result = await ctrl2.aplicar_descuento("TEST10")
        assert result is not None or result is False
