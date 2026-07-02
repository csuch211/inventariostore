"""Tests for AutomationController."""

from __future__ import annotations

import pytest

from services.permissions import Perm


class TestAutomationController:
    @pytest.mark.asyncio
    async def test_obtener_config(self, ctrl):
        result = await ctrl.obtener_config_automation()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_guardar_config(self, ctrl):
        success = await ctrl.guardar_config_automation("model", "prophet")
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_pronosticos(self, ctrl):
        result = await ctrl.obtener_pronosticos()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_obtener_clasificaciones_abc(self, ctrl):
        result = await ctrl.obtener_clasificacion_abc()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_obtener_sugerencias_precio(self, ctrl):
        result = await ctrl.obtener_sugerencias_precio()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_ejecutar_pronostico(self, ctrl):
        ctrl.current_user_permissions = {Perm.AUTOMATION_EJECUTAR}
        result = await ctrl.generar_pronosticos_demanda()
        assert isinstance(result, int)
