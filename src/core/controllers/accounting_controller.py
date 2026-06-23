"""Accounting controller for double-entry bookkeeping."""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AccountingController:
    """Controller for accounting operations."""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Accounting Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    @require_permission(Perm.CONTABILIDAD_ASIENTOS)
    async def crear_asiento(
        self,
        fecha: str,
        descripcion: str,
        tipo: str,
        movimientos: list[dict],
        referencia_id: int | None = None,
        referencia_tipo: str | None = None,
    ) -> tuple[bool, dict]:
        """Create a journal entry."""
        try:
            result = self.db.accounting_repo.crear_asiento(
                fecha=fecha,
                descripcion=descripcion,
                tipo=tipo,
                movimientos=movimientos,
                usuario=self.current_user or "system",
                referencia_id=referencia_id,
                referencia_tipo=referencia_tipo,
            )
            return True, result
        except Exception as e:
            logger.error(f"Error creating journal entry: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CONTABILIDAD_LEER)
    async def obtener_asiento(self, asiento_id: int) -> dict | None:
        """Get journal entry with movements."""
        try:
            return self.db.accounting_repo.obtener_asiento(asiento_id)
        except Exception as e:
            logger.error(f"Error fetching journal entry: {e}")
            return None

    @require_permission(Perm.CONTABILIDAD_LEER)
    async def obtener_asientos(
        self, fecha_inicio: str | None = None, fecha_fin: str | None = None
    ) -> list[dict]:
        """List journal entries."""
        try:
            return self.db.accounting_repo.obtener_asientos(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
        except Exception as e:
            logger.error(f"Error fetching journal entries: {e}")
            return []

    @require_permission(Perm.CONTABILIDAD_PLAN_CUENTAS)
    async def obtener_plan_cuentas(self, tipo: str | None = None) -> list[dict]:
        """Get chart of accounts."""
        try:
            return self.db.accounting_repo.obtener_plan_cuentas(tipo=tipo)
        except Exception as e:
            logger.error(f"Error fetching chart of accounts: {e}")
            return []

    @require_permission(Perm.CONTABILIDAD_LEER)
    async def obtener_balance_comprobacion(
        self, fecha_inicio: str | None = None, fecha_fin: str | None = None
    ) -> list[dict]:
        """Get trial balance."""
        try:
            return self.db.accounting_repo.obtener_balance_comprobacion(
                fecha_inicio=fecha_inicio, fecha_fin=fecha_fin
            )
        except Exception as e:
            logger.error(f"Error fetching trial balance: {e}")
            return []

    @require_permission(Perm.CONTABILIDAD_ASIENTOS)
    async def crear_asiento_venta(self, venta_id: int) -> tuple[bool, dict]:
        """Create automatic journal entry for a sale."""
        try:
            venta = self.db.sale_repo.obtener_venta_por_id(venta_id)
            if not venta:
                return False, {"error": "Sale not found"}

            total = venta.get("total", 0)
            from datetime import datetime
            fecha = datetime.now().strftime("%Y-%m-%d")

            movimientos = [
                {"cuenta_codigo": "1.1.01", "cuenta_nombre": "Caja", "debito": total, "credito": 0},
                {"cuenta_codigo": "4.1.01", "cuenta_nombre": "Ventas de Mercancía", "debito": 0, "credito": total},
            ]

            result = self.db.accounting_repo.crear_asiento(
                fecha=fecha,
                descripcion=f"Venta #{venta_id}",
                tipo="venta",
                movimientos=movimientos,
                usuario=self.current_user or "system",
                referencia_id=venta_id,
                referencia_tipo="venta",
            )
            return True, result
        except Exception as e:
            logger.error(f"Error creating sale journal entry: {e}")
            return False, {"error": str(e)}
