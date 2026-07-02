"""Integration tests for the messaging module across all layers.

Tests the real interaction between:
  - NotificationController → Database (persistence)
  - Push queue → Dispatcher → Senders (message flow)
  - Permission enforcement (RBAC gates)
  - Error propagation across layer boundaries
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import extended_features_db
from services.messaging import create_push_sender_func, send_via_channel
from services.permissions import PermissionException

# =========================================================================
# Helpers (shared across test classes)
# =========================================================================

def _mock_response(is_success: bool = True, json_data: dict | None = None,
                   text: str = ""):
    m = MagicMock()
    m.is_success = is_success
    m.json.return_value = json_data or {}
    m.text = text
    return m


def _async_client_mock(post_return_value=None):
    client = AsyncMock()
    client.__aenter__.return_value = client
    if post_return_value is not None:
        client.post.return_value = post_return_value
    return client


# =========================================================================
# Integration: Notification CRUD → Database
# =========================================================================

class TestNotificationPersistence:
    """Verify that controller CRUD operations persist to the database."""

    @pytest.mark.asyncio
    async def test_crear_y_obtener_plantilla(self, ctrl):
        ok, result = await ctrl.crear_plantilla_notificacion(
            nombre="Test Plantilla",
            asunto="Asunto: {variable}",
            cuerpo="Cuerpo con {variable}",
            tipo="email",
        )
        assert ok is True
        assert "id" in result

        plantillas = await ctrl.obtener_plantillas_notificacion()
        ids = [p["id"] for p in plantillas]
        assert result["id"] in ids

    @pytest.mark.asyncio
    async def test_crear_y_obtener_canal(self, ctrl):
        ok, result = await ctrl.crear_canal_notificacion(
            nombre="Test Canal",
            tipo="email",
            configuracion='{"host": "smtp.test.com"}',
        )
        assert ok is True
        assert "id" in result

        canales = await ctrl.obtener_canales_notificacion()
        ids = [c["id"] for c in canales]
        assert result["id"] in ids

    @pytest.mark.asyncio
    async def test_notificacion_full_lifecycle(self, ctrl):
        ok, result = await ctrl.crear_notificacion(
            titulo="Test Notificación",
            mensaje="Mensaje de prueba",
            tipo="inventory",
            destinatario="admin",
        )
        assert ok is True
        nid = result["id"]

        notifs = await ctrl.obtener_notificaciones()
        assert any(n["id"] == nid for n in notifs)

        ok, _ = await ctrl.marcar_leido(nid)
        assert ok is True

        no_leidas = await ctrl.contar_no_leidas()
        assert isinstance(no_leidas, int)

        ok, _ = await ctrl.eliminar_notificacion(nid)
        assert ok is True

    @pytest.mark.asyncio
    async def test_marcar_todas_leidas(self, ctrl):
        for i in range(3):
            await ctrl.crear_notificacion(
                titulo=f"Test {i}", mensaje="Mensaje",
                tipo="test", destinatario="admin",
            )

        ok, result = await ctrl.marcar_todas_leidas("admin")
        assert ok is True
        assert result["count"] >= 3

    @pytest.mark.asyncio
    async def test_preferencias_usuario(self, ctrl):
        preferencias = await ctrl.obtener_preferencias_notificacion(usuario_id=1)
        assert "email_enabled" in preferencias
        assert "push_enabled" in preferencias

        ok, _ = await ctrl.guardar_preferencias_notificacion(
            usuario_id=1,
            preferencias={"email_enabled": 0, "stock_alertas": 1},
        )
        assert ok is True

        updated = await ctrl.obtener_preferencias_notificacion(usuario_id=1)
        assert updated["email_enabled"] == 0
        assert updated["stock_alertas"] == 1

    @pytest.mark.asyncio
    async def test_eliminar_plantilla(self, ctrl):
        ok, result = await ctrl.crear_plantilla_notificacion(
            nombre="Temp", asunto="A", cuerpo="C", tipo="email"
        )
        assert ok is True
        pid = result["id"]

        ok, _ = await ctrl.eliminar_plantilla_notificacion(pid)
        assert ok is True

        plantillas = await ctrl.obtener_plantillas_notificacion()
        assert pid not in [p["id"] for p in plantillas]


# =========================================================================
# Integration: WhatsApp/Telegram Config Persistence
# =========================================================================

class TestMessagingConfigPersistence:
    """Verify WhatsApp/Telegram config flows through controller → DB."""

    @pytest.mark.asyncio
    async def test_whatsapp_config_guardar_y_obtener(self, ctrl):
        config = {
            "wa_api_key": "test-key-123",
            "wa_phone_id": "test-phone-456",
            "wa_api_url": "https://graph.facebook.com/v18.0",
            "wa_enabled": "si",
        }
        ok, _ = await ctrl.guardar_config_whatsapp(config)
        assert ok is True

        retrieved = await ctrl.obtener_config_whatsapp()
        assert retrieved.get("wa_api_key") == "test-key-123"
        assert retrieved.get("wa_phone_id") == "test-phone-456"
        assert retrieved.get("wa_enabled") == "si"

    @pytest.mark.asyncio
    async def test_telegram_config_guardar_y_obtener(self, ctrl):
        config = {
            "tg_bot_token": "bot:token-789",
            "tg_chat_id": "-100999",
            "tg_enabled": "si",
        }
        ok, _ = await ctrl.guardar_config_telegram(config)
        assert ok is True

        retrieved = await ctrl.obtener_config_telegram()
        assert retrieved.get("tg_bot_token") == "bot:token-789"
        assert retrieved.get("tg_chat_id") == "-100999"

    @pytest.mark.asyncio
    async def test_whatsapp_config_mantiene_valores_previos(self, ctrl):
        await ctrl.guardar_config_whatsapp({
            "wa_api_key": "key1", "wa_phone_id": "ph1",
            "wa_api_url": "https://graph.facebook.com/v18.0", "wa_enabled": "si",
        })
        await ctrl.guardar_config_whatsapp({
            "wa_api_key": "key2", "wa_phone_id": "",
            "wa_api_url": "", "wa_enabled": "no",
        })
        retrieved = await ctrl.obtener_config_whatsapp()
        assert retrieved.get("wa_api_key") == "key2"
        assert retrieved.get("wa_enabled") == "no"


# =========================================================================
# Integration: Push Queue Full Lifecycle
# =========================================================================

class TestPushQueueLifecycle:
    """Real push queue flow: enqueue → dispatch → sent/failed."""

    def test_encolar_y_obtener_jobs(self, ctrl):
        db = ctrl.db
        jid1 = extended_features_db.encolar_job(db, tipo="low_stock", destinatario="test@test.com",
                                     asunto="Test 1", cuerpo="Body 1")
        jid2 = extended_features_db.encolar_job(db, tipo="alerta", destinatario="user@test.com",
                                     asunto="Test 2", cuerpo="Body 2")

        assert jid1 > 0
        assert jid2 > 0
        assert jid2 > jid1

        pendientes = extended_features_db.obtener_jobs(db, estado="pendiente")
        assert len(pendientes) >= 2
        ids = [j["id"] for j in pendientes]
        assert jid1 in ids
        assert jid2 in ids

    def test_despachar_con_sender_exitoso(self, ctrl):
        db = ctrl.db
        jid = extended_features_db.encolar_job(db, tipo="test", destinatario="+52123",
                                    asunto="Dispatch test", cuerpo="OK")

        def fake_sender(cfg, asunto, cuerpo):
            return {"sent": True, "message_id": "msg-1"}

        result = extended_features_db.despachar_jobs_pendientes(db, sender=fake_sender, limit=10)
        assert result["procesados"] >= 1
        assert result["enviados"] >= 1

        jobs = extended_features_db.obtener_jobs(db, estado="enviado", limit=10)
        sent_ids = [j["id"] for j in jobs]
        assert jid in sent_ids

    def test_despachar_con_sender_fallido(self, ctrl):
        db = ctrl.db
        jid = extended_features_db.encolar_job(db, tipo="test", destinatario="fail@test.com",
                                    asunto="Fail test", cuerpo="Fail")

        def fake_sender(cfg, asunto, cuerpo):
            return {"sent": False, "reason": "Simulated failure"}

        result = extended_features_db.despachar_jobs_pendientes(db, sender=fake_sender, limit=10)
        assert result["procesados"] >= 1
        assert result["fallidos"] >= 1

        jobs = extended_features_db.obtener_jobs(db, estado="fallido", limit=10)
        failed_ids = [j["id"] for j in jobs]
        assert jid in failed_ids

    def test_despachar_con_sender_que_lanza_excepcion(self, ctrl):
        db = ctrl.db
        jid = extended_features_db.encolar_job(db, tipo="test", destinatario="error@test.com",
                                    asunto="Exception test", cuerpo="Boom")

        def fake_sender(cfg, asunto, cuerpo):
            raise RuntimeError("Sender crashed!")

        result = extended_features_db.despachar_jobs_pendientes(db, sender=fake_sender, limit=10)
        assert result["procesados"] >= 1
        assert result["fallidos"] >= 1

        jobs = extended_features_db.obtener_jobs(db, estado="fallido", limit=10)
        failed_ids = [j["id"] for j in jobs]
        assert jid in failed_ids

    def test_despachar_limite_respetado(self, ctrl):
        db = ctrl.db
        for i in range(5):
            extended_features_db.encolar_job(db, tipo="test", destinatario=f"u{i}@test.com",
                                  asunto=f"Job {i}", cuerpo=f"Body {i}")

        def fake_sender(cfg, asunto, cuerpo):
            return {"sent": True}

        result = extended_features_db.despachar_jobs_pendientes(db, sender=fake_sender, limit=3)
        assert result["procesados"] == 3


# =========================================================================
# Integration: Controller + Push Queue + Sender
# =========================================================================

class TestControllerPushIntegration:
    """End-to-end: controller.encolar_push → despachar_jobs_push → sender."""

    @pytest.mark.asyncio
    async def test_encolar_push_desde_controller(self, ctrl):
        ok, result = await ctrl.encolar_push(
            tipo="low_stock",
            destinatario="controller@test.com",
            asunto="Controller test",
            cuerpo="Controller body",
        )
        assert ok is True
        assert "id" in result

        jobs = await ctrl.obtener_jobs_push(estado="pendiente")
        assert any(j["id"] == result["id"] for j in jobs)

    @pytest.mark.asyncio
    async def test_despachar_push_con_mock_sender(self, ctrl):
        await ctrl.encolar_push(tipo="test", destinatario="d@test.com",
                                asunto="D", cuerpo="D")

        with patch("services.extended_features_db.despachar_jobs_pendientes") as mock_despachar:
            mock_despachar.return_value = {"procesados": 1, "enviados": 1, "fallidos": 0}
            result = await ctrl.despachar_jobs_push(limit=10)
            assert result["enviados"] == 1

    @pytest.mark.asyncio
    async def test_flujo_completo_whatsapp(self, ctrl):
        await ctrl.guardar_config_whatsapp({
            "wa_api_key": "test-key", "wa_phone_id": "test-ph",
            "wa_api_url": "https://graph.facebook.com/v18.0", "wa_enabled": "si",
        })
        await ctrl.encolar_push(tipo="low_stock", destinatario="+52123",
                                asunto="WA test", cuerpo="WhatsApp body")

        result = extended_features_db.despachar_jobs_pendientes(
            ctrl.db,
            sender=lambda _cfg, _a, _c: {"sent": True, "message_id": "mock-msg-1"},
            limit=10,
        )
        assert result["enviados"] >= 1

    @pytest.mark.asyncio
    async def test_flujo_completo_telegram(self, ctrl):
        await ctrl.guardar_config_telegram({
            "tg_bot_token": "bot:token", "tg_chat_id": "-100999", "tg_enabled": "si",
        })
        await ctrl.encolar_push(tipo="low_stock", destinatario="-100999",
                                asunto="TG test", cuerpo="<b>Telegram body</b>")

        result = extended_features_db.despachar_jobs_pendientes(
            ctrl.db,
            sender=lambda _cfg, _a, _c: {"sent": True, "message_id": 42},
            limit=10,
        )
        assert result["enviados"] >= 1


# =========================================================================
# Integration: Permission Enforcement
# =========================================================================

class TestPermissionEnforcement:
    """Verify RBAC gates block unauthorized operations."""

    @pytest.mark.asyncio
    async def test_whatsapp_config_sin_permiso(self, ctrl):
        ctrl.current_user_permissions = set()
        with pytest.raises(PermissionException):
            await ctrl.obtener_config_whatsapp()

    @pytest.mark.asyncio
    async def test_telegram_config_sin_permiso(self, ctrl):
        ctrl.current_user_permissions = set()
        with pytest.raises(PermissionException):
            await ctrl.obtener_config_telegram()

    @pytest.mark.asyncio
    async def test_crear_plantilla_sin_permiso(self, ctrl):
        ctrl.current_user_permissions = set()
        with pytest.raises(PermissionException):
            await ctrl.crear_plantilla_notificacion(
                nombre="No Perm", asunto="N", cuerpo="N", tipo="email"
            )

    @pytest.mark.asyncio
    async def test_crear_canal_sin_permiso(self, ctrl):
        ctrl.current_user_permissions = set()
        with pytest.raises(PermissionException):
            await ctrl.crear_canal_notificacion(
                nombre="No Perm", tipo="email", configuracion="{}"
            )


# =========================================================================
# Integration: Error Propagation Across Layers
# =========================================================================

class TestErrorPropagation:
    """Errors propagate correctly across layer boundaries."""

    @pytest.mark.asyncio
    async def test_enviar_prueba_whatsapp_sin_config(self, ctrl):
        await ctrl.guardar_config_whatsapp({
            "wa_api_key": "", "wa_phone_id": "",
            "wa_api_url": "", "wa_enabled": "no",
        })
        result = await ctrl.enviar_prueba_whatsapp("+52123")
        assert result["sent"] is False
        assert "empty" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_enviar_prueba_telegram_sin_chat_id(self, ctrl):
        await ctrl.guardar_config_telegram({
            "tg_bot_token": "bot:token", "tg_chat_id": "", "tg_enabled": "si",
        })
        result = await ctrl.enviar_prueba_telegram()
        assert result["sent"] is False
        assert "tg_chat_id not configured" in result["reason"]

    @pytest.mark.asyncio
    async def test_send_via_channel_channel_desconocido(self):
        with pytest.raises(ValueError, match="Unknown channel type"):
            await send_via_channel("fax", "+52123", "T", "B", {})

    def test_create_push_sender_func_sender_desconocido(self):
        sender = create_push_sender_func("slack", lambda: {})
        with pytest.raises(ValueError, match="Unknown channel type"):
            sender({}, "asunto", "cuerpo")

    @pytest.mark.asyncio
    async def test_send_via_channel_whatsapp_disabled(self):
        config = {"wa_api_key": "k", "wa_phone_id": "p", "wa_enabled": "no"}
        result = await send_via_channel("whatsapp", "+52123", "T", "B", config)
        assert result["sent"] is False
        assert "disabled" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_send_via_channel_telegram_disabled(self):
        config = {"tg_bot_token": "t", "tg_chat_id": "c", "tg_enabled": "no"}
        result = await send_via_channel("telegram", "-100", "T", "B", config)
        assert result["sent"] is False
        assert "disabled" in result["reason"].lower()


# =========================================================================
# Integration: EventBus + Notifications
# =========================================================================

class TestEventBusIntegration:
    """EventBus triggers notification creation correctly."""

    @pytest.mark.asyncio
    async def test_event_bus_crea_notificacion(self):
        from core.events import EventBus

        bus = EventBus()
        handler = AsyncMock()
        bus.on("notification.created", handler)
        await bus.emit("notification.created", titulo="Test", mensaje="Hello")
        handler.assert_awaited()

    @pytest.mark.asyncio
    async def test_event_bus_no_interfiere_sin_handler(self, ctrl):
        ok, result = await ctrl.crear_notificacion(
            titulo="No handler", mensaje="Should work",
            tipo="test", destinatario="admin",
        )
        assert ok is True
        assert "id" in result
