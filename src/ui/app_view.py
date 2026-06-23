"""
Professional Flet Application View
Comprehensive inventory management UI with authentication, dashboard, products management,
and export functionality using async/await patterns.
"""

import asyncio
import contextlib
from typing import Any

import flet as ft

from config.settings import (
    APP_NAME,
    APP_VERSION,
    ITEMS_PER_PAGE,
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
    THEME_SUCCESS_COLOR,
    THEME_SUCCESS_LIGHT,
    THEME_SURFACE_COLOR,
    THEME_TABLE_HEADING,
    THEME_TABLE_ROW,
    THEME_TABLE_ROW_ALT,
    THEME_TEXT_MUTED,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    THEME_WARNING_COLOR,
    THEME_WARNING_LIGHT,
)
from core.controller import InventarioController
from core.theme_manager import theme_manager
from services.permissions import Perm
from services.stock_monitor import StockMonitor
from ui import admin_views, entity_views, sales_views, stock_views
from ui import phase1_views as p1
from ui import phase3_views as p3
from ui.charts import BarChart as TopProductosChart
from ui.charts import LineChart as ValorInventarioChart
from ui.charts import PieChart as DistribucionChart
from ui.components import (
    AppHeader,
    DialogHelper,
    FormField,
    LangSwitcher,
    LoadingSpinner,
    SidebarItem,
    SidebarSearch,
    SidebarSection,
    SidebarUserCard,
    SnackBarHelper,
    bind_page,
)
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


# Map of sidebar route -> permission key required to see that entry.
# Routes with value None are always visible (e.g. dashboard, settings, logout).
ROUTE_PERMISSIONS = {
    "dashboard": None,
    "products": None,
    "sales": Perm.VENTAS_LEER,
    "clients": Perm.CLIENTES_LEER,
    "categories": Perm.CATEGORIAS_LEER,
    "suppliers": Perm.PROVEEDORES_LEER,
    "purchase_orders": Perm.ORDENES_LEER,
    "warehouses": Perm.ALMACENES_LEER,
    "warehouse_stock": Perm.ALMACENES_STOCK,
    "stock_alerts": Perm.STOCK_ALERTAS_VER,
    "stock": Perm.STOCK_LEER,
    "scanner": None,
    "export": Perm.EXPORTAR,
    "backups": Perm.BACKUPS_CREAR,
    "users": Perm.USUARIOS_LEER,
    "settings": None,
    "logout": None,
    # Fase 1 routes
    "p1_devoluciones": Perm.DEVOLUCIONES_LEER,
    "p1_transferencias": Perm.TRANSFERENCIAS_LEER,
    "p1_conteos": Perm.CONTEOS_LEER,
    "p1_lotes": Perm.LOTES_LEER,
    "p1_precios": Perm.PRECIOS_LEER,
    "p1_impuestos": Perm.IMPUESTOS_LEER,
    "p1_caja": Perm.CAJA_LEER,
    "p1_busqueda": Perm.PRODUCTOS_LEER,
    "p1_reabasto": Perm.ORDENES_LEER,
    # Fase 3 routes
    "p3_variantes": Perm.VARIANTES_LEER,
    "p3_reportes": Perm.REPORTES_EJECUTAR,
    "p3_push": Perm.PUSH_ENVIAR,
    "p3_image_search": Perm.IMAGE_SEARCH,
}


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

        nav_data_all = [
            ("dashboard", ft.icons.Icons.DASHBOARD, t("nav.dashboard"), None),
            ("products", ft.icons.Icons.INVENTORY_2_OUTLINED, t("nav.products"), None),
            ("sales", ft.icons.Icons.POINT_OF_SALE, t("nav.sales"), None),
            ("clients", ft.icons.Icons.PERSON_OUTLINE, t("nav.clients"), None),
            ("categories", ft.icons.Icons.CATEGORY_OUTLINED, t("nav.categories"), None),
            ("suppliers", ft.icons.Icons.LOCAL_SHIPPING_OUTLINED, t("nav.suppliers"), None),
            (
                "purchase_orders",
                ft.icons.Icons.SHOPPING_CART_OUTLINED,
                t("nav.purchase_orders"),
                None,
            ),
            (
                "stock_alerts",
                ft.icons.Icons.NOTIFICATIONS_ACTIVE_OUTLINED,
                t("nav.stock_alerts"),
                self._stock_alert_count if self._stock_alert_count else None,
            ),
            ("warehouses", ft.icons.Icons.WAREHOUSE, t("nav.warehouses"), None),
            ("stock", ft.icons.Icons.INVENTORY_OUTLINED, t("nav.stock"), None),
            ("scanner", ft.icons.Icons.QR_CODE_SCANNER, "Escáner", None),
            ("export", ft.icons.Icons.FILE_DOWNLOAD_OUTLINED, t("nav.export"), None),
            ("backups", ft.icons.Icons.BACKUP, t("nav.backups"), None),
            ("users", ft.icons.Icons.ADMIN_PANEL_SETTINGS, t("nav.users"), None),
            ("settings", ft.icons.Icons.SETTINGS_OUTLINED, t("nav.settings"), None),
            ("logout", ft.icons.Icons.LOGOUT, t("nav.logout"), None),
            # Fase 1
            ("p1_devoluciones", ft.icons.Icons.UNDO, t("phase1.devoluciones.title"), None),
            (
                "p1_transferencias",
                ft.icons.Icons.SWAP_HORIZ,
                t("phase1.transferencias.title"),
                None,
            ),
            ("p1_conteos", ft.icons.Icons.FACT_CHECK_OUTLINED, t("phase1.conteos.title"), None),
            ("p1_lotes", ft.icons.Icons.LAYERS_OUTLINED, t("phase1.lotes.title"), None),
            ("p1_precios", ft.icons.Icons.PRICE_CHANGE, t("phase1.precios.title"), None),
            (
                "p1_impuestos",
                ft.icons.Icons.RECEIPT_LONG_OUTLINED,
                t("phase1.impuestos.title"),
                None,
            ),
            ("p1_caja", ft.icons.Icons.PAYMENTS, t("phase1.caja.title"), None),
            ("p1_busqueda", ft.icons.Icons.SEARCH, t("phase1.busqueda.title"), None),
            ("p1_reabasto", ft.icons.Icons.AUTORENEW, t("phase1.reabasto.title"), None),
            # Fase 3
            ("p3_variantes", ft.icons.Icons.STYLE_OUTLINED, t("phase3.variantes.title"), None),
            ("p3_reportes", ft.icons.Icons.ASSESSMENT_OUTLINED, t("phase3.reportes.title"), None),
            ("p3_push", ft.icons.Icons.NOTIFICATIONS_ACTIVE, t("phase3.push.title"), None),
            ("p3_image_search", ft.icons.Icons.IMAGE_SEARCH, t("phase3.image_search.title"), None),
        ]
        # Filter nav_data by permissions: hide entries the user lacks
        nav_data = [
            entry
            for entry in nav_data_all
            if ROUTE_PERMISSIONS.get(entry[0]) is None
            or ROUTE_PERMISSIONS[entry[0]] in self.controller.current_user_permissions
        ]
        nav_routes = [d[0] for d in nav_data]

        # Group items into named, collapsible sections. The taxonomy follows
        # the pattern used by Linear / Notion / GitHub: small sections that
        # match how the user thinks about their work, not the database
        # schema.
        sections_def = [
            ("sidebar.section.main", ["dashboard"]),
            (
                "sidebar.section.operations",
                [
                    "sales",
                    "stock_alerts",
                    "stock",
                    "warehouses",
                    "scanner",
                    "purchase_orders",
                ],
            ),
            (
                "sidebar.section.catalog",
                [
                    "products",
                    "categories",
                    "suppliers",
                    "clients",
                    "p1_devoluciones",
                    "p1_transferencias",
                    "p1_conteos",
                    "p1_lotes",
                    "p1_precios",
                    "p1_impuestos",
                    "p1_caja",
                    "p1_reabasto",
                    "p1_busqueda",
                ],
            ),
            (
                "sidebar.section.insights",
                [
                    "p3_variantes",
                    "p3_reportes",
                    "p3_push",
                    "p3_image_search",
                ],
            ),
            (
                "sidebar.section.admin",
                [
                    "export",
                    "backups",
                    "users",
                    "settings",
                    "logout",
                ],
            ),
        ]

        nav_index = {entry[0]: entry for entry in nav_data}

        async def handle_nav_change(e):
            idx = e.control.selected_index
            if idx is not None and 0 <= idx < len(nav_routes):
                await self._navigate_to(nav_routes[idx])

        is_mobile = self._is_mobile()

        C = self._get_colors()
        divider_color = C["divider"]
        text_secondary = C["text_secondary"]
        C["text_muted"]

        # Persistence helpers — survive navigation rebuilds via the
        # controller instance.
        if not hasattr(self.controller, "_sidebar_state"):
            self.controller._sidebar_state = {
                "collapsed": {},  # section_key -> bool
                "query": "",  # current search query
                "last_route": self._current_route,
            }
        sidebar_state = self.controller._sidebar_state

        if is_mobile:
            # On mobile, NavigationBar shows the top 5 most-used destinations.
            # The remaining ones are accessible via a "Más" overflow sheet.
            MOBILE_TOP_KEYS = [
                "dashboard",
                "products",
                "sales",
                "stock_alerts",
                "stock",
                "categories",
            ]
            mobile_items = [nav_index[k] for k in MOBILE_TOP_KEYS if k in nav_index]
            more_items = [e for e in nav_data if e[0] not in MOBILE_TOP_KEYS]

            async def _open_more_sheet(_e):
                rows = []
                for route, icon, label, badge in more_items:

                    async def _go(e, r=route):
                        self._sidebar_more_sheet.open = False
                        self.page.update()
                        await self._navigate_to(r)

                    rows.append(
                        ft.ListTile(
                            leading=ft.Icon(icon),
                            title=ft.Text(label),
                            trailing=(
                                ft.Container(
                                    content=ft.Text(
                                        str(badge),
                                        size=10,
                                        color="white",
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    bgcolor=C["accent"],
                                    padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                                    border_radius=10,
                                )
                                if badge
                                else None
                            ),
                            on_click=_go,
                        )
                    )
                self._sidebar_more_sheet = ft.BottomSheet(
                    content=ft.Container(
                        content=ft.Column(rows, tight=True, scroll=ft.ScrollMode.AUTO),
                        padding=10,
                    ),
                )
                self.page.overlay.append(self._sidebar_more_sheet)
                self._sidebar_more_sheet.open = True
                self.page.update()

            nav_items = []
            for route, icon, label, _badge in mobile_items:
                nav_items.append(ft.NavigationBarDestination(icon=icon, label=label))
            nav_items.append(
                ft.NavigationBarDestination(
                    icon=ft.icons.Icons.MORE_HORIZ,
                    label="Más",
                )
            )
            self._sidebar_nav = ft.NavigationBar(
                destinations=nav_items,
                on_change=lambda e: (
                    asyncio.create_task(_navigate_mobile(e))
                    if (e.control.selected_index or 0) < len(mobile_items)
                    else asyncio.create_task(_open_more_sheet(None))
                ),
                bgcolor=C["surface"],
                border=ft.border.Border(top=ft.BorderSide(1, divider_color)),
            )

            async def _navigate_mobile(e):
                idx = e.control.selected_index
                if idx is not None and 0 <= idx < len(mobile_items):
                    await self._navigate_to(mobile_items[idx][0])
        else:
            # Build the sectioned sidebar.
            ls = LangSwitcher.create(
                on_change=lambda lang: asyncio.create_task(self._refresh_nav_badges()),
                controller=self.controller,
                bg_color=C["surface"],
                text_color=text_secondary,
            )

            # All SidebarItem instances grouped by section, keyed by route
            # so the search filter can address them.
            items_by_route: dict[str, SidebarItem] = {}

            def _make_item(route: str, icon: Any, label: str, badge) -> SidebarItem:
                si = SidebarItem(
                    route=route,
                    icon=icon,
                    label=label,
                    colors=C,
                    is_active=(route == self._current_route),
                    badge=badge,
                    on_click=lambda r=route: asyncio.create_task(self._navigate_to(r)),
                )
                items_by_route[route] = si
                return si

            # Build section controls.
            section_controls: list[ft.Control] = []
            for section_key, route_keys in sections_def:
                items = []
                for rk in route_keys:
                    if rk not in nav_index:
                        continue
                    entry = nav_index[rk]
                    items.append(_make_item(*entry))
                if not items:
                    continue

                sec = SidebarSection(
                    title=t(section_key),
                    items=items,
                    colors=C,
                    collapsed=sidebar_state["collapsed"].get(section_key, False),
                    on_toggle=lambda collapsed, sk=section_key: sidebar_state[
                        "collapsed"
                    ].__setitem__(sk, collapsed),
                )
                section_controls.append(sec.control)

            # Search/quick-switcher filters items across all sections.
            def _apply_filter(query: str) -> None:
                sidebar_state["query"] = query
                q = (query or "").strip().lower()
                for rk, si in items_by_route.items():
                    visible = (not q) or (q in si.label.lower())
                    si.control.visible = visible
                self.page.update()

            def _jump_to_first_match() -> None:
                q = sidebar_state.get("query", "").strip().lower()
                if not q:
                    return
                for entry in nav_data:
                    route, _icon, label, _badge = entry
                    if q in label.lower():
                        asyncio.create_task(self._navigate_to(route))
                        return

            search = SidebarSearch(
                colors=C,
                placeholder=f"{t('sidebar.search.placeholder')}  (Ctrl+K)",
                on_filter=_apply_filter,
                on_submit=_jump_to_first_match,
            )

            # Restore previous query if any (e.g. after lang change rebuilds).
            if sidebar_state.get("query"):
                _apply_filter(sidebar_state["query"])

            user_card = SidebarUserCard(
                username=self.current_user or "system",
                role=self.controller.current_user_role or "-",
                colors=C,
                on_settings=lambda: asyncio.create_task(self._navigate_to("settings")),
                on_logout=lambda: asyncio.create_task(self._logout()),
            )

            self._sidebar_nav = ft.Container(
                content=ft.Column(
                    [
                        # Header
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Icon(
                                            ft.icons.Icons.INVENTORY_2,
                                            color="white",
                                            size=18,
                                        ),
                                        width=32,
                                        height=32,
                                        border_radius=8,
                                        bgcolor=C["primary"],
                                        alignment=ft.alignment.Alignment.CENTER,
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                "Inventario",
                                                size=14,
                                                weight=ft.FontWeight.BOLD,
                                                color=C["text_primary"],
                                            ),
                                            ft.Text(
                                                "Pro",
                                                size=10,
                                                color=C["text_muted"],
                                            ),
                                        ],
                                        spacing=0,
                                    ),
                                ],
                                spacing=10,
                            ),
                            padding=ft.Padding(left=14, right=14, top=14, bottom=8),
                        ),
                        search.control,
                        ls,
                        ft.Container(
                            content=ft.Column(
                                section_controls,
                                spacing=2,
                                scroll=ft.ScrollMode.AUTO,
                                expand=True,
                            ),
                            padding=ft.Padding(left=4, right=4, top=4, bottom=4),
                            expand=True,
                        ),
                        user_card.control,
                    ],
                    spacing=0,
                    expand=True,
                ),
                width=240,
                padding=0,
                bgcolor=C["sidebar_bg"],
                border=ft.border.Border(
                    right=ft.BorderSide(1, C["divider"]),
                ),
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
        try:
            self._stock_alert_count = await self.controller.contar_alertas_stock()
        except Exception:
            self._stock_alert_count = 0
        # Re-render the sidebar by rebuilding the main view
        getattr(self, "_current_route", "dashboard")
        await self._show_main_view()

    # ============ Navigation ============

    async def _navigate_to(self, route: str):
        """Navigate to different sections"""
        self._current_route = route
        self.current_page = 0
        self.current_product_edit = None

        if route == "dashboard":
            await self._show_dashboard()
        elif route == "products":
            await self._show_products_list()
        elif route == "sales":
            await sales_views.show_sales(self)
        elif route == "clients":
            await entity_views.show_clients(self)
        elif route == "stock":
            await self._show_stock_management()
        elif route == "scanner":
            await self._show_scanner()
        elif route == "export":
            await self._show_export_options()
        elif route == "categories":
            await entity_views.show_categories(self)
        elif route == "suppliers":
            await entity_views.show_suppliers(self)
        elif route == "purchase_orders":
            await self._show_purchase_orders()
        elif route == "stock_alerts":
            await stock_views.show_stock_alerts(self)
        elif route == "warehouses":
            await stock_views.show_warehouses(self)
        elif route == "warehouse_stock":
            await stock_views.show_warehouse_stock(self)
        elif route == "backups":
            await admin_views.show_backups(self)
        elif route == "users":
            await admin_views.show_users(self)
        elif route == "settings":
            await admin_views.show_settings(self)
        elif route == "logout":
            await self._logout()
        # Fase 1 routes
        elif route == "p1_devoluciones":
            await p1.show_devoluciones(self)
        elif route == "p1_transferencias":
            await p1.show_transferencias(self)
        elif route == "p1_conteos":
            await p1.show_conteos(self)
        elif route == "p1_lotes":
            await p1.show_lotes(self)
        elif route == "p1_precios":
            await p1.show_precios(self)
        elif route == "p1_impuestos":
            await p1.show_impuestos(self)
        elif route == "p1_caja":
            await p1.show_caja(self)
        elif route == "p1_busqueda":
            await p1.show_busqueda(self)
        elif route == "p1_reabasto":
            await p1.show_reabasto(self)
        # Fase 3 routes
        elif route == "p3_variantes":
            await p3.show_variantes(self)
        elif route == "p3_reportes":
            await p3.show_reportes(self)
        elif route == "p3_push":
            await p3.show_push_queue(self)
        elif route == "p3_image_search":
            await p3.show_image_search(self)

    # ============ Dashboard ============

    async def _show_dashboard(self):
        """Display the unified inventory home/dashboard.

        Single source of truth for KPIs: ``obtener_kpis_dashboard`` aggregates
        all metrics in one DB round-trip, then charts are fetched concurrently.
        Previously this view rendered two overlapping KPI sections (basic stats
        cards + a separate "Executive Dashboard" block) and called four
        additional controllers sequentially; both issues are resolved here.
        """
        loading_container = LoadingSpinner.create()
        if self.main_view:
            self.main_view.content = loading_container
            self.page.update()

        C = self._get_colors()
        try:
            # Single KPI round-trip + concurrent chart queries.
            # ``asyncio.gather`` returns a future, not a coroutine, so we
            # wrap it in a small async function before handing it to
            # ``create_task`` (required since Python 3.14).
            async def _charts():
                return await asyncio.gather(
                    self.controller.obtener_top_productos_stock(limit=10),
                    self.controller.obtener_distribucion_categorias(),
                    self.controller.obtener_serie_inventario(dias=30),
                    self.controller.obtener_todos_productos(),
                )

            kpis_task = asyncio.create_task(self.controller.obtener_kpis_dashboard())
            charts_task = asyncio.create_task(_charts())
            kpis = await kpis_task
            top_productos, distribucion, serie, products = await charts_task

            total_productos = int(kpis.get("total_productos", 0))
            unidades_totales = int(kpis.get("unidades_totales", 0))
            valor_venta = float(kpis.get("valor_inventario_venta", 0))
            valor_costo = float(kpis.get("valor_inventario_costo", 0))
            margen = float(kpis.get("margen_estimado", 0))
            criticos = int(kpis.get("productos_criticos", 0))
            agotados = int(kpis.get("productos_agotados", 0))
            ventas_hoy_count = int(kpis.get("ventas_hoy_count", 0))
            ventas_hoy_total = float(kpis.get("ventas_hoy_total", 0))
            ventas_mes_count = int(kpis.get("ventas_mes_count", 0))
            ventas_mes_total = float(kpis.get("ventas_mes_total", 0))
            top_mes = kpis.get("top_productos_mes", []) or []

            def _fmt_money(v: float) -> str:
                return f"${v:,.2f}"

            def _kpi_card(
                title: str,
                value: str,
                color: str,
                light_color: str,
                icon,
                col_size: int = 3,
            ) -> ft.Container:
                return ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Icon(icon, color=color, size=22),
                                        bgcolor=light_color,
                                        padding=10,
                                        border_radius=8,
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                title,
                                                size=11,
                                                color=C["text_muted"],
                                                weight=ft.FontWeight.W_500,
                                            ),
                                            ft.Text(
                                                value,
                                                size=20,
                                                weight=ft.FontWeight.BOLD,
                                                color=color,
                                            ),
                                        ],
                                        spacing=2,
                                        expand=True,
                                        horizontal_alignment=ft.CrossAxisAlignment.END,
                                    ),
                                ],
                                spacing=12,
                            ),
                        ]
                    ),
                    col={"sm": 6, "md": col_size, "xl": col_size},
                    padding=16,
                    bgcolor=C["surface"],
                    border_radius=12,
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=4, color=C["shadow"]),
                )

            # Row 1: inventory headcount + value + risk (4 cards)
            cards_row1 = [
                _kpi_card(
                    t("dashboard.total_products"),
                    str(total_productos),
                    THEME_PRIMARY_COLOR,
                    THEME_PRIMARY_LIGHT,
                    ft.icons.Icons.INVENTORY_2,
                ),
                _kpi_card(
                    "Unidades",
                    str(unidades_totales),
                    "#0EA5E9",
                    "#E0F2FE",
                    ft.icons.Icons.STORAGE,
                ),
                _kpi_card(
                    t("phase1.dashboard.valor_venta"),
                    _fmt_money(valor_venta),
                    THEME_SUCCESS_COLOR,
                    THEME_SUCCESS_LIGHT,
                    ft.icons.Icons.ATTACH_MONEY,
                ),
                _kpi_card(
                    t("phase1.dashboard.valor_costo"),
                    _fmt_money(valor_costo),
                    "#7C3AED",
                    "#EDE9FE",
                    ft.icons.Icons.PAID,
                ),
            ]
            # Row 2: risk + sales (5 cards). Margen spans 1 col on its own.
            cards_row2 = [
                _kpi_card(
                    t("phase1.dashboard.criticos"),
                    str(criticos),
                    THEME_WARNING_COLOR,
                    THEME_WARNING_LIGHT,
                    ft.icons.Icons.WARNING_AMBER,
                ),
                _kpi_card(
                    t("phase1.dashboard.agotados"),
                    str(agotados),
                    THEME_ACCENT_COLOR,
                    THEME_ACCENT_LIGHT,
                    ft.icons.Icons.ERROR,
                ),
                _kpi_card(
                    t("phase1.dashboard.margen"),
                    _fmt_money(margen),
                    "#0F766E",
                    "#CCFBF1",
                    ft.icons.Icons.TRENDING_UP,
                ),
                _kpi_card(
                    "Ventas hoy",
                    f"{ventas_hoy_count} · {_fmt_money(ventas_hoy_total)}",
                    "#16A34A",
                    "#DCFCE7",
                    ft.icons.Icons.TODAY,
                ),
                _kpi_card(
                    "Ventas mes",
                    f"{ventas_mes_count} · {_fmt_money(ventas_mes_total)}",
                    "#2563EB",
                    "#DBEAFE",
                    ft.icons.Icons.CALENDAR_MONTH,
                ),
            ]

            # Recent products (newest first)
            recent_products = sorted(
                products,
                key=lambda x: x.get("creado_en", x.get("fecha_creacion", "")),
                reverse=True,
            )[:5]
            recent_table_rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(p.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(p.get("nombre", ""))[:30])),
                        ft.DataCell(ft.Text(str(p.get("cantidad", 0)))),
                        ft.DataCell(ft.Text(f"${p.get('precio', 0):.2f}")),
                    ]
                )
                for p in recent_products
            ]
            recent_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text(t("products.code"))),
                    ft.DataColumn(ft.Text(t("products.name"))),
                    ft.DataColumn(ft.Text(t("products.quantity"))),
                    ft.DataColumn(ft.Text(t("products.price"))),
                ],
                rows=recent_table_rows,
                border=ft.border.Border(
                    ft.BorderSide(1, C["divider"]),
                    ft.BorderSide(1, C["divider"]),
                    ft.BorderSide(1, C["divider"]),
                    ft.BorderSide(1, C["divider"]),
                ),
                heading_row_color=C["table_heading"],
                data_row_color=C["table_row"],
                horizontal_lines=ft.BorderSide(0.1, C["divider"]),
                vertical_lines=ft.BorderSide(0.1, C["divider"]),
            )

            # Build charts (flet-charts wrappers from ui/charts.py)
            bar_chart = TopProductosChart.build(
                top_productos,
                title=t("dashboard.chart.top_products"),
                value_label=t("products.quantity"),
                empty_message=t("products.empty"),
                colors=C,
            )
            pie_chart = DistribucionChart.build(
                distribucion,
                title=t("dashboard.chart.by_category"),
                empty_message=t("products.empty"),
                colors=C,
            )
            line_chart = ValorInventarioChart.build(
                serie,
                title=t("dashboard.chart.value_30d"),
                value_label="$",
                empty_message=t("products.empty"),
                colors=C,
            )

            # Top-products-of-the-month table (uses the same kpis payload
            # fetched once at the top of the method).
            top_mes_rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(it.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(it.get("nombre", "")))),
                        ft.DataCell(ft.Text(str(it.get("unidades", 0)))),
                        ft.DataCell(ft.Text(_fmt_money(float(it.get("ingresos", 0) or 0)))),
                    ]
                )
                for it in top_mes
            ]
            top_mes_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text(t("products.code"))),
                    ft.DataColumn(ft.Text(t("phase1.devoluciones.producto"))),
                    ft.DataColumn(ft.Text("Unidades")),
                    ft.DataColumn(ft.Text("Ingresos")),
                ],
                rows=top_mes_rows,
                heading_row_color=C["table_heading"],
                horizontal_lines=ft.BorderSide(0.1, C["divider"]),
                vertical_lines=ft.BorderSide(0.1, C["divider"]),
            )

            content = ft.Column(
                [
                    AppHeader.create(t("dashboard.title"), t("dashboard.subtitle")),
                    # Unified KPI grid: 2 rows, 9 metrics. No more duplicate
                    # "stats cards" + "executive dashboard" blocks.
                    ft.Container(
                        content=ft.ResponsiveRow(
                            controls=cards_row1,
                            columns=12,
                            spacing=15,
                            run_spacing=15,
                        ),
                        padding=20,
                    ),
                    ft.Container(
                        content=ft.ResponsiveRow(
                            controls=cards_row2,
                            columns=12,
                            spacing=15,
                            run_spacing=15,
                        ),
                        padding=ft.Padding(left=20, right=20, top=0, bottom=10),
                    ),
                    # Charts row (responsive: full width on mobile, side-by-side on desktop)
                    ft.Container(
                        content=ft.ResponsiveRow(
                            controls=[
                                ft.Container(
                                    content=bar_chart,
                                    col={"sm": 12, "md": 12, "lg": 6},
                                    padding=10,
                                ),
                                ft.Container(
                                    content=pie_chart,
                                    col={"sm": 12, "md": 12, "lg": 6},
                                    padding=10,
                                ),
                            ],
                            columns=12,
                            spacing=10,
                            run_spacing=10,
                        ),
                        padding=ft.Padding(left=10, right=10, top=0, bottom=10),
                    ),
                    ft.Container(
                        content=ft.Row(
                            [line_chart],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        padding=ft.Padding(left=10, right=10, top=0, bottom=10),
                    ),
                    # Two tables side-by-side on desktop, stacked on mobile.
                    ft.Container(
                        content=ft.ResponsiveRow(
                            controls=[
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Text(
                                                "Productos Recientes",
                                                size=16,
                                                weight=ft.FontWeight.BOLD,
                                                color=C["primary"],
                                            ),
                                            recent_table,
                                        ],
                                        spacing=15,
                                    ),
                                    col={"sm": 12, "lg": 6},
                                    padding=20,
                                    bgcolor=C["surface"],
                                    border_radius=10,
                                ),
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Text(
                                                t("phase1.dashboard.top_mes"),
                                                size=16,
                                                weight=ft.FontWeight.BOLD,
                                                color=C["primary"],
                                            ),
                                            top_mes_table,
                                        ],
                                        spacing=15,
                                    ),
                                    col={"sm": 12, "lg": 6},
                                    padding=20,
                                    bgcolor=C["surface"],
                                    border_radius=10,
                                ),
                            ],
                            columns=12,
                            spacing=15,
                            run_spacing=15,
                        ),
                        padding=ft.Padding(left=20, right=20, top=0, bottom=20),
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )

            if self.main_view:
                self.main_view.content = content
                self.page.update()

        except Exception as e:
            logger.exception(f"dashboard: render failed: {e}")
            SnackBarHelper.error(self.page, f"Error al cargar dashboard: {e!s}")

    # ============ Products Management ============

    async def _show_products_list(self):
        """Display products list with search and pagination"""
        try:
            self.all_products = await self.controller.obtener_todos_productos()
            self.filtered_products = self.all_products
            self.current_page = 0
            self._update_products_table()

        except Exception as e:
            SnackBarHelper.error(self.page, f"Error al cargar productos: {e!s}")

    def _update_products_table(self):
        """Update the products table based on current filters and pagination"""
        try:
            # Calculate pagination
            self.total_pages = max(
                1, (len(self.filtered_products) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            )
            start_idx = self.current_page * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            page_products = self.filtered_products[start_idx:end_idx]

            # Build table rows with action buttons
            rows = []
            can_bulk = (
                self.controller.has_permission(Perm.BULK_ELIMINAR)
                or self.controller.has_permission(Perm.BULK_CATEGORIA)
                or self.controller.has_permission(Perm.BULK_EXPORTAR)
            )
            for product in page_products:

                async def handle_edit(e, p=product):
                    await self._show_product_form(p)

                async def handle_delete(e, p=product):
                    await self._confirm_delete_product(p)

                def make_handler(p):
                    def handle_select(e):
                        pid = p["id"]
                        if pid in self._selected_product_ids:
                            self._selected_product_ids.discard(pid)
                        else:
                            self._selected_product_ids.add(pid)
                        self._refresh_bulk_task = asyncio.create_task(self._refresh_bulk_toolbar())

                    return handle_select

                stock = product.get("cantidad", 0)
                stock_min = product.get("stock_min", 0)
                is_low_stock = stock_min > 0 and stock <= stock_min
                pid = product.get("id")
                checked = pid in self._selected_product_ids
                cells = []
                if can_bulk:
                    cells.append(
                        ft.DataCell(ft.Checkbox(value=checked, on_change=make_handler(product)))
                    )
                cells.extend(
                    [
                        ft.DataCell(ft.Text(str(product.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(product.get("nombre", ""))[:30])),
                        ft.DataCell(
                            ft.Text(
                                str(stock),
                                color="red"
                                if stock <= 0
                                else ("orange" if is_low_stock else "blue"),
                                weight=ft.FontWeight.BOLD,
                            )
                        ),
                        ft.DataCell(ft.Text(f"${product.get('precio', 0):.2f}")),
                        ft.DataCell(ft.Text(str(product.get("categoria", "N/A")))),
                        ft.DataCell(
                            ft.Text(str(product.get("proveedor_nombre", "")) or "-", size=12)
                        ),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.Icons.CREATE,
                                        icon_color=THEME_PRIMARY_COLOR,
                                        on_click=handle_edit,
                                        tooltip="Editar",
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.Icons.REMOVE_CIRCLE,
                                        icon_color=THEME_ACCENT_COLOR,
                                        on_click=handle_delete,
                                        tooltip="Eliminar",
                                    ),
                                ],
                                spacing=5,
                            )
                        ),
                    ]
                )
                rows.append(ft.DataRow(cells=cells))

            bulk_cols = [ft.DataColumn(ft.Text(t("bulk.select_label")))] if can_bulk else []
            # Create table
            table = ft.DataTable(
                columns=[
                    *bulk_cols,
                    ft.DataColumn(ft.Text("Código")),
                    ft.DataColumn(ft.Text("Nombre")),
                    ft.DataColumn(ft.Text("Stock")),
                    ft.DataColumn(ft.Text("Precio")),
                    ft.DataColumn(ft.Text("Categoría")),
                    ft.DataColumn(ft.Text("Proveedor")),
                    ft.DataColumn(ft.Text("Acciones")),
                ],
                rows=rows,
            )

            # Update pagination info
            self.page_info_text.value = f"Página {self.current_page + 1} de {self.total_pages} | Total: {len(self.filtered_products)} productos"

            # Pagination buttons
            async def handle_prev(e):
                if self.current_page > 0:
                    self.current_page -= 1
                    self._update_products_table()

            async def handle_next(e):
                if self.current_page < self.total_pages - 1:
                    self.current_page += 1
                    self._update_products_table()

            page_btns = []
            max_visible = 5
            half = max_visible // 2
            start_page = max(0, self.current_page - half)
            end_page = min(self.total_pages, start_page + max_visible)
            if end_page - start_page < max_visible:
                start_page = max(0, end_page - max_visible)

            for p in range(start_page, end_page):
                is_current = p == self.current_page

                async def go_to_page(e, page_num=p):
                    if 0 <= page_num < self.total_pages:
                        self.current_page = page_num
                        self._update_products_table()

                page_btns.append(
                    ft.Container(
                        content=ft.Text(
                            str(p + 1),
                            size=13,
                            weight=ft.FontWeight.BOLD if is_current else ft.FontWeight.NORMAL,
                            color="white" if is_current else THEME_PRIMARY_COLOR,
                        ),
                        padding=8,
                        bgcolor=THEME_PRIMARY_COLOR if is_current else "transparent",
                        border_radius=4,
                        on_click=go_to_page,
                        ink=True,
                    )
                )

            pagination_row = ft.Row(
                [
                    ft.IconButton(
                        icon=ft.icons.Icons.ARROW_BACK_IOS,
                        on_click=handle_prev,
                        disabled=self.current_page == 0,
                    ),
                    *page_btns,
                    ft.IconButton(
                        icon=ft.icons.Icons.ARROW_FORWARD_IOS,
                        on_click=handle_next,
                        disabled=self.current_page >= self.total_pages - 1,
                    ),
                    ft.Container(expand=True),
                    self.page_info_text,
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=4,
            )

            # Build content
            self._bulk_toolbar_container = None
            if can_bulk:
                sel_count = len(self._selected_product_ids)
                bulk_content = ft.Row(
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
                self._bulk_toolbar_container = ft.Container(
                    content=bulk_content,
                    padding=20,
                    visible=bool(self._selected_product_ids),
                )

            content = ft.Column(
                [
                    AppHeader.create("Productos", "Gestión del catálogo"),
                    ft.Container(
                        content=ft.ResponsiveRow(
                            [
                                ft.Container(
                                    self.search_field,
                                    col={"sm": 12, "md": 8, "lg": 9},
                                ),
                                ft.Container(
                                    ft.Button(
                                        content=ft.Text("+ Nuevo Producto"),
                                        on_click=self._handle_new_product,
                                        style=ft.ButtonStyle(
                                            bgcolor=THEME_PRIMARY_COLOR,
                                            color="white",
                                        ),
                                    ),
                                    col={"sm": 12, "md": 4, "lg": 3},
                                ),
                            ],
                            columns=12,
                            spacing=10,
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=20,
                    ),
                    self._bulk_toolbar_container
                    if self._bulk_toolbar_container
                    else ft.Container(),
                    ft.Container(
                        content=table,
                        padding=20,
                        expand=True,
                    ),
                    ft.Container(
                        content=pagination_row,
                        padding=10,
                        bgcolor=THEME_SURFACE_COLOR,
                    ),
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )

            if self.main_view:
                self.main_view.content = content
                self.page.update()

        except Exception as e:
            SnackBarHelper.error(self.page, f"Error actualizando tabla: {e!s}")

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

    async def _show_product_form(self, product: dict | None = None):
        """Display form for adding/editing products"""
        self.current_product_edit = product
        is_edit = product is not None

        # Fetch suppliers and categories for dropdowns
        proveedores = await self.controller.obtener_proveedores()
        categorias = await self.controller.obtener_categorias()
        cat_options = (
            [c["nombre"] for c in categorias]
            if categorias
            else ["Electrónica", "Ropa", "Alimentos", "Otros"]
        )

        # Form fields.
        #
        # Tab order in Flet 0.85 is implicit — driven by the widget tree
        # traversal order in the Flutter web client. With nested
        # ``ft.ResponsiveRow`` + ``ft.Column`` wrappers the browser's
        # native tab order can jump out of the form (e.g. into the
        # sidebar "Ventas" / "Clientes" buttons) once focus leaves the
        # last field. We pin the order explicitly by chaining ``on_submit``
        # (Enter) and a custom Tab handler on every field that advances
        # focus to the next field via ``page.focus()``.
        codigo_field = FormField.create_text_field(
            label="Código",
            hint="Código único del producto",
            required=True,
        )
        nombre_field = FormField.create_text_field(
            label="Nombre",
            hint="Nombre del producto",
            required=True,
        )
        cantidad_field = FormField.create_text_field(
            label="Cantidad",
            hint="0",
            required=True,
        )
        precio_field = FormField.create_text_field(
            label="Precio",
            hint="0.00",
            required=True,
        )
        categoria_field = FormField.create_dropdown(
            label="Categoría",
            options=cat_options,
        )
        stock_min_field = FormField.create_text_field(
            label="Stock Mínimo",
            hint="0",
        )
        unidad_field = ft.Dropdown(
            label="Unidad de Medida",
            options=[
                ft.dropdown.Option("unidad", "Unidad"),
                ft.dropdown.Option("kg", "Kilogramo"),
                ft.dropdown.Option("g", "Gramo"),
                ft.dropdown.Option("l", "Litro"),
                ft.dropdown.Option("ml", "Mililitro"),
                ft.dropdown.Option("m", "Metro"),
                ft.dropdown.Option("caja", "Caja"),
                ft.dropdown.Option("pack", "Pack"),
            ],
            value="unidad",
            border_color=THEME_PRIMARY_COLOR,
            focused_border_color=THEME_ACCENT_COLOR,
            filled=True,
            fill_color="gray50",
        )
        proveedor_field = ft.Dropdown(
            label="Proveedor",
            options=[ft.dropdown.Option(key=str(p["id"]), text=p["nombre"]) for p in proveedores],
            border_color=THEME_PRIMARY_COLOR,
            focused_border_color=THEME_ACCENT_COLOR,
            filled=True,
            fill_color="gray50",
        )
        descripcion_field = FormField.create_text_field(
            label="Descripción",
            hint="Descripción del producto",
            multiline=True,
        )

        # Explicit focus chain. Each field's ``on_submit`` (Enter) and
        # custom Tab handler advance focus to the next field via
        # ``page.focus()``. This guarantees a linear order regardless
        # of how the browser lays out the nested ResponsiveRows.
        field_chain = [
            ("codigo", codigo_field, "nombre"),
            ("nombre", nombre_field, "cantidad"),
            ("cantidad", cantidad_field, "precio"),
            ("precio", precio_field, "stock_min"),
            ("stock_min", stock_min_field, "categoria"),
            ("categoria", categoria_field, "unidad"),
            ("unidad", unidad_field, "proveedor"),
            ("proveedor", proveedor_field, "descripcion"),
            # descripcion_field is multiline: Enter inserts a newline, so
            # Tab is the only way out of it. ``on_submit`` here triggers
            # the Save button instead of advancing to a non-existent
            # next field.
            ("descripcion", descripcion_field, "save"),
        ]
        by_name = {
            "codigo": codigo_field,
            "nombre": nombre_field,
            "cantidad": cantidad_field,
            "precio": precio_field,
            "stock_min": stock_min_field,
            "categoria": categoria_field,
            "unidad": unidad_field,
            "proveedor": proveedor_field,
            "descripcion": descripcion_field,
        }
        next_field = {name: by_name.get(target) for name, _, target in field_chain}
        # Save button is set below; we keep a placeholder reference so
        # on_submit on the last multiline field can trigger it.
        save_btn_ref: list = [None]

        def _advance(name: str):
            """Move focus to the next field in the chain (or save_btn)."""
            if name == "descripcion":
                if save_btn_ref[0] is not None:
                    save_btn_ref[0].focus()
                return
            target = next_field.get(name)
            if target is not None:
                with contextlib.suppress(Exception):
                    target.focus()

        for name, field, _ in field_chain:
            # on_submit fires when the user presses Enter on the field.
            # We use ``name=name`` as a default-argument trick so the
            # closure captures the current value of ``name`` instead of
            # the loop's final binding. The handler is sync because
            # ``_advance`` only calls ``focus()`` — no awaits needed.
            if name != "descripcion":

                def _on_submit(_e, _name=name):
                    _advance(_name)

                field.on_submit = _on_submit

            # Intercept Tab to keep focus inside the form even when the
            # browser would otherwise jump to the sidebar.
            def _on_key(_e, _name=name):
                if getattr(_e, "key", "") in ("Tab", "\t") and not getattr(_e, "shift", False):
                    _advance(_name)
                    with contextlib.suppress(Exception):
                        _e.handled = True

            try:
                field.on_key_down = _on_key
            except Exception:
                # Older Flet builds may not expose on_key_down; fall back
                # silently and rely on on_submit.
                pass

        # Pre-fill if editing
        if is_edit:
            codigo_field.value = product.get("codigo", "")
            codigo_field.disabled = True
            nombre_field.value = product.get("nombre", "")
            cantidad_field.value = str(product.get("cantidad", ""))
            precio_field.value = str(product.get("precio", ""))
            categoria_field.value = product.get("categoria", "")
            stock_min_field.value = str(product.get("stock_min", 0))
            proveedor_field.value = (
                str(product.get("proveedor_id", "")) if product.get("proveedor_id") else None
            )
            unidad_field.value = product.get("unidad_medida", "unidad")
            descripcion_field.value = product.get("descripcion", "")

        error_text = ft.Text("", color=THEME_ACCENT_COLOR, size=12)

        async def handle_save(e):
            """Save product"""
            error_text.value = ""

            # Validation
            if not codigo_field.value:
                error_text.value = "El código es requerido"
                self.page.update()
                return

            if not nombre_field.value:
                error_text.value = "El nombre es requerido"
                self.page.update()
                return

            if not cantidad_field.value:
                error_text.value = "La cantidad es requerida"
                self.page.update()
                return

            if not precio_field.value:
                error_text.value = "El precio es requerido"
                self.page.update()
                return

            save_btn.disabled = True
            try:
                proveedor_id = (
                    int(proveedor_field.value)
                    if proveedor_field.value and proveedor_field.value != "None"
                    else None
                )
                if is_edit:
                    # Update existing product
                    success, result = await self.controller.actualizar_producto(
                        producto_id=product.get("id", 0),
                        nombre=nombre_field.value,
                        cantidad=cantidad_field.value,
                        precio=precio_field.value,
                        descripcion=descripcion_field.value,
                        categoria=categoria_field.value or "Otros",
                        stock_min=stock_min_field.value or "0",
                        proveedor_id=proveedor_id,
                    )
                else:
                    # Create new product
                    success, result = await self.controller.crear_producto(
                        codigo=codigo_field.value,
                        nombre=nombre_field.value,
                        cantidad=cantidad_field.value,
                        precio=precio_field.value,
                        descripcion=descripcion_field.value,
                        categoria=categoria_field.value or "Otros",
                        stock_min=stock_min_field.value or "0",
                        proveedor_id=proveedor_id,
                    )

                if success:
                    msg = "Producto actualizado" if is_edit else "Producto creado"
                    # Close the dialog first so the snackbar renders
                    # against the products list, not on top of it.
                    self.page.pop_dialog()
                    SnackBarHelper.success(self.page, msg)
                    await self._show_products_list()
                else:
                    SnackBarHelper.error(self.page, result.get("error", "Error desconocido"))
                    save_btn.disabled = False

            except Exception as ex:
                SnackBarHelper.error(self.page, f"Error: {ex!s}")
                save_btn.disabled = False

        save_btn = ft.Button(
            content=ft.Text("Guardar"),
            width=150,
            on_click=handle_save,
            style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, color="white"),
        )
        # Register the save button with the focus chain so Tab from the
        # multiline description lands on Guardar instead of escaping to
        # the sidebar.
        save_btn_ref[0] = save_btn

        cancel_btn = ft.OutlinedButton(
            content=ft.Text("Cancelar"),
            width=150,
            # Just close the dialog. The product list behind the modal
            # barrier stays untouched.
            on_click=lambda e: self.page.pop_dialog(),
        )

        # Barcode/QR display section for editing
        code_section = ft.Container(visible=False)

        async def _build_code_cards(codigo):
            """Build code cards for given product code"""
            b64_barcode = await self.controller.obtener_codigo_barras_base64(codigo)
            b64_qr = await self.controller.obtener_qr_base64(codigo)
            cards = []
            if b64_barcode:
                img = ft.Image(src="", width=200, height=60, fit=ft.BoxFit.CONTAIN)
                img.src_base64 = b64_barcode
                cards.append(
                    ft.Container(
                        content=ft.Column(
                            [ft.Text("Código de Barras", size=11, color="gray600"), img],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=5,
                        ),
                        col={"sm": 6, "md": 6, "lg": 6},
                        padding=10,
                        bgcolor="gray50",
                        border_radius=8,
                    )
                )
            if b64_qr:
                img = ft.Image(src="", width=100, height=100, fit=ft.BoxFit.CONTAIN)
                img.src_base64 = b64_qr
                cards.append(
                    ft.Container(
                        content=ft.Column(
                            [ft.Text("Código QR", size=11, color="gray600"), img],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=5,
                        ),
                        col={"sm": 6, "md": 6, "lg": 6},
                        padding=10,
                        bgcolor="gray50",
                        border_radius=8,
                    )
                )
            return cards

        if is_edit:
            cards = await _build_code_cards(product.get("codigo", ""))
            if cards:
                code_section.content = ft.ResponsiveRow(cards, columns=12, spacing=15)
                code_section.visible = True

        async def handle_generate_codes(e):
            """Generate barcode and QR codes for product"""
            code = codigo_field.value.strip()
            if not code:
                SnackBarHelper.error(self.page, "Primero ingrese un código de producto")
                return
            await self.controller.generar_codigos_producto(code)
            cards = await _build_code_cards(code)
            if cards:
                code_section.content = ft.ResponsiveRow(cards, columns=12, spacing=15)
                code_section.visible = True
            else:
                code_section.visible = False
            self.page.update()
            SnackBarHelper.success(self.page, "Códigos generados")

        gen_codes_btn = ft.TextButton(
            content=ft.Text("Generar códigos de barras y QR"),
            icon=ft.icons.Icons.QR_CODE,
            on_click=handle_generate_codes,
        )

        # Build a *modal* AlertDialog instead of injecting the form into
        # main_view.content. The dialog isolates the focus tree, so Tab
        # walks the form fields and Save/Cancel close the dialog without
        # the browser ever escaping into the sidebar.
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Editar Producto" if is_edit else "Nuevo Producto",
                weight=ft.FontWeight.BOLD,
                size=20,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        codigo_field,
                        nombre_field,
                        ft.ResponsiveRow(
                            [cantidad_field, precio_field],
                            columns=12,
                            spacing=15,
                        ),
                        ft.ResponsiveRow(
                            [stock_min_field, categoria_field],
                            columns=12,
                            spacing=15,
                        ),
                        ft.ResponsiveRow(
                            [unidad_field, proveedor_field],
                            columns=12,
                            spacing=15,
                        ),
                        descripcion_field,
                        code_section,
                        gen_codes_btn,
                        error_text,
                    ],
                    spacing=15,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=560,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=cancel_btn.on_click,
                ),
                ft.Button(
                    content=ft.Text("Guardar"),
                    on_click=save_btn.on_click,
                    style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, color="white"),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)
        self.page.update()

    async def _confirm_delete_product(self, product: dict):
        """Show confirmation dialog before deleting product"""

        async def handle_delete(e):
            self.page.pop_dialog()
            try:
                success, result = await self.controller.eliminar_producto(product.get("id", 0))
                if success:
                    SnackBarHelper.success(self.page, "Producto eliminado")
                    await self._show_products_list()
                else:
                    SnackBarHelper.error(self.page, result.get("error", "Error al eliminar"))
            except Exception as ex:
                SnackBarHelper.error(self.page, f"Error: {ex!s}")

        DialogHelper.confirmation_dialog(
            self.page,
            title="Eliminar Producto",
            content=f"¿Estás seguro de que deseas eliminar '{product.get('nombre')}'?",
            on_yes=handle_delete,
        )

    # ============ Products Actions ============

    async def _handle_new_product(self, e):
        """Handle new product button click"""
        await self._show_product_form()

    # ============ Stock Management ============

    async def _show_stock_management(self):
        """Display stock management interface"""
        products = await self.controller.obtener_todos_productos()

        # Stock history table
        selected_product = None
        history_rows = []

        async def handle_product_select(e):
            nonlocal selected_product, history_rows
            if not e.control.value:
                return

            selected_product = next(
                (p for p in products if str(p.get("id", "")) == e.control.value), None
            )
            if selected_product:
                history = await self.controller.obtener_historial_stock(
                    selected_product.get("id", 0)
                )
                history_rows = []

                for h in history:
                    history_rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(str(h.get("creado_en", ""))[:10])),
                                ft.DataCell(ft.Text(str(h.get("tipo_movimiento", "")))),
                                ft.DataCell(ft.Text(str(h.get("cantidad_nueva", 0)))),
                                ft.DataCell(ft.Text(str(h.get("usuario", "")))),
                            ]
                        )
                    )

                history_table.rows = history_rows
                cantidad_ajuste.value = str(selected_product.get("cantidad", 0))
                self.page.update()

        product_dropdown = ft.Dropdown(
            label="Selecciona un producto",
            options=[
                ft.dropdown.Option(key=str(p.get("id", "")), text=p.get("nombre", ""))
                for p in products
            ],
            border_color=THEME_PRIMARY_COLOR,
            focused_border_color=THEME_ACCENT_COLOR,
            filled=True,
            fill_color="gray50",
            on_select=handle_product_select,
        )

        history_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Tipo")),
                ft.DataColumn(ft.Text("Cantidad")),
                ft.DataColumn(ft.Text("Usuario")),
            ],
            rows=[],
        )

        # Stock adjustment form
        cantidad_ajuste = FormField.create_text_field(
            label="Cantidad",
            hint="Cantidad a sumar o restar",
        )
        tipo_movimiento = ft.Dropdown(
            label="Tipo de Movimiento",
            options=[
                ft.dropdown.Option("entrada", "Entrada (compra) — suma stock"),
                ft.dropdown.Option("salida", "Salida (venta) — resta stock"),
                ft.dropdown.Option("ajuste", "Ajuste — fija stock exacto"),
                ft.dropdown.Option("transferencia", "Transferencia"),
            ],
            border_color=THEME_PRIMARY_COLOR,
            focused_border_color=THEME_ACCENT_COLOR,
            filled=True,
            fill_color="gray50",
        )
        razon_field = FormField.create_text_field(
            label="Razón",
            hint="Motivo del movimiento",
        )

        # Build the focus chain so Enter / Tab walk the form linearly
        # instead of jumping to sidebar controls. Same pattern as
        # _show_product_form / _show_new_sale. The submit button is
        # resolved at runtime from the page tree by label so we don't
        # need to bind it through an awkward inline-named-temporary.
        stock_field_chain = [
            ("cantidad_ajuste", cantidad_ajuste, "tipo_movimiento"),
            ("tipo_movimiento", tipo_movimiento, "razon"),
            ("razon", razon_field, "submit"),
        ]
        stock_by_name = {
            "cantidad_ajuste": cantidad_ajuste,
            "tipo_movimiento": tipo_movimiento,
            "razon": razon_field,
        }

        def _find_submit_btn(label: str):
            # _show_stock_management sets main_view.content directly but
            # never calls page.add, so the button is reachable via the
            # main_view subtree, not the page root.
            return AppView._find_submit_btn_static(
                self.main_view, label
            ) or AppView._find_submit_btn_static(self.page, label)

        def _advance_stock(name):
            if name == "razon":
                btn = _find_submit_btn("Actualizar Stock")
                if btn is not None:
                    with contextlib.suppress(Exception):
                        btn.focus()
                return
            tgt = stock_by_name.get(name)
            if tgt is not None:
                with contextlib.suppress(Exception):
                    tgt.focus()

        for name, field, _ in stock_field_chain:

            def _on_submit_stock(_e, _name=name):
                _advance_stock(_name)

            field.on_submit = _on_submit_stock

            def _on_key_stock(_e, _name=name):
                if getattr(_e, "key", "") in ("Tab", "\t") and not getattr(_e, "shift", False):
                    _advance_stock(_name)
                    with contextlib.suppress(Exception):
                        _e.handled = True

            with contextlib.suppress(Exception):
                field.on_key_down = _on_key_stock

        async def handle_update_stock(e):
            """Update stock for selected product"""
            nonlocal selected_product
            if not selected_product:
                SnackBarHelper.error(self.page, "Selecciona un producto")
                return

            if not cantidad_ajuste.value or not tipo_movimiento.value:
                SnackBarHelper.error(self.page, "Completa todos los campos")
                return

            try:
                success, result = await self.controller.actualizar_stock(
                    producto_id=selected_product.get("id", 0),
                    cantidad_nueva=cantidad_ajuste.value,
                    tipo_movimiento=tipo_movimiento.value,
                    razon=razon_field.value,
                )

                if success:
                    SnackBarHelper.success(self.page, "Stock actualizado")
                    razon_field.value = ""
                    selected_product = result if isinstance(result, dict) else selected_product
                    # Refresh history
                    history = await self.controller.obtener_historial_stock(
                        selected_product.get("id", 0)
                    )
                    history_rows.clear()
                    for h in history:
                        history_rows.append(
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(str(h.get("creado_en", ""))[:10])),
                                    ft.DataCell(ft.Text(str(h.get("tipo_movimiento", "")))),
                                    ft.DataCell(ft.Text(str(h.get("cantidad_nueva", 0)))),
                                    ft.DataCell(ft.Text(str(h.get("usuario", "")))),
                                ]
                            )
                        )
                    history_table.rows = list(history_rows)
                    self.page.update()

            except Exception as ex:
                SnackBarHelper.error(self.page, f"Error: {ex!s}")

        # Build a *modal* AlertDialog. The dialog isolates the focus tree
        # so the user can adjust stock multiple times in a row without
        # Tab escaping to the sidebar. "Cerrar" closes the dialog.
        content = ft.Container(
            content=ft.Column(
                [
                    product_dropdown,
                    ft.Divider(height=1),
                    ft.Text(
                        "Historial de Movimientos",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=THEME_PRIMARY_COLOR,
                    ),
                    history_table,
                    ft.Divider(height=10),
                    ft.Text(
                        "Ajustar Stock",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=THEME_PRIMARY_COLOR,
                    ),
                    cantidad_ajuste,
                    tipo_movimiento,
                    razon_field,
                    ft.Button(
                        content=ft.Text("Actualizar Stock"),
                        on_click=handle_update_stock,
                        width=200,
                        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, color="white"),
                    ),
                ],
                spacing=10,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=640,
        )
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Gestión de Stock",
                weight=ft.FontWeight.BOLD,
                size=20,
            ),
            content=content,
            actions=[
                ft.TextButton(
                    "Cerrar",
                    on_click=lambda e: self.page.pop_dialog(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)
        self.page.update()

    # ============ Scanner ============

    async def _show_scanner(self):
        """Display barcode/QR scanner view"""
        C = self._get_colors()

        async def handle_scan_input(e):
            """Handle scanned or typed barcode input"""
            data = scan_field.value.strip()
            if not data:
                return
            try:
                producto = await self.controller.buscar_por_codigo_escaneado(data)
                if producto:
                    self._scanner_result_container.content = self._build_scanner_result(producto)
                else:
                    self._scanner_result_container.content = ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.icons.Icons.SEARCH_OFF, size=48, color="gray400"),
                                ft.Text("Producto no encontrado", size=16, color="gray600"),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=10,
                        ),
                        padding=40,
                        alignment="center",
                    )
                self.page.update()
            except Exception as ex:
                SnackBarHelper.error(self.page, f"Error: {ex!s}")

        async def handle_pick_file(e):
            SnackBarHelper.info(self.page, "Selector de archivos no disponible en esta versión")

        scan_field = ft.TextField(
            label="Código de barras / QR",
            hint_text="Escanee o ingrese manualmente el código",
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
            autofocus=True,
            on_submit=handle_scan_input,
            suffix_icon=ft.icons.Icons.SEARCH,
            expand=True,
        )

        scan_btn = ft.Button(
            content=ft.Text("Buscar"),
            on_click=handle_scan_input,
            style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, color="white"),
        )

        file_scan_btn = ft.OutlinedButton(
            "Escanear desde imagen",
            icon=ft.icons.Icons.IMAGE_SEARCH,
            on_click=handle_pick_file,
        )

        availability = await self.controller.scanner_disponibilidad()
        status_pills = []
        for name, avail in availability.items():
            status_pills.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.icons.Icons.CHECK_CIRCLE if avail else ft.icons.Icons.CANCEL,
                                size=14,
                                color="green" if avail else "red",
                            ),
                            ft.Text(name, size=11, color="gray600"),
                        ],
                        spacing=3,
                    ),
                    padding=ft.Padding(right=15),
                )
            )

        self._scanner_result_container = ft.Container(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.icons.Icons.QR_CODE_SCANNER, size=48, color="gray400"),
                        ft.Text("Ingrese o escanee un código", size=14, color="gray600"),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=60,
                alignment="center",
            ),
            expand=True,
        )

        content = ft.Column(
            [
                AppHeader.create("Escáner", "Buscar productos por código de barras o QR"),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row([scan_field, scan_btn], spacing=10),
                            ft.Container(height=10),
                            file_scan_btn,
                            ft.Divider(height=1),
                            ft.Row(status_pills, spacing=5),
                        ],
                        spacing=5,
                    ),
                    padding=20,
                ),
                self._scanner_result_container,
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        if self.main_view:
            self.main_view.content = content
            self.page.update()

    def _build_scanner_result(self, producto: dict) -> ft.Container:
        """Build product result card for scanner view"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.icons.Icons.CHECK_CIRCLE, color="green", size=24),
                                ft.Text(
                                    "Producto encontrado",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color="green",
                                ),
                            ],
                            spacing=5,
                        ),
                        padding=10,
                    ),
                    ft.Divider(height=1),
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text("Código:", weight=ft.FontWeight.BOLD, size=13),
                                    ft.Text(str(producto.get("codigo", "")), size=13),
                                ],
                                spacing=10,
                            ),
                            ft.Row(
                                [
                                    ft.Text("Nombre:", weight=ft.FontWeight.BOLD, size=13),
                                    ft.Text(str(producto.get("nombre", "")), size=13),
                                ],
                                spacing=10,
                            ),
                            ft.Row(
                                [
                                    ft.Text("Stock:", weight=ft.FontWeight.BOLD, size=13),
                                    ft.Text(
                                        str(producto.get("cantidad", 0)),
                                        size=13,
                                        color="blue" if producto.get("cantidad", 0) > 0 else "red",
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.Row(
                                [
                                    ft.Text("Precio:", weight=ft.FontWeight.BOLD, size=13),
                                    ft.Text(f"${producto.get('precio', 0):.2f}", size=13),
                                ],
                                spacing=10,
                            ),
                            ft.Row(
                                [
                                    ft.Text("Categoría:", weight=ft.FontWeight.BOLD, size=13),
                                    ft.Text(str(producto.get("categoria", "N/A")), size=13),
                                ],
                                spacing=10,
                            ),
                        ],
                        spacing=8,
                        padding=15,
                    ),
                ],
                spacing=0,
            ),
            bgcolor=THEME_SURFACE_COLOR,
            border_radius=10,
            margin=20,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=3, color="rgba(0,0,0,0.05)"),
        )

    # ============ Export Options ============

    async def _show_export_options(self):
        """Display export options"""
        export_status = ft.Text("", size=12)

        async def handle_export_csv(e):
            """Export to CSV"""
            try:
                export_status.value = "Exportando CSV..."
                export_btn_csv.disabled = True
                self.page.update()

                success, path = await self.controller.exportar_csv()
                if success:
                    SnackBarHelper.success(self.page, f"CSV exportado: {path}")
                    export_status.value = f"✓ Exportado a: {path}"
                else:
                    SnackBarHelper.error(self.page, f"Error: {path}")
                    export_status.value = f"✗ Error: {path}"

            except Exception as ex:
                SnackBarHelper.error(self.page, f"Error: {ex!s}")
                export_status.value = f"✗ Error: {ex!s}"
            finally:
                export_btn_csv.disabled = False
                self.page.update()

        async def handle_export_json(e):
            """Export to JSON"""
            try:
                export_status.value = "Exportando JSON..."
                export_btn_json.disabled = True
                self.page.update()

                success, path = await self.controller.exportar_json()
                if success:
                    SnackBarHelper.success(self.page, f"JSON exportado: {path}")
                    export_status.value = f"✓ Exportado a: {path}"
                else:
                    SnackBarHelper.error(self.page, f"Error: {path}")
                    export_status.value = f"✗ Error: {path}"

            except Exception as ex:
                SnackBarHelper.error(self.page, f"Error: {ex!s}")
                export_status.value = f"✗ Error: {ex!s}"
            finally:
                export_btn_json.disabled = False
                self.page.update()

        async def handle_export_report(e):
            """Export summary report"""
            try:
                export_status.value = "Generando reporte..."
                export_btn_report.disabled = True
                self.page.update()

                success, path = await self.controller.exportar_reporte()
                if success:
                    SnackBarHelper.success(self.page, f"Reporte exportado: {path}")
                    export_status.value = f"✓ Exportado a: {path}"
                else:
                    SnackBarHelper.error(self.page, f"Error: {path}")
                    export_status.value = f"✗ Error: {path}"

            except Exception as ex:
                SnackBarHelper.error(self.page, f"Error: {ex!s}")
                export_status.value = f"✗ Error: {ex!s}"
            finally:
                export_btn_report.disabled = False
                self.page.update()

        async def handle_export_pdf(e):
            """Export to PDF"""
            try:
                export_status.value = "Exportando PDF..."
                export_btn_pdf.disabled = True
                self.page.update()

                success, path = await self.controller.exportar_pdf()
                if success:
                    SnackBarHelper.success(self.page, f"PDF exportado: {path}")
                    export_status.value = f"✓ Exportado a: {path}"
                else:
                    SnackBarHelper.error(self.page, f"Error: {path}")
                    export_status.value = f"✗ Error: {path}"

            except Exception as ex:
                SnackBarHelper.error(self.page, f"Error: {ex!s}")
                export_status.value = f"✗ Error: {ex!s}"
            finally:
                export_btn_pdf.disabled = False
                self.page.update()

        async def handle_export_xlsx(e):
            """Export to Excel"""
            try:
                export_status.value = "Exportando Excel..."
                export_btn_xlsx.disabled = True
                self.page.update()

                success, path = await self.controller.exportar_xlsx()
                if success:
                    SnackBarHelper.success(self.page, f"Excel exportado: {path}")
                    export_status.value = f"✓ Exportado a: {path}"
                else:
                    SnackBarHelper.error(self.page, f"Error: {path}")
                    export_status.value = f"✗ Error: {path}"

            except Exception as ex:
                SnackBarHelper.error(self.page, f"Error: {ex!s}")
                export_status.value = f"✗ Error: {ex!s}"
            finally:
                export_btn_xlsx.disabled = False
                self.page.update()

        export_btn_csv = ft.Button(
            content=ft.Text("Exportar a CSV"),
            on_click=handle_export_csv,
            width=200,
            height=50,
            style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, color="white"),
        )

        export_btn_json = ft.Button(
            content=ft.Text("Exportar a JSON"),
            on_click=handle_export_json,
            width=200,
            height=50,
            style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, color="white"),
        )

        export_btn_report = ft.Button(
            content=ft.Text("Generar Reporte"),
            on_click=handle_export_report,
            width=200,
            height=50,
            style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, color="white"),
        )

        export_btn_pdf = ft.Button(
            content=ft.Text("Exportar a PDF"),
            on_click=handle_export_pdf,
            width=200,
            height=50,
            style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, color="white"),
        )

        export_btn_xlsx = ft.Button(
            content=ft.Text("Exportar a Excel"),
            on_click=handle_export_xlsx,
            width=200,
            height=50,
            style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, color="white"),
        )

        async def handle_import_click(e):
            """Open the import dialog and dispatch to CSV/XLSX importer."""
            await _show_import_dialog()

        import_btn = ft.Button(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.Icons.UPLOAD_FILE, color="white"),
                    ft.Text(t("export.import_csv"), color="white"),
                ],
                spacing=5,
            ),
            on_click=handle_import_click,
            width=200,
            height=50,
            style=ft.ButtonStyle(bgcolor="green700"),
        )

        async def _show_import_dialog():
            """Show a dialog asking for the file path; detect format by extension."""
            C = self._get_colors()
            path_field = FormField.create_text_field(
                label=t("export.import_path_label"),
                hint=t("export.import_path_hint"),
                page=self.page,
                colors=C,
            )
            path_field.width = 480

            async def do_import(_e):
                path = (path_field.value or "").strip()
                if not path:
                    SnackBarHelper.error(self.page, t("export.import_path_label"))
                    return
                # Strip optional surrounding quotes (Windows paste habit).
                path = path.strip('"').strip("'")
                lower = path.lower()
                self.page.pop_dialog()
                if lower.endswith(".xlsx"):
                    success, errors = await self.controller.importar_productos_xlsx(path)
                else:
                    # Default to CSV for .csv and any other extension — matches
                    # the previous behaviour where CSV was the only path.
                    success, errors = await self.controller.importar_productos_csv(path)
                if errors:
                    SnackBarHelper.success(
                        self.page,
                        t(
                            "export.import_partial",
                            success=success,
                            errors=len(errors),
                        ),
                    )
                    # Surface the first few errors in the status label so the
                    # user can copy them.
                    preview = "; ".join(errors[:3])
                    if len(errors) > 3:
                        preview += f" (+{len(errors) - 3} más)"
                    export_status.value = preview
                else:
                    SnackBarHelper.success(self.page, t("export.import_success", success=success))
                    export_status.value = f"✓ Importados: {success}"
                self.page.update()
                # Refresh the active view if it's a products-related route.
                if self._current_route in ("products", "dashboard"):
                    with contextlib.suppress(Exception):
                        await self._navigate_to(self._current_route)

            dialog = ft.AlertDialog(
                title=ft.Text(t("export.import_dialog_title")),
                content=ft.Container(content=path_field, padding=10),
                actions=[
                    ft.TextButton(
                        t("common.cancel"),
                        on_click=lambda e: self.page.pop_dialog(),
                    ),
                    ft.TextButton(t("common.save"), on_click=do_import),
                ],
            )
            dialog.open = True
            self.page.show_dialog(dialog)
            self.page.update()

        content = ft.Column(
            [
                AppHeader.create(t("export.title"), t("export.subtitle")),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                t("export.subtitle"),
                                size=14,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Container(height=20),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Text(
                                                    "CSV",
                                                    size=16,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                export_btn_csv,
                                            ],
                                            alignment=ft.MainAxisAlignment.CENTER,
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            spacing=10,
                                        ),
                                        col={"sm": 6, "md": 4, "lg": 2},
                                        padding=20,
                                        bgcolor=THEME_SURFACE_COLOR,
                                        border_radius=10,
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Text(
                                                    "JSON",
                                                    size=16,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                export_btn_json,
                                            ],
                                            alignment=ft.MainAxisAlignment.CENTER,
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            spacing=10,
                                        ),
                                        col={"sm": 6, "md": 4, "lg": 2},
                                        padding=20,
                                        bgcolor=THEME_SURFACE_COLOR,
                                        border_radius=10,
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Text(
                                                    "Reporte",
                                                    size=16,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                export_btn_report,
                                            ],
                                            alignment=ft.MainAxisAlignment.CENTER,
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            spacing=10,
                                        ),
                                        col={"sm": 6, "md": 4, "lg": 2},
                                        padding=20,
                                        bgcolor=THEME_SURFACE_COLOR,
                                        border_radius=10,
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Text(
                                                    "PDF",
                                                    size=16,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                export_btn_pdf,
                                            ],
                                            alignment=ft.MainAxisAlignment.CENTER,
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            spacing=10,
                                        ),
                                        col={"sm": 6, "md": 4, "lg": 2},
                                        padding=20,
                                        bgcolor=THEME_SURFACE_COLOR,
                                        border_radius=10,
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Text(
                                                    "Excel",
                                                    size=16,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                export_btn_xlsx,
                                            ],
                                            alignment=ft.MainAxisAlignment.CENTER,
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            spacing=10,
                                        ),
                                        col={"sm": 6, "md": 4, "lg": 2},
                                        padding=20,
                                        bgcolor=THEME_SURFACE_COLOR,
                                        border_radius=10,
                                    ),
                                ],
                                columns=12,
                                spacing=20,
                                run_spacing=20,
                            ),
                            ft.Container(height=20),
                            ft.Divider(),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(
                                            ft.icons.Icons.UPLOAD_FILE,
                                            color="gray700",
                                        ),
                                        ft.Text(
                                            t("export.import_csv"),
                                            size=14,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        import_btn,
                                    ],
                                    spacing=15,
                                    alignment=ft.MainAxisAlignment.START,
                                ),
                                padding=10,
                            ),
                            export_status,
                        ],
                        spacing=15,
                    ),
                    padding=30,
                    expand=True,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        if self.main_view:
            self.main_view.content = content
            self.page.update()

    # ============ Purchase Orders ============

    async def _show_purchase_orders(self):
        """Display purchase orders view."""
        ordenes = await self.controller.obtener_ordenes_compra()

        async def open_new(e):
            await self._show_order_form()

        async def handle_receive(e, orden):
            ok, result = await self.controller.recibir_orden(orden.get("id"))
            if ok:
                SnackBarHelper.success(
                    self.page, t("purchase_orders.received_success", id=orden.get("id"))
                )
                await self._refresh_nav_badges()
                await self._show_purchase_orders()
            else:
                SnackBarHelper.error(self.page, result.get("error", t("common.error")))

        async def handle_cancel(e, orden):
            ok, _ = await self.controller.cancelar_orden(orden.get("id"))
            if ok:
                SnackBarHelper.success(self.page, t("common.success"))
                await self._show_purchase_orders()
            else:
                SnackBarHelper.error(self.page, t("common.error"))

        def status_label(s):
            return {
                "pendiente": t("purchase_orders.status.pending"),
                "recibida": t("purchase_orders.status.received"),
                "cancelada": t("purchase_orders.status.cancelled"),
            }.get(s, s)

        def status_color(s):
            return {
                "pendiente": "orange",
                "recibida": "green",
                "cancelada": "red",
            }.get(s, "gray600")

        def build_rows():
            rows = []
            for o in ordenes:
                actions = []
                if o.get("estado") == "pendiente":
                    actions.append(
                        ft.IconButton(
                            icon=ft.icons.Icons.CHECK_CIRCLE,
                            icon_color="green",
                            tooltip=t("purchase_orders.receive"),
                            on_click=lambda e, oo=o: asyncio.create_task(handle_receive(e, oo)),
                        )
                    )
                    actions.append(
                        ft.IconButton(
                            icon=ft.icons.Icons.CANCEL,
                            icon_color="red",
                            tooltip=t("purchase_orders.cancel_order"),
                            on_click=lambda e, oo=o: asyncio.create_task(handle_cancel(e, oo)),
                        )
                    )
                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(f"#{o.get('id', '')}")),
                            ft.DataCell(ft.Text(str(o.get("proveedor_nombre", "") or "-"))),
                            ft.DataCell(ft.Text(str(o.get("producto_nombre", "") or "-"))),
                            ft.DataCell(ft.Text(str(o.get("cantidad", 0)))),
                            ft.DataCell(
                                ft.Text(
                                    status_label(o.get("estado", "")),
                                    color=status_color(o.get("estado", "")),
                                    weight=ft.FontWeight.BOLD,
                                )
                            ),
                            ft.DataCell(ft.Row(actions, spacing=2)),
                        ]
                    )
                )
            return rows

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text(t("purchase_orders.supplier"))),
                ft.DataColumn(ft.Text(t("purchase_orders.product"))),
                ft.DataColumn(ft.Text(t("purchase_orders.quantity"))),
                ft.DataColumn(ft.Text(t("purchase_orders.status"))),
                ft.DataColumn(ft.Text(t("common.edit"))),
            ],
            rows=build_rows(),
        )

        new_btn = ft.Button(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.Icons.ADD, color="white"),
                    ft.Text(t("purchase_orders.new"), color="white"),
                ],
                spacing=5,
            ),
            on_click=open_new,
            style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
        )

        content = ft.Column(
            [
                AppHeader.create(t("purchase_orders.title"), t("purchase_orders.subtitle")),
                ft.Container(
                    content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                    padding=20,
                ),
                ft.Container(content=table, padding=20, expand=True)
                if ordenes
                else ft.Container(
                    content=ft.Text(t("purchase_orders.empty"), color="gray600"),
                    padding=40,
                    alignment="center",
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        if self.main_view:
            self.main_view.content = content
            self.page.update()

    async def _show_order_form(self):
        """Show new purchase order form."""
        proveedores = await self.controller.obtener_proveedores()
        productos = await self.controller.obtener_todos_productos()

        if not proveedores or not productos:
            SnackBarHelper.error(
                self.page,
                "Necesita al menos un proveedor y un producto",
            )
            return

        proveedor_dd = ft.Dropdown(
            label=t("purchase_orders.supplier"),
            options=[ft.dropdown.Option(key=str(p["id"]), text=p["nombre"]) for p in proveedores],
            border_color=THEME_PRIMARY_COLOR,
            focused_border_color=THEME_ACCENT_COLOR,
            filled=True,
            fill_color="gray50",
        )
        producto_dd = ft.Dropdown(
            label=t("purchase_orders.product"),
            options=[
                ft.dropdown.Option(
                    key=str(p["id"]),
                    text=f"{p.get('codigo', '')} - {p.get('nombre', '')}",
                )
                for p in productos
            ],
            border_color=THEME_PRIMARY_COLOR,
            focused_border_color=THEME_ACCENT_COLOR,
            filled=True,
            fill_color="gray50",
        )
        cantidad = FormField.create_text_field(label=t("purchase_orders.quantity"), required=True)

        async def save(e):
            try:
                qty = int(cantidad.value)
            except ValueError, TypeError:
                SnackBarHelper.error(self.page, t("common.validation_error"))
                return
            if not proveedor_dd.value or not producto_dd.value or qty <= 0:
                SnackBarHelper.error(self.page, t("common.validation_error"))
                return
            ok, result = await self.controller.crear_orden_compra(
                proveedor_id=int(proveedor_dd.value),
                producto_id=int(producto_dd.value),
                cantidad=qty,
            )
            self.page.pop_dialog()
            if ok:
                SnackBarHelper.success(self.page, t("common.success"))
                await self._show_purchase_orders()
            else:
                SnackBarHelper.error(self.page, result.get("error", t("common.error")))

        dialog = ft.AlertDialog(
            title=ft.Text(t("purchase_orders.new")),
            content=ft.Column([proveedor_dd, producto_dd, cantidad], tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        self.page.show_dialog(dialog)
        self.page.update()

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

    def _refresh_nav_badges_sync(self) -> None:
        """Update the sidebar stock-alert badge without rebuilding the page.

        Cheaper than calling `_refresh_nav_badges()` (which re-renders the
        whole main view) when we only need to bump a counter.
        """
        # Walk children to find the badge chip on the stock_alerts entry.
        # We don't know its exact type at this point, so we just trigger
        # a full refresh — the rebuild is idempotent and cheap.
        try:
            if self._sidebar_nav is not None:
                # Schedule the async refresh; safe to fire-and-forget here.
                asyncio.create_task(self._refresh_nav_badges())
        except RuntimeError:
            # No running loop (e.g. during shutdown).
            pass

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

    # ============ Settings (enhanced) ============

    # ============ Bulk Operations (F2.2) ============

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

    # ============ Warehouses / Almacenes (F2.1) ============

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
