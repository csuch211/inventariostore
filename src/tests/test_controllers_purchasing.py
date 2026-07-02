"""Tests for PurchasingController."""

from __future__ import annotations

import pytest


class TestPurchasingController:
    @pytest.mark.asyncio
    async def test_crear_cotizacion(self, ctrl):
        _, prov = await ctrl.crear_proveedor("Prov Cot", email="cot@test.com")
        items = [{"producto_id": 1, "cantidad": 10, "precio_unitario": 15.0}]
        success, result = await ctrl.crear_cotizacion(
            proveedor_id=prov["id"], items=items
        )
        assert success is True
        assert result["numero"].startswith("COT-")

    @pytest.mark.asyncio
    async def test_obtener_cotizaciones(self, ctrl):
        result = await ctrl.obtener_cotizaciones()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_registrar_recepcion(self, ctrl):
        _, prov = await ctrl.crear_proveedor("Prov Rec", email="rec@test.com")
        items = [{"producto_id": 1, "cantidad_recibida": 5}]
        success, result = await ctrl.crear_recepcion(
            proveedor_id=prov["id"], items=items
        )
        assert success is True
        assert result["numero"].startswith("REC-")

    @pytest.mark.asyncio
    async def test_evaluar_proveedor(self, ctrl):
        _, prov = await ctrl.crear_proveedor("Prov Eval", email="eval@test.com")
        from datetime import date
        success, _result = await ctrl.crear_evaluacion_proveedor(
            proveedor_id=prov["id"], evaluador="admin",
            fecha=date.today().isoformat(),
            calidad=4.5, comentarios="Excelente"
        )
        assert success is True
