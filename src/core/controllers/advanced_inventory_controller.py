"""
Advanced inventory controller for returns, transfers, counting, lots, prices, taxes, cash register, and KPIs
"""

from services import advanced_inventory_db
from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.exceptions import (
    DatabaseException,
    StockInsufficientException,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AdvancedInventoryController:
    """Advanced inventory features controller"""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("AdvancedInventory Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Fase 1: Devoluciones ============

    @require_permission(Perm.DEVOLUCIONES_CREAR)
    async def crear_devolucion(
        self,
        venta_id: int,
        items: list[dict],
        motivo: str = "",
    ) -> tuple[bool, dict]:
        """Register a return. Each item must have producto_id, cantidad, precio_unitario.
        Stock is restored and a nota de crédito is emitted (negative payment)."""
        try:
            result = advanced_inventory_db.crear_devolucion(
                self.db,
                venta_id=venta_id,
                items=items,
                motivo=motivo,
                usuario=self.current_user or "system",
            )
            return True, result
        except (DatabaseException, StockInsufficientException) as e:
            logger.exception(f"Error creating return: {e}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.exception(f"Error creating return: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.DEVOLUCIONES_LEER)
    async def obtener_devoluciones(self, venta_id: int | None = None) -> list[dict]:
        try:
            return advanced_inventory_db.obtener_devoluciones(self.db, venta_id=venta_id)
        except Exception as e:
            logger.exception(f"Error fetching returns: {e}")
            return []

    # ============ Fase 1: Transferencias entre almacenes ============

    @require_permission(Perm.TRANSFERENCIAS_CREAR)
    async def crear_transferencia_almacen(
        self,
        almacen_origen_id: int,
        almacen_destino_id: int,
        producto_id: int,
        cantidad: int,
        nota: str = "",
    ) -> tuple[bool, dict]:
        try:
            result = advanced_inventory_db.crear_transferencia(
                self.db,
                almacen_origen_id=almacen_origen_id,
                almacen_destino_id=almacen_destino_id,
                producto_id=producto_id,
                cantidad=cantidad,
                nota=nota,
                usuario=self.current_user or "system",
            )
            return True, result
        except (DatabaseException, StockInsufficientException) as e:
            logger.exception(f"Error transferring stock: {e}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.exception(f"Error transferring stock: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.TRANSFERENCIAS_LEER)
    async def obtener_transferencias_almacen(self, almacen_id: int | None = None) -> list[dict]:
        try:
            return advanced_inventory_db.obtener_transferencias(self.db, almacen_id=almacen_id)
        except Exception as e:
            logger.exception(f"Error fetching transfers: {e}")
            return []

    # ============ Fase 1: Conteo físico ============

    @require_permission(Perm.CONTEOS_CREAR)
    async def crear_sesion_conteo(
        self,
        nombre: str,
        almacen_id: int | None = None,
        notas: str = "",
        producto_ids: list[int] | None = None,
    ) -> tuple[bool, dict]:
        try:
            sesion_id = advanced_inventory_db.crear_sesion_conteo(
                self.db,
                nombre=nombre,
                almacen_id=almacen_id,
                notas=notas,
                usuario=self.current_user or "system",
                producto_ids=producto_ids,
            )
            return True, {"id": sesion_id}
        except Exception as e:
            logger.exception(f"Error creating count session: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CONTEOS_CREAR)
    async def registrar_conteo_item(
        self,
        sesion_id: int,
        producto_id: int,
        cantidad_contada: float,
        notas: str = "",
    ) -> tuple[bool, dict]:
        try:
            item_id = advanced_inventory_db.registrar_conteo_item(
                self.db,
                sesion_id=sesion_id,
                producto_id=producto_id,
                cantidad_contada=cantidad_contada,
                notas=notas,
                usuario=self.current_user or "system",
            )
            return True, {"id": item_id}
        except Exception as e:
            logger.exception(f"Error recording count: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CONTEOS_AJUSTAR)
    async def cerrar_sesion_conteo(
        self,
        sesion_id: int,
        aplicar_ajustes: bool = False,
    ) -> tuple[bool, dict]:
        try:
            result = advanced_inventory_db.cerrar_sesion_conteo(
                self.db,
                sesion_id=sesion_id,
                aplicar_ajustes=aplicar_ajustes,
                usuario=self.current_user or "system",
            )
            return True, result
        except Exception as e:
            logger.exception(f"Error closing count session: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CONTEOS_LEER)
    async def obtener_sesion_conteo(self, sesion_id: int) -> dict | None:
        try:
            return advanced_inventory_db.obtener_sesion_conteo(self.db, sesion_id=sesion_id)
        except Exception as e:
            logger.exception(f"Error fetching session: {e}")
            return None

    @require_permission(Perm.CONTEOS_LEER)
    async def obtener_sesiones_conteo(self) -> list[dict]:
        try:
            return advanced_inventory_db.obtener_sesiones_conteo(self.db)
        except Exception as e:
            logger.exception(f"Error fetching sessions: {e}")
            return []

    # ============ Fase 1: Lotes / Series / Vencimientos ============

    @require_permission(Perm.LOTES_GESTIONAR)
    async def crear_lote(
        self,
        producto_id: int,
        codigo_lote: str,
        cantidad_inicial: int,
        fecha_fabricacion: str | None = None,
        fecha_vencimiento: str | None = None,
        serie: str | None = None,
        ubicacion: str | None = None,
        proveedor_id: int | None = None,
    ) -> tuple[bool, dict]:
        try:
            lote_id = advanced_inventory_db.crear_lote(
                self.db,
                producto_id=producto_id,
                codigo_lote=codigo_lote,
                cantidad_inicial=cantidad_inicial,
                fecha_fabricacion=fecha_fabricacion,
                fecha_vencimiento=fecha_vencimiento,
                serie=serie,
                ubicacion=ubicacion,
                proveedor_id=proveedor_id,
                usuario=self.current_user or "system",
            )
            return True, {"id": lote_id}
        except Exception as e:
            logger.exception(f"Error creating lot: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.LOTES_LEER)
    async def obtener_lotes(
        self,
        producto_id: int | None = None,
        proximos_vencer_dias: int | None = None,
    ) -> list[dict]:
        try:
            return advanced_inventory_db.obtener_lotes(
                self.db,
                producto_id=producto_id,
                proximos_vencer_dias=proximos_vencer_dias,
            )
        except Exception as e:
            logger.exception(f"Error fetching lots: {e}")
            return []

    @require_permission(Perm.LOTES_GESTIONAR)
    async def eliminar_lote(self, lote_id: int) -> tuple[bool, dict]:
        try:
            advanced_inventory_db.eliminar_lote(self.db, lote_id=lote_id, usuario=self.current_user or "system")
            return True, {"message": "Lote eliminado"}
        except Exception as e:
            logger.exception(f"Error deleting lot: {e}")
            return False, {"error": str(e)}

    # ============ Fase 1: Listas de precios multi-nivel ============

    @require_permission(Perm.PRECIOS_GESTIONAR)
    async def crear_lista_precio(self, nombre: str, descripcion: str = "") -> tuple[bool, dict]:
        try:
            lista_id = advanced_inventory_db.crear_lista_precio(
                self.db,
                nombre=nombre,
                descripcion=descripcion,
                usuario=self.current_user or "system",
            )
            return True, {"id": lista_id, "nombre": nombre}
        except Exception as e:
            logger.exception(f"Error creating price list: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.PRECIOS_LEER)
    async def obtener_listas_precios(self, solo_activas: bool = True) -> list[dict]:
        try:
            return advanced_inventory_db.obtener_listas_precios(self.db, solo_activas=solo_activas)
        except Exception as e:
            logger.exception(f"Error fetching price lists: {e}")
            return []

    @require_permission(Perm.PRECIOS_GESTIONAR)
    async def asignar_precio(
        self,
        producto_id: int,
        lista_id: int,
        precio: float,
    ) -> tuple[bool, dict]:
        try:
            pid = advanced_inventory_db.asignar_precio(
                self.db,
                producto_id=producto_id,
                lista_id=lista_id,
                precio=precio,
                usuario=self.current_user or "system",
            )
            return True, {"id": pid}
        except Exception as e:
            logger.exception(f"Error assigning price: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.PRECIOS_LEER)
    async def obtener_precio_producto(
        self,
        producto_id: int,
        lista_id: int | None = None,
    ) -> dict:
        try:
            return advanced_inventory_db.obtener_precio_producto(
                self.db,
                producto_id=producto_id,
                lista_id=lista_id,
            )
        except Exception as e:
            logger.exception(f"Error fetching product price: {e}")
            return {}

    @require_permission(Perm.PRECIOS_GESTIONAR)
    async def actualizar_precios_producto(
        self,
        producto_id: int,
        precio: float | None = None,
        precio_costo: float | None = None,
        margen: float | None = None,
    ) -> tuple[bool, dict]:
        try:
            result = advanced_inventory_db.actualizar_precios_producto(
                self.db,
                producto_id=producto_id,
                precio=precio,
                precio_costo=precio_costo,
                margen=margen,
                usuario=self.current_user or "system",
            )
            return True, result
        except Exception as e:
            logger.exception(f"Error updating product prices: {e}")
            return False, {"error": str(e)}

    # ============ Fase 1: Impuestos ============

    @require_permission(Perm.IMPUESTOS_GESTIONAR)
    async def crear_impuesto(
        self,
        nombre: str,
        porcentaje: float,
        tipo: str = "iva",
    ) -> tuple[bool, dict]:
        try:
            tax_id = advanced_inventory_db.crear_impuesto(
                self.db,
                nombre=nombre,
                porcentaje=porcentaje,
                tipo=tipo,
                usuario=self.current_user or "system",
            )
            return True, {"id": tax_id, "nombre": nombre}
        except Exception as e:
            logger.exception(f"Error creating tax: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.IMPUESTOS_LEER)
    async def obtener_impuestos(self, solo_activos: bool = True) -> list[dict]:
        try:
            return advanced_inventory_db.obtener_impuestos(self.db, solo_activos=solo_activos)
        except Exception as e:
            logger.exception(f"Error fetching taxes: {e}")
            return []

    async def calcular_precio_con_impuesto(
        self,
        precio_base: float,
        porcentaje: float,
    ) -> dict:
        try:
            return advanced_inventory_db.calcular_precio_con_impuesto(precio_base, porcentaje)
        except Exception as e:
            logger.exception(f"Error calculating tax: {e}")
            return {"base": 0, "porcentaje": 0, "impuesto": 0, "total": 0}

    @require_permission(Perm.IMPUESTOS_GESTIONAR)
    async def asignar_impuesto_producto(
        self,
        producto_id: int,
        impuesto_id: int | None,
    ) -> tuple[bool, dict]:
        try:
            advanced_inventory_db.asignar_impuesto_producto(
                self.db,
                producto_id=producto_id,
                impuesto_id=impuesto_id,
                usuario=self.current_user or "system",
            )
            return True, {"message": "Impuesto asignado"}
        except Exception as e:
            logger.exception(f"Error assigning tax: {e}")
            return False, {"error": str(e)}

    # ============ Fase 1: Caja / Turnos POS ============

    @require_permission(Perm.CAJA_GESTIONAR)
    async def abrir_turno_caja(
        self,
        monto_inicial: float = 0,
        notas: str = "",
    ) -> tuple[bool, dict]:
        try:
            turno_id = advanced_inventory_db.abrir_turno(
                self.db,
                usuario=self.current_user or "system",
                monto_inicial=monto_inicial,
                notas=notas,
            )
            return True, {"id": turno_id}
        except Exception as e:
            logger.exception(f"Error opening shift: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CAJA_GESTIONAR)
    async def registrar_movimiento_caja(
        self,
        turno_id: int,
        tipo: str,
        monto: float,
        concepto: str = "",
        referencia: str = "",
    ) -> tuple[bool, dict]:
        try:
            mid = advanced_inventory_db.registrar_movimiento_caja(
                self.db,
                turno_id=turno_id,
                tipo=tipo,
                monto=monto,
                concepto=concepto,
                referencia=referencia,
            )
            return True, {"id": mid}
        except Exception as e:
            logger.exception(f"Error registering cash movement: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CAJA_GESTIONAR)
    async def asociar_venta_a_turno(self, turno_id: int, venta_id: int) -> bool:
        try:
            return advanced_inventory_db.asociar_venta_a_turno(self.db, turno_id, venta_id)
        except Exception as e:
            logger.exception(f"Error linking sale to shift: {e}")
            return False

    @require_permission(Perm.CAJA_GESTIONAR)
    async def cerrar_turno_caja(
        self,
        turno_id: int,
        monto_final: float,
        notas: str = "",
    ) -> tuple[bool, dict]:
        try:
            result = advanced_inventory_db.cerrar_turno(
                self.db,
                turno_id=turno_id,
                monto_final=monto_final,
                notas=notas,
                usuario=self.current_user or "system",
            )
            return True, result
        except Exception as e:
            logger.exception(f"Error closing shift: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CAJA_LEER)
    async def obtener_turno_caja(self, turno_id: int) -> dict | None:
        try:
            return advanced_inventory_db.obtener_turno(self.db, turno_id=turno_id)
        except Exception as e:
            logger.exception(f"Error fetching shift: {e}")
            return None

    @require_permission(Perm.CAJA_LEER)
    async def obtener_turnos_caja(self, usuario: str | None = None) -> list[dict]:
        try:
            return advanced_inventory_db.obtener_turnos(self.db, usuario=usuario)
        except Exception as e:
            logger.exception(f"Error fetching shifts: {e}")
            return []

    async def obtener_turno_abierto(self, usuario: str) -> dict | None:
        try:
            return advanced_inventory_db.obtener_turno_abierto(self.db, usuario=usuario)
        except Exception as e:
            logger.exception(f"Error fetching open shift: {e}")
            return None

    # ============ Fase 1: Dashboard KPIs ============

    @require_permission(Perm.DASHBOARD_VER)
    async def obtener_kpis_dashboard(self) -> dict:
        try:
            return advanced_inventory_db.obtener_kpis_dashboard(self.db)
        except Exception as e:
            logger.exception(f"Error computing KPIs: {e}")
            return {}
