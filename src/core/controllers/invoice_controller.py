"""Invoice controller for billing operations."""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class InvoiceController:
    """Controller for invoice and billing operations."""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Invoice Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    @require_permission(Perm.FACTURAS_CREAR)
    async def crear_factura(
        self,
        cliente_id: int,
        items: list[dict],
        tipo: str = "factura",
        descuento_total: float = 0,
        notas: str = "",
        venta_id: int | None = None,
    ) -> tuple[bool, dict]:
        """Create an invoice."""
        try:
            result = self.db.invoice_repo.crear_factura(
                cliente_id=cliente_id,
                items=items,
                tipo=tipo,
                descuento_total=descuento_total,
                notas=notas,
                usuario=self.current_user or "system",
                venta_id=venta_id,
            )
            return True, result
        except Exception as e:
            logger.exception(f"Error creating invoice: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.FACTURAS_LEER)
    async def obtener_factura(self, factura_id: int) -> dict | None:
        """Get invoice with line items."""
        try:
            return self.db.invoice_repo.obtener_factura(factura_id)
        except Exception as e:
            logger.exception(f"Error fetching invoice: {e}")
            return None

    @require_permission(Perm.FACTURAS_LEER)
    async def obtener_facturas(
        self, estado: str | None = None, cliente_id: int | None = None
    ) -> list[dict]:
        """List invoices."""
        try:
            return self.db.invoice_repo.obtener_facturas(estado=estado, cliente_id=cliente_id)
        except Exception as e:
            logger.exception(f"Error fetching invoices: {e}")
            return []

    @require_permission(Perm.FACTURAS_CANCELAR)
    async def cancelar_factura(self, factura_id: int) -> tuple[bool, dict]:
        """Cancel an invoice."""
        try:
            self.db.invoice_repo.eliminar_factura(factura_id, usuario=self.current_user or "system")
            return True, {"message": "Invoice cancelled"}
        except Exception as e:
            logger.exception(f"Error cancelling invoice: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.FACTURAS_CREAR)
    async def crear_factura_desde_venta(self, venta_id: int) -> tuple[bool, dict]:
        """Create an invoice from an existing sale."""
        try:
            venta = self.db.sale_repo.obtener_venta_por_id(venta_id)
            if not venta:
                return False, {"error": "Sale not found"}

            items = []
            for det in venta.get("detalles", []):
                items.append({
                    "producto_id": det.get("producto_id"),
                    "descripcion": det.get("producto_nombre", ""),
                    "cantidad": det.get("cantidad", 1),
                    "precio_unitario": det.get("precio_unitario", 0),
                })

            result = self.db.invoice_repo.crear_factura(
                cliente_id=venta.get("cliente_id", 1),
                items=items,
                tipo="factura",
                notas=f"Generada desde venta #{venta_id}",
                usuario=self.current_user or "system",
                venta_id=venta_id,
            )
            return True, result
        except Exception as e:
            logger.exception(f"Error creating invoice from sale: {e}")
            return False, {"error": str(e)}
