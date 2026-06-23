"""Tests for invoice and accounting modules."""

from __future__ import annotations

import pytest


class TestInvoiceRepository:
    @pytest.mark.asyncio
    async def test_crear_factura(self, ctrl):
        """Test creating an invoice."""
        ok, client = await ctrl.crear_cliente("Test Client", "555-1234")
        assert ok

        items = [
            {"producto_id": None, "descripcion": "Product A", "cantidad": 2, "precio_unitario": 100.0},
            {"producto_id": None, "descripcion": "Product B", "cantidad": 1, "precio_unitario": 50.0},
        ]
        ok, result = await ctrl.crear_factura(
            cliente_id=client["id"],
            items=items,
            notas="Test invoice",
        )
        assert ok
        assert "numero" in result
        assert result["numero"].startswith("FACT-")
        assert result["total"] == 250.0

    @pytest.mark.asyncio
    async def test_crear_factura_con_impuestos(self, ctrl):
        """Test creating an invoice with taxes."""
        ok, client = await ctrl.crear_cliente("Tax Client")
        assert ok

        items = [
            {"producto_id": None, "descripcion": "Product", "cantidad": 1, "precio_unitario": 100.0, "impuesto_pct": 19.0},
        ]
        ok, result = await ctrl.crear_factura(cliente_id=client["id"], items=items)
        assert ok
        assert abs(result["total"] - 119.0) < 0.01

    @pytest.mark.asyncio
    async def test_crear_factura_con_descuento(self, ctrl):
        """Test creating an invoice with discount."""
        ok, client = await ctrl.crear_cliente("Discount Client")
        assert ok

        items = [{"producto_id": None, "descripcion": "Product", "cantidad": 1, "precio_unitario": 100.0}]
        ok, result = await ctrl.crear_factura(
            cliente_id=client["id"], items=items, descuento_total=10.0
        )
        assert ok
        assert result["total"] == 90.0

    @pytest.mark.asyncio
    async def test_obtener_factura(self, ctrl):
        """Test fetching an invoice."""
        ok, client = await ctrl.crear_cliente("Fetch Client")
        items = [{"producto_id": None, "descripcion": "Item", "cantidad": 1, "precio_unitario": 25.0}]
        ok, result = await ctrl.crear_factura(cliente_id=client["id"], items=items)

        factura = await ctrl.obtener_factura(result["id"])
        assert factura is not None
        assert factura["numero"] == result["numero"]
        assert len(factura["detalle"]) == 1

    @pytest.mark.asyncio
    async def test_obtener_facturas(self, ctrl):
        """Test listing invoices."""
        ok, client = await ctrl.crear_cliente("List Client")
        items = [{"producto_id": None, "descripcion": "Item", "cantidad": 1, "precio_unitario": 10.0}]
        await ctrl.crear_factura(cliente_id=client["id"], items=items)

        facturas = await ctrl.obtener_facturas()
        assert len(facturas) >= 1

    @pytest.mark.asyncio
    async def test_cancelar_factura(self, ctrl):
        """Test cancelling an invoice."""
        ok, client = await ctrl.crear_cliente("Cancel Client")
        items = [{"producto_id": None, "descripcion": "Item", "cantidad": 1, "precio_unitario": 10.0}]
        ok, result = await ctrl.crear_factura(cliente_id=client["id"], items=items)

        ok, _ = await ctrl.cancelar_factura(result["id"])
        assert ok

        factura = await ctrl.obtener_factura(result["id"])
        assert factura["estado"] == "cancelada"


class TestAccountingController:
    @pytest.mark.asyncio
    async def test_crear_asiento(self, ctrl):
        """Test creating a journal entry."""
        movimientos = [
            {"cuenta_codigo": "1.1.01", "cuenta_nombre": "Caja", "debito": 100.0, "credito": 0},
            {"cuenta_codigo": "4.1.01", "cuenta_nombre": "Ventas", "debito": 0, "credito": 100.0},
        ]
        ok, result = await ctrl.crear_asiento(
            fecha="2026-06-23",
            descripcion="Test entry",
            tipo="venta",
            movimientos=movimientos,
        )
        assert ok
        assert "numero" in result
        assert result["numero"].startswith("ASI-")

    @pytest.mark.asyncio
    async def test_crear_asiento_desbalanceado(self, ctrl):
        """Test that unbalanced entries are rejected."""
        movimientos = [
            {"cuenta_codigo": "1.1.01", "cuenta_nombre": "Caja", "debito": 100.0, "credito": 0},
            {"cuenta_codigo": "4.1.01", "cuenta_nombre": "Ventas", "debito": 0, "credito": 50.0},
        ]
        ok, result = await ctrl.crear_asiento(
            fecha="2026-06-23",
            descripcion="Unbalanced",
            tipo="venta",
            movimientos=movimientos,
        )
        assert not ok
        assert "error" in result

    @pytest.mark.asyncio
    async def test_obtener_asiento(self, ctrl):
        """Test fetching a journal entry."""
        movimientos = [
            {"cuenta_codigo": "1.1.01", "cuenta_nombre": "Caja", "debito": 50.0, "credito": 0},
            {"cuenta_codigo": "4.1.01", "cuenta_nombre": "Ventas", "debito": 0, "credito": 50.0},
        ]
        ok, result = await ctrl.crear_asiento(
            fecha="2026-06-23", descripcion="Fetch test", tipo="venta", movimientos=movimientos
        )
        asiento = await ctrl.obtener_asiento(result["id"])
        assert asiento is not None
        assert len(asiento["movimientos"]) == 2

    @pytest.mark.asyncio
    async def test_obtener_plan_cuentas(self, ctrl):
        """Test fetching chart of accounts."""
        cuentas = await ctrl.obtener_plan_cuentas()
        assert len(cuentas) > 0
        assert any(c["codigo"] == "1.1.01" for c in cuentas)

    @pytest.mark.asyncio
    async def test_obtener_balance_comprobacion(self, ctrl):
        """Test trial balance."""
        balance = await ctrl.obtener_balance_comprobacion()
        assert isinstance(balance, list)
