"""Notifications controller for notification management."""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.messaging import send_via_channel
from services.permissions import Perm, require_permission
from utils.crypto import SECRET_KEYS, encrypt_value
from utils.logger import setup_logger

logger = setup_logger(__name__)

WHATSAPP_CFG_KEYS = frozenset({"wa_api_key", "wa_phone_id", "wa_api_url", "wa_enabled"})
TELEGRAM_CFG_KEYS = frozenset({"tg_bot_token", "tg_chat_id", "tg_enabled"})


class NotificationController:
    """Controller for notification operations."""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Notification Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Plantillas ============

    @require_permission(Perm.NOTIFICACIONES_CONFIGURAR)
    async def crear_plantilla(self, **kwargs) -> tuple[bool, dict]:
        """Create notification template."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.notification_repo.crear_plantilla(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error creating template: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.NOTIFICACIONES_CONFIGURAR)
    async def obtener_plantillas(self, tipo: str | None = None) -> list[dict]:
        """List notification templates."""
        try:
            return self.db.notification_repo.obtener_plantillas(tipo=tipo)
        except Exception as e:
            logger.exception(f"Error fetching templates: {e}")
            return []

    @require_permission(Perm.NOTIFICACIONES_CONFIGURAR)
    async def eliminar_plantilla(self, plantilla_id: int) -> tuple[bool, dict]:
        """Delete notification template."""
        try:
            self.db.notification_repo.eliminar_plantilla(
                plantilla_id, usuario=self.current_user or "system"
            )
            return True, {"message": "Template deleted"}
        except Exception as e:
            logger.exception(f"Error deleting template: {e}")
            return False, {"error": str(e)}

    # ============ Canales ============

    @require_permission(Perm.NOTIFICACIONES_CONFIGURAR)
    async def crear_canal(self, **kwargs) -> tuple[bool, dict]:
        """Create notification channel."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.notification_repo.crear_canal(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error creating channel: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.NOTIFICACIONES_CONFIGURAR)
    async def obtener_canales(self) -> list[dict]:
        """List notification channels."""
        try:
            return self.db.notification_repo.obtener_canales()
        except Exception as e:
            logger.exception(f"Error fetching channels: {e}")
            return []

    # ============ Notificaciones ============

    @require_permission(Perm.NOTIFICACIONES_CONFIGURAR)
    async def crear_notificacion(self, **kwargs) -> tuple[bool, dict]:
        """Create a notification."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.notification_repo.crear_notificacion(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error creating notification: {e}")
            return False, {"error": str(e)}

    async def obtener_notificaciones(
        self, destinatario: str | None = None, tipo: str | None = None,
        estado: str | None = None, limit: int = 50
    ) -> list[dict]:
        """List notifications."""
        try:
            return self.db.notification_repo.obtener_notificaciones(
                destinatario=destinatario, tipo=tipo, estado=estado, limit=limit
            )
        except Exception as e:
            logger.exception(f"Error fetching notifications: {e}")
            return []

    async def marcar_leido(self, notificacion_id: int) -> tuple[bool, dict]:
        """Mark notification as read."""
        try:
            self.db.notification_repo.marcar_leido(notificacion_id)
            return True, {"message": "Notification marked as read"}
        except Exception as e:
            logger.exception(f"Error marking notification: {e}")
            return False, {"error": str(e)}

    async def marcar_todas_leidas(self, destinatario: str | None = None) -> tuple[bool, dict]:
        """Mark all notifications as read."""
        try:
            count = self.db.notification_repo.marcar_todas_leidas(destinatario)
            return True, {"count": count}
        except Exception as e:
            logger.exception(f"Error marking notifications: {e}")
            return False, {"error": str(e)}

    async def contar_no_leidas(self, destinatario: str | None = None) -> int:
        """Count unread notifications."""
        try:
            return self.db.notification_repo.contar_no_leidas(destinatario)
        except Exception as e:
            logger.exception(f"Error counting notifications: {e}")
            return 0

    async def eliminar_notificacion(self, notificacion_id: int) -> tuple[bool, dict]:
        """Delete notification."""
        try:
            self.db.notification_repo.eliminar_notificacion(notificacion_id)
            return True, {"message": "Notification deleted"}
        except Exception as e:
            logger.exception(f"Error deleting notification: {e}")
            return False, {"error": str(e)}

    # ============ Preferencias ============

    async def obtener_preferencias(self, usuario_id: int) -> dict:
        """Get user notification preferences."""
        try:
            return self.db.notification_repo.obtener_preferencias(usuario_id)
        except Exception as e:
            logger.exception(f"Error fetching preferences: {e}")
            return {}

    async def guardar_preferencias(self, usuario_id: int, preferencias: dict) -> tuple[bool, dict]:
        """Save user notification preferences."""
        try:
            self.db.notification_repo.guardar_preferencias(usuario_id, preferencias)
            return True, {"message": "Preferences saved"}
        except Exception as e:
            logger.exception(f"Error saving preferences: {e}")
            return False, {"error": str(e)}

    # ============ WhatsApp ============

    @require_permission(Perm.WHATSAPP_CONFIGURAR)
    async def obtener_config_whatsapp(self) -> dict:
        """Get WhatsApp config from DB."""
        return {
            k: self.db.obtener_config(k, "")
            for k in WHATSAPP_CFG_KEYS
        }

    @require_permission(Perm.WHATSAPP_CONFIGURAR)
    async def guardar_config_whatsapp(self, config: dict) -> tuple[bool, dict]:
        """Save WhatsApp config to DB."""
        try:
            for k in WHATSAPP_CFG_KEYS:
                if k in config:
                    value = str(config[k])
                    if k in SECRET_KEYS:
                        value = encrypt_value(value)
                    self.db.guardar_config(k, value)
            return True, {"message": "WhatsApp configuration saved"}
        except Exception as e:
            logger.exception(f"Error saving WhatsApp config: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.WHATSAPP_ENVIAR)
    async def enviar_prueba_whatsapp(self, destinatario: str) -> dict:
        """Send a test WhatsApp message."""
        try:
            config = await self.obtener_config_whatsapp()
            return await send_via_channel(
                "whatsapp", destinatario,
                "Test", "Test message from InventarioStore",
                config,
            )
        except Exception as e:
            logger.exception(f"Error sending WhatsApp test: {e}")
            return {"sent": False, "reason": str(e)}

    # ============ Telegram ============

    @require_permission(Perm.TELEGRAM_CONFIGURAR)
    async def obtener_config_telegram(self) -> dict:
        """Get Telegram config from DB."""
        return {
            k: self.db.obtener_config(k, "")
            for k in TELEGRAM_CFG_KEYS
        }

    @require_permission(Perm.TELEGRAM_CONFIGURAR)
    async def guardar_config_telegram(self, config: dict) -> tuple[bool, dict]:
        """Save Telegram config to DB."""
        try:
            for k in TELEGRAM_CFG_KEYS:
                if k in config:
                    value = str(config[k])
                    if k in SECRET_KEYS:
                        value = encrypt_value(value)
                    self.db.guardar_config(k, value)
            return True, {"message": "Telegram configuration saved"}
        except Exception as e:
            logger.exception(f"Error saving Telegram config: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.TELEGRAM_ENVIAR)
    async def enviar_prueba_telegram(self) -> dict:
        """Send a test Telegram message."""
        try:
            config = await self.obtener_config_telegram()
            chat_id = config.get("tg_chat_id", "")
            if not chat_id:
                return {"sent": False, "reason": "tg_chat_id not configured"}
            return await send_via_channel(
                "telegram", chat_id,
                "Test", "<b>Test message</b> from InventarioStore",
                config,
            )
        except Exception as e:
            logger.exception(f"Error sending Telegram test: {e}")
            return {"sent": False, "reason": str(e)}
