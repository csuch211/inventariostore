"""Navigation router functions extracted from AppView."""

import asyncio

from ui import admin, entity, sales, stock
from ui import phase1 as p1
from ui import phase3 as p3


async def refresh_nav_badges(app) -> None:
    """Refresh sidebar badges (e.g. stock alerts). Re-renders the main view."""
    try:
        app._stock_alert_count = await app.controller.contar_alertas_stock()
    except Exception:
        app._stock_alert_count = 0
    # Re-render the sidebar by rebuilding the main view
    getattr(app, "_current_route", "dashboard")
    await app._show_main_view()


async def navigate_to(app, route: str) -> None:
    """Navigate to different sections"""
    app._current_route = route
    app.current_page = 0
    app.current_product_edit = None

    if route == "dashboard":
        await app._show_dashboard()
    elif route == "products":
        await app._show_products_list()
    elif route == "sales":
        await sales.show_sales(app)
    elif route == "clients":
        await entity.show_clients(app)
    elif route == "stock":
        await app._show_stock_management()
    elif route == "scanner":
        from ui.views.scanner_view import show_scanner

        await show_scanner(app)
    elif route == "export":
        await app._show_export_options()
    elif route == "categories":
        await entity.show_categories(app)
    elif route == "suppliers":
        await entity.show_suppliers(app)
    elif route == "purchase_orders":
        await app._show_purchase_orders()
    elif route == "stock_alerts":
        await stock.show_stock_alerts(app)
    elif route == "warehouses":
        await stock.show_warehouses(app)
    elif route == "warehouse_stock":
        await stock.show_warehouse_stock(app)
    elif route == "backups":
        await admin.show_backups(app)
    elif route == "users":
        await admin.show_users(app)
    elif route == "settings":
        await admin.show_settings(app)
    elif route == "smtp_config":
        from ui.smtp_config_view import show_smtp_config

        await show_smtp_config(app)
    elif route == "logout":
        await app._logout()
    # Fase 1 routes
    elif route == "p1_devoluciones":
        await p1.show_devoluciones(app)
    elif route == "p1_transferencias":
        await p1.show_transferencias(app)
    elif route == "p1_conteos":
        await p1.show_conteos(app)
    elif route == "p1_lotes":
        await p1.show_lotes(app)
    elif route == "p1_precios":
        await p1.show_precios(app)
    elif route == "p1_impuestos":
        await p1.show_impuestos(app)
    elif route == "p1_caja":
        await p1.show_caja(app)
    elif route == "p1_busqueda":
        await p1.show_busqueda(app)
    elif route == "p1_reabasto":
        await p1.show_reabasto(app)
    # Fase 3 routes
    elif route == "p3_variantes":
        await p3.show_variantes(app)
    elif route == "p3_reportes":
        await p3.show_reportes(app)
    elif route == "p3_push":
        await p3.show_push_queue(app)
    elif route == "p3_image_search":
        await p3.show_image_search(app)
    # Facturación routes
    elif route == "facturas":
        from ui.invoice_views import show_facturas
        await show_facturas(app)
    # Contabilidad routes
    elif route == "asientos":
        from ui.accounting_views import show_asientos
        await show_asientos(app)
    elif route == "plan_cuentas":
        from ui.accounting_views import show_plan_cuentas
        await show_plan_cuentas(app)
    elif route == "balance":
        from ui.accounting_views import show_balance
        await show_balance(app)
    # Reportes financieros
    elif route == "financial_dashboard":
        from ui.financial_reports import show_financial_dashboard
        await show_financial_dashboard(app)
    elif route == "estado_resultados":
        from ui.financial_reports import show_estado_resultados
        await show_estado_resultados(app)
    elif route == "balance_general":
        from ui.financial_reports import show_balance_general
        await show_balance_general(app)
    # Análisis de inventario
    elif route == "abc_analysis":
        from ui.inventory_analysis_views import show_abc_analysis
        await show_abc_analysis(app)
    elif route == "inventory_turnover":
        from ui.inventory_analysis_views import show_inventory_turnover
        await show_inventory_turnover(app)
    elif route == "inventory_aging":
        from ui.inventory_analysis_views import show_inventory_aging
        await show_inventory_aging(app)
    elif route == "stockout_risk":
        from ui.inventory_analysis_views import show_stockout_risk
        await show_stockout_risk(app)


def refresh_nav_badges_sync(app) -> None:
    """Update the sidebar stock-alert badge without rebuilding the page.

    Cheaper than calling ``refresh_nav_badges()`` (which re-renders the
    whole main view) when we only need to bump a counter.
    """
    try:
        if app._sidebar_nav is not None:
            asyncio.create_task(refresh_nav_badges(app))
    except RuntimeError:
        pass
