"""Navigation router with declarative route definitions."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from services.permissions import Perm
from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class RouteDef:
    """Definition of a single route."""
    handler: Callable  # async function (app) -> None
    permission: Any = None  # Perm.* or None for public
    module_path: str | None = None  # Used for lazy import module hint


# Lazy import wrappers to avoid circular imports
async def _show_sales(app):
    from ui import sales
    await sales.show_sales(app)


async def _show_clients(app):
    from ui import entity
    await entity.show_clients(app)


async def _show_categories(app):
    from ui import entity
    await entity.show_categories(app)


async def _show_suppliers(app):
    from ui import entity
    await entity.show_suppliers(app)


async def _show_stock_alerts(app):
    from ui import stock
    await stock.show_stock_alerts(app)


async def _show_warehouses(app):
    from ui import stock
    await stock.show_warehouses(app)


async def _show_warehouse_stock(app):
    from ui import stock
    await stock.show_warehouse_stock(app)


async def _show_backups(app):
    from ui import admin
    await admin.show_backups(app)


async def _show_users(app):
    from ui import admin
    await admin.show_users(app)


async def _show_settings(app):
    from ui import admin
    await admin.show_settings(app)


async def _show_scanner(app):
    from ui.views.scanner_view import show_scanner
    await show_scanner(app)


async def _show_smtp_config(app):
    from ui.smtp_config_view import show_smtp_config
    await show_smtp_config(app)


async def _show_facturas(app):
    from ui.invoice_views import show_facturas
    await show_facturas(app)


async def _show_asientos(app):
    from ui.accounting_views import show_asientos
    await show_asientos(app)


async def _show_plan_cuentas(app):
    from ui.accounting_views import show_plan_cuentas
    await show_plan_cuentas(app)


async def _show_balance(app):
    from ui.accounting_views import show_balance
    await show_balance(app)


async def _show_financial_dashboard(app):
    from ui.financial_reports import show_financial_dashboard
    await show_financial_dashboard(app)


async def _show_estado_resultados(app):
    from ui.financial_reports import show_estado_resultados
    await show_estado_resultados(app)


async def _show_balance_general(app):
    from ui.financial_reports import show_balance_general
    await show_balance_general(app)


async def _show_abc_analysis(app):
    from ui.inventory_analysis_views import show_abc_analysis
    await show_abc_analysis(app)


async def _show_inventory_turnover(app):
    from ui.inventory_analysis_views import show_inventory_turnover
    await show_inventory_turnover(app)


async def _show_inventory_aging(app):
    from ui.inventory_analysis_views import show_inventory_aging
    await show_inventory_aging(app)


async def _show_stockout_risk(app):
    from ui.inventory_analysis_views import show_stockout_risk
    await show_stockout_risk(app)


async def _show_empleados(app):
    from ui.hr_views import show_empleados
    await show_empleados(app)


async def _show_cotizaciones(app):
    from ui.purchasing_views import show_cotizaciones
    await show_cotizaciones(app)


async def _show_contactos(app):
    from ui.crm_views import show_contactos
    await show_contactos(app)


async def _show_pipeline(app):
    from ui.crm_views import show_pipeline
    await show_pipeline(app)


async def _show_documentos(app):
    from ui.document_views import show_documentos
    await show_documentos(app)


async def _show_notificaciones(app):
    from ui.notification_views import show_notificaciones
    await show_notificaciones(app)


async def _show_plantillas_notificacion(app):
    from ui.notification_views import show_plantillas_notificacion
    await show_plantillas_notificacion(app)


async def _show_messaging(app):
    from ui.messaging_config_view import show_messaging_config
    await show_messaging_config(app)


async def _show_cart(app):
    from ui.cart_views import show_cart
    await show_cart(app)


async def _show_cart_config(app):
    from ui.cart_views import show_cart_config
    await show_cart_config(app)


async def _show_store(app):
    from ui.store_public import show_store_public
    await show_store_public(app)


async def _show_store_config(app):
    from ui.store_views import show_store_config
    await show_store_config(app)


async def _show_store_products(app):
    from ui.store_views import show_store_products
    await show_store_products(app)


async def _show_store_orders(app):
    from ui.store_views import show_store_orders
    await show_store_orders(app)


async def _show_automation(app):
    from ui.automation_views import show_automation
    await show_automation(app)


async def _show_automation_abc(app):
    from ui.automation_views import show_automation_abc
    await show_automation_abc(app)


async def _show_automation_forecasts(app):
    from ui.automation_views import show_automation_forecasts
    await show_automation_forecasts(app)


async def _show_automation_segments(app):
    from ui.automation_views import show_automation_segments
    await show_automation_segments(app)


async def _show_automation_pricing(app):
    from ui.automation_views import show_automation_pricing
    await show_automation_pricing(app)


# Advanced Inventory
async def _show_p1_devoluciones(app):
    from ui import advanced_inventory as p1
    await p1.show_devoluciones(app)


async def _show_p1_transferencias(app):
    from ui import advanced_inventory as p1
    await p1.show_transferencias(app)


async def _show_p1_conteos(app):
    from ui import advanced_inventory as p1
    await p1.show_conteos(app)


async def _show_p1_lotes(app):
    from ui import advanced_inventory as p1
    await p1.show_lotes(app)


async def _show_p1_precios(app):
    from ui import advanced_inventory as p1
    await p1.show_precios(app)


async def _show_p1_impuestos(app):
    from ui import advanced_inventory as p1
    await p1.show_impuestos(app)


async def _show_p1_caja(app):
    from ui import advanced_inventory as p1
    await p1.show_caja(app)


async def _show_p1_busqueda(app):
    from ui import advanced_inventory as p1
    await p1.show_busqueda(app)


async def _show_p1_reabasto(app):
    from ui import advanced_inventory as p1
    await p1.show_reabasto(app)


# Extended Features
async def _show_p3_variantes(app):
    from ui import extended_features as p3
    await p3.show_variantes(app)


async def _show_p3_reportes(app):
    from ui import extended_features as p3
    await p3.show_reportes(app)


async def _show_p3_push(app):
    from ui import extended_features as p3
    await p3.show_push_queue(app)


async def _show_p3_image_search(app):
    from ui import extended_features as p3
    await p3.show_image_search(app)


# Declarative route registry
ROUTES: dict[str, RouteDef] = {
    "dashboard": RouteDef(handler=lambda app: app._show_dashboard()),
    "products": RouteDef(handler=lambda app: app._show_products_list()),
    "sales": RouteDef(handler=_show_sales, permission=Perm.VENTAS_LEER),
    "clients": RouteDef(handler=_show_clients, permission=Perm.CLIENTES_LEER),
    "categories": RouteDef(handler=_show_categories, permission=Perm.CATEGORIAS_LEER),
    "suppliers": RouteDef(handler=_show_suppliers, permission=Perm.PROVEEDORES_LEER),
    "stock": RouteDef(handler=lambda app: app._show_stock_management()),
    "scanner": RouteDef(handler=_show_scanner),
    "export": RouteDef(handler=lambda app: app._show_export_options()),
    "purchase_orders": RouteDef(handler=lambda app: app._show_purchase_orders(), permission=Perm.ORDENES_LEER),
    "stock_alerts": RouteDef(handler=_show_stock_alerts, permission=Perm.STOCK_ALERTAS_VER),
    "warehouses": RouteDef(handler=_show_warehouses, permission=Perm.ALMACENES_LEER),
    "warehouse_stock": RouteDef(handler=_show_warehouse_stock, permission=Perm.ALMACENES_STOCK),
    "backups": RouteDef(handler=_show_backups, permission=Perm.BACKUPS_CREAR),
    "users": RouteDef(handler=_show_users, permission=Perm.USUARIOS_LEER),
    "settings": RouteDef(handler=_show_settings),
    "logout": RouteDef(handler=lambda app: app._logout()),
    "smtp_config": RouteDef(handler=_show_smtp_config),
    # Fase 1
    "p1_devoluciones": RouteDef(handler=_show_p1_devoluciones, permission=Perm.DEVOLUCIONES_LEER),
    "p1_transferencias": RouteDef(handler=_show_p1_transferencias, permission=Perm.TRANSFERENCIAS_LEER),
    "p1_conteos": RouteDef(handler=_show_p1_conteos, permission=Perm.CONTEOS_LEER),
    "p1_lotes": RouteDef(handler=_show_p1_lotes, permission=Perm.LOTES_LEER),
    "p1_precios": RouteDef(handler=_show_p1_precios, permission=Perm.PRECIOS_LEER),
    "p1_impuestos": RouteDef(handler=_show_p1_impuestos, permission=Perm.IMPUESTOS_LEER),
    "p1_caja": RouteDef(handler=_show_p1_caja, permission=Perm.CAJA_LEER),
    "p1_busqueda": RouteDef(handler=_show_p1_busqueda, permission=Perm.PRODUCTOS_LEER),
    "p1_reabasto": RouteDef(handler=_show_p1_reabasto, permission=Perm.ORDENES_LEER),
    # Fase 3
    "p3_variantes": RouteDef(handler=_show_p3_variantes, permission=Perm.VARIANTES_LEER),
    "p3_reportes": RouteDef(handler=_show_p3_reportes, permission=Perm.REPORTES_EJECUTAR),
    "p3_push": RouteDef(handler=_show_p3_push, permission=Perm.PUSH_ENVIAR),
    "p3_image_search": RouteDef(handler=_show_p3_image_search, permission=Perm.IMAGE_SEARCH),
    # Facturación
    "facturas": RouteDef(handler=_show_facturas, permission=Perm.FACTURAS_LEER),
    # Contabilidad
    "asientos": RouteDef(handler=_show_asientos, permission=Perm.CONTABILIDAD_LEER),
    "plan_cuentas": RouteDef(handler=_show_plan_cuentas, permission=Perm.CONTABILIDAD_PLAN_CUENTAS),
    "balance": RouteDef(handler=_show_balance, permission=Perm.CONTABILIDAD_LEER),
    # Reportes financieros
    "financial_dashboard": RouteDef(handler=_show_financial_dashboard, permission=Perm.CONTABILIDAD_LEER),
    "estado_resultados": RouteDef(handler=_show_estado_resultados, permission=Perm.CONTABILIDAD_LEER),
    "balance_general": RouteDef(handler=_show_balance_general, permission=Perm.CONTABILIDAD_LEER),
    # Análisis de inventario
    "abc_analysis": RouteDef(handler=_show_abc_analysis, permission=Perm.STOCK_LEER),
    "inventory_turnover": RouteDef(handler=_show_inventory_turnover, permission=Perm.STOCK_LEER),
    "inventory_aging": RouteDef(handler=_show_inventory_aging, permission=Perm.STOCK_LEER),
    "stockout_risk": RouteDef(handler=_show_stockout_risk, permission=Perm.STOCK_LEER),
    # RRHH
    "empleados": RouteDef(handler=_show_empleados, permission=Perm.USUARIOS_LEER),
    # Compras
    "cotizaciones": RouteDef(handler=_show_cotizaciones, permission=Perm.ORDENES_LEER),
    # CRM
    "contactos": RouteDef(handler=_show_contactos, permission=Perm.CLIENTES_LEER),
    "pipeline": RouteDef(handler=_show_pipeline, permission=Perm.CLIENTES_LEER),
    # Documentos
    "documentos": RouteDef(handler=_show_documentos, permission=Perm.USUARIOS_LEER),
    # Notificaciones
    "notificaciones": RouteDef(handler=_show_notificaciones, permission=Perm.NOTIFICACIONES_CONFIGURAR),
    "plantillas_notificacion": RouteDef(handler=_show_plantillas_notificacion, permission=Perm.NOTIFICACIONES_CONFIGURAR),
    "messaging": RouteDef(handler=_show_messaging, permission=Perm.WHATSAPP_CONFIGURAR),
    # Carrito
    "cart": RouteDef(handler=_show_cart, permission=Perm.CARRITO_LEER),
    "cart_config": RouteDef(handler=_show_cart_config, permission=Perm.CARRITO_CONFIGURAR),
    # Tienda
    "store": RouteDef(handler=_show_store, permission=Perm.TIENDA_LEER),
    "store_config": RouteDef(handler=_show_store_config, permission=Perm.TIENDA_GESTIONAR),
    "store_products": RouteDef(handler=_show_store_products, permission=Perm.TIENDA_GESTIONAR),
    "store_orders": RouteDef(handler=_show_store_orders, permission=Perm.TIENDA_PEDIDOS_LEER),
    # Automatización
    "automation": RouteDef(handler=_show_automation, permission=Perm.AUTOMATION_LEER),
    "automation_abc": RouteDef(handler=_show_automation_abc, permission=Perm.AUTOMATION_LEER),
    "automation_forecasts": RouteDef(handler=_show_automation_forecasts, permission=Perm.AUTOMATION_LEER),
    "automation_segments": RouteDef(handler=_show_automation_segments, permission=Perm.AUTOMATION_LEER),
    "automation_pricing": RouteDef(handler=_show_automation_pricing, permission=Perm.AUTOMATION_LEER),
}


async def refresh_nav_badges(app) -> None:
    """Refresh sidebar badges (e.g. stock alerts). Re-renders the main view."""
    try:
        app._stock_alert_count = await app.controller.contar_alertas_stock()
    except Exception as e:
        logger.error("Error al refrescar badges de navegación: %s", e)
        app._stock_alert_count = 0
    getattr(app, "_current_route", "dashboard")
    await app._show_main_view()


async def navigate_to(app, route: str) -> None:
    """Navigate to a route using the declarative registry."""
    route_def = ROUTES.get(route)
    if route_def is None:
        logger.warning("Ruta desconocida: %s", route)
        route_def = ROUTES.get("dashboard")
        if route_def is None:
            return

    app._current_route = route
    app.current_page = 0
    app.current_product_edit = None

    await route_def.handler(app)


def refresh_nav_badges_sync(app) -> None:
    """Update the sidebar stock-alert badge without rebuilding the page."""
    try:
        if app._sidebar_nav is not None:
            task = asyncio.create_task(refresh_nav_badges(app))
            task.add_done_callback(lambda t: None)
    except RuntimeError:
        pass
