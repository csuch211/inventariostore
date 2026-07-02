"""Online store controller."""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class StoreController:
    """Controller for the online store module."""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Store Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Store Config ============

    async def obtener_config_tienda(self) -> dict[str, str]:
        try:
            return self.db.store_repo.obtener_config()
        except Exception as e:
            logger.exception(f"Error fetching store config: {e}")
            return {}

    async def guardar_config_tienda(self, clave: str, valor: str) -> bool:
        try:
            self.db.store_repo.guardar_config(clave, valor)
            return True
        except Exception as e:
            logger.exception(f"Error saving store config: {e}")
            return False

    # ============ Store Products ============

    async def listar_productos_tienda(self, solo_visibles: bool = True) -> list[dict]:
        try:
            return self.db.store_repo.listar_productos_tienda(solo_visibles=solo_visibles)
        except Exception as e:
            logger.exception(f"Error listing store products: {e}")
            return []

    async def sincronizar_producto(
        self, producto_id: int, visible: bool = False,
        descripcion_larga: str = "", imagen_url: str = "",
        destacado: bool = False, orden: int = 0
    ) -> bool:
        try:
            self.db.store_repo.sincronizar_producto(
                producto_id=producto_id, visible=visible,
                descripcion_larga=descripcion_larga, imagen_url=imagen_url,
                destacado=destacado, orden=orden,
            )
            return True
        except Exception as e:
            logger.exception(f"Error syncing store product: {e}")
            return False

    async def eliminar_producto_tienda(self, producto_id: int) -> bool:
        try:
            self.db.store_repo.eliminar_producto_tienda(producto_id)
            return True
        except Exception as e:
            logger.exception(f"Error deleting store product: {e}")
            return False

    async def obtener_productos_destacados(self, limit: int = 8) -> list[dict]:
        try:
            return self.db.store_repo.obtener_productos_destacados(limit=limit)
        except Exception as e:
            logger.exception(f"Error fetching featured products: {e}")
            return []

    # ============ Store Orders ============

    async def crear_pedido_tienda(
        self, cliente_nombre: str, cliente_email: str,
        cliente_telefono: str, direccion_envio: str,
        notas: str, total: float, items: list[dict],
        metodo_pago: str = "pendiente"
    ) -> tuple[bool, dict]:
        try:
            pedido_id = self.db.store_repo.crear_pedido(
                cliente_nombre=cliente_nombre, cliente_email=cliente_email,
                cliente_telefono=cliente_telefono, direccion_envio=direccion_envio,
                notas=notas, total=total, items=items, metodo_pago=metodo_pago,
            )
            return True, {"id": pedido_id, "total": total}
        except Exception as e:
            logger.exception(f"Error creating store order: {e}")
            return False, {"error": str(e)}

    async def obtener_pedidos_tienda(self, estado: str | None = None) -> list[dict]:
        try:
            return self.db.store_repo.obtener_pedidos(estado=estado)
        except Exception as e:
            logger.exception(f"Error fetching store orders: {e}")
            return []

    async def obtener_pedido_tienda(self, pedido_id: int) -> dict | None:
        try:
            return self.db.store_repo.obtener_pedido_por_id(pedido_id)
        except Exception as e:
            logger.exception(f"Error fetching store order: {e}")
            return None

    async def actualizar_estado_pedido(self, pedido_id: int, estado: str) -> bool:
        try:
            self.db.store_repo.actualizar_estado_pedido(pedido_id, estado)
            return True
        except Exception as e:
            logger.exception(f"Error updating order status: {e}")
            return False

    async def obtener_estadisticas_tienda(self) -> dict:
        try:
            return self.db.store_repo.obtener_estadisticas_tienda()
        except Exception as e:
            logger.exception(f"Error fetching store stats: {e}")
            return {"total_pedidos": 0, "pendientes": 0, "entregados": 0, "ingresos_totales": 0}
