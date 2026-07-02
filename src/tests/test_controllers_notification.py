"""Tests for NotificationController."""

from __future__ import annotations

import pytest


class TestNotificationController:
    @pytest.mark.asyncio
    async def test_crear_plantilla(self, ctrl):
        success, result = await ctrl.crear_plantilla_notificacion(
            nombre="Bienvenida",
            asunto="Bienvenido {{nombre}}",
            cuerpo="Hola {{nombre}}, gracias por registrarte.",
            tipo="email",
        )
        assert success is True
        assert "id" in result

    @pytest.mark.asyncio
    async def test_obtener_plantillas(self, ctrl):
        result = await ctrl.obtener_plantillas_notificacion()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_eliminar_plantilla(self, ctrl):
        _, created = await ctrl.crear_plantilla_notificacion(
            nombre="TempDel", asunto="S", cuerpo="C"
        )
        success, _ = await ctrl.eliminar_plantilla_notificacion(created["id"])
        assert success is True

    @pytest.mark.asyncio
    async def test_guardar_config_smtp(self, ctrl):
        success = await ctrl.guardar_config_ventas(
            "smtp_host", "smtp.gmail.com"
        )
        assert success is True

    @pytest.mark.asyncio
    async def test_obtener_config(self, ctrl):
        result = await ctrl.obtener_config_ventas()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_obtener_logs(self, ctrl):
        result = await ctrl.obtener_notificaciones()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_guardar_whatsapp_config(self, ctrl):
        success, _ = await ctrl.guardar_config_whatsapp({"wa_api_key": "test-key"})
        assert success is True

    @pytest.mark.asyncio
    async def test_guardar_telegram_config(self, ctrl):
        success, _ = await ctrl.guardar_config_telegram({"tg_bot_token": "bot:token"})
        assert success is True
