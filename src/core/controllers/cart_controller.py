"""Cart and sales config controller."""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from utils.logger import setup_logger
from utils.validators import Validator

logger = setup_logger(__name__)


class CartController:
    """Controller for persistent shopping carts and sales configuration."""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Cart Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Persistent Cart ============

    async def obtener_carrito_activo(self) -> dict | None:
        try:
            usuario = self.current_user or "system"
            return self.db.cart_repo.obtener_carrito_activo(usuario)
        except Exception as e:
            logger.exception(f"Error fetching active cart: {e}")
            return None

    async def obtener_o_crear_carrito(self) -> dict:
        try:
            usuario = self.current_user or "system"
            return self.db.cart_repo.obtener_o_crear_carrito(usuario)
        except Exception as e:
            logger.exception(f"Error getting/creating cart: {e}")
            return {"id": None, "items": []}

    async def agregar_al_carrito(self, producto_id: int, cantidad: int, precio_unitario: float) -> bool:
        try:
            # Validate inputs
            ok, err = Validator.validate_positive_int(cantidad, "Cantidad")
            if not ok:
                logger.warning("Invalid cart quantity: %s", err)
                return False
            ok, err = Validator.validate_moneda(precio_unitario, "Precio unitario")
            if not ok:
                logger.warning("Invalid cart price: %s", err)
                return False

            usuario = self.current_user or "system"
            cart = self.db.cart_repo.obtener_o_crear_carrito(usuario)
            self.db.cart_repo.agregar_item(cart["id"], producto_id, cantidad, precio_unitario)
            return True
        except Exception as e:
            logger.exception(f"Error adding to cart: {e}")
            return False

    async def actualizar_item_carrito(self, item_id: int, cantidad: int) -> bool:
        try:
            self.db.cart_repo.actualizar_cantidad(item_id, cantidad)
            return True
        except Exception as e:
            logger.exception(f"Error updating cart item: {e}")
            return False

    async def eliminar_item_carrito(self, item_id: int) -> bool:
        try:
            self.db.cart_repo.eliminar_item(item_id)
            return True
        except Exception as e:
            logger.exception(f"Error deleting cart item: {e}")
            return False

    async def obtener_items_carrito(self, carrito_id: int) -> list[dict]:
        try:
            return self.db.cart_repo.obtener_items(carrito_id)
        except Exception as e:
            logger.exception(f"Error fetching cart items: {e}")
            return []

    async def vaciar_carrito(self, carrito_id: int) -> bool:
        try:
            self.db.cart_repo.vaciar_carrito(carrito_id)
            return True
        except Exception as e:
            logger.exception(f"Error emptying cart: {e}")
            return False

    async def marcar_carrito_convertido(self, carrito_id: int) -> bool:
        try:
            self.db.cart_repo.marcar_convertido(carrito_id)
            return True
        except Exception as e:
            logger.exception(f"Error marking cart converted: {e}")
            return False

    async def obtener_carrito_con_items(self) -> dict | None:
        try:
            cart = await self.obtener_carrito_activo()
            if not cart:
                return None
            cart["items"] = await self.obtener_items_carrito(cart["id"])
            cart["total"] = sum(
                (i.get("precio_unitario", 0) or 0) * (i.get("cantidad", 0) or 0)
                for i in cart["items"]
            )
            return cart
        except Exception as e:
            logger.exception(f"Error fetching cart with items: {e}")
            return None

    # ============ Sales Configuration ============

    async def obtener_config_ventas(self) -> dict[str, str]:
        try:
            return self.db.cart_repo.obtener_config_ventas()
        except Exception as e:
            logger.exception(f"Error fetching sales config: {e}")
            return {}

    async def guardar_config_ventas(self, clave: str, valor: str) -> bool:
        try:
            self.db.cart_repo.guardar_config_ventas(clave, valor)
            return True
        except Exception as e:
            logger.exception(f"Error saving sales config: {e}")
            return False

    async def obtener_tasa_iva(self) -> float:
        try:
            config = await self.obtener_config_ventas()
            return float(config.get("iva_rate", "0.0"))
        except (ValueError, TypeError):
            return 0.0
