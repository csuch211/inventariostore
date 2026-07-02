"""Tests for HRController."""

from __future__ import annotations

import pytest


class TestHRController:
    @pytest.mark.asyncio
    async def test_crear_empleado(self, ctrl):
        success, result = await ctrl.crear_empleado(
            nombre="Carlos", apellido="López", email="carlos@hr.com"
        )
        assert success is True
        assert "id" in result

    @pytest.mark.asyncio
    async def test_obtener_empleados(self, ctrl):
        result = await ctrl.obtener_empleados()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_crear_nomina(self, ctrl):
        _, emp = await ctrl.crear_empleado(nombre="Ana", apellido="HR")
        success, _result = await ctrl.crear_nomina(
            empleado_id=emp["id"],
            periodo_inicio="2025-01-01",
            periodo_fin="2025-01-31",
            salario_bruto=50000,
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_nominas(self, ctrl):
        result = await ctrl.obtener_nomina()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_solicitar_vacacion(self, ctrl):
        _, emp = await ctrl.crear_empleado(nombre="Luis", apellido="Vac")
        success, _result = await ctrl.solicitar_vacaciones(
            empleado_id=emp["id"],
            fecha_inicio="2025-06-01",
            fecha_fin="2025-06-15",
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_crear_evaluacion(self, ctrl):
        _, emp = await ctrl.crear_empleado(nombre="Eval", apellido="Employee")
        from datetime import date
        success, _result = await ctrl.crear_evaluacion(
            empleado_id=emp["id"],
            evaluador="admin",
            fecha=date.today().isoformat(),
            periodo="2025-Q1",
            puntuacion=4.5,
        )
        assert success is True
