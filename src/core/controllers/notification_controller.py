"""Notifications controller for notification management."""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


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
            logger.error(f"Error creating template: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.NOTIFICACIONES_CONFIGURAR)
    async def obtener_plantillas(self, tipo: str | None = None) -> list[dict]:
        """List notification templates."""
        try:
            return self.db.notification_repo.obtener_plantillas(tipo=tipo)
        except Exception as e:
            logger.error(f"Error fetching templates: {e}")
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
            logger.error(f"Error deleting template: {e}")
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
            logger.error(f"Error creating channel: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.NOTIFICACIONES_CONFIGURAR)
    async def obtener_canales(self) -> list[dict]:
        """List notification channels."""
        try:
            return self.db.notification_repo.obtener_canales()
        except Exception as e:
            logger.error(f"Error fetching channels: {e}")
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
            logger.error(f"Error creating notification: {e}")
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
            logger.error(f"Error fetching notifications: {e}")
            return []

    async def marcar_leido(self, notificacion_id: int) -> tuple[bool, dict]:
        """Mark notification as read."""
        try:
            self.db.notification_repo.marcar_leido(notificacion_id)
            return True, {"message": "Notification marked as read"}
        except Exception as e:
            logger.error(f"Error marking notification: {e}")
            return False, {"error": str(e)}

    async def marcar_todas_leidas(self, destinatario: str | None = None) -> tuple[bool, dict]:
        """Mark all notifications as read."""
        try:
            count = self.db.notification_repo.marcar_todas_leidas(destinatario)
            return True, {"count": count}
        except Exception as e:
            logger.error(f"Error marking notifications: {e}")
            return False, {"error": str(e)}

    async def contar_no_leidas(self, destinatario: str | None = None) -> int:
        """Count unread notifications."""
        try:
            return self.db.notification_repo.contar_no_leidas(destinatario)
        except Exception as e:
            logger.error(f"Error counting notifications: {e}")
            return 0

    async def eliminar_notificacion(self, notificacion_id: int) -> tuple[bool, dict]:
        """Delete notification."""
        try:
            self.db.notification_repo.eliminar_notificacion(notificacion_id)
            return True, {"message": "Notification deleted"}
        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            return False, {"error": str(e)}

    # ============ Preferencias ============

    async def obtener_preferencias(self, usuario_id: int) -> dict:
        """Get user notification preferences."""
        try:
            return self.db.notification_repo.obtener_preferencias(usuario_id)
        except Exception as e:
            logger.error(f"Error fetching preferences: {e}")
            return {}

    async def guardar_preferencias(self, usuario_id: int, preferencias: dict) -> tuple[bool, dict]:
        """Save user notification preferences."""
        try:
            self.db.notification_repo.guardar_preferencias(usuario_id, preferencias)
            return True, {"message": "Preferences saved"}
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
            return False, {"error": str(e)}
