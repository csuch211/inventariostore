"""Tests for the notification domain controller.

Verifies that NotificationController correctly delegates to the
repository and enforces permission checks via @require_permission.
"""

from __future__ import annotations

import pytest

from services.permissions import Perm, PermissionException


class TestNotificationControllerPlantillas:
    @pytest.mark.asyncio
    async def test_crear_plantilla(self, ctrl):
        ok, result = await ctrl.crear_plantilla_notificacion(
            nombre="Alerta Stock",
            asunto="Stock bajo",
            cuerpo="Producto: {nombre}",
            tipo="email",
        )
        assert ok is True
        assert "id" in result
        assert result["id"] > 0

    @pytest.mark.asyncio
    async def test_crear_plantilla_duplicada(self, ctrl):
        await ctrl.crear_plantilla_notificacion(
            nombre="DupePlantilla", asunto="A", cuerpo="B"
        )
        ok, result = await ctrl.crear_plantilla_notificacion(
            nombre="DupePlantilla", asunto="A", cuerpo="B"
        )
        assert ok is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_obtener_plantillas(self, ctrl):
        await ctrl.crear_plantilla_notificacion(
            nombre="Plant1", asunto="S1", cuerpo="C1", tipo="email"
        )
        await ctrl.crear_plantilla_notificacion(
            nombre="Plant2", asunto="S2", cuerpo="C2", tipo="push"
        )
        plantillas = await ctrl.obtener_plantillas_notificacion()
        assert len(plantillas) >= 2

    @pytest.mark.asyncio
    async def test_obtener_plantillas_por_tipo(self, ctrl):
        await ctrl.crear_plantilla_notificacion(
            nombre="EmailOnly", asunto="E", cuerpo="E", tipo="email"
        )
        emails = await ctrl.obtener_plantillas_notificacion(tipo="email")
        assert all(p["tipo"] == "email" for p in emails)

    @pytest.mark.asyncio
    async def test_eliminar_plantilla(self, ctrl):
        ok, result = await ctrl.crear_plantilla_notificacion(
            nombre="DelPlant", asunto="X", cuerpo="Y"
        )
        assert ok is True
        pid = result["id"]
        ok2, _ = await ctrl.eliminar_plantilla_notificacion(pid)
        assert ok2 is True
        plantillas = await ctrl.obtener_plantillas_notificacion()
        assert not any(p["id"] == pid for p in plantillas)


class TestNotificationControllerCanales:
    @pytest.mark.asyncio
    async def test_crear_canal(self, ctrl):
        ok, result = await ctrl.crear_canal_notificacion(
            nombre="SMS Principal", tipo="sms", configuracion="{}"
        )
        assert ok is True
        assert "id" in result

    @pytest.mark.asyncio
    async def test_obtener_canales(self, ctrl):
        await ctrl.crear_canal_notificacion(nombre="ChanA", tipo="email")
        await ctrl.crear_canal_notificacion(nombre="ChanB", tipo="push")
        canales = await ctrl.obtener_canales_notificacion()
        assert len(canales) >= 2


class TestNotificationControllerNotificaciones:
    @pytest.mark.asyncio
    async def test_crear_notificacion(self, ctrl):
        ok, result = await ctrl.crear_notificacion(
            titulo="Test",
            mensaje="Mensaje de prueba",
            tipo="info",
            destinatario="admin",
        )
        assert ok is True
        assert "id" in result

    @pytest.mark.asyncio
    async def test_obtener_notificaciones(self, ctrl):
        await ctrl.crear_notificacion(titulo="N1", mensaje="M1", tipo="info")
        await ctrl.crear_notificacion(titulo="N2", mensaje="M2", tipo="warning")
        notifs = await ctrl.obtener_notificaciones(limit=10)
        assert len(notifs) >= 2

    @pytest.mark.asyncio
    async def test_obtener_notificaciones_con_filtros(self, ctrl):
        await ctrl.crear_notificacion(
            titulo="W", mensaje="W", tipo="warning", destinatario="op1"
        )
        await ctrl.crear_notificacion(
            titulo="I", mensaje="I", tipo="info", destinatario="op2"
        )
        filtered = await ctrl.obtener_notificaciones(
            destinatario="op1", tipo="warning", limit=10
        )
        assert len(filtered) >= 1
        assert all(n["destinatario"] == "op1" for n in filtered)

    @pytest.mark.asyncio
    async def test_marcar_leido(self, ctrl):
        ok, result = await ctrl.crear_notificacion(titulo="Leer", mensaje="LM")
        assert ok
        nid = result["id"]
        ok2, _ = await ctrl.marcar_leido(nid)
        assert ok2 is True
        notifs = await ctrl.obtener_notificaciones(limit=10)
        target = next(n for n in notifs if n["id"] == nid)
        assert target["estado"] == "leido"

    @pytest.mark.asyncio
    async def test_marcar_todas_leidas(self, ctrl):
        await ctrl.crear_notificacion(titulo="A", mensaje="A", destinatario="target_u")
        await ctrl.crear_notificacion(titulo="B", mensaje="B", destinatario="target_u")
        ok, result = await ctrl.marcar_todas_leidas(destinatario="target_u")
        assert ok is True
        assert result.get("count", 0) >= 2

    @pytest.mark.asyncio
    async def test_contar_no_leidas(self, ctrl):
        await ctrl.crear_notificacion(titulo="Unread", mensaje="U", destinatario="counter")
        count = await ctrl.contar_no_leidas(destinatario="counter")
        assert count >= 1

    @pytest.mark.asyncio
    async def test_eliminar_notificacion(self, ctrl):
        ok, result = await ctrl.crear_notificacion(titulo="Del", mensaje="D")
        assert ok
        nid = result["id"]
        ok2, _ = await ctrl.eliminar_notificacion(nid)
        assert ok2 is True
        notifs = await ctrl.obtener_notificaciones(limit=100)
        assert not any(n["id"] == nid for n in notifs)


class TestNotificationControllerPreferencias:
    @pytest.mark.asyncio
    async def test_obtener_preferencias_defaults(self, ctrl):
        prefs = await ctrl.obtener_preferencias_notificacion(usuario_id=9999)
        assert prefs.get("email_enabled") == 1
        assert prefs.get("frecuencia") == "inmediato"

    @pytest.mark.asyncio
    async def test_guardar_preferencias(self, ctrl):
        ok, _ = await ctrl.guardar_preferencias_notificacion(
            usuario_id=100,
            preferencias={"email_enabled": 0, "push_enabled": 1, "frecuencia": "semanal"},
        )
        assert ok is True
        prefs = await ctrl.obtener_preferencias_notificacion(usuario_id=100)
        assert prefs["email_enabled"] == 0
        assert prefs["frecuencia"] == "semanal"


class TestNotificationControllerPermisos:
    @pytest.mark.asyncio
    async def test_sin_permiso_rechaza_plantilla(self, ctrl):
        ctrl.current_user_permissions = set()
        with pytest.raises(PermissionException):
            await ctrl.crear_plantilla_notificacion(
                nombre="NoPerm", asunto="X", cuerpo="Y"
            )

    @pytest.mark.asyncio
    async def test_sin_permiso_rechaza_canal(self, ctrl):
        ctrl.current_user_permissions = set()
        with pytest.raises(PermissionException):
            await ctrl.crear_canal_notificacion(nombre="NoPerm", tipo="email")

    @pytest.mark.asyncio
    async def test_con_permiso_ok(self, ctrl):
        assert Perm.NOTIFICACIONES_CONFIGURAR in ctrl.current_user_permissions


class TestNotificationIntegration:
    @pytest.mark.asyncio
    async def test_notification_lifecycle(self, ctrl):
        ok, n = await ctrl.crear_notificacion(
            titulo="Ciclo", mensaje="Vida", tipo="info", destinatario="integ"
        )
        assert ok
        nid = n["id"]
        count_before = await ctrl.contar_no_leidas(destinatario="integ")
        assert count_before >= 1
        await ctrl.marcar_leido(nid)
        count_after = await ctrl.contar_no_leidas(destinatario="integ")
        assert count_after <= count_before
        ok_del, _ = await ctrl.eliminar_notificacion(nid)
        assert ok_del is True

    @pytest.mark.asyncio
    async def test_plantilla_lifecycle(self, ctrl):
        ok, p = await ctrl.crear_plantilla_notificacion(
            nombre="CyclePlant", asunto="S", cuerpo="C", tipo="email"
        )
        assert ok
        pid = p["id"]
        plantillas = await ctrl.obtener_plantillas_notificacion()
        assert any(pt["id"] == pid for pt in plantillas)
        ok_del, _ = await ctrl.eliminar_plantilla_notificacion(pid)
        assert ok_del is True
        plantillas2 = await ctrl.obtener_plantillas_notificacion()
        assert not any(pt["id"] == pid for pt in plantillas2)

    @pytest.mark.asyncio
    async def test_preferencias_lifecycle(self, ctrl):
        ok, _ = await ctrl.guardar_preferencias_notificacion(
            usuario_id=200,
            preferencias={"email_enabled": 0, "frecuencia": "nunca"},
        )
        assert ok
        prefs = await ctrl.obtener_preferencias_notificacion(usuario_id=200)
        assert prefs["email_enabled"] == 0
        assert prefs["frecuencia"] == "nunca"
