"""Inventory controller for comprehensive inventory management.

Combines existing warehouse/stock functionality with new analysis capabilities.
"""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.inventory_analysis import (
    analisis_abc,
    analisis_envejecimiento,
    calcular_riesgo_agotamiento,
    calcular_rotacion_inventario,
)
from services.inventory_valuation import calcular_valor_inventario
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class InventoryController:
    """Comprehensive inventory management controller."""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Inventory Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Stock Management ============

    @require_permission(Perm.STOCK_LEER)
    async def obtener_stock_producto(self, producto_id: int) -> dict | None:
        """Get stock information for a product."""
        try:
            return self.db.obtener_producto_por_id(producto_id)
        except Exception as e:
            logger.exception(f"Error fetching product stock: {e}")
            return None

    @require_permission(Perm.STOCK_ACTUALIZAR)
    async def ajustar_stock(
        self, producto_id: int, cantidad: int, tipo: str = "ajuste", razon: str = ""
    ) -> tuple[bool, dict]:
        """Adjust product stock."""
        try:
            result = self.db.actualizar_stock(
                producto_id=producto_id,
                cantidad_nueva=cantidad,
                tipo_movimiento=tipo,
                razon=razon,
                usuario=self.current_user or "system",
            )
            return True, result
        except Exception as e:
            logger.exception(f"Error adjusting stock: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.STOCK_LEER)
    async def obtener_historial_stock(self, producto_id: int) -> list[dict]:
        """Get stock movement history for a product."""
        try:
            return self.db.obtener_historial_stock(producto_id)
        except Exception as e:
            logger.exception(f"Error fetching stock history: {e}")
            return []

    # ============ Warehouse Management ============

    @require_permission(Perm.ALMACENES_LEER)
    async def obtener_almacenes(self) -> list[dict]:
        """List all warehouses."""
        try:
            return self.db.obtener_almacenes()
        except Exception as e:
            logger.exception(f"Error fetching warehouses: {e}")
            return []

    @require_permission(Perm.ALMACENES_GESTIONAR)
    async def crear_almacen(self, nombre: str, ubicacion: str = "") -> tuple[bool, dict]:
        """Create a warehouse."""
        try:
            result = self.db.crear_almacen(
                nombre=nombre, ubicacion=ubicacion, usuario=self.current_user or "system"
            )
            return True, result
        except Exception as e:
            logger.exception(f"Error creating warehouse: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.ALMACENES_STOCK)
    async def obtener_inventario_almacen(self, almacen_id: int) -> list[dict]:
        """Get inventory for a specific warehouse."""
        try:
            return self.db.obtener_inventario_almacen(almacen_id)
        except Exception as e:
            logger.exception(f"Error fetching warehouse inventory: {e}")
            return []

    # ============ Inventory Analysis ============

    @require_permission(Perm.STOCK_LEER)
    async def analisis_abc(self) -> list[dict]:
        """Perform ABC analysis on inventory."""
        try:
            productos = self.db.obtener_todos_productos()
            return analisis_abc(productos)
        except Exception as e:
            logger.exception(f"Error performing ABC analysis: {e}")
            return []

    @require_permission(Perm.STOCK_LEER)
    async def calcular_rotacion(self, dias: int = 30) -> dict:
        """Calculate inventory turnover."""
        try:
            productos = self.db.obtener_todos_productos()
            # Get sales for the period
            ventas = self.db.obtener_ventas()
            return calcular_rotacion_inventario(productos, ventas)
        except Exception as e:
            logger.exception(f"Error calculating turnover: {e}")
            return {"turnover_ratio": 0, "days_of_supply": 0, "stockout_risk": "unknown"}

    @require_permission(Perm.STOCK_LEER)
    async def analisis_envejecimiento(self) -> list[dict]:
        """Analyze inventory aging."""
        try:
            productos = self.db.obtener_todos_productos()
            return analisis_envejecimiento(productos)
        except Exception as e:
            logger.exception(f"Error performing aging analysis: {e}")
            return []

    @require_permission(Perm.STOCK_LEER)
    async def riesgo_agotamiento(self) -> list[dict]:
        """Calculate stockout risk for all products."""
        try:
            productos = self.db.obtener_todos_productos()
            return calcular_riesgo_agotamiento(productos)
        except Exception as e:
            logger.exception(f"Error calculating stockout risk: {e}")
            return []

    @require_permission(Perm.STOCK_LEER)
    async def valor_inventario(self, metodo: str = "promedio") -> dict:
        """Calculate inventory valuation."""
        try:
            productos = self.db.obtener_todos_productos()
            return calcular_valor_inventario(productos, metodo)
        except Exception as e:
            logger.exception(f"Error calculating inventory valuation: {e}")
            return {"total_value": 0, "total_quantity": 0, "average_cost": 0}

    # ============ Inventory Reports ============

    @require_permission(Perm.STOCK_LEER)
    async def generar_reporte_inventario(self) -> dict:
        """Generate comprehensive inventory report."""
        try:
            productos = self.db.obtener_todos_productos()

            # Basic stats
            total_productos = len(productos)
            total_unidades = sum(p.get("cantidad", 0) for p in productos)
            valor_total = sum(p.get("cantidad", 0) * p.get("precio", 0) for p in productos)

            # ABC analysis
            abc = analisis_abc(productos)
            abc_summary = {
                "A": len([p for p in abc if p.get("abc_class") == "A"]),
                "B": len([p for p in abc if p.get("abc_class") == "B"]),
                "C": len([p for p in abc if p.get("abc_class") == "C"]),
            }

            # Stockout risk
            risk = calcular_riesgo_agotamiento(productos)
            risk_summary = {
                "critical": len([p for p in risk if p.get("risk_level") == "critical"]),
                "high": len([p for p in risk if p.get("risk_level") == "high"]),
                "medium": len([p for p in risk if p.get("risk_level") == "medium"]),
                "low": len([p for p in risk if p.get("risk_level") == "low"]),
            }

            # Valuation
            valuation = calcular_valor_inventario(productos)

            return {
                "total_productos": total_productos,
                "total_unidades": total_unidades,
                "valor_total": valor_total,
                "abc_analysis": abc_summary,
                "stockout_risk": risk_summary,
                "valuation": valuation,
            }
        except Exception as e:
            logger.exception(f"Error generating inventory report: {e}")
            return {}
