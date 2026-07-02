"""
Product controller for CRUD, categories, suppliers, barcodes/QR, and import operations
"""

import asyncio

_background_tasks: set[asyncio.Task] = set()

from services.auth import AuthService
from services.code_handler import CodeHandler
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger
from utils.validators import Validator

logger = setup_logger(__name__)


class ProductController:
    """Product management controller"""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Product Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    @require_permission(Perm.PRODUCTOS_CREAR)
    async def crear_producto(
        self,
        codigo: str,
        nombre: str,
        cantidad: str,
        precio: str,
        descripcion: str = "",
        categoria: str = "",
        stock_min: str = "0",
        proveedor_id: int | None = None,
        unidad_medida: str = "unidad",
    ) -> tuple[bool, dict]:
        """Create new product with validation"""
        try:
            # Validate all inputs
            is_valid, error = Validator.validate_codigo(codigo)
            if not is_valid:
                return False, {"error": error}

            is_valid, error = Validator.validate_nombre(nombre)
            if not is_valid:
                return False, {"error": error}

            is_valid, error = Validator.validate_cantidad(cantidad)
            if not is_valid:
                return False, {"error": error}

            is_valid, error = Validator.validate_precio(precio)
            if not is_valid:
                return False, {"error": error}

            if descripcion:
                is_valid, error = Validator.validate_descripcion(descripcion)
                if not is_valid:
                    return False, {"error": error}

            is_valid, error = Validator.validate_cantidad(stock_min)
            if not is_valid:
                return False, {"error": "Stock mínimo inválido"}

            # Create product

            producto = self.db.crear_producto(
                codigo=codigo,
                nombre=nombre,
                cantidad=int(cantidad),
                precio=float(precio),
                descripcion=descripcion,
                categoria=categoria,
                stock_min=int(stock_min),
                proveedor_id=proveedor_id,
                usuario=self.current_user or "system",
            )

            logger.info(f"Product created: {codigo}")
            task = asyncio.create_task(self.generar_codigos_producto(codigo))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
            return True, producto
        except Exception as e:
            logger.exception(f"Error creating product: {e}")
            return False, {"error": str(e)}

    async def obtener_todos_productos(self) -> list[dict]:
        """Get all active products"""
        try:
            return self.db.obtener_todos_productos()
        except Exception as e:
            logger.exception(f"Error fetching products: {e}")
            return []

    async def obtener_producto(self, producto_id: int) -> dict | None:
        """Get single product"""
        try:
            return self.db.obtener_producto_por_id(producto_id)
        except Exception as e:
            logger.exception(f"Error fetching product: {e}")
            return None

    async def buscar_productos(self, query: str) -> list[dict]:
        """Search products"""
        try:
            if not query or len(query) < 2:
                return []

            return self.db.buscar_productos(query)
        except Exception as e:
            logger.exception(f"Error searching products: {e}")
            return []

    @require_permission(Perm.PRODUCTOS_ACTUALIZAR)
    async def actualizar_producto(
        self,
        producto_id: int,
        nombre: str | None = None,
        cantidad: str | None = None,
        precio: str | None = None,
        descripcion: str | None = None,
        categoria: str | None = None,
        stock_min: str | None = None,
        proveedor_id: int | None = None,
        unidad_medida: str | None = None,
    ) -> tuple[bool, dict]:
        """Update product"""
        try:
            # Validate optional inputs
            if cantidad is not None and cantidad != "":
                ok, err = Validator.validate_cantidad(cantidad)
                if not ok:
                    return False, {"error": f"Cantidad inválida: {err}"}

            if precio is not None and precio != "":
                ok, err = Validator.validate_precio(precio)
                if not ok:
                    return False, {"error": f"Precio inválido: {err}"}

            if stock_min is not None and stock_min != "":
                ok, err = Validator.validate_cantidad(stock_min)
                if not ok:
                    return False, {"error": f"Stock mínimo inválido: {err}"}

            producto = self.db.actualizar_producto(
                producto_id=producto_id,
                nombre=nombre,
                cantidad=int(cantidad) if cantidad else None,
                precio=float(precio) if precio else None,
                descripcion=descripcion,
                categoria=categoria,
                stock_min=int(stock_min) if stock_min else None,
                proveedor_id=proveedor_id,
                usuario=self.current_user or "system",
            )

            logger.info(f"Product {producto_id} updated")
            codigo = producto.get("codigo", "")
            if codigo:
                task = asyncio.create_task(self.generar_codigos_producto(codigo))
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
            return True, producto
        except Exception as e:
            logger.exception(f"Error updating product: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.STOCK_ACTUALIZAR)
    async def actualizar_stock(
        self,
        producto_id: int,
        cantidad_nueva: str,
        tipo_movimiento: str = "ajuste",
        razon: str = "",
    ) -> tuple[bool, dict]:
        """Update product stock"""
        try:
            is_valid, error = Validator.validate_cantidad(cantidad_nueva)
            if not is_valid:
                return False, {"error": error}

            producto = self.db.actualizar_stock(
                producto_id=producto_id,
                cantidad_nueva=int(cantidad_nueva),
                tipo_movimiento=tipo_movimiento,
                razon=razon,
                usuario=self.current_user or "system",
            )

            logger.info(f"Stock updated for product {producto_id}")
            return True, producto
        except Exception as e:
            logger.exception(f"Error updating stock: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.PRODUCTOS_ELIMINAR)
    async def eliminar_producto(self, producto_id: int) -> tuple[bool, dict]:
        """Delete product (soft delete)"""
        try:
            self.db.eliminar_producto(
                producto_id=producto_id,
                usuario=self.current_user or "system",
            )
            logger.info(f"Product {producto_id} deleted")
            return True, {"message": "Producto eliminado"}
        except Exception as e:
            logger.exception(f"Error deleting product: {e}")
            return False, {"error": str(e)}

    # ============ Barcode / QR Scanner ============

    async def generar_codigos_producto(self, codigo: str) -> dict:
        """Generate barcode and QR codes for a product code"""
        try:
            barcode_path = CodeHandler.generar_codigo_barras(codigo)
            qr_path = CodeHandler.generar_qr(codigo)
            result = {
                "barcode": str(barcode_path) if barcode_path else None,
                "qr": str(qr_path) if qr_path else None,
            }
            logger.info(f"Codes generated for {codigo}")
            return result
        except Exception as e:
            logger.exception(f"Error generating codes for {codigo}: {e}")
            return {"barcode": None, "qr": None}

    async def regenerar_codigos_todos(self) -> tuple[int, int, list[str]]:
        """Regenerate barcode/QR codes for all products. Returns (success_count, fail_count, errors)."""
        productos = await self.obtener_todos_productos()
        success = 0
        fail = 0
        errors = []
        for p in productos:
            codigo = p.get("codigo", "")
            if not codigo:
                continue
            try:
                result = await self.generar_codigos_producto(codigo)
                if result.get("barcode") or result.get("qr"):
                    success += 1
                else:
                    fail += 1
                    errors.append(codigo)
            except Exception as e:
                fail += 1
                errors.append(f"{codigo}: {e}")
        return success, fail, errors

    async def obtener_codigo_barras_base64(self, codigo: str) -> str | None:
        """Get barcode image as base64 string"""
        try:
            path = CodeHandler.obtener_codigo_barras(codigo)
            if path:
                return CodeHandler.imagen_a_base64(path)
            return None
        except Exception as e:
            logger.exception(f"Error getting barcode base64: {e}")
            return None

    async def obtener_qr_base64(self, codigo: str) -> str | None:
        """Get QR image as base64 string"""
        try:
            path = CodeHandler.obtener_qr(codigo)
            if path:
                return CodeHandler.imagen_a_base64(path)
            return None
        except Exception as e:
            logger.exception(f"Error getting QR base64: {e}")
            return None

    async def buscar_por_codigo_escaneado(self, data: str) -> dict | None:
        """Search product by scanned barcode/QR data"""
        try:
            data = data.strip().strip("\r\n\t")
            if not data:
                return None
            producto = self.db.obtener_producto_por_codigo(data)
            if producto:
                return producto
            productos = self.db.buscar_productos(data)
            if productos:
                return productos[0]
            return None
        except Exception as e:
            logger.exception(f"Error searching by scanned code: {e}")
            return None

    async def escanear_desde_imagen(self, ruta_imagen: str) -> dict | None:
        """Read barcode/QR from image and find matching product"""
        try:
            code_data = CodeHandler.leer_codigo_desde_imagen(ruta_imagen)
            if not code_data:
                return None
            return await self.buscar_por_codigo_escaneado(code_data)
        except Exception as e:
            logger.exception(f"Error scanning image: {e}")
            return None

    async def scanner_disponibilidad(self) -> dict:
        """Check which code scanning features are available"""
        return CodeHandler.disponibilidad()

    # ============ Categorias ============

    async def obtener_categorias(self) -> list[dict]:
        try:
            return self.db.obtener_categorias()
        except Exception as e:
            logger.exception(f"Error fetching categories: {e}")
            return []

    @require_permission(Perm.CATEGORIAS_GESTIONAR)
    async def crear_categoria(self, nombre: str, descripcion: str = "") -> tuple[bool, dict]:
        is_valid, error = Validator.validate_nombre(nombre)
        if not is_valid:
            return False, {"error": error}
        try:
            categoria_id = self.db.crear_categoria(
                nombre=nombre,
                descripcion=descripcion,
                usuario=self.current_user or "system",
            )
            logger.info(f"Category created: {nombre}")
            return True, {"id": categoria_id, "nombre": nombre}
        except Exception as e:
            logger.exception(f"Error creating category: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CATEGORIAS_GESTIONAR)
    async def actualizar_categoria(
        self, categoria_id: int, nombre: str, descripcion: str = ""
    ) -> tuple[bool, dict]:
        is_valid, error = Validator.validate_nombre(nombre)
        if not is_valid:
            return False, {"error": error}
        try:
            self.db.actualizar_categoria(
                categoria_id=categoria_id,
                nombre=nombre,
                descripcion=descripcion,
                usuario=self.current_user or "system",
            )
            logger.info(f"Category {categoria_id} updated")
            return True, {"id": categoria_id, "nombre": nombre}
        except Exception as e:
            logger.exception(f"Error updating category: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.CATEGORIAS_GESTIONAR)
    async def eliminar_categoria(self, categoria_id: int) -> tuple[bool, dict]:
        try:
            self.db.eliminar_categoria(
                categoria_id=categoria_id,
                usuario=self.current_user or "system",
            )
            logger.info(f"Category {categoria_id} deleted")
            return True, {"message": "Categoria eliminada"}
        except Exception as e:
            logger.exception(f"Error deleting category: {e}")
            return False, {"error": str(e)}

    async def seed_categorias_iniciales(self, nombres: list[str]) -> int:
        """Seed initial categories on first run. Returns count inserted."""
        try:
            return self.db.seed_categorias(
                nombres=nombres,
                usuario=self.current_user or "system",
            )
        except Exception as e:
            logger.exception(f"Error seeding categories: {e}")
            return 0

    # ============ Proveedores ============

    async def obtener_proveedores(self) -> list[dict]:
        try:
            return self.db.obtener_proveedores()
        except Exception as e:
            logger.exception(f"Error fetching suppliers: {e}")
            return []

    @require_permission(Perm.PROVEEDORES_GESTIONAR)
    async def crear_proveedor(
        self,
        nombre: str,
        contacto: str = "",
        telefono: str = "",
        email: str = "",
        direccion: str = "",
    ) -> tuple[bool, dict]:
        is_valid, error = Validator.validate_nombre(nombre)
        if not is_valid:
            return False, {"error": error}
        if telefono:
            is_valid, error = Validator.validate_telefono(telefono)
            if not is_valid:
                return False, {"error": error}
        if email:
            is_valid, error = Validator.validate_email(email)
            if not is_valid:
                return False, {"error": error}
        try:
            proveedor_id = self.db.crear_proveedor(
                nombre=nombre,
                contacto=contacto,
                telefono=telefono,
                email=email,
                direccion=direccion,
                usuario=self.current_user or "system",
            )
            logger.info(f"Supplier created: {nombre}")
            return True, {"id": proveedor_id, "nombre": nombre}
        except Exception as e:
            logger.exception(f"Error creating supplier: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.PROVEEDORES_GESTIONAR)
    async def actualizar_proveedor(
        self,
        proveedor_id: int,
        nombre: str,
        contacto: str = "",
        telefono: str = "",
        email: str = "",
        direccion: str = "",
    ) -> tuple[bool, dict]:
        is_valid, error = Validator.validate_nombre(nombre)
        if not is_valid:
            return False, {"error": error}
        if email:
            is_valid, error = Validator.validate_email(email)
            if not is_valid:
                return False, {"error": error}
        try:
            self.db.actualizar_proveedor(
                proveedor_id=proveedor_id,
                nombre=nombre,
                contacto=contacto,
                telefono=telefono,
                email=email,
                direccion=direccion,
                usuario=self.current_user or "system",
            )
            logger.info(f"Supplier {proveedor_id} updated")
            return True, {"id": proveedor_id, "nombre": nombre}
        except Exception as e:
            logger.exception(f"Error updating supplier: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.PROVEEDORES_GESTIONAR)
    async def eliminar_proveedor(self, proveedor_id: int) -> tuple[bool, dict]:
        try:
            self.db.eliminar_proveedor(
                proveedor_id=proveedor_id,
                usuario=self.current_user or "system",
            )
            logger.info(f"Supplier {proveedor_id} deleted")
            return True, {"message": "Proveedor eliminado"}
        except Exception as e:
            logger.exception(f"Error deleting supplier: {e}")
            return False, {"error": str(e)}

    # ============ Ordenes de compra ============

    async def obtener_ordenes_compra(self, estado: str | None = None) -> list[dict]:
        try:
            return self.db.obtener_ordenes_compra(estado=estado)
        except Exception as e:
            logger.exception(f"Error fetching orders: {e}")
            return []

    @require_permission(Perm.ORDENES_CREAR)
    async def crear_orden_compra(
        self, proveedor_id: int, producto_id: int, cantidad: int
    ) -> tuple[bool, dict]:
        if cantidad <= 0:
            return False, {"error": "La cantidad debe ser mayor a cero"}
        try:
            orden_id = self.db.crear_orden_compra(
                proveedor_id=proveedor_id,
                producto_id=producto_id,
                cantidad=cantidad,
                usuario=self.current_user or "system",
            )
            logger.info(f"Order {orden_id} created")
            return True, {"id": orden_id}
        except Exception as e:
            logger.exception(f"Error creating order: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.ORDENES_RECIBIR)
    async def recibir_orden(self, orden_id: int) -> tuple[bool, dict]:
        """Mark order as received and add the quantity to the product stock."""
        try:
            orden = self.db.obtener_orden_compra_por_id(orden_id)
            if not orden:
                return False, {"error": "Orden no encontrada"}
            if orden["estado"] == "recibida":
                return False, {"error": "La orden ya fue recibida"}
            self.db.cambiar_estado_orden(
                orden_id=orden_id,
                nuevo_estado="recibida",
                usuario=self.current_user or "system",
            )
            # Apply stock entry using existing logic
            self.db.actualizar_stock(
                producto_id=orden["producto_id"],
                cantidad_nueva=orden["cantidad"],
                tipo_movimiento="entrada",
                razon=f"Orden de compra #{orden_id}",
                usuario=self.current_user or "system",
            )
            logger.info(f"Order {orden_id} received, stock updated")
            return True, {"message": "Orden recibida y stock actualizado"}
        except Exception as e:
            logger.exception(f"Error receiving order: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.ORDENES_CANCELAR)
    async def cancelar_orden(self, orden_id: int) -> tuple[bool, dict]:
        try:
            self.db.cambiar_estado_orden(
                orden_id=orden_id,
                nuevo_estado="cancelada",
                usuario=self.current_user or "system",
            )
            logger.info(f"Order {orden_id} cancelled")
            return True, {"message": "Orden cancelada"}
        except Exception as e:
            logger.exception(f"Error cancelling order: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.ORDENES_CANCELAR)
    async def eliminar_orden_compra(self, orden_id: int) -> tuple[bool, dict]:
        try:
            self.db.eliminar_orden_compra(
                orden_id=orden_id,
                usuario=self.current_user or "system",
            )
            return True, {"message": "Orden eliminada"}
        except Exception as e:
            logger.exception(f"Error deleting order: {e}")
            return False, {"error": str(e)}

    # ============ CSV Import ============

    @require_permission(Perm.IMPORTAR)
    async def importar_productos_csv(self, filepath: str) -> tuple[int, list[str]]:
        """Import products from CSV. Returns (success_count, error_list).

        Expected columns: codigo, nombre, cantidad, precio, categoria, descripcion.
        Stock_min is optional (default 0). Validation runs per row.
        """
        try:
            return ExportService.import_from_csv(
                filepath,
                crear_producto_fn=lambda **kwargs: self.db.crear_producto(
                    usuario=self.current_user or "system", **kwargs
                ),
            )
        except Exception as e:
            logger.exception(f"Error importing CSV: {e}")
            return 0, [str(e)]

    async def importar_productos_xlsx(self, filepath: str) -> tuple[int, list[str]]:
        """Import products from XLSX. Returns (success_count, error_list).

        Same expected columns as the CSV importer: codigo, nombre, cantidad,
        precio, categoria, descripcion. Stock_min is optional (default 0).
        """
        try:
            return ExportService.import_from_xlsx(
                filepath,
                crear_producto_fn=lambda **kwargs: self.db.crear_producto(
                    usuario=self.current_user or "system", **kwargs
                ),
            )
        except Exception as e:
            logger.exception(f"Error importing XLSX: {e}")
            return 0, [str(e)]
