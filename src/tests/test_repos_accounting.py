"""Tests for AccountingRepository: journal entries, account plans."""

from __future__ import annotations

from datetime import date

import pytest

from utils.exceptions import DatabaseException

_YEAR = str(date.today().year)


@pytest.fixture
def accounting_repo(ctrl):
    return ctrl.db.accounting_repo


class TestAccountingRepository:
    def test_crear_asiento_success(self, accounting_repo):
        movimientos = [
            {"cuenta_codigo": "1101", "cuenta_nombre": "Caja", "debito": 1000, "credito": 0},
            {"cuenta_codigo": "4101", "cuenta_nombre": "Ventas", "debito": 0, "credito": 1000},
        ]
        result = accounting_repo.crear_asiento(
            fecha=f"{_YEAR}-01-15",
            descripcion="Venta de prueba",
            tipo="venta",
            movimientos=movimientos,
        )
        assert "id" in result
        assert result["numero"].startswith("ASI-")

    def test_crear_asiento_unbalanced_raises(self, accounting_repo):
        movimientos = [
            {"cuenta_codigo": "1101", "cuenta_nombre": "Caja", "debito": 1000, "credito": 0},
            {"cuenta_codigo": "4101", "cuenta_nombre": "Ventas", "debito": 0, "credito": 500},
        ]
        with pytest.raises(DatabaseException, match=r"Debits.*must equal credits"):
            accounting_repo.crear_asiento(
                fecha=f"{_YEAR}-01-15",
                descripcion="Unbalanced",
                tipo="ajuste",
                movimientos=movimientos,
            )

    def test_obtener_asiento(self, accounting_repo):
        movs = [{"cuenta_codigo": "1101", "cuenta_nombre": "Caja", "debito": 500, "credito": 0},
                {"cuenta_codigo": "4101", "cuenta_nombre": "Ventas", "debito": 0, "credito": 500}]
        created = accounting_repo.crear_asiento(f"{_YEAR}-01-15", "Test", "venta", movs)
        fetched = accounting_repo.obtener_asiento(created["id"])
        assert fetched is not None
        assert fetched["descripcion"] == "Test"

    def test_listar_asientos(self, accounting_repo):
        movs = [{"cuenta_codigo": "1101", "cuenta_nombre": "Caja", "debito": 100, "credito": 0},
                {"cuenta_codigo": "4101", "cuenta_nombre": "Ventas", "debito": 0, "credito": 100}]
        accounting_repo.crear_asiento(f"{_YEAR}-02-01", "List test", "venta", movs)
        asientos = accounting_repo.obtener_asientos()
        assert len(asientos) >= 1

    def test_obtener_plan_cuentas(self, accounting_repo):
        cuentas = accounting_repo.obtener_plan_cuentas()
        assert isinstance(cuentas, list)
