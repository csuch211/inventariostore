"""
Professional Flet Application View
Comprehensive inventory management UI with authentication, dashboard, products management,
and export functionality using async/await patterns.
"""

import asyncio
import contextlib

import flet as ft

from config.settings import (
    APP_NAME,
    APP_VERSION,
    STOCK_LOW_DEFAULT,
    STOCK_MONITOR_INTERVAL_SECONDS,
    THEME_ACCENT_COLOR,
    THEME_ACCENT_LIGHT,
    THEME_BACKGROUND_COLOR,
    THEME_DANGER,
    THEME_DARK_ACCENT_COLOR,
    THEME_DARK_ACCENT_LIGHT,
    THEME_DARK_BACKGROUND_COLOR,
    THEME_DARK_CARD_COLOR,
    THEME_DARK_DIVIDER,
    THEME_DARK_FOCUS_RING,
    THEME_DARK_HOVER_TINT,
    THEME_DARK_INPUT_BORDER,
    THEME_DARK_INPUT_FILL,
    THEME_DARK_PRIMARY_COLOR,
    THEME_DARK_PRIMARY_LIGHT,
    THEME_DARK_PRIMARY_TINT,
    THEME_DARK_SHADOW,
    THEME_DARK_SIDEBAR_BG,
    THEME_DARK_SURFACE_COLOR,
    THEME_DARK_TABLE_HEADING,
    THEME_DARK_TABLE_ROW,
    THEME_DARK_TABLE_ROW_ALT,
    THEME_DARK_TEXT_MUTED,
    THEME_DARK_TEXT_PRIMARY,
    THEME_DARK_TEXT_SECONDARY,
    THEME_DIVIDER,
    THEME_HOVER_TINT,
    THEME_INPUT_BORDER,
    THEME_INPUT_FILL,
    THEME_PRIMARY_COLOR,
    THEME_PRIMARY_DARK,
    THEME_PRIMARY_LIGHT,
    THEME_PRIMARY_TINT,
    THEME_SHADOW,
    THEME_SIDEBAR_BG,
    THEME_SURFACE_COLOR,
    THEME_TABLE_HEADING,
    THEME_TABLE_ROW,
    THEME_TABLE_ROW_ALT,
    THEME_TEXT_MUTED,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    THEME_WARNING_COLOR,
)
from core.controller import InventarioController
from core.theme_manager import theme_manager
from services.permissions import Perm
from services.stock_monitor import StockMonitor
from ui.components import (
    FormField,
    LoadingSpinner,
    SnackBarHelper,
    bind_page,
)
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
    """Main application view with professional UI/UX"""

    MOBILE_BREAKPOINT = 600

    def __init__(self, page: ft.Page):
        """Initialize the application view"""
        self.page = page
        # Register this page with the components module so static helpers
        # (AppHeader, FormField, DataTable) can resolve theme colors.
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
        # FilePickers in Flet 0.85 do not accept a page= kwarg. The control
        # registers itself with the page automatically when it is added
        # to page.overlay and the page is updated for the first time. We
        # keep references on self and add them once in _setup_page().
        self._scanner_file_picker = None
        self._scanner_result_container = ft.Container()
        self._csv_import_picker = None
        self._stock_alert_count = 0
        self._selected_product_ids = set()
        self._bulk_toolbar_container = None
        self._bulk_toolbar = None
        self._theme_switch = None

        # Background stock monitor — started after login, stopped on logout.
        # Initialized lazily so the constructor doesn't require a running
        # event loop.
        self._stock_monitor = None

        self._setup_page()

    def _get_colors(self):
        if self.page.theme_mode == ft.ThemeMode.DARK:
            return dict(
                primary=THEME_DARK_PRIMARY_COLOR,
                primary_light=THEME_DARK_PRIMARY_LIGHT,
                primary_dark=THEME_DARK_PRIMARY_COLOR,
                accent=THEME_DARK_ACCENT_COLOR,
                accent_light=THEME_DARK_ACCENT_LIGHT,
                background=THEME_DARK_BACKGROUND_COLOR,
                surface=THEME_DARK_SURFACE_COLOR,
                card=THEME_DARK_CARD_COLOR,
                sidebar_bg=THEME_DARK_SIDEBAR_BG,
                primary_tint=THEME_DARK_PRIMARY_TINT,
                hover_tint=THEME_DARK_HOVER_TINT,
                text_primary=THEME_DARK_TEXT_PRIMARY,
                text_secondary=THEME_DARK_TEXT_SECONDARY,
                text_muted=THEME_DARK_TEXT_MUTED,
                text_on_input=THEME_DARK_TEXT_PRIMARY,
                input_fill=THEME_DARK_INPUT_FILL,
                input_border=THEME_DARK_INPUT_BORDER,
                focus_ring=THEME_DARK_FOCUS_RING,
                cursor=THEME_DARK_FOCUS_RING,
                selection="#1E3A5F",
                helper=THEME_DARK_TEXT_SECONDARY,
                table_heading=THEME_DARK_TABLE_HEADING,
                table_row=THEME_DARK_TABLE_ROW,
                table_row_alt=THEME_DARK_TABLE_ROW_ALT,
                divider=THEME_DARK_DIVIDER,
                shadow=THEME_DARK_SHADOW,
            )
        return dict(
            primary=THEME_PRIMARY_COLOR,
            primary_light=THEME_PRIMARY_LIGHT,
            primary_dark=THEME_PRIMARY_DARK,
            accent=THEME_ACCENT_COLOR,
            accent_light=THEME_ACCENT_LIGHT,
            background=THEME_BACKGROUND_COLOR,
            surface=THEME_SURFACE_COLOR,
            card=THEME_SURFACE_COLOR,
            sidebar_bg=THEME_SIDEBAR_BG,
            primary_tint=THEME_PRIMARY_TINT,
            hover_tint=THEME_HOVER_TINT,
            text_primary=THEME_TEXT_PRIMARY,
            text_secondary=THEME_TEXT_SECONDARY,
            text_muted=THEME_TEXT_MUTED,
            text_on_input="#0F172A",
            input_fill=THEME_INPUT_FILL,
            input_border=THEME_INPUT_BORDER,
            focus_ring=THEME_PRIMARY_COLOR,
            cursor=THEME_PRIMARY_COLOR,
            selection="#BFDBFE",
            helper=THEME_TEXT_SECONDARY,
            table_heading=THEME_TABLE_HEADING,
            table_row=THEME_TABLE_ROW,
            table_row_alt=THEME_TABLE_ROW_ALT,
            divider=THEME_DIVIDER,
            shadow=THEME_SHADOW,
        )

    def _is_mobile(self):
        return self.page.width < self.MOBILE_BREAKPOINT if self.page.width else False

    def _setup_page(self):
        """Configure page settings and theme"""
        self.page.title = APP_NAME
        self.page.theme_mode = ft.ThemeMode.LIGHT

        self.page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=THEME_PRIMARY_COLOR,
                primary_container=THEME_PRIMARY_LIGHT,
                secondary=THEME_ACCENT_COLOR,
                secondary_container=THEME_ACCENT_LIGHT,
                surface=THEME_SURFACE_COLOR,
                surface_tint=THEME_PRIMARY_LIGHT,
                on_surface=THEME_TEXT_PRIMARY,
                on_surface_variant=THEME_TEXT_SECONDARY,
            ),
        )
        self.page.dark_theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=THEME_DARK_PRIMARY_COLOR,
                primary_container=THEME_DARK_PRIMARY_LIGHT,
                secondary=THEME_DARK_ACCENT_COLOR,
                secondary_container=THEME_DARK_ACCENT_LIGHT,
                surface=THEME_DARK_SURFACE_COLOR,
                surface_tint=THEME_DARK_PRIMARY_LIGHT,
                on_surface=THEME_DARK_TEXT_PRIMARY,
                on_surface_variant=THEME_DARK_TEXT_SECONDARY,
            ),
        )
        self.page.padding = 0
        self.page.spacing = 0
        self.page.bgcolor = THEME_BACKGROUND_COLOR

        # FilePickers are registered lazily in show methods to avoid
        # "unknown control filepicker" error when the page is not yet
        # mounted on the client.

    def _ensure_file_pickers_in_overlay(self):
        """No-op: FilePicker is not available in this Flet build."""

    def _drain_dialogs(self):
        """Pop every queued dialog (alert, snackbar, etc.).

        page.clean() clears page.controls but leaves page._dialogs untouched,
        so any dialog opened earlier (typically SnackBars from a previous
        flow) would otherwise stay on top of the new view. Repeated login
        cycles without a real page reset would otherwise leave the "Sesión
        cerrada" snackbar from logout on top of the new login screen.
        """
        pop = getattr(self.page, "pop_dialog", None)
        if pop is None:
            return
        # Page.pop_dialog returns None (no exception) when no dialog is open,
        # so we must check the return value — otherwise the loop spins forever
        # and the UI thread blocks, leaving the user staring at an empty frame.
        for _ in range(64):  # safety cap so we never spin forever
            try:
                closed = pop()
            except Exception:
                return
            if closed is None:
                return

    def _create_search_field(self) -> ft.TextField:
        """Create a search field for products"""

        async def handle_search(e):
            """Handle search input"""
            query = e.control.value.strip().lower()
            if query:
                self.filtered_products = [
                    p
                    for p in self.all_products
                    if query in p.get("nombre", "").lower()
                    or query in p.get("codigo", "").lower()
                    or query in p.get("categoria", "").lower()
                ]
            else:
                self.filtered_products = self.all_products
            self.current_page = 0
            self._update_products_table()

        C = self._get_colors()
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
        """Display loading spinner"""
        self.main_view = LoadingSpinner.create()
        self.page.clean()
        self._ensure_file_pickers_in_overlay()
        self.page.add(self.main_view)

    async def start(self):
        """Start the application"""
        self.show_loading()
        await self._show_login_screen()

    # ============ Authentication ============

    async def _show_login_screen(self):
        """Display login screen with validation"""
        # Reset the active route so a stale value (e.g. "logout") does not
        # survive into the next login and cause _show_main_view to navigate
        # straight back to logout right after authentication.
        self._current_route = "dashboard"
        C = self._get_colors()
        username_field = FormField.create_text_field(
            label="Usuario",
            hint="Ingresa tu usuario",
            required=True,
        )
        error_text = ft.Text("", color=C["accent"], size=12)

        async def handle_login(e):
            """Handle login button click"""
            error_text.value = ""
            username = username_field.value.strip()
            password = password_field.value

            # Validation
            if not username:
                error_text.value = "El usuario es requerido"
                self.page.update()
                return

            if not password:
                error_text.value = "La contraseña es requerida"
                self.page.update()
                return

            if len(password) < 6:
                error_text.value = "La contraseña debe tener al menos 6 caracteres"
                self.page.update()
                return

            try:
                login_btn.disabled = True
                self.show_loading()

                # Perform async login
                session = await self.controller.login(username, password)
                logger.info(f"login flow: controller.login OK for {username}")
                self.current_user = username
                self.current_token = session.get("token")

                # Apply stored theme
                theme_mode = await self.controller.obtener_tema_usuario()
                logger.info(f"login flow: theme fetched ({theme_mode})")
                self.page.theme_mode = (
                    ft.ThemeMode.DARK if theme_mode == "dark" else ft.ThemeMode.LIGHT
                )
                C = self._get_colors()
                self.page.bgcolor = C["background"]

                SnackBarHelper.success(self.page, f"¡Bienvenido, {username}!")
                logger.info("login flow: entering _show_main_view")
                await self._show_main_view()
                logger.info("login flow: _show_main_view returned")

                # Boot the background stock monitor and run an immediate
                # check. If low-stock products exist, surface a dismissable
                # banner so the user sees them right after login.
                await self._start_stock_monitor()
                initial_alerts = await self.controller.obtener_alertas_stock()
                await self._show_login_alert_banner(initial_alerts)

            except Exception as ex:
                logger.exception(f"login flow: failure during post-login steps: {ex}")
                # Reset state on failure so the next attempt starts clean.
                self.current_user = None
                self.current_token = None
                SnackBarHelper.error(self.page, f"Error de login: {ex!s}")
                login_btn.disabled = False
                await self._show_login_screen()

        password_field = ft.TextField(
            label="Contraseña",
            password=True,
            can_reveal_password=True,
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
            hint_text="Ingresa tu contraseña",
            on_submit=handle_login,
        )

        login_btn = ft.Button(
            content=ft.Text("Ingresar"),
            width=300,
            height=50,
            on_click=handle_login,
            style=ft.ButtonStyle(
                color="white",
                bgcolor=C["primary"],
            ),
        )

        card_width = min(380, self.page.width * 0.85) if self.page.width else 340

        login_card = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.icons.Icons.INVENTORY_2, size=40, color=C["primary"]),
                                ft.Text(
                                    APP_NAME,
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=C["primary"],
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Text(
                                    f"v{APP_VERSION}",
                                    size=11,
                                    color=C["text_muted"],
                                    text_align=ft.TextAlign.CENTER,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=4,
                        ),
                        padding=ft.padding.Padding(left=0, right=0, top=0, bottom=10),
                    ),
                    ft.Divider(height=1, color=C["divider"]),
                    ft.Container(height=5),
                    username_field,
                    password_field,
                    error_text,
                    ft.Container(height=5),
                    login_btn,
                    ft.TextButton(
                        content=ft.Text(
                            "¿Olvidaste tu contraseña?",
                            color=C["primary"],
                            size=12,
                        ),
                        on_click=lambda e: asyncio.create_task(self._show_forgot_password()),
                    ),
                    ft.TextButton(
                        content=ft.Text(
                            "¿No tienes cuenta? Regístrate",
                            color=C["primary"],
                            size=12,
                        ),
                        on_click=lambda e: asyncio.create_task(self._show_register_form()),
                    ),
                ],
                spacing=12,
                width=card_width,
            ),
            bgcolor=C["surface"],
            padding=30,
            border_radius=16,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=C["shadow"]),
        )

        login_container = ft.Container(
            content=ft.Column(
                [
                    ft.Container(expand=True),
                    login_card,
                    ft.Container(expand=True),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            bgcolor=C["background"],
        )

        self.page.clean()
        # Drain any dialogs still queued from the previous session (e.g. the
        # "Sesión cerrada" snackbar shown by _logout). SnackBar in Flet 0.85
        # is a DialogControl shown via page.show_dialog(); page.clean() does
        # not touch the dialog stack, so leftover dialogs would otherwise
        # accumulate and could swallow subsequent input.
        self._drain_dialogs()
        self._ensure_file_pickers_in_overlay()
        self.page.add(login_container)
        logger.info("login screen rendered")

    async def _show_register_form(self):
        """Display user registration form."""
        from ui.register_view import show_register_form

        await show_register_form(self)

    async def _show_forgot_password(self):
        """Display forgot password form."""
        from ui.forgot_password_view import show_forgot_password

        await show_forgot_password(self)

    # ============ Main View ============

    async def _show_main_view(self):
        """Display main application view with responsive layout"""
        # Seed initial categories on first run, then refresh the in-memory
        # list so the dashboard and product form pick them up.
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

        # Compute initial stock-alert count for sidebar badge.
        try:
            self._stock_alert_count = await self.controller.contar_alertas_stock()
        except Exception:
            self._stock_alert_count = 0

        # Build nav_data_all with stock alert badge.
        nav_data_all = list(NAV_DATA_ALL)
        # Patch stock_alerts entry with actual count (NAV_DATA_ALL has None).
        nav_data_all = [
            (
                route,
                icon,
                label,
                self._stock_alert_count
                if route == "stock_alerts" and self._stock_alert_count
                else badge,
            )
            for route, icon, label, badge in nav_data_all
        ]

        # Filter nav_data by permissions: hide entries the user lacks
        nav_data = [
            entry
            for entry in nav_data_all
            if ROUTE_PERMISSIONS.get(entry[0]) is None
            or ROUTE_PERMISSIONS[entry[0]] in self.controller.current_user_permissions
        ]
        nav_index = {entry[0]: entry for entry in nav_data}

        is_mobile = self._is_mobile()
        C = self._get_colors()

        # Persistence helpers — survive navigation rebuilds via the
        # controller instance.
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
                self,
                nav_data,
                mobile_items,
                more_items,
                C,
                nav_index,
            )
        else:
            self._sidebar_nav = build_sidebar_desktop(
                self,
                nav_data,
                SECTIONS_DEF,
                nav_index,
                C,
                sidebar_state,
            )

        self.main_view = ft.Container(expand=True, bgcolor=C["background"])

        if is_mobile:
            layout = ft.Column(
                [self.main_view, self._sidebar_nav],
                spacing=0,
                expand=True,
            )
        else:
            layout = ft.Row(
                [self._sidebar_nav, self.main_view],
                spacing=0,
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            )

        self.page.clean()
        self._ensure_file_pickers_in_overlay()
        self.page.add(layout)
        dest = getattr(self, "_current_route", "dashboard")
        # Guard against an out-of-band "_current_route" (e.g. "logout" left
        # over from a prior session) that would otherwise route us back into
        # the auth flow right after login.
        if dest not in {
            "dashboard",
            "products",
            "sales",
            "clients",
            "categories",
            "suppliers",
            "purchase_orders",
            "stock_alerts",
            "warehouses",
            "stock",
            "scanner",
            "export",
            "backups",
            "users",
            "settings",
            "warehouse_stock",
        }:
            dest = "dashboard"
            self._current_route = "dashboard"
        await self._navigate_to(dest)

    async def _refresh_nav_badges(self):
        """Refresh sidebar badges (e.g. stock alerts). Re-renders the main view."""
        from ui.views.nav_router import refresh_nav_badges

        await refresh_nav_badges(self)

    # ============ Navigation ============

    async def _navigate_to(self, route: str):
        """Navigate to different sections"""
        from ui.views.nav_router import navigate_to

        await navigate_to(self, route)

    def _refresh_nav_badges_sync(self) -> None:
        """Update the sidebar stock-alert badge without rebuilding the page.

        Cheaper than calling ``_refresh_nav_badges()`` (which re-renders the
        whole main view) when we only need to bump a counter.
        """
        from ui.views.nav_router import refresh_nav_badges_sync

        refresh_nav_badges_sync(self)

    # ============ Dashboard ============

    async def _show_dashboard(self):
        """Display the unified inventory home/dashboard."""
        from ui.views.dashboard_view import show_dashboard

        await show_dashboard(self)

    # ============ Products Management ============

    async def _show_products_list(self):
        """Display products list with search and pagination"""
        from ui.views.product_view import show_products_list

        await show_products_list(self)

    def _update_products_table(self):
        """Update the products table based on current filters and pagination"""
        from ui.views.product_view import update_products_table

        update_products_table(self)

    async def _show_product_form(self, product: dict | None = None):
        """Display form for adding/editing products"""
        from ui.views.product_view import show_product_form

        await show_product_form(self, product)

    async def _confirm_delete_product(self, product: dict):
        """Show confirmation dialog before deleting product"""
        from ui.views.product_view import confirm_delete_product

        await confirm_delete_product(self, product)

    # ============ Products Actions ============

    async def _handle_new_product(self, e):
        """Handle new product button click"""
        from ui.views.product_view import handle_new_product

        await handle_new_product(self, e)

    # ============ Stock Management ============

    async def _show_stock_management(self):
        """Display stock management interface"""
        from ui.views.dialogs import show_stock_management

        await show_stock_management(self)

    # ============ Scanner ============

    async def _show_scanner(self):
        """Display barcode/QR scanner view"""
        from ui.views.scanner_view import show_scanner

        await show_scanner(self)

    def _build_scanner_result(self, producto: dict) -> ft.Container:
        """Build product result card for scanner view"""
        from ui.views.scanner_view import build_scanner_result

        return build_scanner_result(self, producto)

    # ============ Export Options ============

    async def _show_export_options(self):
        """Display export options"""
        from ui.views.dialogs import show_export_options

        await show_export_options(self)

    # ============ Purchase Orders ============

    async def _show_purchase_orders(self):
        """Display purchase orders view."""
        from ui.views.dialogs import show_purchase_orders

        await show_purchase_orders(self)

    async def _show_order_form(self):
        """Show new purchase order form."""
        from ui.views.dialogs import show_order_form

        await show_order_form(self)

    # ============ Stock Alerts ============

    async def _start_stock_monitor(self) -> None:
        """Boot the background stock monitor and run an immediate check.

        Called from `handle_login` after a successful login. Starts the
        polling task and fires the alert callback if low-stock products
        exist — so the user sees the SnackBar immediately, without waiting
        for the first tick of the interval.
        """
        if self._stock_monitor is None:
            self._stock_monitor = StockMonitor(
                db=self.controller.db,
                callback=self._on_stock_alerts_changed,
                interval_seconds=STOCK_MONITOR_INTERVAL_SECONDS,
                low_threshold=STOCK_LOW_DEFAULT,
            )
        await self._stock_monitor.start()
        # First check has already fired the callback in start(); if the
        # callback suppressed the SnackBar (e.g. user dismissed it), this
        # is a no-op.

    async def _stop_stock_monitor(self) -> None:
        """Cancel the background monitor on logout / app close."""
        if self._stock_monitor and self._stock_monitor.is_running:
            await self._stock_monitor.stop()
        self._stock_monitor = None

    async def _on_stock_alerts_changed(self, alertas: list[dict]) -> None:
        """Handle a new snapshot of low-stock products.

        - Refreshes the sidebar badge so the user sees fresh counts even
          if they're not on the alerts view.
        - Shows an in-app SnackBar/Banner when the alert is non-empty.
          The SnackBar is suppressed on the initial check right after
          login (the dedicated `_show_login_alert_banner` handles that
          with a richer, dismissable banner instead).
        """
        try:
            criticas = sum(1 for a in alertas if a.get("alert_level") == "critical")
            bajas = sum(1 for a in alertas if a.get("alert_level") == "low")
            self._stock_alert_count = len(alertas)
            # Update the sidebar badge live (only if the main view exists).
            if self._sidebar_nav is not None:
                self._refresh_nav_badges_sync()
            if alertas:
                msg = t(
                    "stock_alerts.snapshot_toast",
                    criticals=criticas,
                    lows=bajas,
                    total=len(alertas),
                )
                if criticas > 0:
                    SnackBarHelper.error(self.page, msg)
                else:
                    # No `warning` helper exists — fall back to info and tint
                    # amber so the urgency is still clear.
                    SnackBarHelper._show(
                        self.page,
                        ft.SnackBar(
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.Icons.WARNING_AMBER, color="white"),
                                    ft.Text(msg, color="white"),
                                ],
                                spacing=10,
                            ),
                            bgcolor=THEME_WARNING_COLOR,
                        ),
                    )
        except Exception as e:
            logger.exception(f"stock alert callback failed: {e}")

    # ============ Theme ============

    async def _on_theme_change(self, e):
        """Persist the user's theme choice and repaint the active view.

        Critical: a full main-view rebuild is required here, not just
        ``page.update()`` or ``_navigate_to()``. Many components bake
        the resolved palette into widget properties at construction
        time (sidebar items, settings tiles, dialogs, tables), so
        flipping ``page.theme_mode`` alone leaves stale colors on
        screen until something else triggers a rebuild — which is
        why the user observed "the theme only changes when I switch
        language".

        ``_refresh_nav_badges()`` does exactly what we need: it
        re-counts alerts and re-runs ``_show_main_view()``, which
        rebuilds the sidebar and the current route's body with the
        new palette.
        """
        is_dark = e.control.value
        mode = "dark" if is_dark else "light"
        await self.controller.cambiar_tema(mode)
        # Apply via ThemeManager so page.theme / page.dark_theme are
        # kept in sync (Material 3 color scheme tokens).
        theme_manager.apply(self.page, mode)
        SnackBarHelper.success(self.page, f"Tema cambiado a {'oscuro' if is_dark else 'claro'}")
        # Full rebuild of the main view + sidebar so every component
        # picks up the new palette. Without this the user has to
        # change language to force a rebuild — the symptom we're fixing.
        try:
            await self._refresh_nav_badges()
        except Exception:
            # Fallback: navigate to the current route to rebuild the body.
            try:
                await self._navigate_to(self._current_route)
            except Exception:
                self.page.update()

    async def _on_theme_choice_change(self, e):
        """Handle change for the segmented theme picker (light/dark/auto).

        ``e.control.value`` is one of ``"light" | "dark" | "auto"``.

        See ``_on_theme_change`` for why we call ``_refresh_nav_badges``
        instead of just ``_navigate_to`` — many components cache the
        palette at construction time and need a full rebuild.
        """
        choice = e.control.value
        if choice not in ("light", "dark", "auto"):
            return
        await self.controller.cambiar_tema(choice)
        theme_manager.apply(self.page, choice)
        labels = {"light": "claro", "dark": "oscuro", "auto": "automático"}
        SnackBarHelper.success(self.page, f"Tema cambiado a {labels[choice]}")
        try:
            await self._refresh_nav_badges()
        except Exception:
            try:
                await self._navigate_to(self._current_route)
            except Exception:
                self.page.update()

    # ============ Bulk Operations (F2.2) ============

    async def _refresh_bulk_toolbar(self):
        """Refresh just the bulk toolbar without rebuilding the entire table"""
        if not self._bulk_toolbar_container:
            return
        try:
            sel_count = len(self._selected_product_ids)
            new_content = ft.Row(
                [
                    ft.Text(
                        t("bulk.select_products", count=sel_count),
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Button(
                        content=ft.Text(
                            t("bulk.delete_btn", default="").replace(
                                "{count}", str(max(sel_count, 1))
                            )
                            or "Eliminar"
                        ),
                        on_click=lambda e: asyncio.create_task(self._bulk_delete()),
                        style=ft.ButtonStyle(bgcolor=THEME_ACCENT_COLOR, color="white"),
                    )
                    if self.controller.has_permission(Perm.BULK_ELIMINAR)
                    else ft.Container(),
                    ft.OutlinedButton(
                        content=ft.Text(t("bulk.category_btn")),
                        on_click=lambda e: asyncio.create_task(self._bulk_change_category()),
                    ),
                    ft.OutlinedButton(
                        content=ft.Text(t("bulk.export_btn")),
                        on_click=lambda e: asyncio.create_task(self._bulk_export()),
                    ),
                ],
                spacing=8,
                wrap=True,
            )
            self._bulk_toolbar_container.content = new_content
            self._bulk_toolbar_container.visible = bool(sel_count)
            self.page.update()
        except Exception as e:
            SnackBarHelper.error(self.page, f"Error actualizando toolbar: {e!s}")

    async def _bulk_delete(self):
        ids = list(self._selected_product_ids)
        if not ids:
            SnackBarHelper.info(self.page, t("bulk.no_selection"))
            return

        def confirm(e):
            self.page.pop_dialog()
            asyncio.create_task(self._do_bulk_delete(ids))

        dialog = ft.AlertDialog(
            title=ft.Text(t("common.delete")),
            content=ft.Text(t("bulk.delete_confirm", count=len(ids))),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.TextButton(t("common.delete"), on_click=confirm),
            ],
        )
        dialog.open = True
        self.page.show_dialog(dialog)
        self.page.update()

    async def _do_bulk_delete(self, ids):
        ok, count = await self.controller.bulk_eliminar_productos(ids)
        if ok:
            self._selected_product_ids.clear()
            SnackBarHelper.success(self.page, t("bulk.delete_success", count=count))
            await self._show_products_list()
        else:
            SnackBarHelper.error(self.page, t("common.error"))

    async def _bulk_change_category(self):
        ids = list(self._selected_product_ids)
        if not ids:
            SnackBarHelper.info(self.page, t("bulk.no_selection"))
            return
        categorias = await self.controller.obtener_categorias()
        cat_options = (
            [c["nombre"] for c in categorias]
            if categorias
            else ["Electrónica", "Ropa", "Alimentos", "Otros"]
        )
        dd = ft.Dropdown(
            label=t("bulk.category_placeholder"),
            options=[ft.dropdown.Option(c) for c in cat_options],
            width=250,
        )

        async def save(e):
            if not dd.value:
                SnackBarHelper.error(self.page, t("common.validation_error"))
                return
            ok, count = await self.controller.bulk_actualizar_categoria(ids, dd.value)
            self.page.pop_dialog()
            if ok:
                self._selected_product_ids.clear()
                SnackBarHelper.success(
                    self.page, t("bulk.category_success", count=count, cat=dd.value)
                )
                await self._show_products_list()
            else:
                SnackBarHelper.error(self.page, t("common.error"))

        dialog = ft.AlertDialog(
            title=ft.Text(t("bulk.category_btn")),
            content=ft.Column(
                [ft.Text(t("bulk.select_products", count=len(ids))), dd], tight=True, spacing=10
            ),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        self.page.show_dialog(dialog)
        self.page.update()

    async def _bulk_export(self):
        ids = list(self._selected_product_ids)
        if not ids:
            SnackBarHelper.info(self.page, t("bulk.no_selection"))
            return
        fmt = ft.Dropdown(
            label=t("bulk.export_format"),
            options=[
                ft.dropdown.Option("csv", "CSV"),
                ft.dropdown.Option("json", "JSON"),
                ft.dropdown.Option("xlsx", "Excel"),
            ],
            value="csv",
            width=200,
        )

        async def do_export(e):
            self.page.pop_dialog()
            ok, result = await self.controller.bulk_exportar_productos(ids, fmt.value)
            if ok:
                self._selected_product_ids.clear()
                SnackBarHelper.success(self.page, t("bulk.export_success", path=result))
            else:
                SnackBarHelper.error(self.page, result)
            await self._refresh_bulk_toolbar()

        dialog = ft.AlertDialog(
            title=ft.Text(t("bulk.export_btn")),
            content=ft.Column(
                [ft.Text(t("bulk.select_products", count=len(ids))), fmt], tight=True, spacing=10
            ),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=do_export),
            ],
        )
        dialog.open = True
        self.page.show_dialog(dialog)
        self.page.update()

    # ============ Login Alert Banner ============

    async def _show_login_alert_banner(self, alertas: list[dict]) -> None:
        """Show a dismissable banner at the top of the page after login.

        Earlier revisions prepended a banner to ``main_view.content`` so it
        sat above the active screen — but every time the page rebuilt
        (route change, monitor poll, theme switch) the banner was
        re-prepended, producing stacked duplicates with overlapping
        "Ver"/"Cerrar" buttons.

        The fix: keep the banner as a **top-level page overlay** (the same
        place SnackBars live) and only show it once per login. The
        Flet ``Banner`` control gives us a native dismissable surface that
        does not collide with route rebuilds, and we replace any previous
        instance before showing so re-logins don't stack.
        """
        if not alertas:
            return
        criticas = sum(1 for a in alertas if a.get("alert_level") == "critical")
        bajas = sum(1 for a in alertas if a.get("alert_level") == "low")
        color = THEME_DANGER if criticas > 0 else THEME_WARNING_COLOR
        banner_text = t(
            "stock_alerts.login_banner",
            criticals=criticas,
            lows=bajas,
            total=len(alertas),
        )
        icon = ft.icons.Icons.ERROR if criticas > 0 else ft.icons.Icons.WARNING_AMBER

        async def _view_alerts(_e):
            try:
                await self._navigate_to("stock_alerts")
            finally:
                self._close_login_banner()

        def _dismiss(_e):
            self._close_login_banner()

        # If a banner is already on screen from a previous login, remove
        # it before opening the new one. This guarantees one banner at a
        # time regardless of how many times we call this method.
        self._close_login_banner()

        actions = [
            ft.TextButton(t("stock_alerts.view"), on_click=_view_alerts),
            ft.TextButton(t("common.close"), on_click=_dismiss),
        ]
        banner = ft.Banner(
            bgcolor=color,
            leading=ft.Icon(icon, color="white", size=28),
            content=ft.Text(banner_text, color="white", size=14),
            actions=actions,
        )
        self._login_alert_banner = banner
        # Banner uses page.show_dialog because it is a DialogControl.
        self.page.show_dialog(banner)
        self.page.update()

    def _close_login_banner(self) -> None:
        """Remove the login alert banner if one is on screen."""
        banner = getattr(self, "_login_alert_banner", None)
        if banner is None:
            return
        with contextlib.suppress(Exception):
            self.page.pop_dialog()
        # Reset the reference so a future login can attach a fresh banner
        # without "already-shown" suppression.
        self._login_alert_banner = None

    def _dismiss_login_banner(self) -> None:
        """Backward-compat alias for the old dismiss API."""
        self._close_login_banner()

    @staticmethod
    def _find_submit_btn_static(page, label: str, translated_label: str = ""):
        """Walk the live page tree and return the first ft.Button whose
        visible text matches ``label`` (or ``translated_label``).

        Used by the focus chains built in ``_show_stock_management`` and
        ``_show_new_sale`` to land on the submit button without forcing
        the surrounding ``ft.Column`` literal to be split into named
        temporaries. Returns ``None`` if no match is found.

        The Button's ``content`` is often a ``ft.Row`` of (Icon, Text),
        so we descend into ``Row``/``Column`` content and match against
        any descendant ``ft.Text`` whose ``value`` matches.
        """
        if not page:
            return None
        candidates = {label}
        if translated_label:
            candidates.add(translated_label)
        try:
            stack = [page]
            while stack:
                node = stack.pop()
                if isinstance(node, ft.Button):
                    # Direct text content (e.g. ``content=ft.Text(...)``).
                    content = getattr(node, "content", None)
                    txt = getattr(content, "value", None) or getattr(content, "text", None)
                    if isinstance(txt, str) and txt.strip() in candidates:
                        return node
                    # Composite content (e.g. ``content=ft.Row([Icon, Text])``).
                    sub = [content]
                    sub.extend(getattr(content, "controls", None) or [])
                    for item in sub:
                        if isinstance(item, ft.Text):
                            v = getattr(item, "value", None)
                            if isinstance(v, str) and v.strip() in candidates:
                                return node
                inner = getattr(node, "content", None)
                if inner is not None and inner is not node:
                    stack.append(inner)
                for c in getattr(node, "controls", None) or []:
                    if c is not node:
                        stack.append(c)
        except Exception:
            return None
        return None

    # ============ Logout ============

    async def _logout(self):
        """Logout and return to login screen"""
        logger.info("logout: starting")
        # Reset the active route BEFORE clearing the user — otherwise
        # _show_main_view() after re-login would call _navigate_to("logout")
        # and log us out again immediately.
        self._current_route = "dashboard"
        try:
            if self.current_token:
                await self.controller.logout(self.current_token)
        except Exception as logout_err:
            logger.exception(f"logout: backend logout failed: {logout_err}")
        finally:
            self.current_user = None
            self.current_token = None
            self.controller.current_user = None
            self.controller.current_user_role = None
            self.controller.current_user_permissions = set()
        # Cancel the background stock monitor so the polling task doesn't
        # outlive the session.
        with contextlib.suppress(Exception):
            await self._stop_stock_monitor()
        # Clear any dialogs left over from the main view
        self._drain_dialogs()
        # Clean the page completely to remove the "Sesión cerrada" snackbar
        # and any other UI elements before showing the login screen
        self.page.clean()
        self._ensure_file_pickers_in_overlay()
        try:
            await self._show_login_screen()
        except Exception as e:
            logger.exception(f"logout: failed to show login screen: {e}")
            SnackBarHelper.error(self.page, f"Error al cerrar sesión: {e!s}")
