"""
Sales controller for clients, sales, and cash register operations
"""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger
from utils.validators import Validator

logger = setup_logger(__name__)


class SalesController:
    """Sales and client management controller"""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Sales Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Client management (Sales module) ============

    async def obtener_clientes(self) -> list[dict]:
        try:
            return self.db.obtener_clientes()
        except Exception as e:
            logger.error(f"Error fetching customers: {e}")
            return []

    async def obtener_cliente(self, cliente_id: int) -> dict | None:
        try:
            return self.db.obtener_cliente_por_id(cliente_id)
        except Exception as e:
            logger.error(f"Error fetching customer: {e}")
            return None

    @require_permission(Perm.CLIENTES_GESTIONAR)
    async def crear_cliente(
        self, nombre: str, telefono: str = "", email: str = "", direccion: str = ""
    ) -> tuple[bool, dict]:
        if not nombre or len(nombre) < 2:
            return False, {"error": "El nombre debe tener al menos 2 caracteres"}
        try:
            cliente_id = self.db.crear_cliente(
                nombre=nombre,
                telefono=telefono,
                email=email,
                direccion=direccion,
                usuario=self.current_user or "system",
            )
            logger.info(f"Customer created: {nombre}")
            return True, {"id": cliente_id, "nombre": nombre}
        except Exception as e:
            logger.error(f"Error creating customer: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CLIENTES_GESTIONAR)
    async def actualizar_cliente(
        self, cliente_id: int, nombre: str, telefono: str = "", email: str = "", direccion: str = ""
    ) -> tuple[bool, dict]:
        if not nombre or len(nombre) < 2:
            return False, {"error": "El nombre debe tener al menos 2 caracteres"}
        try:
            self.db.actualizar_cliente(
                cliente_id=cliente_id,
                nombre=nombre,
                telefono=telefono,
                email=email,
                direccion=direccion,
                usuario=self.current_user or "system",
            )
            logger.info(f"Customer {cliente_id} updated")
            return True, {"id": cliente_id, "nombre": nombre}
        except Exception as e:
            logger.error(f"Error updating customer: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CLIENTES_GESTIONAR)
    async def eliminar_cliente(self, cliente_id: int) -> tuple[bool, dict]:
        try:
            self.db.eliminar_cliente(
                cliente_id=cliente_id,
                usuario=self.current_user or "system",
            )
            logger.info(f"Customer {cliente_id} deleted")
            return True, {"message": "Cliente eliminado"}
        except Exception as e:
            logger.error(f"Error deleting customer: {e}")
            return False, {"error": str(e)}

    # ============ Sales / POS ============

    async def obtener_ventas(self) -> list[dict]:
        try:
            return self.db.obtener_ventas()
        except Exception as e:
            logger.error(f"Error fetching sales: {e}")
            return []

    async def obtener_venta(self, venta_id: int) -> dict | None:
        try:
            return self.db.obtener_venta_por_id(venta_id)
        except Exception as e:
            logger.error(f"Error fetching sale: {e}")
            return None

    @require_permission(Perm.VENTAS_CREAR)
    async def crear_venta(
        self,
        cliente_id: int,
        items: list[dict],
        metodo_pago: str = "efectivo",
        referencia: str = "",
    ) -> tuple[bool, dict]:
        """Create a new sale.

        Args:
            cliente_id: Customer ID (0 for walk-in).
            items: List of dicts with keys: producto_id, cantidad, precio_unitario, subtotal.
            metodo_pago: Payment method (efectivo, tarjeta, transferencia, etc).
            referencia: Payment reference if applicable.

        Returns:
            Tuple[bool, Dict] with venta_id on success.
        """
        if not items:
            return False, {"error": "La venta debe tener al menos un producto"}
        for item in items:
            if not Validator.validate_cantidad(str(item.get("cantidad", 0)))[0]:
                return False, {"error": "Cantidad inválida en uno de los productos"}
        try:
            total = sum(item.get("subtotal", 0) for item in items)

            venta_id = self.db.crear_venta(
                cliente_id=cliente_id if cliente_id > 0 else None,
                total=total,
                items=items,
                metodo_pago=metodo_pago,
                referencia=referencia,
                usuario=self.current_user or "system",
            )
            logger.info(f"Sale created: #{venta_id} total=${total:.2f}")
            return True, {"id": venta_id, "total": total}
        except Exception as e:
            logger.error(f"Error creating sale: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.VENTAS_CANCELAR)
    async def cancelar_venta(self, venta_id: int) -> tuple[bool, dict]:
        try:
            self.db.cancelar_venta(
                venta_id=venta_id,
                usuario=self.current_user or "system",
            )
            logger.info(f"Sale cancelled: #{venta_id}")
            return True, {"message": "Venta cancelada y stock revertido"}
        except Exception as e:
            logger.error(f"Error cancelling sale: {e}")
            return False, {"error": str(e)}

    async def obtener_estadisticas_ventas(self) -> dict:
        try:
            return self.db.obtener_ventas_estadisticas()
        except Exception as e:
            logger.error(f"Error fetching sales stats: {e}")
            return {"total_ventas": 0, "ingresos_totales": 0, "ingresos_hoy": 0, "ventas_hoy": 0}
