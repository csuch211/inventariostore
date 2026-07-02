"""Tests for PurchasingRepository: quotations, supplier eval, receiving."""

from __future__ import annotations

import pytest


@pytest.fixture
def purch_repo(ctrl):
    return ctrl.db.purchasing_repo


@pytest.fixture
def provider_id(ctrl):
    prov_id = ctrl.db.product_repo.crear_proveedor("Purchasing Prov", "prov@test.com")
    return prov_id


class TestPurchasingQuotations:
    def test_crear_cotizacion(self, purch_repo, provider_id):
        items = [{"producto_id": 1, "cantidad": 10, "precio_unitario": 15.0}]
        result = purch_repo.crear_cotizacion(
            proveedor_id=provider_id, items=items, notas="Cotización urgente"
        )
        assert "id" in result
        assert result["numero"].startswith("COT-")

    def test_crear_cotizacion_multiple_items(self, purch_repo, provider_id):
        items = [
            {"producto_id": 1, "cantidad": 5, "precio_unitario": 10.0},
            {"producto_id": 2, "cantidad": 3, "precio_unitario": 20.0},
        ]
        result = purch_repo.crear_cotizacion(provider_id, items)
        assert result["subtotal"] == 110.0  # 5*10 + 3*20

    def test_obtener_cotizaciones(self, purch_repo, provider_id):
        items = [{"producto_id": 1, "cantidad": 1, "precio_unitario": 5.0}]
        purch_repo.crear_cotizacion(provider_id, items)
        cotizaciones = purch_repo.obtener_cotizaciones()
        assert isinstance(cotizaciones, list)
        assert len(cotizaciones) >= 1


class TestPurchasingReceiving:
    def test_registrar_recepcion(self, purch_repo, provider_id):
        items = [{"producto_id": 1, "cantidad_recibida": 10}]
        result = purch_repo.crear_recepcion(
            proveedor_id=provider_id, items=items, usuario="tester"
        )
        assert "id" in result
        assert result["numero"].startswith("REC-")

    def test_obtener_recepciones(self, purch_repo, provider_id):
        items = [{"producto_id": 1, "cantidad_recibida": 5}]
        purch_repo.crear_recepcion(provider_id, items)
        recepciones = purch_repo.obtener_recepciones()
        assert isinstance(recepciones, list)


class TestPurchasingSupplierEval:
    def test_evaluar_proveedor(self, purch_repo, provider_id):
        result = purch_repo.crear_evaluacion_proveedor(
            proveedor_id=provider_id,
            evaluador="tester",
            fecha="2025-01-15",
            calidad=4.5,
            puntualidad=4.0,
            precio=4.0,
            servicio=4.0,
            comentarios="Buen servicio",
        )
        assert "id" in result

    def test_obtener_evaluaciones(self, purch_repo, provider_id):
        purch_repo.crear_evaluacion_proveedor(provider_id, evaluador="tester", fecha="2025-01-15", calidad=4.0, puntualidad=4.0, precio=4.0, servicio=4.0, comentarios="OK")
        evals = purch_repo.obtener_evaluaciones_proveedor(proveedor_id=provider_id)
        assert isinstance(evals, list)
        assert len(evals) >= 1
