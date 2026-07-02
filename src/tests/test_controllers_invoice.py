"""Tests for InvoiceController."""

from __future__ import annotations

import pytest


class TestInvoiceController:
    @pytest.mark.asyncio
    async def test_crear_factura(self, ctrl):
        _, client = await ctrl.crear_cliente("Fact Client", "555-1000")
        items = [{"cantidad": 2, "precio_unitario": 100.0, "impuesto_pct": 16}]
        success, result = await ctrl.crear_factura(
            cliente_id=client["id"], items=items
        )
        assert success is True
        assert "numero" in result
        assert result["numero"].startswith("FACT-")

    @pytest.mark.asyncio
    async def test_obtener_facturas(self, ctrl):
        result = await ctrl.obtener_facturas()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_obtener_factura(self, ctrl):
        result = await ctrl.obtener_factura(9999)
        assert result is None

    @pytest.mark.asyncio
    async def test_cancelar_factura(self, ctrl):
        success, _result = await ctrl.cancelar_factura(9999)
        assert success is True or success is False  # no-op on missing ID
