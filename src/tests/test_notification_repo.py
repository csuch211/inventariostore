"""Tests for the NotificationRepository layer.

Verifies CRUD operations for templates, channels, notifications,
and user preferences using an isolated SQLite DB.
"""

from __future__ import annotations

import pytest

from services.repository.notification_repo import NotificationRepository
from utils.exceptions import DatabaseException


@pytest.fixture
def notif_repo(ctrl) -> NotificationRepository:
    return ctrl.db.notification_repo


class TestNotificationRepositoryPlantillas:
    def test_crear_plantilla(self, notif_repo: NotificationRepository):
        result = notif_repo.crear_plantilla(
            nombre="Stock Bajo",
            asunto="Alerta de stock bajo",
            cuerpo="El producto {nombre} tiene {cantidad} unidades.",
            tipo="email",
            variables="nombre,cantidad",
            usuario="tester",
        )
        assert "id" in result
        assert result["id"] > 0

    def test_crear_plantilla_duplicada(self, notif_repo: NotificationRepository):
        notif_repo.crear_plantilla(nombre="Duplicada", asunto="Test", cuerpo="Test")
        with pytest.raises(DatabaseException):
            notif_repo.crear_plantilla(nombre="Duplicada", asunto="Test", cuerpo="Test")

    def test_obtener_plantillas_sin_filtro(self, notif_repo: NotificationRepository):
        notif_repo.crear_plantilla(nombre="PlantA", asunto="A", cuerpo="A", tipo="email")
        notif_repo.crear_plantilla(nombre="PlantB", asunto="B", cuerpo="B", tipo="push")
        plantillas = notif_repo.obtener_plantillas()
        assert len(plantillas) >= 2

    def test_obtener_plantillas_por_tipo(self, notif_repo: NotificationRepository):
        notif_repo.crear_plantilla(nombre="TestEmailType", asunto="E", cuerpo="E", tipo="email")
        notif_repo.crear_plantilla(nombre="TestPushType", asunto="P", cuerpo="P", tipo="push")
        emails = notif_repo.obtener_plantillas(tipo="email")
        assert isinstance(emails, list)
        assert all(p["tipo"] == "email" for p in emails)

    def test_eliminar_plantilla(self, notif_repo: NotificationRepository):
        result = notif_repo.crear_plantilla(nombre="ToDelete", asunto="D", cuerpo="D")
        pid = result["id"]
        notif_repo.eliminar_plantilla(pid, usuario="tester")
        plantillas = notif_repo.obtener_plantillas()
        assert not any(p["id"] == pid for p in plantillas)


class TestNotificationRepositoryCanales:
    def test_crear_canal(self, notif_repo: NotificationRepository):
        result = notif_repo.crear_canal(
            nombre="Email Principal",
            tipo="email",
            configuracion='{"host":"smtp.example.com"}',
            usuario="tester",
        )
        assert "id" in result
        assert result["id"] > 0

    def test_crear_canal_duplicado(self, notif_repo: NotificationRepository):
        notif_repo.crear_canal(nombre="CanalUnico", tipo="sms")
        with pytest.raises(DatabaseException):
            notif_repo.crear_canal(nombre="CanalUnico", tipo="push")

    def test_obtener_canales(self, notif_repo: NotificationRepository):
        notif_repo.crear_canal(nombre="CanalA", tipo="email")
        notif_repo.crear_canal(nombre="CanalB", tipo="push")
        canales = notif_repo.obtener_canales()
        assert len(canales) >= 2


class TestNotificationRepositoryNotificaciones:
    def test_crear_notificacion(self, notif_repo: NotificationRepository):
        result = notif_repo.crear_notificacion(
            titulo="Stock Bajo",
            mensaje="El producto X tiene 2 unidades",
            tipo="warning",
            canal="sistema",
            destinatario="admin",
            referencia_tipo="producto",
            referencia_id=1,
            usuario="tester",
        )
        assert "id" in result
        assert result["id"] > 0

    def test_obtener_notificaciones_sin_filtros(self, notif_repo: NotificationRepository):
        notif_repo.crear_notificacion(titulo="N1", mensaje="M1")
        notif_repo.crear_notificacion(titulo="N2", mensaje="M2")
        notifs = notif_repo.obtener_notificaciones(limit=10)
        assert len(notifs) >= 2

    def test_obtener_notificaciones_con_filtros(self, notif_repo: NotificationRepository):
        notif_repo.crear_notificacion(
            titulo="Warning", mensaje="W", tipo="warning", destinatario="user1"
        )
        notif_repo.crear_notificacion(
            titulo="Info", mensaje="I", tipo="info", destinatario="user2"
        )
        filtered = notif_repo.obtener_notificaciones(
            destinatario="user1", tipo="warning", limit=10
        )
        assert all(n["destinatario"] == "user1" for n in filtered)
        assert all(n["tipo"] == "warning" for n in filtered)

    def test_marcar_leido(self, notif_repo: NotificationRepository):
        result = notif_repo.crear_notificacion(titulo="Leer", mensaje="M")
        nid = result["id"]
        notif_repo.marcar_leido(nid)
        notifs = notif_repo.obtener_notificaciones(limit=10)
        target = next(n for n in notifs if n["id"] == nid)
        assert target["estado"] == "leido"
        assert target["leido_en"] is not None

    def test_marcar_todas_leidas(self, notif_repo: NotificationRepository):
        notif_repo.crear_notificacion(titulo="A", mensaje="A", destinatario="admin")
        notif_repo.crear_notificacion(titulo="B", mensaje="B", destinatario="admin")
        count = notif_repo.marcar_todas_leidas(destinatario="admin")
        assert count >= 2
        notifs = notif_repo.obtener_notificaciones(destinatario="admin", limit=10)
        assert all(n["estado"] == "leido" for n in notifs)

    def test_contar_no_leidas(self, notif_repo: NotificationRepository):
        notif_repo.crear_notificacion(titulo="Unread", mensaje="U", destinatario="user_x")
        count = notif_repo.contar_no_leidas(destinatario="user_x")
        assert count >= 1

    def test_contar_no_leidas_sin_destinatario(self, notif_repo: NotificationRepository):
        notif_repo.crear_notificacion(titulo="Global", mensaje="G")
        count = notif_repo.contar_no_leidas()
        assert count >= 1

    def test_eliminar_notificacion(self, notif_repo: NotificationRepository):
        result = notif_repo.crear_notificacion(titulo="Del", mensaje="D")
        nid = result["id"]
        notif_repo.eliminar_notificacion(nid)
        notifs = notif_repo.obtener_notificaciones(limit=100)
        assert not any(n["id"] == nid for n in notifs)


class TestNotificationRepositoryPreferencias:
    def test_obtener_preferencias_defaults(self, notif_repo: NotificationRepository):
        prefs = notif_repo.obtener_preferencias(usuario_id=9999)
        assert prefs["email_enabled"] == 1
        assert prefs["push_enabled"] == 1
        assert prefs["stock_alertas"] == 1
        assert prefs["frecuencia"] == "inmediato"

    def test_guardar_y_obtener_preferencias(self, notif_repo: NotificationRepository):
        notif_repo.guardar_preferencias(
            usuario_id=42,
            preferencias={"email_enabled": 0, "push_enabled": 1, "frecuencia": "diario"},
        )
        prefs = notif_repo.obtener_preferencias(usuario_id=42)
        assert prefs["email_enabled"] == 0
        assert prefs["push_enabled"] == 1
        assert prefs["frecuencia"] == "diario"
