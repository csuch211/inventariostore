"""
RBAC permission catalog and helpers.

Defines the canonical permission keys used across the app, plus helpers for:
- `PermissionException` raised when an action is denied.
- `require_permission(perm)` decorator that gates controller methods.
- `roles_default_permissions()` mapping roles to their default permission sets.

Permission keys follow the pattern '<module>.<action>' where action is one of:
- `leer`, `crear`, `actualizar`, `eliminar`, `gestionar`, `recibir`, `cancelar`,
  `importar`, `exportar`.
"""

import inspect
from functools import wraps

from utils.exceptions import InventarioException
from utils.logger import setup_logger

logger = setup_logger(__name__)


# ============ Permission keys ============


class Perm:
    """Catalog of permission keys. Keep this list authoritative."""

    # Productos
    PRODUCTOS_LEER = "productos.leer"
    PRODUCTOS_CREAR = "productos.crear"
    PRODUCTOS_ACTUALIZAR = "productos.actualizar"
    PRODUCTOS_ELIMINAR = "productos.eliminar"

    # Categorías
    CATEGORIAS_LEER = "categorias.leer"
    CATEGORIAS_GESTIONAR = "categorias.gestionar"

    # Proveedores
    PROVEEDORES_LEER = "proveedores.leer"
    PROVEEDORES_GESTIONAR = "proveedores.gestionar"

    # Órdenes de compra
    ORDENES_LEER = "ordenes.leer"
    ORDENES_CREAR = "ordenes.crear"
    ORDENES_RECIBIR = "ordenes.recibir"
    ORDENES_CANCELAR = "ordenes.cancelar"

    # Stock
    STOCK_LEER = "stock.leer"
    STOCK_ACTUALIZAR = "stock.actualizar"
    STOCK_ALERTAS_VER = "stock_alertas.ver"

    # Exportar / Importar
    EXPORTAR = "exportar.leer"
    IMPORTAR = "importar.leer"

    # Usuarios
    USUARIOS_LEER = "usuarios.leer"
    USUARIOS_GESTIONAR = "usuarios.gestionar"

    # Ventas / POS
    VENTAS_LEER = "ventas.leer"
    VENTAS_CREAR = "ventas.crear"
    VENTAS_CANCELAR = "ventas.cancelar"

    # Clientes
    CLIENTES_LEER = "clientes.leer"
    CLIENTES_GESTIONAR = "clientes.gestionar"

    # Backups
    BACKUPS_CREAR = "backups.crear"
    BACKUPS_RESTAURAR = "backups.restaurar"

    # Almacenes (F2.1)
    ALMACENES_LEER = "almacenes.leer"
    ALMACENES_GESTIONAR = "almacenes.gestionar"
    ALMACENES_STOCK = "almacenes.stock"

    # Operaciones masivas (F2.2)
    BULK_ELIMINAR = "bulk.eliminar"
    BULK_CATEGORIA = "bulk.categoria"
    BULK_EXPORTAR = "bulk.exportar"

    # Notificaciones (F2.3)
    NOTIFICACIONES_CONFIGURAR = "notificaciones.configurar"

    # Auditoría
    AUDITORIA_LEER = "auditoria.leer"

    # Devoluciones / notas de crédito (Fase 1)
    DEVOLUCIONES_LEER = "devoluciones.leer"
    DEVOLUCIONES_CREAR = "devoluciones.crear"

    # Transferencias entre almacenes (Fase 1)
    TRANSFERENCIAS_LEER = "transferencias.leer"
    TRANSFERENCIAS_CREAR = "transferencias.crear"

    # Conteo físico / reconciliación (Fase 1)
    CONTEOS_LEER = "conteos.leer"
    CONTEOS_CREAR = "conteos.crear"
    CONTEOS_AJUSTAR = "conteos.ajustar"

    # Lotes / series / vencimientos (Fase 1)
    LOTES_LEER = "lotes.leer"
    LOTES_GESTIONAR = "lotes.gestionar"

    # Precios multi-nivel (Fase 1)
    PRECIOS_LEER = "precios.leer"
    PRECIOS_GESTIONAR = "precios.gestionar"

    # Impuestos (Fase 1)
    IMPUESTOS_LEER = "impuestos.leer"
    IMPUESTOS_GESTIONAR = "impuestos.gestionar"

    # Caja / turnos POS (Fase 1)
    CAJA_LEER = "caja.leer"
    CAJA_GESTIONAR = "caja.gestionar"

    # Dashboard ejecutivo
    DASHBOARD_VER = "dashboard.ver"

    # Fase 3 — infraestructura
    VARIANTES_LEER = "variantes.leer"
    VARIANTES_GESTIONAR = "variantes.gestionar"
    REPORTES_GUARDAR = "reportes.guardar"
    REPORTES_EJECUTAR = "reportes.ejecutar"
    API_ACCEDER = "api.acceder"
    IMAGE_SEARCH = "image_search.ejecutar"
    PUSH_ENVIAR = "push.enviar"
    PUSH_CONFIGURAR = "push.configurar"


# All permissions grouped by module for display in the UI
PERMISSIONS_BY_MODULE: dict[str, list[dict[str, str]]] = {
    "productos": [
        {"clave": Perm.PRODUCTOS_LEER, "descripcion": "Ver productos"},
        {"clave": Perm.PRODUCTOS_CREAR, "descripcion": "Crear productos"},
        {"clave": Perm.PRODUCTOS_ACTUALIZAR, "descripcion": "Editar productos"},
        {"clave": Perm.PRODUCTOS_ELIMINAR, "descripcion": "Eliminar productos"},
    ],
    "categorias": [
        {"clave": Perm.CATEGORIAS_LEER, "descripcion": "Ver categorías"},
        {"clave": Perm.CATEGORIAS_GESTIONAR, "descripcion": "Crear/editar/eliminar categorías"},
    ],
    "proveedores": [
        {"clave": Perm.PROVEEDORES_LEER, "descripcion": "Ver proveedores"},
        {"clave": Perm.PROVEEDORES_GESTIONAR, "descripcion": "Crear/editar/eliminar proveedores"},
    ],
    "ordenes": [
        {"clave": Perm.ORDENES_LEER, "descripcion": "Ver órdenes de compra"},
        {"clave": Perm.ORDENES_CREAR, "descripcion": "Crear órdenes de compra"},
        {"clave": Perm.ORDENES_RECIBIR, "descripcion": "Recibir órdenes (actualiza stock)"},
        {"clave": Perm.ORDENES_CANCELAR, "descripcion": "Cancelar órdenes"},
    ],
    "stock": [
        {"clave": Perm.STOCK_LEER, "descripcion": "Ver historial de stock"},
        {"clave": Perm.STOCK_ACTUALIZAR, "descripcion": "Ajustar stock manualmente"},
        {"clave": Perm.STOCK_ALERTAS_VER, "descripcion": "Ver alertas de stock bajo"},
    ],
    "datos": [
        {"clave": Perm.EXPORTAR, "descripcion": "Exportar datos"},
        {"clave": Perm.IMPORTAR, "descripcion": "Importar productos desde CSV"},
    ],
    "usuarios": [
        {"clave": Perm.USUARIOS_LEER, "descripcion": "Ver usuarios"},
        {"clave": Perm.USUARIOS_GESTIONAR, "descripcion": "Crear/editar/eliminar usuarios"},
    ],
    "ventas": [
        {"clave": Perm.VENTAS_LEER, "descripcion": "Ver ventas"},
        {"clave": Perm.VENTAS_CREAR, "descripcion": "Crear ventas (cobra y descuenta stock)"},
        {"clave": Perm.VENTAS_CANCELAR, "descripcion": "Cancelar ventas (revierte stock)"},
    ],
    "clientes": [
        {"clave": Perm.CLIENTES_LEER, "descripcion": "Ver clientes"},
        {"clave": Perm.CLIENTES_GESTIONAR, "descripcion": "Crear/editar/eliminar clientes"},
    ],
    "backups": [
        {"clave": Perm.BACKUPS_CREAR, "descripcion": "Crear copias de seguridad"},
        {"clave": Perm.BACKUPS_RESTAURAR, "descripcion": "Restaurar copias de seguridad"},
    ],
    "almacenes": [
        {"clave": Perm.ALMACENES_LEER, "descripcion": "Ver almacenes"},
        {"clave": Perm.ALMACENES_GESTIONAR, "descripcion": "Crear/editar/eliminar almacenes"},
        {"clave": Perm.ALMACENES_STOCK, "descripcion": "Ajustar stock por almacén"},
    ],
    "bulk": [
        {"clave": Perm.BULK_ELIMINAR, "descripcion": "Eliminación masiva de productos"},
        {"clave": Perm.BULK_CATEGORIA, "descripcion": "Cambiar categoría masivamente"},
        {"clave": Perm.BULK_EXPORTAR, "descripcion": "Exportar selección de productos"},
    ],
    "notificaciones": [
        {"clave": Perm.NOTIFICACIONES_CONFIGURAR, "descripcion": "Configurar notificaciones email"},
    ],
    "auditoria": [
        {"clave": Perm.AUDITORIA_LEER, "descripcion": "Ver registro de auditoría"},
    ],
    "devoluciones": [
        {"clave": Perm.DEVOLUCIONES_LEER, "descripcion": "Ver devoluciones"},
        {"clave": Perm.DEVOLUCIONES_CREAR, "descripcion": "Registrar devoluciones"},
    ],
    "transferencias": [
        {"clave": Perm.TRANSFERENCIAS_LEER, "descripcion": "Ver transferencias entre almacenes"},
        {"clave": Perm.TRANSFERENCIAS_CREAR, "descripcion": "Crear transferencias entre almacenes"},
    ],
    "conteos": [
        {"clave": Perm.CONTEOS_LEER, "descripcion": "Ver sesiones de conteo físico"},
        {"clave": Perm.CONTEOS_CREAR, "descripcion": "Crear sesiones de conteo físico"},
        {"clave": Perm.CONTEOS_AJUSTAR, "descripcion": "Aplicar ajustes desde conteo físico"},
    ],
    "lotes": [
        {"clave": Perm.LOTES_LEER, "descripcion": "Ver lotes/series/vencimientos"},
        {"clave": Perm.LOTES_GESTIONAR, "descripcion": "Crear/editar lotes y series"},
    ],
    "precios": [
        {"clave": Perm.PRECIOS_LEER, "descripcion": "Ver listas de precios"},
        {"clave": Perm.PRECIOS_GESTIONAR, "descripcion": "Gestionar listas de precios"},
    ],
    "impuestos": [
        {"clave": Perm.IMPUESTOS_LEER, "descripcion": "Ver configuración de impuestos"},
        {"clave": Perm.IMPUESTOS_GESTIONAR, "descripcion": "Configurar impuestos"},
    ],
    "caja": [
        {"clave": Perm.CAJA_LEER, "descripcion": "Ver turnos/cuadres de caja"},
        {
            "clave": Perm.CAJA_GESTIONAR,
            "descripcion": "Abrir/cerrar turnos y registrar movimientos",
        },
    ],
    "dashboard": [
        {"clave": Perm.DASHBOARD_VER, "descripcion": "Ver dashboard ejecutivo / KPIs"},
    ],
    "variantes": [
        {"clave": Perm.VARIANTES_LEER, "descripcion": "Ver variantes de producto"},
        {"clave": Perm.VARIANTES_GESTIONAR, "descripcion": "Crear/editar variantes"},
    ],
    "reportes": [
        {"clave": Perm.REPORTES_EJECUTAR, "descripcion": "Ejecutar reportes personalizables"},
        {"clave": Perm.REPORTES_GUARDAR, "descripcion": "Guardar plantillas de reporte"},
    ],
    "api": [
        {"clave": Perm.API_ACCEDER, "descripcion": "Consumir API REST"},
    ],
    "image_search": [
        {"clave": Perm.IMAGE_SEARCH, "descripcion": "Ejecutar búsqueda por imagen"},
    ],
    "push": [
        {"clave": Perm.PUSH_ENVIAR, "descripcion": "Encolar/enviar notificaciones push"},
        {"clave": Perm.PUSH_CONFIGURAR, "descripcion": "Configurar SMTP y destinos de push"},
    ],
}

ALL_PERMISSION_KEYS: list[str] = [
    item["clave"] for module in PERMISSIONS_BY_MODULE.values() for item in module
]


# ============ Default role -> permissions mapping ============


def _admin_perms() -> set[str]:
    return set(ALL_PERMISSION_KEYS)


def _operador_perms() -> set[str]:
    return {
        Perm.PRODUCTOS_LEER,
        Perm.PRODUCTOS_CREAR,
        Perm.PRODUCTOS_ACTUALIZAR,
        Perm.CATEGORIAS_LEER,
        Perm.PROVEEDORES_LEER,
        Perm.ORDENES_LEER,
        Perm.ORDENES_CREAR,
        Perm.ORDENES_RECIBIR,
        Perm.STOCK_LEER,
        Perm.STOCK_ACTUALIZAR,
        Perm.STOCK_ALERTAS_VER,
        Perm.EXPORTAR,
        Perm.ORDENES_CANCELAR,
        # Ventas & clientes
        Perm.VENTAS_LEER,
        Perm.VENTAS_CREAR,
        Perm.CLIENTES_LEER,
        Perm.CLIENTES_GESTIONAR,
        Perm.BACKUPS_CREAR,
        # Almacenes (F2.1)
        Perm.ALMACENES_LEER,
        Perm.ALMACENES_STOCK,
        # Bulk (F2.2)
        Perm.BULK_EXPORTAR,
        # Fase 1 — permisos operativos de inventario
        Perm.DEVOLUCIONES_LEER,
        Perm.DEVOLUCIONES_CREAR,
        Perm.TRANSFERENCIAS_LEER,
        Perm.TRANSFERENCIAS_CREAR,
        Perm.CONTEOS_LEER,
        Perm.CONTEOS_CREAR,
        Perm.CONTEOS_AJUSTAR,
        Perm.LOTES_LEER,
        Perm.LOTES_GESTIONAR,
        Perm.PRECIOS_LEER,
        Perm.CAJA_LEER,
        Perm.CAJA_GESTIONAR,
        Perm.DASHBOARD_VER,
        # Fase 3
        Perm.VARIANTES_LEER,
        Perm.VARIANTES_GESTIONAR,
        Perm.REPORTES_EJECUTAR,
        Perm.REPORTES_GUARDAR,
        Perm.PUSH_ENVIAR,
    }


def _viewer_perms() -> set[str]:
    return {
        Perm.PRODUCTOS_LEER,
        Perm.CATEGORIAS_LEER,
        Perm.PROVEEDORES_LEER,
        Perm.ORDENES_LEER,
        Perm.STOCK_LEER,
        Perm.STOCK_ALERTAS_VER,
        Perm.EXPORTAR,
        Perm.VENTAS_LEER,
        Perm.CLIENTES_LEER,
        # Almacenes (F2.1)
        Perm.ALMACENES_LEER,
        # Fase 1 — solo lectura
        Perm.DEVOLUCIONES_LEER,
        Perm.TRANSFERENCIAS_LEER,
        Perm.CONTEOS_LEER,
        Perm.LOTES_LEER,
        Perm.PRECIOS_LEER,
        Perm.IMPUESTOS_LEER,
        Perm.CAJA_LEER,
        Perm.DASHBOARD_VER,
        # Fase 3 — solo lectura
        Perm.VARIANTES_LEER,
        Perm.REPORTES_EJECUTAR,
    }


ROLE_DEFAULT_PERMISSIONS: dict[str, set[str]] = {
    "admin": _admin_perms(),
    "operador": _operador_perms(),
    "viewer": _viewer_perms(),
}

ROLE_DESCRIPTIONS = {
    "admin": "Acceso total al sistema",
    "operador": "Gestión diaria de inventario, stock y órdenes",
    "viewer": "Solo lectura",
}


# ============ PermissionException ============


class PermissionException(InventarioException):
    """Raised when a user lacks the required permission for an action."""

    pass


# ============ Decorator ============


def require_permission(perm_key: str):
    """Decorator that gates a controller method on a permission.

    Usage:
        @require_permission(Perm.PRODUCTOS_ELIMINAR)
        async def eliminar_producto(self, ...):
            ...

    The decorator looks for `self.current_user_permissions` (a list/set of
    permission keys). If the key is missing, raises `PermissionException`.
    Methods that should NOT be gated should not use this decorator.
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            perms = getattr(self, "current_user_permissions", None) or set()
            if perm_key not in perms:
                username = getattr(self, "current_user", "?")
                logger.warning(
                    f"Permission denied: {username} tried '{perm_key}' on {func.__name__}"
                )
                raise PermissionException(
                    f"Sin permiso: '{perm_key}' requerido para {func.__name__}"
                )
            return await func(self, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            perms = getattr(self, "current_user_permissions", None) or set()
            if perm_key not in perms:
                username = getattr(self, "current_user", "?")
                logger.warning(
                    f"Permission denied: {username} tried '{perm_key}' on {func.__name__}"
                )
                raise PermissionException(
                    f"Sin permiso: '{perm_key}' requerido para {func.__name__}"
                )
            return func(self, *args, **kwargs)

        # Pick the right wrapper based on whether the wrapped function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
