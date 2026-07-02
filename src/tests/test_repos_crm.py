"""Tests for CRMRepository: contacts, opportunities, activities."""

from __future__ import annotations

import pytest


@pytest.fixture
def crm_repo(ctrl):
    return ctrl.db.crm_repo


class TestCRMContactos:
    def test_crear_contacto(self, crm_repo):
        result = crm_repo.crear_contacto(
            nombre="Juan", apellido="Pérez", email="juan@test.com"
        )
        assert "id" in result
        assert result["id"] > 0

    def test_obtener_contacto(self, crm_repo):
        created = crm_repo.crear_contacto(nombre="María", apellido="López")
        fetched = crm_repo.obtener_contacto(created["id"])
        assert fetched is not None
        assert fetched["nombre"] == "María"

    def test_obtener_contactos(self, crm_repo):
        crm_repo.crear_contacto(nombre="Ana", apellido="García")
        contactos = crm_repo.obtener_contactos()
        assert len(contactos) >= 1

    def test_actualizar_contacto(self, crm_repo):
        created = crm_repo.crear_contacto(nombre="Old", apellido="Name")
        result = crm_repo.actualizar_contacto(created["id"], nombre="New")
        assert result is True
        fetched = crm_repo.obtener_contacto(created["id"])
        assert fetched["nombre"] == "New"

    def test_eliminar_contacto(self, crm_repo):
        created = crm_repo.crear_contacto(nombre="Del", apellido="Me")
        result = crm_repo.eliminar_contacto(created["id"])
        assert result is True
        fetched = crm_repo.obtener_contacto(created["id"])
        assert fetched is None or fetched.get("estado") == "inactivo"

    def test_crear_contacto_sin_nombre(self, crm_repo):
        result = crm_repo.crear_contacto(nombre="", apellido="")
        assert "id" in result  # repo allows empty names


class TestCRMOportunidades:
    def test_crear_oportunidad(self, crm_repo):
        # First create a contact for the opportunity
        contacto = crm_repo.crear_contacto(nombre="Cliente", apellido="Oportunidad")
        result = crm_repo.crear_oportunidad(
            contacto_id=contacto["id"], titulo="Venta grande", monto=5000.0
        )
        assert "id" in result

    def test_obtener_oportunidades(self, crm_repo):
        contacto = crm_repo.crear_contacto(nombre="C", apellido="Ops")
        crm_repo.crear_oportunidad(contacto_id=contacto["id"], titulo="Oportunidad A", monto=1000)
        ops = crm_repo.obtener_oportunidades()
        assert isinstance(ops, list)
        assert len(ops) >= 1

    def test_actualizar_oportunidad_etapa(self, crm_repo):
        contacto = crm_repo.crear_contacto(nombre="C2", apellido="Progreso")
        created = crm_repo.crear_oportunidad(contacto_id=contacto["id"], titulo="Progreso", monto=2000)
        result = crm_repo.actualizar_estado_oportunidad(created["id"], nuevo_estado="ganada")
        assert result is True


class TestCRMActividades:
    def test_crear_actividad(self, crm_repo):
        # First create a contact
        contacto = crm_repo.crear_contacto(nombre="Contacto", apellido="Act")
        result = crm_repo.crear_actividad(
            contacto_id=contacto["id"], tipo="llamada", titulo="Follow up"
        )
        assert "id" in result

    def test_obtener_actividades(self, crm_repo):
        contacto = crm_repo.crear_contacto(nombre="C", apellido="Act2")
        crm_repo.crear_actividad(contacto_id=contacto["id"], tipo="email", titulo="Email")
        acts = crm_repo.obtener_actividades()
        assert isinstance(acts, list)
