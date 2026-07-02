"""Sales controller for enhanced sales operations."""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SalesEnhancedController:
    """Controller for enhanced sales operations."""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Sales Enhanced Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Descuentos ============

    @require_permission(Perm.VENTAS_CREAR)
    async def crear_descuento(self, **kwargs) -> tuple[bool, dict]:
        """Create a discount code."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.sales_enhanced_repo.crear_descuento(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error creating discount: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.VENTAS_LEER)
    async def obtener_descuentos(self) -> list[dict]:
        """List discounts."""
        try:
            return self.db.sales_enhanced_repo.obtener_descuentos()
        except Exception as e:
            logger.exception(f"Error fetching discounts: {e}")
            return []

    @require_permission(Perm.VENTAS_CREAR)
    async def aplicar_descuento(self, codigo: str) -> dict | None:
        """Apply a discount code."""
        try:
            return self.db.sales_enhanced_repo.aplicar_descuento(codigo)
        except Exception as e:
            logger.exception(f"Error applying discount: {e}")
            return None

    @require_permission(Perm.VENTAS_CREAR)
    async def eliminar_descuento(self, descuento_id: int) -> tuple[bool, dict]:
        """Delete discount."""
        try:
            self.db.sales_enhanced_repo.eliminar_descuento(
                descuento_id, usuario=self.current_user or "system"
            )
            return True, {"message": "Discount deleted"}
        except Exception as e:
            logger.exception(f"Error deleting discount: {e}")
            return False, {"error": str(e)}

    # ============ Promociones ============

    @require_permission(Perm.VENTAS_CREAR)
    async def crear_promocion(self, **kwargs) -> tuple[bool, dict]:
        """Create a promotion."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.sales_enhanced_repo.crear_promocion(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error creating promotion: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.VENTAS_LEER)
    async def obtener_promociones(self) -> list[dict]:
        """List promotions."""
        try:
            return self.db.sales_enhanced_repo.obtener_promociones()
        except Exception as e:
            logger.exception(f"Error fetching promotions: {e}")
            return []

    @require_permission(Perm.VENTAS_CREAR)
    async def eliminar_promocion(self, promocion_id: int) -> tuple[bool, dict]:
        """Delete promotion."""
        try:
            self.db.sales_enhanced_repo.eliminar_promocion(
                promocion_id, usuario=self.current_user or "system"
            )
            return True, {"message": "Promotion deleted"}
        except Exception as e:
            logger.exception(f"Error deleting promotion: {e}")
            return False, {"error": str(e)}

    # ============ Reportes de Ventas ============

    @require_permission(Perm.VENTAS_LEER)
    async def ventas_por_periodo(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Get sales summary for a period."""
        try:
            return self.db.sales_enhanced_repo.ventas_por_periodo(fecha_inicio, fecha_fin)
        except Exception as e:
            logger.exception(f"Error fetching sales report: {e}")
            return {}

    @require_permission(Perm.VENTAS_LEER)
    async def ventas_por_producto(self, fecha_inicio: str, fecha_fin: str) -> list[dict]:
        """Get sales by product."""
        try:
            return self.db.sales_enhanced_repo.ventas_por_producto(fecha_inicio, fecha_fin)
        except Exception as e:
            logger.exception(f"Error fetching sales by product: {e}")
            return []

    @require_permission(Perm.VENTAS_LEER)
    async def ventas_por_cliente(self, fecha_inicio: str, fecha_fin: str) -> list[dict]:
        """Get sales by client."""
        try:
            return self.db.sales_enhanced_repo.ventas_por_cliente(fecha_inicio, fecha_fin)
        except Exception as e:
            logger.exception(f"Error fetching sales by client: {e}")
            return []
