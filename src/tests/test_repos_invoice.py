"""Tests for InvoiceRepository: invoices, credit notes."""

from __future__ import annotations

import pytest


@pytest.fixture
def invoice_repo(ctrl):
    return ctrl.db.invoice_repo


@pytest.fixture
def client_id(ctrl):
    cid = ctrl.db.sale_repo.crear_cliente("Invoice Client", "555-1000")
    return cid


class TestInvoiceRepository:
    def test_crear_factura_basic(self, invoice_repo, client_id):
        items = [{"cantidad": 2, "precio_unitario": 50.0, "impuesto_pct": 16.0}]
        result = invoice_repo.crear_factura(
            cliente_id=client_id,
            items=items,
            tipo="factura",
        )
        assert "id" in result
        assert result["numero"].startswith("FACT-")
        assert result["total"] > 0

    def test_crear_factura_con_descuento(self, invoice_repo, client_id):
        items = [{"cantidad": 10, "precio_unitario": 100.0, "descuento_pct": 10, "impuesto_pct": 16}]
        result = invoice_repo.crear_factura(
            cliente_id=client_id, items=items, descuento_total=0
        )
        # 10 * 100 = 1000, line discount 10% affects tax base (900), tax 16% of 900 = 144
        # total = subtotal(1000) - descuento_total(0) + impuestos_total(144) = 1144
        assert result["total"] == 1144.0

    def test_crear_factura_multiple_items(self, invoice_repo, client_id):
        items = [
            {"cantidad": 1, "precio_unitario": 200.0, "impuesto_pct": 0},
            {"cantidad": 3, "precio_unitario": 50.0, "impuesto_pct": 16},
        ]
        result = invoice_repo.crear_factura(client_id, items)
        # item2: 150 * 1.16 = 174, total = 200 + 174 = 374
        assert result["total"] == 374.0

    def test_crear_boleta(self, invoice_repo, client_id):
        items = [{"cantidad": 1, "precio_unitario": 25.0}]
        result = invoice_repo.crear_factura(
            cliente_id=client_id, items=items, tipo="boleta"
        )
        assert result["numero"].startswith("BOL-")

    def test_crear_nota_credito(self, invoice_repo, client_id):
        items = [{"cantidad": 1, "precio_unitario": 100.0}]
        result = invoice_repo.crear_factura(
            cliente_id=client_id, items=items, tipo="nota_credito"
        )
        assert result["numero"].startswith("NC-")

    def test_obtener_factura(self, invoice_repo, client_id):
        items = [{"cantidad": 1, "precio_unitario": 50.0}]
        created = invoice_repo.crear_factura(client_id, items)
        fetched = invoice_repo.obtener_factura(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]

    def test_obtener_facturas(self, invoice_repo, client_id):
        items = [{"cantidad": 1, "precio_unitario": 30.0}]
        invoice_repo.crear_factura(client_id, items)
        facturas = invoice_repo.obtener_facturas()
        assert isinstance(facturas, list)
        assert len(facturas) >= 1

    def test_cancelar_factura(self, invoice_repo, client_id):
        items = [{"cantidad": 1, "precio_unitario": 75.0}]
        created = invoice_repo.crear_factura(client_id, items)
        result = invoice_repo.actualizar_estado(created["id"], nuevo_estado="cancelada", usuario="tester")
        assert result is True

    def test_invoice_number_sequential(self, invoice_repo, client_id):
        items = [{"cantidad": 1, "precio_unitario": 10.0}]
        r1 = invoice_repo.crear_factura(client_id, items)
        r2 = invoice_repo.crear_factura(client_id, items)
        # Different numbers
        assert r1["numero"] != r2["numero"]
