"""
Warehouse controller for almacenes, bulk operations, stock alerts, advanced search, and restocking
"""

from services import advanced_inventory_db
from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class WarehouseController:
    """Warehouse and bulk operations controller"""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Warehouse Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Stock alerts ============

    async def obtener_alertas_stock(self) -> list[dict]:
        """Get products with low stock (cantidad <= stock_min)."""
        try:
            return self.db.obtener_productos_con_stock_bajo()
        except Exception as e:
            logger.exception(f"Error fetching stock alerts: {e}")
            return []

    async def contar_alertas_stock(self) -> int:
        """Count of low-stock alerts. Cheap query for sidebar badge."""
        try:
            productos = await self.obtener_alertas_stock()
            return len(productos)
        except Exception:
            return 0

    # ============ Almacenes / Warehouses (F2.1) ============

    async def obtener_almacenes(self) -> list[dict]:
        try:
            return self.db.obtener_almacenes()
        except Exception as e:
            logger.exception(f"Error fetching warehouses: {e}")
            return []

    @require_permission(Perm.ALMACENES_GESTIONAR)
    async def crear_almacen(self, nombre: str, ubicacion: str = "") -> tuple[bool, dict]:
        if not nombre or len(nombre) < 2:
            return False, {"error": "Nombre inválido (mín. 2 caracteres)"}
        try:
            aid = self.db.crear_almacen(
                nombre=nombre, ubicacion=ubicacion, usuario=self.current_user or "system"
            )
            logger.info(f"Warehouse created: {nombre}")
            return True, {"id": aid, "nombre": nombre}
        except Exception as e:
            logger.exception(f"Error creating warehouse: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.ALMACENES_GESTIONAR)
    async def actualizar_almacen(
        self, almacen_id: int, nombre: str | None = None, ubicacion: str | None = None
    ) -> tuple[bool, dict]:
        try:
            self.db.actualizar_almacen(
                almacen_id=almacen_id,
                nombre=nombre,
                ubicacion=ubicacion,
                usuario=self.current_user or "system",
            )
            return True, {"message": "Almacén actualizado"}
        except Exception as e:
            logger.exception(f"Error updating warehouse: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.ALMACENES_GESTIONAR)
    async def eliminar_almacen(self, almacen_id: int) -> tuple[bool, dict]:
        try:
            self.db.eliminar_almacen(almacen_id=almacen_id, usuario=self.current_user or "system")
            return True, {"message": "Almacén eliminado"}
        except Exception as e:
            logger.exception(f"Error deleting warehouse: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.ALMACENES_STOCK)
    async def obtener_inventario_almacen(self, almacen_id: int) -> list[dict]:
        try:
            return self.db.obtener_inventario_almacen(almacen_id)
        except Exception as e:
            logger.exception(f"Error fetching warehouse inventory: {e}")
            return []

    @require_permission(Perm.ALMACENES_STOCK)
    async def ajustar_stock_almacen(
        self, producto_id: int, almacen_id: int, cantidad: int
    ) -> tuple[bool, dict]:
        try:
            old = self.db.ajustar_stock_almacen(
                producto_id=producto_id,
                almacen_id=almacen_id,
                cantidad=cantidad,
                usuario=self.current_user or "system",
            )
            logger.info(
                f"Warehouse stock adjusted: product={producto_id}, almacen={almacen_id}: {old} -> {cantidad}"
            )
            return True, {"old": old, "new": cantidad}
        except Exception as e:
            logger.exception(f"Error adjusting warehouse stock: {e}")
            return False, {"error": str(e)}

    async def obtener_todo_stock_almacenes(self) -> list[dict]:
        try:
            return self.db.obtener_todo_stock_almacenes()
        except Exception as e:
            logger.exception(f"Error fetching all warehouse stock: {e}")
            return []

    # ============ Bulk Operations (F2.2) ============

    @require_permission(Perm.BULK_ELIMINAR)
    async def bulk_eliminar_productos(self, ids: list[int]) -> tuple[bool, int]:
        try:
            count = self.db.bulk_eliminar_productos(ids=ids, usuario=self.current_user or "system")
            logger.info(f"Bulk deleted {count} products")
            return True, count
        except Exception as e:
            logger.exception(f"Error bulk deleting: {e}")
            return False, 0

    @require_permission(Perm.BULK_CATEGORIA)
    async def bulk_actualizar_categoria(self, ids: list[int], categoria: str) -> tuple[bool, int]:
        try:
            count = self.db.bulk_actualizar_categoria(
                ids=ids, categoria=categoria, usuario=self.current_user or "system"
            )
            logger.info(f"Bulk category update: {count} products -> {categoria}")
            return True, count
        except Exception as e:
            logger.exception(f"Error bulk updating category: {e}")
            return False, 0

    @require_permission(Perm.BULK_EXPORTAR)
    async def bulk_exportar_productos(self, ids: list[int], fmt: str = "csv") -> tuple[bool, str]:
        try:
            productos = self.db.bulk_exportar_productos(ids)
            if not productos:
                return False, "No products selected"
            if fmt == "csv":
                path = self.export_service.export_to_csv(productos)
            elif fmt == "json":
                path = self.export_service.export_to_json(productos)
            elif fmt == "xlsx":
                path = self.export_service.export_to_xlsx(productos)
            else:
                return False, f"Unsupported format: {fmt}"
            return True, str(path)
        except Exception as e:
            logger.exception(f"Error bulk exporting: {e}")
            return False, str(e)

    # ============ Fase 1: Búsqueda avanzada ============

    @require_permission(Perm.PRODUCTOS_LEER)
    async def buscar_productos_avanzado(
        self,
        texto: str | None = None,
        categoria: str | None = None,
        proveedor_id: int | None = None,
        precio_min: float | None = None,
        precio_max: float | None = None,
        stock_min: int | None = None,
        stock_max: int | None = None,
        solo_bajo_stock: bool = False,
        orden: str = "nombre",
        limite: int = 200,
    ) -> list[dict]:
        try:
            return advanced_inventory_db.buscar_productos_avanzado(
                self.db,
                texto=texto,
                categoria=categoria,
                proveedor_id=proveedor_id,
                precio_min=precio_min,
                precio_max=precio_max,
                stock_min=stock_min,
                stock_max=stock_max,
                solo_bajo_stock=solo_bajo_stock,
                orden=orden,
                limite=limite,
            )
        except Exception as e:
            logger.exception(f"Error in advanced search: {e}")
            return []

    # ============ Fase 1: Auto-reaprovisionamiento ============

    @require_permission(Perm.ORDENES_CREAR)
    async def sugerir_reabastecimiento(
        self,
        supplier_id: int | None = None,
    ) -> list[dict]:
        try:
            return advanced_inventory_db.sugerir_reabastecimiento(self.db, supplier_id=supplier_id)
        except Exception as e:
            logger.exception(f"Error computing suggestions: {e}")
            return []

    @require_permission(Perm.ORDENES_CREAR)
    async def crear_ordenes_desde_sugerencias(
        self,
        supplier_id: int,
        suggestions: list[dict],
    ) -> tuple[bool, dict]:
        try:
            ids = advanced_inventory_db.crear_ordenes_desde_sugerencias(
                self.db,
                supplier_id=supplier_id,
                suggestions=suggestions,
                usuario=self.current_user or "system",
            )
            return True, {"ids": ids, "count": len(ids)}
        except Exception as e:
            logger.exception(f"Error creating orders from suggestions: {e}")
            return False, {"error": str(e)}
