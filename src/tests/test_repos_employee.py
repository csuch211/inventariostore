"""Tests for EmployeeRepository: employee CRUD."""

from __future__ import annotations

import pytest


@pytest.fixture
def employee_repo(ctrl):
    return ctrl.db.employee_repo


class TestEmployeeRepository:
    def test_crear_empleado(self, employee_repo):
        result = employee_repo.crear_empleado(
            nombre="Carlos", apellido="López", email="carlos@test.com"
        )
        assert "id" in result
        assert result["numero_empleado"].startswith("EMP-")

    def test_obtener_empleado(self, employee_repo):
        created = employee_repo.crear_empleado(nombre="Ana", apellido="Martínez")
        fetched = employee_repo.obtener_empleado(created["id"])
        assert fetched is not None
        assert fetched["nombre"] == "Ana"

    def test_obtener_empleados(self, employee_repo):
        employee_repo.crear_empleado(nombre="Luis", apellido="García")
        empleados = employee_repo.obtener_empleados()
        assert isinstance(empleados, list)
        assert len(empleados) >= 1

    def test_actualizar_empleado(self, employee_repo):
        created = employee_repo.crear_empleado(nombre="Old", apellido="Name")
        result = employee_repo.actualizar_empleado(created["id"], nombre="New")
        assert result is True
        fetched = employee_repo.obtener_empleado(created["id"])
        assert fetched["nombre"] == "New"

    def test_eliminar_empleado_soft(self, employee_repo):
        created = employee_repo.crear_empleado(nombre="Del", apellido="Me")
        result = employee_repo.eliminar_empleado(created["id"])
        assert result is True
        fetched = employee_repo.obtener_empleado(created["id"])
        assert fetched is None or fetched.get("estado") == "inactivo"

    def test_crear_empleado_with_all_fields(self, employee_repo):
        result = employee_repo.crear_empleado(
            nombre="Full", apellido="Employee",
            email="full@test.com", telefono="555-0100",
            fecha_nacimiento="1990-01-01", fecha_ingreso="2025-01-01",
            puesto="Developer", departamento="IT",
            salario_base=50000.0, notas="Nota de prueba",
        )
        assert "id" in result
        assert result["numero_empleado"].startswith("EMP-")
