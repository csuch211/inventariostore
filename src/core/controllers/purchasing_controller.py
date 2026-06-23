"""Purchasing controller for quotations, supplier evaluations, and receiving."""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PurchasingController:
    """Controller for purchasing operations."""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Purchasing Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Cotizaciones ============

    @require_permission(Perm.ORDENES_CREAR)
    async def crear_cotizacion(
        self,
        proveedor_id: int,
        items: list[dict],
        fecha_validez: str = "",
        notas: str = "",
    ) -> tuple[bool, dict]:
        """Create a quotation."""
        try:
            result = self.db.purchasing_repo.crear_cotizacion(
                proveedor_id=proveedor_id,
                items=items,
                fecha_validez=fecha_validez,
                notas=notas,
                usuario=self.current_user or "system",
            )
            return True, result
        except Exception as e:
            logger.error(f"Error creating quotation: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.ORDENES_LEER)
    async def obtener_cotizacion(self, cotizacion_id: int) -> dict | None:
        """Get quotation with detail lines."""
        try:
            return self.db.purchasing_repo.obtener_cotizacion(cotizacion_id)
        except Exception as e:
            logger.error(f"Error fetching quotation: {e}")
            return None

    @require_permission(Perm.ORDENES_LEER)
    async def obtener_cotizaciones(
        self, proveedor_id: int | None = None, estado: str | None = None
    ) -> list[dict]:
        """List quotations."""
        try:
            return self.db.purchasing_repo.obtener_cotizaciones(
                proveedor_id=proveedor_id, estado=estado
            )
        except Exception as e:
            logger.error(f"Error fetching quotations: {e}")
            return []

    @require_permission(Perm.ORDENES_CREAR)
    async def aprobar_cotizacion(self, cotizacion_id: int) -> tuple[bool, dict]:
        """Approve a quotation."""
        try:
            self.db.purchasing_repo.aprobar_cotizacion(
                cotizacion_id, usuario=self.current_user or "system"
            )
            return True, {"message": "Quotation approved"}
        except Exception as e:
            logger.error(f"Error approving quotation: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.ORDENES_CANCELAR)
    async def rechazar_cotizacion(self, cotizacion_id: int) -> tuple[bool, dict]:
        """Reject a quotation."""
        try:
            self.db.purchasing_repo.rechazar_cotizacion(
                cotizacion_id, usuario=self.current_user or "system"
            )
            return True, {"message": "Quotation rejected"}
        except Exception as e:
            logger.error(f"Error rejecting quotation: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.ORDENES_CREAR)
    async def convertir_a_orden(self, cotizacion_id: int) -> tuple[bool, dict]:
        """Convert quotation to purchase order."""
        try:
            result = self.db.purchasing_repo.convertir_a_orden(
                cotizacion_id, usuario=self.current_user or "system"
            )
            return True, result
        except Exception as e:
            logger.error(f"Error converting quotation: {e}")
            return False, {"error": str(e)}

    # ============ Evaluaciones de Proveedor ============

    @require_permission(Perm.PROVEEDORES_GESTIONAR)
    async def crear_evaluacion_proveedor(self, **kwargs) -> tuple[bool, dict]:
        """Create supplier evaluation."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.purchasing_repo.crear_evaluacion_proveedor(**kwargs)
            return True, result
        except Exception as e:
            logger.error(f"Error creating supplier evaluation: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.PROVEEDORES_LEER)
    async def obtener_evaluaciones_proveedor(
        self, proveedor_id: int | None = None
    ) -> list[dict]:
        """List supplier evaluations."""
        try:
            return self.db.purchasing_repo.obtener_evaluaciones_proveedor(
                proveedor_id=proveedor_id
            )
        except Exception as e:
            logger.error(f"Error fetching evaluations: {e}")
            return []

    @require_permission(Perm.PROVEEDORES_LEER)
    async def promedio_evaluacion_proveedor(self, proveedor_id: int) -> dict:
        """Get average evaluation scores for a supplier."""
        try:
            return self.db.purchasing_repo.promedio_evaluacion_proveedor(proveedor_id)
        except Exception as e:
            logger.error(f"Error calculating average scores: {e}")
            return {}

    # ============ Recepciones ============

    @require_permission(Perm.ORDENES_RECIBIR)
    async def crear_recepcion(
        self,
        proveedor_id: int,
        items: list[dict],
        orden_compra_id: int | None = None,
        calidad: str = "aceptada",
        notas: str = "",
    ) -> tuple[bool, dict]:
        """Create a goods received note."""
        try:
            result = self.db.purchasing_repo.crear_recepcion(
                proveedor_id=proveedor_id,
                items=items,
                orden_compra_id=orden_compra_id,
                calidad=calidad,
                notas=notas,
                usuario=self.current_user or "system",
            )
            return True, result
        except Exception as e:
            logger.error(f"Error creating reception: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.ORDENES_LEER)
    async def obtener_recepciones(
        self, proveedor_id: int | None = None
    ) -> list[dict]:
        """List receptions."""
        try:
            return self.db.purchasing_repo.obtener_recepciones(
                proveedor_id=proveedor_id
            )
        except Exception as e:
            logger.error(f"Error fetching receptions: {e}")
            return []
