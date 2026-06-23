"""Extracted view modules for InventarioStore.

These modules contain the view logic extracted from app_view.py
to improve maintainability and reduce the God Class.
"""

from ui.views.dashboard_view import show_dashboard
from ui.views.dialogs import (
    show_export_options,
    show_order_form,
    show_purchase_orders,
    show_stock_management,
)
from ui.views.nav_router import (
    navigate_to,
    refresh_nav_badges,
    refresh_nav_badges_sync,
)
from ui.views.product_view import (
    confirm_delete_product,
    handle_new_product,
    show_product_form,
    show_products_list,
    update_products_table,
)
from ui.views.scanner_view import build_scanner_result, show_scanner
from ui.views.sidebar_builder import (
    MOBILE_TOP_KEYS,
    NAV_DATA_ALL,
    ROUTE_PERMISSIONS,
    SECTIONS_DEF,
    build_sidebar_desktop,
    build_sidebar_mobile,
)

__all__ = [
    "MOBILE_TOP_KEYS",
    "NAV_DATA_ALL",
    "ROUTE_PERMISSIONS",
    "SECTIONS_DEF",
    "build_sidebar_desktop",
    "build_sidebar_mobile",
    "build_scanner_result",
    "confirm_delete_product",
    "handle_new_product",
    "navigate_to",
    "refresh_nav_badges",
    "refresh_nav_badges_sync",
    "show_dashboard",
    "show_export_options",
    "show_order_form",
    "show_product_form",
    "show_products_list",
    "show_purchase_orders",
    "show_scanner",
    "show_stock_management",
    "update_products_table",
]
