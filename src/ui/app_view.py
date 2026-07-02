"""
Application view — lightweight orchestrator.

Heavy UI logic has been extracted to dedicated managers:
- ``ui.auth_manager`` — login, logout, register, forgot password
- ``ui.stock_alert_manager`` — background stock monitor
- ``ui.bulk_manager`` — multi-select operations
"""

import asyncio
import contextlib

import flet as ft

from config.settings import APP_NAME
from core.controller import InventarioController
from core.theme_manager import theme_manager
from ui.auth_manager import (
    close_login_banner,
    logout,
    show_forgot_password,
    show_login_alert_banner,
    show_login_screen,
    show_register_form,
)
from ui.bulk_manager import bulk_change_category, bulk_delete, bulk_export, refresh_toolbar
from ui.components import LoadingSpinner, SnackBarHelper, bind_page
from ui.stock_alert_manager import on_alerts_changed, start_monitor, stop_monitor
from ui.views.sidebar_builder import (
    MOBILE_TOP_KEYS,
    NAV_DATA_ALL,
    ROUTE_PERMISSIONS,
    SECTIONS_DEF,
    build_sidebar_desktop,
    build_sidebar_mobile,
)
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AppView:
    """Main application view — orchestrator over managers and sub-views."""

    MOBILE_BREAKPOINT = 600
    TABLET_BREAKPOINT = 1024

    def __init__(self, page: ft.Page):
        self.page = page
        bind_page(page)
        self.controller = InventarioController()
        self.current_user = None
        self.current_token = None
        self.current_page = 0
        self.total_pages = 1
        self._current_route = "dashboard"
        self.all_products = []
        self.filtered_products = []
        self.current_product_edit = None

        # UI Components
        self.main_view = None
        self.products_table = None
        self.search_field = self._create_search_field()
        self.page_info_text = ft.Text("")
        self._sidebar_nav = None
        self._scanner_file_picker = None
        self._scanner_result_container = ft.Container()
        self._csv_import_picker = None
        self._stock_alert_count = 0
        self._selected_product_ids = set()
        self._bulk_toolbar_container = None
        self._bulk_toolbar = None
        self._theme_switch = None
        self._stock_monitor = None

        self._setup_page()
        self._form_factor = self._detect_form_factor()
        self._is_mobile = self._form_factor == "mobile"
        self.page.on_resized = self._on_resized

    def _detect_form_factor(self) -> str:
        """Detect form factor based on page width."""
        w = self.page.width or 1024
        if w < self.MOBILE_BREAKPOINT:
            return "mobile"
        if w < self.TABLET_BREAKPOINT:
            return "tablet"
        return "desktop"

    # ---- Setup & Utilities ----

    def _on_resized(self, e=None):
        was = self._form_factor
        self._form_factor = self._detect_form_factor()
        self._is_mobile = self._form_factor == "mobile"
        if was != self._form_factor:
            self._resize_task = asyncio.create_task(self._show_main_view())

    def _setup_page(self):
        self.page.title = APP_NAME
        theme_manager.apply(self.page, "light")
        self.page.padding = 0
        self.page.spacing = 0

    def _ensure_file_pickers_in_overlay(self):
        """No-op: FilePicker is not available in this Flet build."""

    def _drain_dialogs(self):
        pop = getattr(self.page, "pop_dialog", None)
        if pop is None:
            return
        for _ in range(64):
            try:
                closed = pop()
            except Exception as e:
                logger.error("Error al cerrar diálogo: %s", e)
                return
            if closed is None:
                return

    def _create_search_field(self) -> ft.TextField:
        async def handle_search(e):
            query = e.control.value.strip().lower()
            if query:
                self.filtered_products = [
                    p for p in self.all_products
                    if query in p.get("nombre", "").lower()
                    or query in p.get("codigo", "").lower()
                    or query in p.get("categoria", "").lower()
                ]
            else:
                self.filtered_products = self.all_products
            self.current_page = 0
            self._update_products_table()

        C = theme_manager.palette(page=self.page)
        return ft.TextField(
            label="Buscar",
            hint_text="Búsqueda por código, nombre o categoría",
            border_color=C["input_border"],
            focused_border_color=C["focus_ring"],
            filled=True,
            fill_color=C["input_fill"],
            color=C["text_on_input"],
            cursor_color=C["cursor"],
            selection_color=C["selection"],
            label_style=ft.TextStyle(color=C["text_secondary"]),
            hint_style=ft.TextStyle(color=C["text_muted"]),
            text_style=ft.TextStyle(color=C["text_on_input"], size=14),
            expand=True,
            on_change=handle_search,
        )

    def show_loading(self):
        self.main_view = LoadingSpinner.create(page=self.page)
        self.page.clean()
        self._ensure_file_pickers_in_overlay()
        self.page.add(self.main_view)

    # ---- Entry point ----

    async def start(self):
        self.show_loading()
        await show_login_screen(self)

    # ---- Authentication (delegates to auth_manager) ----

    async def _show_login_screen(self):
        await show_login_screen(self)

    async def _show_register_form(self):
        await show_register_form(self)

    async def _show_forgot_password(self):
        await show_forgot_password(self)

    async def _logout(self):
        await logout(self)

    # ---- Main View ----

    async def _show_main_view(self):
        with contextlib.suppress(Exception):
            await self.controller.seed_categorias_iniciales(
                [
                    t("categories.preset.electronics"),
                    t("categories.preset.clothing"),
                    t("categories.preset.food"),
                    t("categories.preset.home"),
                    t("categories.preset.other"),
                ]
            )

        try:
            self._stock_alert_count = await self.controller.contar_alertas_stock()
        except Exception as e:
            logger.error("Error al contar alertas de stock: %s", e)
            self._stock_alert_count = 0

        nav_data_all = list(NAV_DATA_ALL)
        nav_data_all = [
            (route, icon, label,
             self._stock_alert_count if route == "stock_alerts" and self._stock_alert_count else badge)
            for route, icon, label, badge in nav_data_all
        ]

        nav_data = [
            entry for entry in nav_data_all
            if ROUTE_PERMISSIONS.get(entry[0]) is None
            or ROUTE_PERMISSIONS[entry[0]] in self.controller.current_user_permissions
        ]
        nav_index = {entry[0]: entry for entry in nav_data}

        is_mobile = self._is_mobile
        is_tablet = self._form_factor == "tablet"
        C = theme_manager.palette(page=self.page)

        if not hasattr(self.controller, "_sidebar_state"):
            self.controller._sidebar_state = {
                "collapsed": {},
                "query": "",
                "last_route": self._current_route,
            }
        sidebar_state = self.controller._sidebar_state

        if is_mobile:
            mobile_items = [nav_index[k] for k in MOBILE_TOP_KEYS if k in nav_index]
            more_items = [e for e in nav_data if e[0] not in MOBILE_TOP_KEYS]
            self._sidebar_nav = build_sidebar_mobile(
                self, nav_data, mobile_items, more_items, C, nav_index,
            )
        else:
            sidebar_width = 200 if is_tablet else 240
            self._sidebar_nav = build_sidebar_desktop(
                self, nav_data, SECTIONS_DEF, nav_index, C, sidebar_state,
                width=sidebar_width,
            )

        self.main_view = ft.Container(
            expand=True,
            bgcolor=C["background"],
            animate_opacity=ft.Animation(duration=200, curve=ft.AnimationCurve.EASE_OUT),
            opacity=1,
        )

        if is_mobile:
            layout = ft.Column([self.main_view, self._sidebar_nav], spacing=0, expand=True)
        else:
            layout = ft.Row(
                [self._sidebar_nav, self.main_view],
                spacing=0, expand=True,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            )

        self.page.clean()
        self._ensure_file_pickers_in_overlay()
        self.page.add(layout)

        dest = getattr(self, "_current_route", "dashboard")
        valid_routes = {
            "dashboard", "products", "sales", "clients", "categories", "suppliers",
            "purchase_orders", "stock_alerts", "warehouses", "stock", "scanner",
            "export", "backups", "users", "settings", "warehouse_stock",
            "smtp_config", "messaging",
        }
        if dest not in valid_routes:
            dest = "dashboard"
            self._current_route = "dashboard"
        await self._navigate_to(dest)

    # ---- Navigation (delegates to nav_router) ----

    async def _navigate_to(self, route: str):
        from ui.views.nav_router import navigate_to

        # Fade-out current content
        if self.main_view and self.main_view.opacity > 0:
            self.main_view.opacity = 0
            self.page.update()
            await asyncio.sleep(0.12)

        await navigate_to(self, route)

        # Fade-in new content
        if self.main_view:
            self.main_view.opacity = 1
            self.page.update()

    async def _refresh_nav_badges(self):
        from ui.views.nav_router import refresh_nav_badges

        await refresh_nav_badges(self)

    def _refresh_nav_badges_sync(self) -> None:
        from ui.views.nav_router import refresh_nav_badges_sync

        refresh_nav_badges_sync(self)

    # ---- View delegates (1-liners) ----

    async def _show_dashboard(self):
        from ui.views.dashboard_view import show_dashboard
        await show_dashboard(self)

    async def _show_products_list(self):
        from ui.views.product_view import show_products_list
        await show_products_list(self)

    def _update_products_table(self):
        from ui.views.product_view import update_products_table
        update_products_table(self)

    async def _show_product_form(self, product=None):
        from ui.views.product_view import show_product_form
        await show_product_form(self, product)

    async def _confirm_delete_product(self, product):
        from ui.views.product_view import confirm_delete_product
        await confirm_delete_product(self, product)

    async def _handle_new_product(self, e):
        from ui.views.product_view import handle_new_product
        await handle_new_product(self, e)

    async def _show_stock_management(self):
        from ui.views.dialogs import show_stock_management
        await show_stock_management(self)

    async def _show_scanner(self):
        from ui.views.scanner_view import show_scanner
        await show_scanner(self)

    def _build_scanner_result(self, producto):
        from ui.views.scanner_view import build_scanner_result
        return build_scanner_result(self, producto)

    async def _show_export_options(self):
        from ui.views.dialogs import show_export_options
        await show_export_options(self)

    async def _show_purchase_orders(self):
        from ui.views.dialogs import show_purchase_orders
        await show_purchase_orders(self)

    async def _show_order_form(self):
        from ui.views.dialogs import show_order_form
        await show_order_form(self)

    # ---- Stock monitor (delegates to stock_alert_manager) ----

    async def _start_stock_monitor(self):
        await start_monitor(self)

    async def _stop_stock_monitor(self):
        await stop_monitor(self)

    async def _on_stock_alerts_changed(self, alertas):
        on_alerts_changed(self, alertas)

    # ---- Theme ----

    async def _on_theme_change(self, e):
        is_dark = e.control.value
        mode = "dark" if is_dark else "light"
        await self.controller.cambiar_tema(mode)
        theme_manager.apply(self.page, mode)
        SnackBarHelper.success(self.page, f"Tema cambiado a {'oscuro' if is_dark else 'claro'}")
        try:
            await self._refresh_nav_badges()
        except Exception as exc:
            logger.error("Error al refrescar nav badges (theme change): %s", exc)
            try:
                await self._navigate_to(self._current_route)
            except Exception as exc2:
                logger.error("Error al navegar en fallback: %s", exc2)
                self.page.update()

    async def _on_theme_choice_change(self, e):
        choice = e.control.value
        if choice not in ("light", "dark", "auto"):
            return
        await self.controller.cambiar_tema(choice)
        theme_manager.apply(self.page, choice)
        labels = {"light": "claro", "dark": "oscuro", "auto": "automático"}
        SnackBarHelper.success(self.page, f"Tema cambiado a {labels[choice]}")
        try:
            await self._refresh_nav_badges()
        except Exception as exc:
            logger.error("Error al refrescar nav badges (theme choice): %s", exc)
            try:
                await self._navigate_to(self._current_route)
            except Exception as exc2:
                logger.error("Error al navegar en fallback (theme choice): %s", exc2)
                self.page.update()

    # ---- Bulk operations (delegates to bulk_manager) ----

    async def _refresh_bulk_toolbar(self):
        await refresh_toolbar(self)

    async def _bulk_delete(self):
        await bulk_delete(self)

    async def _bulk_change_category(self):
        await bulk_change_category(self)

    async def _bulk_export(self):
        await bulk_export(self)

    # ---- Login alert banner (delegates to auth_manager) ----

    async def _show_login_alert_banner(self, alertas):
        await show_login_alert_banner(self, alertas)

    def _close_login_banner(self):
        close_login_banner(self)

    def _dismiss_login_banner(self):
        self._close_login_banner()

    # ---- Static utility ----

    @staticmethod
    def _find_submit_btn_static(page, label: str, translated_label: str = ""):
        from ui._utils import find_submit_btn

        return find_submit_btn(page, label, translated_label)
