"""Tests for CRMController."""

from __future__ import annotations

import pytest


class TestCRMController:
    @pytest.mark.asyncio
    async def test_crear_contacto(self, ctrl):
        success, result = await ctrl.crear_contacto(
            nombre="Juan", apellido="Pérez", email="juan@crm.com"
        )
        assert success is True
        assert "id" in result

    @pytest.mark.asyncio
    async def test_obtener_contactos(self, ctrl):
        result = await ctrl.obtener_contactos()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_crear_oportunidad(self, ctrl):
        success, contact = await ctrl.crear_contacto(nombre="Cliente", apellido="Oportunidad")
        assert success is True
        success, _result = await ctrl.crear_oportunidad(
            contacto_id=contact["id"], titulo="Venta CRM", monto=10000.0
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_oportunidades(self, ctrl):
        result = await ctrl.obtener_oportunidades()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_crear_actividad(self, ctrl):
        _, contact = await ctrl.crear_contacto(nombre="Act", apellido="Test")
        success, _result = await ctrl.crear_actividad(
            tipo="llamada", titulo="Follow up", contacto_id=contact["id"]
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_actividades(self, ctrl):
        result = await ctrl.obtener_actividades()
        assert isinstance(result, list)
