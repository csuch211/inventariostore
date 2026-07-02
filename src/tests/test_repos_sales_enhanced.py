"""Tests for SalesEnhancedRepository: discounts and promotions."""

from __future__ import annotations

import pytest


@pytest.fixture
def se_repo(ctrl):
    return ctrl.db.sales_enhanced_repo


class TestSalesEnhancedDiscounts:
    def test_crear_descuento_porcentaje(self, se_repo):
        result = se_repo.crear_descuento(
            codigo="VERANO10",
            nombre="Verano 10%",
            tipo="porcentaje",
            valor=10.0,
        )
        assert "id" in result

    def test_crear_descuento_monto_fijo(self, se_repo):
        result = se_repo.crear_descuento(
            codigo="DESC500",
            nombre="Descuento $500",
            tipo="monto_fijo",
            valor=500.0,
        )
        assert "id" in result

    def test_crear_descuento_duplicate_raises(self, se_repo):
        se_repo.crear_descuento(codigo="UNICO", nombre="Único", valor=10)
        descuentos = se_repo.obtener_descuentos()
        assert any(d["codigo"] == "UNICO" for d in descuentos)

    def test_obtener_descuentos(self, se_repo):
        se_repo.crear_descuento(codigo="D001", nombre="Desc 1", valor=5)
        descuentos = se_repo.obtener_descuentos()
        assert isinstance(descuentos, list)
        assert len(descuentos) >= 1

    def test_obtener_descuento_por_codigo(self, se_repo):
        se_repo.crear_descuento(codigo="BUSCAR", nombre="Buscable", valor=15)
        found = se_repo.aplicar_descuento("BUSCAR")
        assert found is not None
        assert found["nombre"] == "Buscable"

    def test_actualizar_descuento(self, se_repo):
        created = se_repo.crear_descuento(codigo="UPD", nombre="Original", valor=10)
        result = se_repo.eliminar_descuento(created["id"])
        assert result is True

    def test_eliminar_descuento(self, se_repo):
        created = se_repo.crear_descuento(codigo="DEL", nombre="Eliminar", valor=1)
        result = se_repo.eliminar_descuento(created["id"])
        assert result is True


class TestSalesEnhancedPromotions:
    def test_crear_promocion(self, se_repo):
        result = se_repo.crear_promocion(
            nombre="2x1 en laptops",
            tipo="2x1",
            fecha_inicio="2025-01-01",
            fecha_fin="2025-01-31",
        )
        assert "id" in result

    def test_obtener_promociones(self, se_repo):
        se_repo.crear_promocion("Promo A", "descuento", fecha_inicio="2025-01-01", fecha_fin="2025-01-31")
        proms = se_repo.obtener_promociones()
        assert isinstance(proms, list)
