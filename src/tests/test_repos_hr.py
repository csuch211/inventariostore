"""Tests for HRRepository: payroll, attendance, vacations, evaluations."""

from __future__ import annotations

import pytest


@pytest.fixture
def hr_repo(ctrl):
    return ctrl.db.hr_repo


@pytest.fixture
def employee_id(ctrl):
    result = ctrl.db.employee_repo.crear_empleado(nombre="HR", apellido="Employee")
    return result["id"]


class TestHRPayroll:
    def test_crear_nomina(self, hr_repo, employee_id):
        result = hr_repo.crear_nomina(
            empleado_id=employee_id,
            periodo_inicio="2025-01-01",
            periodo_fin="2025-01-31",
            salario_bruto=50000.0,
            deducciones=5000.0,
            bonificaciones=2000.0,
        )
        assert "id" in result
        assert result["salario_neto"] == 47000.0  # 50000 - 5000 + 2000

    def test_obtener_nomina(self, hr_repo, employee_id):
        hr_repo.crear_nomina(employee_id, "2025-01-01", "2025-01-31", 50000)
        nominas = hr_repo.obtener_nomina(empleado_id=employee_id)
        assert len(nominas) >= 1

    def test_crear_nomina_negative_deductions(self, hr_repo, employee_id):
        # Should handle gracefully
        result = hr_repo.crear_nomina(
            employee_id, "2025-01-01", "2025-01-31", 50000,
            deducciones=60000, bonificaciones=0,
        )
        assert result["salario_neto"] < 0  # Allowed


class TestHRAttendance:
    def test_registrar_asistencia(self, hr_repo, employee_id):
        result = hr_repo.registrar_asistencia(
            employee_id, "2025-01-15", "entrada", "08:00"
        )
        assert "id" in result

    def test_obtener_asistencias(self, hr_repo, employee_id):
        hr_repo.registrar_asistencia(employee_id, "2025-01-15", "entrada", "08:00")
        asistencias = hr_repo.obtener_asistencia(empleado_id=employee_id)
        assert isinstance(asistencias, list)
        assert len(asistencias) >= 1


class TestHRVacations:
    def test_solicitar_vacacion(self, hr_repo, employee_id):
        result = hr_repo.solicitar_vacaciones(
            employee_id, "2025-06-01", "2025-06-15", motivo="Vacaciones anuales"
        )
        assert "id" in result

    def test_obtener_vacaciones(self, hr_repo, employee_id):
        hr_repo.solicitar_vacaciones(employee_id, "2025-06-01", "2025-06-15")
        vacs = hr_repo.obtener_vacaciones(empleado_id=employee_id)
        assert isinstance(vacs, list)
        assert len(vacs) >= 1

    def test_aprobar_vacacion(self, hr_repo, employee_id):
        sol = hr_repo.solicitar_vacaciones(employee_id, "2025-07-01", "2025-07-10")
        result = hr_repo.aprobar_vacaciones(sol["id"], aprobado_por="manager")
        assert result is True


class TestHREvaluations:
    def test_crear_evaluacion(self, hr_repo, employee_id):
        result = hr_repo.crear_evaluacion(
            employee_id, evaluador="system", fecha="2025-04-01",
            periodo="2025-Q1", puntuacion=4.5, notas="Excelente desempeño"
        )
        assert "id" in result

    def test_obtener_evaluaciones(self, hr_repo, employee_id):
        hr_repo.crear_evaluacion(employee_id, evaluador="system", fecha="2025-04-01", periodo="2025-Q1", puntuacion=4.5)
        evals = hr_repo.obtener_evaluaciones(empleado_id=employee_id)
        assert isinstance(evals, list)
        assert len(evals) >= 1
