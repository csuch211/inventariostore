"""
Thin facade that delegates to domain controllers.

InventarioController instantiates ten domain controllers and forwards every
call.  ``current_user`` / ``current_user_permissions`` are propagated to all
children whenever they change (see ``_sync_children``).
"""

from collections.abc import Callable

from core.controllers.accounting_controller import AccountingController
from core.controllers.admin_controller import AdminController
from core.controllers.auth_controller import AuthController
from core.controllers.invoice_controller import InvoiceController
from core.controllers.inventory_controller import InventoryController
from core.controllers.phase1_controller import Phase1Controller
from core.controllers.phase3_controller import Phase3Controller
from core.controllers.product_controller import ProductController
from core.controllers.report_controller import ReportController
from core.controllers.sales_controller import SalesController
from core.controllers.warehouse_controller import WarehouseController
from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class InventarioController:
    """Main controller for inventory management – thin facade over domain controllers."""

    def __init__(self):
        self.db = DatabaseManager()
        self.auth_service = AuthService(db=self.db)
        self.export_service = ExportService()

        self._auth = AuthController(self.db, self.auth_service, self.export_service)
        self._products = ProductController(self.db, self.auth_service, self.export_service)
        self._sales = SalesController(self.db, self.auth_service, self.export_service)
        self._warehouse = WarehouseController(self.db, self.auth_service, self.export_service)
        self._reports = ReportController(self.db, self.auth_service, self.export_service)
        self._admin = AdminController(self.db, self.auth_service, self.export_service)
        self._phase1 = Phase1Controller(self.db, self.auth_service, self.export_service)
        self._phase3 = Phase3Controller(self.db, self.auth_service, self.export_service)
        self._invoices = InvoiceController(self.db, self.auth_service, self.export_service)
        self._accounting = AccountingController(self.db, self.auth_service, self.export_service)
        self._inventory = InventoryController(self.db, self.auth_service, self.export_service)

        self._current_user = None
        self._current_user_role = None
        self._current_user_permissions: set[str] = set()
        logger.info("Inventory Controller initialized")

    @property
    def current_user(self):
        return self._current_user

    @current_user.setter
    def current_user(self, value):
        self._current_user = value
        self._sync_children()

    @property
    def current_user_role(self):
        return self._current_user_role

    @current_user_role.setter
    def current_user_role(self, value):
        self._current_user_role = value

    @property
    def current_user_permissions(self):
        return self._current_user_permissions

    @current_user_permissions.setter
    def current_user_permissions(self, value):
        self._current_user_permissions = value
        self._sync_children()

    def _sync_children(self):
        for ctrl in [
            self._auth,
            self._products,
            self._sales,
            self._warehouse,
            self._reports,
            self._admin,
            self._phase1,
            self._phase3,
            self._invoices,
            self._accounting,
            self._inventory,
        ]:
            ctrl.current_user = self._current_user
            ctrl.current_user_role = self._current_user_role
            ctrl.current_user_permissions = self._current_user_permissions

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Authentication ============

    async def login(self, username: str, password: str) -> dict:
        result = await self._auth.login(username, password)
        self._current_user = username
        self._current_user_role = result.get("rol", "operador")
        self._current_user_permissions = set(result.get("permissions", []))
        self._sync_children()
        return result

    async def logout(self, token: str):
        await self._auth.logout(token)
        self._current_user = None
        self._current_user_role = None
        self._current_user_permissions = set()
        self._sync_children()

    # ============ Products ============

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
        return await self._products.crear_producto(
            codigo=codigo,
            nombre=nombre,
            cantidad=cantidad,
            precio=precio,
            descripcion=descripcion,
            categoria=categoria,
            stock_min=stock_min,
            proveedor_id=proveedor_id,
            unidad_medida=unidad_medida,
        )

    async def obtener_todos_productos(self) -> list[dict]:
        return await self._products.obtener_todos_productos()

    async def obtener_producto(self, producto_id: int) -> dict | None:
        return await self._products.obtener_producto(producto_id)

    async def buscar_productos(self, query: str) -> list[dict]:
        return await self._products.buscar_productos(query)

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
        return await self._products.actualizar_producto(
            producto_id=producto_id,
            nombre=nombre,
            cantidad=cantidad,
            precio=precio,
            descripcion=descripcion,
            categoria=categoria,
            stock_min=stock_min,
            proveedor_id=proveedor_id,
            unidad_medida=unidad_medida,
        )

    async def actualizar_stock(
        self,
        producto_id: int,
        cantidad_nueva: str,
        tipo_movimiento: str = "ajuste",
        razon: str = "",
    ) -> tuple[bool, dict]:
        return await self._products.actualizar_stock(
            producto_id=producto_id,
            cantidad_nueva=cantidad_nueva,
            tipo_movimiento=tipo_movimiento,
            razon=razon,
        )

    async def eliminar_producto(self, producto_id: int) -> tuple[bool, dict]:
        return await self._products.eliminar_producto(producto_id)

    # ============ Barcode / QR Scanner ============

    async def generar_codigos_producto(self, codigo: str) -> dict:
        return await self._products.generar_codigos_producto(codigo)

    async def regenerar_codigos_todos(self) -> tuple[int, int, list[str]]:
        return await self._products.regenerar_codigos_todos()

    async def obtener_codigo_barras_base64(self, codigo: str) -> str | None:
        return await self._products.obtener_codigo_barras_base64(codigo)

    async def obtener_qr_base64(self, codigo: str) -> str | None:
        return await self._products.obtener_qr_base64(codigo)

    async def buscar_por_codigo_escaneado(self, data: str) -> dict | None:
        return await self._products.buscar_por_codigo_escaneado(data)

    async def escanear_desde_imagen(self, ruta_imagen: str) -> dict | None:
        return await self._products.escanear_desde_imagen(ruta_imagen)

    async def scanner_disponibilidad(self) -> dict:
        return await self._products.scanner_disponibilidad()

    # ============ Categorias ============

    async def obtener_categorias(self) -> list[dict]:
        return await self._products.obtener_categorias()

    async def crear_categoria(self, nombre: str, descripcion: str = "") -> tuple[bool, dict]:
        return await self._products.crear_categoria(nombre=nombre, descripcion=descripcion)

    async def actualizar_categoria(
        self, categoria_id: int, nombre: str, descripcion: str = ""
    ) -> tuple[bool, dict]:
        return await self._products.actualizar_categoria(
            categoria_id=categoria_id,
            nombre=nombre,
            descripcion=descripcion,
        )

    async def eliminar_categoria(self, categoria_id: int) -> tuple[bool, dict]:
        return await self._products.eliminar_categoria(categoria_id)

    async def seed_categorias_iniciales(self, nombres: list[str]) -> int:
        return await self._products.seed_categorias_iniciales(nombres)

    # ============ Proveedores ============

    async def obtener_proveedores(self) -> list[dict]:
        return await self._products.obtener_proveedores()

    async def crear_proveedor(
        self,
        nombre: str,
        contacto: str = "",
        telefono: str = "",
        email: str = "",
        direccion: str = "",
    ) -> tuple[bool, dict]:
        return await self._products.crear_proveedor(
            nombre=nombre,
            contacto=contacto,
            telefono=telefono,
            email=email,
            direccion=direccion,
        )

    async def actualizar_proveedor(
        self,
        proveedor_id: int,
        nombre: str,
        contacto: str = "",
        telefono: str = "",
        email: str = "",
        direccion: str = "",
    ) -> tuple[bool, dict]:
        return await self._products.actualizar_proveedor(
            proveedor_id=proveedor_id,
            nombre=nombre,
            contacto=contacto,
            telefono=telefono,
            email=email,
            direccion=direccion,
        )

    async def eliminar_proveedor(self, proveedor_id: int) -> tuple[bool, dict]:
        return await self._products.eliminar_proveedor(proveedor_id)

    # ============ Ordenes de compra ============

    async def obtener_ordenes_compra(self, estado: str | None = None) -> list[dict]:
        return await self._products.obtener_ordenes_compra(estado=estado)

    async def crear_orden_compra(
        self, proveedor_id: int, producto_id: int, cantidad: int
    ) -> tuple[bool, dict]:
        return await self._products.crear_orden_compra(
            proveedor_id=proveedor_id,
            producto_id=producto_id,
            cantidad=cantidad,
        )

    async def recibir_orden(self, orden_id: int) -> tuple[bool, dict]:
        return await self._products.recibir_orden(orden_id)

    async def cancelar_orden(self, orden_id: int) -> tuple[bool, dict]:
        return await self._products.cancelar_orden(orden_id)

    async def eliminar_orden_compra(self, orden_id: int) -> tuple[bool, dict]:
        return await self._products.eliminar_orden_compra(orden_id)

    # ============ CSV Import ============

    async def importar_productos_csv(self, filepath: str) -> tuple[int, list[str]]:
        return await self._products.importar_productos_csv(filepath)

    async def importar_productos_xlsx(self, filepath: str) -> tuple[int, list[str]]:
        return await self._products.importar_productos_xlsx(filepath)

    # ============ Sales / Clients ============

    async def obtener_clientes(self) -> list[dict]:
        return await self._sales.obtener_clientes()

    async def obtener_cliente(self, cliente_id: int) -> dict | None:
        return await self._sales.obtener_cliente(cliente_id)

    async def crear_cliente(
        self, nombre: str, telefono: str = "", email: str = "", direccion: str = ""
    ) -> tuple[bool, dict]:
        return await self._sales.crear_cliente(
            nombre=nombre,
            telefono=telefono,
            email=email,
            direccion=direccion,
        )

    async def actualizar_cliente(
        self, cliente_id: int, nombre: str, telefono: str = "", email: str = "", direccion: str = ""
    ) -> tuple[bool, dict]:
        return await self._sales.actualizar_cliente(
            cliente_id=cliente_id,
            nombre=nombre,
            telefono=telefono,
            email=email,
            direccion=direccion,
        )

    async def eliminar_cliente(self, cliente_id: int) -> tuple[bool, dict]:
        return await self._sales.eliminar_cliente(cliente_id)

    async def obtener_ventas(self) -> list[dict]:
        return await self._sales.obtener_ventas()

    async def obtener_venta(self, venta_id: int) -> dict | None:
        return await self._sales.obtener_venta(venta_id)

    async def crear_venta(
        self,
        cliente_id: int,
        items: list[dict],
        metodo_pago: str = "efectivo",
        referencia: str = "",
    ) -> tuple[bool, dict]:
        return await self._sales.crear_venta(
            cliente_id=cliente_id,
            items=items,
            metodo_pago=metodo_pago,
            referencia=referencia,
        )

    async def cancelar_venta(self, venta_id: int) -> tuple[bool, dict]:
        return await self._sales.cancelar_venta(venta_id)

    async def obtener_estadisticas_ventas(self) -> dict:
        return await self._sales.obtener_estadisticas_ventas()

    # ============ Stock alerts ============

    async def obtener_alertas_stock(self) -> list[dict]:
        return await self._warehouse.obtener_alertas_stock()

    async def contar_alertas_stock(self) -> int:
        return await self._warehouse.contar_alertas_stock()

    # ============ Almacenes / Warehouses ============

    async def obtener_almacenes(self) -> list[dict]:
        return await self._warehouse.obtener_almacenes()

    async def crear_almacen(self, nombre: str, ubicacion: str = "") -> tuple[bool, dict]:
        return await self._warehouse.crear_almacen(nombre=nombre, ubicacion=ubicacion)

    async def actualizar_almacen(
        self, almacen_id: int, nombre: str | None = None, ubicacion: str | None = None
    ) -> tuple[bool, dict]:
        return await self._warehouse.actualizar_almacen(
            almacen_id=almacen_id,
            nombre=nombre,
            ubicacion=ubicacion,
        )

    async def eliminar_almacen(self, almacen_id: int) -> tuple[bool, dict]:
        return await self._warehouse.eliminar_almacen(almacen_id)

    async def obtener_inventario_almacen(self, almacen_id: int) -> list[dict]:
        return await self._warehouse.obtener_inventario_almacen(almacen_id)

    async def ajustar_stock_almacen(
        self, producto_id: int, almacen_id: int, cantidad: int
    ) -> tuple[bool, dict]:
        return await self._warehouse.ajustar_stock_almacen(
            producto_id=producto_id,
            almacen_id=almacen_id,
            cantidad=cantidad,
        )

    async def obtener_todo_stock_almacenes(self) -> list[dict]:
        return await self._warehouse.obtener_todo_stock_almacenes()

    # ============ Bulk Operations ============

    async def bulk_eliminar_productos(self, ids: list[int]) -> tuple[bool, int]:
        return await self._warehouse.bulk_eliminar_productos(ids=ids)

    async def bulk_actualizar_categoria(self, ids: list[int], categoria: str) -> tuple[bool, int]:
        return await self._warehouse.bulk_actualizar_categoria(ids=ids, categoria=categoria)

    async def bulk_exportar_productos(self, ids: list[int], fmt: str = "csv") -> tuple[bool, str]:
        return await self._warehouse.bulk_exportar_productos(ids=ids, fmt=fmt)

    # ============ Reports / Statistics ============

    async def obtener_estadisticas(self) -> dict:
        return await self._reports.obtener_estadisticas()

    async def obtener_historial_stock(self, producto_id: int) -> list[dict]:
        return await self._reports.obtener_historial_stock(producto_id)

    async def exportar_csv(self, productos: list[dict] | None = None) -> tuple[bool, str]:
        return await self._reports.exportar_csv(productos=productos)

    async def exportar_json(self, productos: list[dict] | None = None) -> tuple[bool, str]:
        return await self._reports.exportar_json(productos=productos)

    async def exportar_reporte(self) -> tuple[bool, str]:
        return await self._reports.exportar_reporte()

    async def exportar_pdf(self, productos: list[dict] | None = None) -> tuple[bool, str]:
        return await self._reports.exportar_pdf(productos=productos)

    async def exportar_xlsx(self, productos: list[dict] | None = None) -> tuple[bool, str]:
        return await self._reports.exportar_xlsx(productos=productos)

    # ============ Charts ============

    async def obtener_distribucion_categorias(self) -> list[dict]:
        return await self._reports.obtener_distribucion_categorias()

    async def obtener_top_productos_stock(self, limit: int = 10) -> list[dict]:
        return await self._reports.obtener_top_productos_stock(limit=limit)

    async def obtener_serie_inventario(self, dias: int = 30) -> list[dict]:
        return await self._reports.obtener_serie_inventario(dias=dias)

    # ============ Notifications / Email ============

    async def obtener_config_smtp(self) -> dict:
        return await self._reports.obtener_config_smtp()

    async def guardar_config_smtp(self, config: dict) -> bool:
        return await self._reports.guardar_config_smtp(config)

    async def enviar_alerta_stock(self) -> dict:
        return await self._reports.enviar_alerta_stock()

    async def verificar_stock_bajo(self) -> list[dict]:
        return await self._reports.verificar_stock_bajo()

    # ============ User management ============

    async def obtener_usuarios_con_roles(self) -> list[dict]:
        return await self._admin.obtener_usuarios_con_roles()

    async def crear_usuario(
        self,
        username: str,
        password: str,
        nombre: str,
        rol_nombre: str = "operador",
    ) -> tuple[bool, dict]:
        return await self._admin.crear_usuario(
            username=username,
            password=password,
            nombre=nombre,
            rol_nombre=rol_nombre,
        )

    async def asignar_rol(self, usuario_id: int, rol_nombre: str) -> tuple[bool, dict]:
        return await self._admin.asignar_rol(usuario_id=usuario_id, rol_nombre=rol_nombre)

    async def toggle_permiso_extra(
        self, usuario_id: int, permiso_clave: str, agregar: bool
    ) -> tuple[bool, dict]:
        return await self._admin.toggle_permiso_extra(
            usuario_id=usuario_id,
            permiso_clave=permiso_clave,
            agregar=agregar,
        )

    async def obtener_permisos_catalogo(self) -> list[dict]:
        return await self._admin.obtener_permisos_catalogo()

    async def obtener_roles(self) -> list[dict]:
        return await self._admin.obtener_roles()

    # ============ Theme management ============

    async def obtener_tema_usuario(self) -> str:
        return await self._admin.obtener_tema_usuario()

    async def cambiar_tema(self, modo: str) -> bool:
        return await self._admin.cambiar_tema(modo)

    # ============ Backup management ============

    async def crear_backup(self) -> dict:
        return await self._admin.crear_backup()

    async def listar_backups(self) -> list[dict]:
        return await self._admin.listar_backups()

    async def restaurar_backup(self, backup_path: str) -> dict:
        return await self._admin.restaurar_backup(backup_path)

    async def eliminar_backup_registro(self, backup_id: int, ruta: str = "") -> bool:
        return await self._admin.eliminar_backup_registro(backup_id, ruta=ruta)

    # ============ Fase 1: Devoluciones ============

    async def crear_devolucion(
        self,
        venta_id: int,
        items: list[dict],
        motivo: str = "",
    ) -> tuple[bool, dict]:
        return await self._phase1.crear_devolucion(
            venta_id=venta_id,
            items=items,
            motivo=motivo,
        )

    async def obtener_devoluciones(self, venta_id: int | None = None) -> list[dict]:
        return await self._phase1.obtener_devoluciones(venta_id=venta_id)

    # ============ Fase 1: Transferencias entre almacenes ============

    async def crear_transferencia_almacen(
        self,
        almacen_origen_id: int,
        almacen_destino_id: int,
        producto_id: int,
        cantidad: int,
        nota: str = "",
    ) -> tuple[bool, dict]:
        return await self._phase1.crear_transferencia_almacen(
            almacen_origen_id=almacen_origen_id,
            almacen_destino_id=almacen_destino_id,
            producto_id=producto_id,
            cantidad=cantidad,
            nota=nota,
        )

    async def obtener_transferencias_almacen(self, almacen_id: int | None = None) -> list[dict]:
        return await self._phase1.obtener_transferencias_almacen(almacen_id=almacen_id)

    # ============ Fase 1: Conteo fisico ============

    async def crear_sesion_conteo(
        self,
        nombre: str,
        almacen_id: int | None = None,
        notas: str = "",
        producto_ids: list[int] | None = None,
    ) -> tuple[bool, dict]:
        return await self._phase1.crear_sesion_conteo(
            nombre=nombre,
            almacen_id=almacen_id,
            notas=notas,
            producto_ids=producto_ids,
        )

    async def registrar_conteo_item(
        self,
        sesion_id: int,
        producto_id: int,
        cantidad_contada: float,
        notas: str = "",
    ) -> tuple[bool, dict]:
        return await self._phase1.registrar_conteo_item(
            sesion_id=sesion_id,
            producto_id=producto_id,
            cantidad_contada=cantidad_contada,
            notas=notas,
        )

    async def cerrar_sesion_conteo(
        self,
        sesion_id: int,
        aplicar_ajustes: bool = False,
    ) -> tuple[bool, dict]:
        return await self._phase1.cerrar_sesion_conteo(
            sesion_id=sesion_id,
            aplicar_ajustes=aplicar_ajustes,
        )

    async def obtener_sesion_conteo(self, sesion_id: int) -> dict | None:
        return await self._phase1.obtener_sesion_conteo(sesion_id)

    async def obtener_sesiones_conteo(self) -> list[dict]:
        return await self._phase1.obtener_sesiones_conteo()

    # ============ Fase 1: Lotes / Series / Vencimientos ============

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
        return await self._phase1.crear_lote(
            producto_id=producto_id,
            codigo_lote=codigo_lote,
            cantidad_inicial=cantidad_inicial,
            fecha_fabricacion=fecha_fabricacion,
            fecha_vencimiento=fecha_vencimiento,
            serie=serie,
            ubicacion=ubicacion,
            proveedor_id=proveedor_id,
        )

    async def obtener_lotes(
        self,
        producto_id: int | None = None,
        proximos_vencer_dias: int | None = None,
    ) -> list[dict]:
        return await self._phase1.obtener_lotes(
            producto_id=producto_id,
            proximos_vencer_dias=proximos_vencer_dias,
        )

    async def eliminar_lote(self, lote_id: int) -> tuple[bool, dict]:
        return await self._phase1.eliminar_lote(lote_id)

    # ============ Fase 1: Listas de precios multi-nivel ============

    async def crear_lista_precio(self, nombre: str, descripcion: str = "") -> tuple[bool, dict]:
        return await self._phase1.crear_lista_precio(nombre=nombre, descripcion=descripcion)

    async def obtener_listas_precios(self, solo_activas: bool = True) -> list[dict]:
        return await self._phase1.obtener_listas_precios(solo_activas=solo_activas)

    async def asignar_precio(
        self,
        producto_id: int,
        lista_id: int,
        precio: float,
    ) -> tuple[bool, dict]:
        return await self._phase1.asignar_precio(
            producto_id=producto_id,
            lista_id=lista_id,
            precio=precio,
        )

    async def obtener_precio_producto(
        self,
        producto_id: int,
        lista_id: int | None = None,
    ) -> dict:
        return await self._phase1.obtener_precio_producto(
            producto_id=producto_id,
            lista_id=lista_id,
        )

    async def actualizar_precios_producto(
        self,
        producto_id: int,
        precio: float | None = None,
        precio_costo: float | None = None,
        margen: float | None = None,
    ) -> tuple[bool, dict]:
        return await self._phase1.actualizar_precios_producto(
            producto_id=producto_id,
            precio=precio,
            precio_costo=precio_costo,
            margen=margen,
        )

    # ============ Fase 1: Impuestos ============

    async def crear_impuesto(
        self,
        nombre: str,
        porcentaje: float,
        tipo: str = "iva",
    ) -> tuple[bool, dict]:
        return await self._phase1.crear_impuesto(
            nombre=nombre,
            porcentaje=porcentaje,
            tipo=tipo,
        )

    async def obtener_impuestos(self, solo_activos: bool = True) -> list[dict]:
        return await self._phase1.obtener_impuestos(solo_activos=solo_activos)

    async def calcular_precio_con_impuesto(
        self,
        precio_base: float,
        porcentaje: float,
    ) -> dict:
        return await self._phase1.calcular_precio_con_impuesto(
            precio_base=precio_base,
            porcentaje=porcentaje,
        )

    async def asignar_impuesto_producto(
        self,
        producto_id: int,
        impuesto_id: int | None,
    ) -> tuple[bool, dict]:
        return await self._phase1.asignar_impuesto_producto(
            producto_id=producto_id,
            impuesto_id=impuesto_id,
        )

    # ============ Fase 1: Caja / Turnos POS ============

    async def abrir_turno_caja(
        self,
        monto_inicial: float = 0,
        notas: str = "",
    ) -> tuple[bool, dict]:
        return await self._phase1.abrir_turno_caja(monto_inicial=monto_inicial, notas=notas)

    async def registrar_movimiento_caja(
        self,
        turno_id: int,
        tipo: str,
        monto: float,
        concepto: str = "",
        referencia: str = "",
    ) -> tuple[bool, dict]:
        return await self._phase1.registrar_movimiento_caja(
            turno_id=turno_id,
            tipo=tipo,
            monto=monto,
            concepto=concepto,
            referencia=referencia,
        )

    async def asociar_venta_a_turno(self, turno_id: int, venta_id: int) -> bool:
        return await self._phase1.asociar_venta_a_turno(turno_id, venta_id)

    async def cerrar_turno_caja(
        self,
        turno_id: int,
        monto_final: float,
        notas: str = "",
    ) -> tuple[bool, dict]:
        return await self._phase1.cerrar_turno_caja(
            turno_id=turno_id,
            monto_final=monto_final,
            notas=notas,
        )

    async def obtener_turno_caja(self, turno_id: int) -> dict | None:
        return await self._phase1.obtener_turno_caja(turno_id)

    async def obtener_turnos_caja(self, usuario: str | None = None) -> list[dict]:
        return await self._phase1.obtener_turnos_caja(usuario=usuario)

    async def obtener_turno_abierto(self, usuario: str) -> dict | None:
        return await self._phase1.obtener_turno_abierto(usuario)

    # ============ Fase 1: Dashboard KPIs ============

    async def obtener_kpis_dashboard(self) -> dict:
        return await self._phase1.obtener_kpis_dashboard()

    # ============ Advanced Search / Restocking (warehouse) ============

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
        return await self._warehouse.buscar_productos_avanzado(
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

    async def sugerir_reabastecimiento(
        self,
        supplier_id: int | None = None,
    ) -> list[dict]:
        return await self._warehouse.sugerir_reabastecimiento(supplier_id=supplier_id)

    async def crear_ordenes_desde_sugerencias(
        self,
        supplier_id: int,
        suggestions: list[dict],
    ) -> tuple[bool, dict]:
        return await self._warehouse.crear_ordenes_desde_sugerencias(
            supplier_id=supplier_id,
            suggestions=suggestions,
        )

    # ============ Push / Email queue ============

    async def encolar_push(
        self,
        tipo: str,
        destinatario: str,
        asunto: str,
        cuerpo: str,
    ) -> tuple[bool, dict]:
        return await self._admin.encolar_push(
            tipo=tipo,
            destinatario=destinatario,
            asunto=asunto,
            cuerpo=cuerpo,
        )

    async def obtener_jobs_push(
        self,
        estado: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        return await self._admin.obtener_jobs_push(estado=estado, limit=limit)

    async def despachar_jobs_push(self, limit: int = 25) -> dict:
        return await self._admin.despachar_jobs_push(limit=limit)

    # ============ Fase 3: Variantes de producto ============

    async def crear_variante(
        self,
        producto_id: int,
        sku: str,
        atributos: dict[str, str],
        cantidad: int = 0,
        precio_override: float | None = None,
    ) -> tuple[bool, dict]:
        return await self._phase3.crear_variante(
            producto_id=producto_id,
            sku=sku,
            atributos=atributos,
            cantidad=cantidad,
            precio_override=precio_override,
        )

    async def obtener_variantes(
        self,
        producto_id: int | None = None,
        sku: str | None = None,
        solo_activas: bool = True,
    ) -> list[dict]:
        return await self._phase3.obtener_variantes(
            producto_id=producto_id,
            sku=sku,
            solo_activas=solo_activas,
        )

    async def actualizar_stock_variante(
        self,
        variante_id: int,
        cantidad: int,
    ) -> tuple[bool, dict]:
        return await self._phase3.actualizar_stock_variante(
            variante_id=variante_id,
            cantidad=cantidad,
        )

    async def eliminar_variante(self, variante_id: int) -> tuple[bool, dict]:
        return await self._phase3.eliminar_variante(variante_id)

    # ============ Fase 3: Reportes personalizables ============

    async def guardar_plantilla_reporte(
        self,
        nombre: str,
        modulo: str,
        columnas: list[str],
        filtros: dict | None = None,
        agrupacion: str | None = None,
        ordenado_por: str | None = None,
    ) -> tuple[bool, dict]:
        return await self._phase3.guardar_plantilla_reporte(
            nombre=nombre,
            modulo=modulo,
            columnas=columnas,
            filtros=filtros,
            agrupacion=agrupacion,
            ordenado_por=ordenado_por,
        )

    async def obtener_plantillas_reporte(self) -> list[dict]:
        return await self._phase3.obtener_plantillas_reporte()

    async def eliminar_plantilla_reporte(self, plantilla_id: int) -> tuple[bool, dict]:
        return await self._phase3.eliminar_plantilla_reporte(plantilla_id)

    async def ejecutar_reporte(
        self,
        modulo: str,
        columnas: list[str],
        filtros: dict | None = None,
        agrupacion: str | None = None,
        ordenado_por: str | None = None,
    ) -> dict:
        return await self._phase3.ejecutar_reporte(
            modulo=modulo,
            columnas=columnas,
            filtros=filtros,
            agrupacion=agrupacion,
            ordenado_por=ordenado_por,
        )

    async def obtener_modulos_reporte(self) -> list[dict]:
        return await self._phase3.obtener_modulos_reporte()

    # ============ Fase 3: i18n persistente ============

    async def obtener_idioma_usuario(self, usuario: str) -> str:
        return await self._phase3.obtener_idioma_usuario(usuario)

    async def cambiar_idioma(self, usuario: str, idioma: str) -> tuple[bool, dict]:
        return await self._phase3.cambiar_idioma(usuario, idioma)

    async def obtener_idiomas_disponibles(self) -> list[dict]:
        return await self._phase3.obtener_idiomas_disponibles()

    # ============ Fase 3: Busqueda por imagen ============

    async def buscar_por_imagen(
        self,
        ruta_imagen: str,
        extractor: Callable[[str], list[float]] | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        return await self._phase3.buscar_por_imagen(
            ruta_imagen=ruta_imagen,
            extractor=extractor,
            top_k=top_k,
        )

    # ============ Facturación ============

    async def crear_factura(
        self,
        cliente_id: int,
        items: list[dict],
        tipo: str = "factura",
        descuento_total: float = 0,
        notas: str = "",
        venta_id: int | None = None,
    ) -> tuple[bool, dict]:
        return await self._invoices.crear_factura(
            cliente_id=cliente_id,
            items=items,
            tipo=tipo,
            descuento_total=descuento_total,
            notas=notas,
            venta_id=venta_id,
        )

    async def obtener_factura(self, factura_id: int) -> dict | None:
        return await self._invoices.obtener_factura(factura_id)

    async def obtener_facturas(
        self, estado: str | None = None, cliente_id: int | None = None
    ) -> list[dict]:
        return await self._invoices.obtener_facturas(estado=estado, cliente_id=cliente_id)

    async def cancelar_factura(self, factura_id: int) -> tuple[bool, dict]:
        return await self._invoices.cancelar_factura(factura_id)

    async def crear_factura_desde_venta(self, venta_id: int) -> tuple[bool, dict]:
        return await self._invoices.crear_factura_desde_venta(venta_id)

    # ============ Contabilidad ============

    async def crear_asiento(
        self,
        fecha: str,
        descripcion: str,
        tipo: str,
        movimientos: list[dict],
        referencia_id: int | None = None,
        referencia_tipo: str | None = None,
    ) -> tuple[bool, dict]:
        return await self._accounting.crear_asiento(
            fecha=fecha,
            descripcion=descripcion,
            tipo=tipo,
            movimientos=movimientos,
            referencia_id=referencia_id,
            referencia_tipo=referencia_tipo,
        )

    async def obtener_asiento(self, asiento_id: int) -> dict | None:
        return await self._accounting.obtener_asiento(asiento_id)

    async def obtener_asientos(
        self, fecha_inicio: str | None = None, fecha_fin: str | None = None
    ) -> list[dict]:
        return await self._accounting.obtener_asientos(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

    async def obtener_plan_cuentas(self, tipo: str | None = None) -> list[dict]:
        return await self._accounting.obtener_plan_cuentas(tipo=tipo)

    async def obtener_balance_comprobacion(
        self, fecha_inicio: str | None = None, fecha_fin: str | None = None
    ) -> list[dict]:
        return await self._accounting.obtener_balance_comprobacion(
            fecha_inicio=fecha_inicio, fecha_fin=fecha_fin
        )

    async def crear_asiento_venta(self, venta_id: int) -> tuple[bool, dict]:
        return await self._accounting.crear_asiento_venta(venta_id)

    # ============ Inventario ============

    async def analisis_abc(self) -> list[dict]:
        return await self._inventory.analisis_abc()

    async def calcular_rotacion(self, dias: int = 30) -> dict:
        return await self._inventory.calcular_rotacion(dias=dias)

    async def analisis_envejecimiento(self) -> list[dict]:
        return await self._inventory.analisis_envejecimiento()

    async def riesgo_agotamiento(self) -> list[dict]:
        return await self._inventory.riesgo_agotamiento()

    async def valor_inventario(self, metodo: str = "promedio") -> dict:
        return await self._inventory.valor_inventario(metodo=metodo)

    async def generar_reporte_inventario(self) -> dict:
        return await self._inventory.generar_reporte_inventario()
