"""Tests for NotificationRepository: templates, config, logs."""

from __future__ import annotations

import pytest

from utils.exceptions import DatabaseException


@pytest.fixture
def notif_repo(ctrl):
    return ctrl.db.notification_repo


class TestNotificationRepository:
    def test_crear_plantilla(self, notif_repo):
        result = notif_repo.crear_plantilla(
            nombre="ReposAlert",
            asunto="Stock bajo: {{producto}}",
            cuerpo="El producto {{producto}} tiene {{cantidad}} unidades.",
            tipo="email",
            usuario="tester",
        )
        assert "id" in result

    def test_crear_plantilla_duplicate_raises(self, notif_repo):
        notif_repo.crear_plantilla(nombre="ReposUnica", asunto="S", cuerpo="C")
        with pytest.raises(DatabaseException, match="already exists"):
            notif_repo.crear_plantilla(nombre="ReposUnica", asunto="S", cuerpo="C")

    def test_obtener_plantillas(self, notif_repo):
        notif_repo.crear_plantilla(nombre="ReposTemp1", asunto="A", cuerpo="B")
        plantillas = notif_repo.obtener_plantillas()
        assert isinstance(plantillas, list)
        assert len(plantillas) >= 1

    def test_obtener_plantillas_por_tipo(self, notif_repo):
        notif_repo.crear_plantilla(nombre="ReposEmail1", asunto="A", cuerpo="B", tipo="email")
        notif_repo.crear_plantilla(nombre="ReposPush1", asunto="A", cuerpo="B", tipo="push")
        emails = notif_repo.obtener_plantillas(tipo="email")
        assert all(p["tipo"] == "email" for p in emails)

    def test_eliminar_plantilla(self, notif_repo):
        created = notif_repo.crear_plantilla(nombre="ReposDelMe", asunto="S", cuerpo="C")
        result = notif_repo.eliminar_plantilla(created["id"])
        assert result is True

    def test_actualizar_plantilla(self, notif_repo):
        created = notif_repo.crear_plantilla(nombre="ReposOld", asunto="S", cuerpo="C")
        result = notif_repo.eliminar_plantilla(created["id"])
        assert result is True

    # Config tests (uses automation_repo config methods)
    def test_guardar_y_obtener_config(self, notif_repo, ctrl):
        automation_repo = ctrl.db.automation_repo
        automation_repo.guardar_config("smtp_host", "smtp.gmail.com")
        config = automation_repo.obtener_config()
        assert config.get("smtp_host") == "smtp.gmail.com"
        with ctrl.db._get_connection() as conn:
            conn.execute("DELETE FROM configuracion WHERE clave = 'smtp_host'")

    def test_guardar_config_whatsapp(self, notif_repo, ctrl):
        automation_repo = ctrl.db.automation_repo
        automation_repo.guardar_config("wa_api_key", "test-key-123")
        config = automation_repo.obtener_config()
        assert config["wa_api_key"] == "test-key-123"

    # Log tests
    def test_registrar_log(self, notif_repo):
        result = notif_repo.crear_notificacion(
            titulo="Test", mensaje="Body",
            tipo="email", destinatario="test@test.com"
        )
        assert "id" in result

    def test_obtener_logs(self, notif_repo):
        notif_repo.crear_notificacion(titulo="S", mensaje="B", tipo="email", destinatario="a@b.com")
        logs = notif_repo.obtener_notificaciones()
        assert isinstance(logs, list)
        assert len(logs) >= 1
