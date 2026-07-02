"""
Report controller for statistics, exports, charts, SMTP, and KPIs
"""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.notifier import get_smtp_config, send_low_stock_alert
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ReportController:
    """Reports, statistics, exports, and notifications controller"""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Report Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Reports ============

    async def obtener_estadisticas(self) -> dict:
        """Get inventory statistics"""
        try:
            return self.db.obtener_estadisticas()
        except Exception as e:
            logger.exception(f"Error fetching statistics: {e}")
            return {}

    async def obtener_historial_stock(self, producto_id: int) -> list[dict]:
        """Get stock history"""
        try:
            return self.db.obtener_historial_stock(producto_id)
        except Exception as e:
            logger.exception(f"Error fetching stock history: {e}")
            return []

    async def exportar_csv(self, productos: list[dict] | None = None) -> tuple[bool, str]:
        """Export products to CSV"""
        try:
            if not productos:
                productos = self.db.obtener_todos_productos()
            path = self.export_service.export_to_csv(productos)
            logger.info(f"CSV export completed: {path}")
            return True, str(path)
        except Exception as e:
            logger.exception(f"Error exporting CSV: {e}")
            return False, str(e)

    async def exportar_json(self, productos: list[dict] | None = None) -> tuple[bool, str]:
        """Export products to JSON"""
        try:
            if not productos:
                productos = self.db.obtener_todos_productos()
            path = self.export_service.export_to_json(productos)
            logger.info(f"JSON export completed: {path}")
            return True, str(path)
        except Exception as e:
            logger.exception(f"Error exporting JSON: {e}")
            return False, str(e)

    async def exportar_reporte(self) -> tuple[bool, str]:
        """Export summary report"""
        try:
            stats = await self.obtener_estadisticas()
            path = self.export_service.export_summary_report(stats)
            logger.info(f"Report export completed: {path}")
            return True, str(path)
        except Exception as e:
            logger.exception(f"Error exporting report: {e}")
            return False, str(e)

    async def exportar_pdf(self, productos: list[dict] | None = None) -> tuple[bool, str]:
        """Export products to PDF"""
        try:
            if not productos:
                productos = await self.db.obtener_todos_productos()
            path = self.export_service.export_to_pdf(productos)
            logger.info(f"PDF export completed: {path}")
            return True, str(path)
        except Exception as e:
            logger.exception(f"Error exporting PDF: {e}")
            return False, str(e)

    async def exportar_xlsx(self, productos: list[dict] | None = None) -> tuple[bool, str]:
        """Export products to Excel XLSX"""
        try:
            if not productos:
                productos = await self.db.obtener_todos_productos()
            path = self.export_service.export_to_xlsx(productos)
            logger.info(f"XLSX export completed: {path}")
            return True, str(path)
        except Exception as e:
            logger.exception(f"Error exporting XLSX: {e}")
            return False, str(e)

    # ============ Charts ============

    async def obtener_distribucion_categorias(self) -> list[dict]:
        try:
            return self.db.obtener_distribucion_categorias()
        except Exception as e:
            logger.exception(f"Error fetching category distribution: {e}")
            return []

    async def obtener_top_productos_stock(self, limit: int = 10) -> list[dict]:
        try:
            return self.db.obtener_top_productos_por_stock(limit=limit)
        except Exception as e:
            logger.exception(f"Error fetching top products: {e}")
            return []

    async def obtener_serie_inventario(self, dias: int = 30) -> list[dict]:
        try:
            return self.db.obtener_serie_inventario(dias=dias)
        except Exception as e:
            logger.exception(f"Error fetching inventory series: {e}")
            return []

    # ============ Notifications / Email (F2.3) ============

    @require_permission(Perm.NOTIFICACIONES_CONFIGURAR)
    async def obtener_config_smtp(self) -> dict:
        try:
            return get_smtp_config(self.db)
        except Exception as e:
            logger.exception(f"Error getting SMTP config: {e}")
            return {}

    @require_permission(Perm.NOTIFICACIONES_CONFIGURAR)
    async def guardar_config_smtp(self, config: dict) -> bool:
        try:
            for key in (
                "smtp_host",
                "smtp_port",
                "smtp_user",
                "smtp_password",
                "smtp_from_email",
                "smtp_to_email",
                "notify_low_stock",
            ):
                if key in config:
                    self.db.guardar_config(key, str(config[key]))
            return True
        except Exception as e:
            logger.exception(f"Error saving SMTP config: {e}")
            return False

    @require_permission(Perm.NOTIFICACIONES_CONFIGURAR)
    async def enviar_alerta_stock(self) -> dict:
        """Manually send low stock alert."""
        try:
            return send_low_stock_alert(self.db)
        except Exception as e:
            logger.exception(f"Error sending stock alert: {e}")
            return {"sent": False, "reason": str(e)}

    async def verificar_stock_bajo(self) -> list[dict]:
        """Get low stock products (for UI badge)."""
        try:
            return self.db.obtener_productos_stock_bajo()
        except Exception as e:
            logger.exception(f"Error checking low stock: {e}")
            return []
