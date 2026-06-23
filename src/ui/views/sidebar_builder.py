"""
Standalone sidebar/navigation builders extracted from AppView.

Each function receives an ``app`` (AppView instance) and uses its public /
protected attributes.  The ``self`` references in the original code are
replaced by ``app`` accordingly.
"""

from __future__ import annotations

import asyncio
from typing import Any

import flet as ft

from services.permissions import Perm
from ui.components import (
    LangSwitcher,
    SidebarItem,
    SidebarSearch,
    SidebarSection,
    SidebarUserCard,
)
from utils.i18n import t

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
    # Facturación routes
    "facturas": Perm.FACTURAS_LEER,
    # Contabilidad routes
    "asientos": Perm.CONTABILIDAD_LEER,
    "plan_cuentas": Perm.CONTABILIDAD_PLAN_CUENTAS,
    "balance": Perm.CONTABILIDAD_LEER,
}

NAV_DATA_ALL = [
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
        None,
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
    # Facturación
    ("facturas", ft.icons.Icons.RECEIPT, "Facturas", None),
    # Contabilidad
    ("asientos", ft.icons.Icons.BOOK, "Asientos Contables", None),
    ("plan_cuentas", ft.icons.Icons.ACCOUNT_TREE, "Plan de Cuentas", None),
    ("balance", ft.icons.Icons.BALANCE, "Balance Comprobación", None),
]

SECTIONS_DEF = [
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
        "sidebar.section.billing",
        [
            "facturas",
            "asientos",
            "plan_cuentas",
            "balance",
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

MOBILE_TOP_KEYS = [
    "dashboard",
    "products",
    "sales",
    "stock_alerts",
    "stock",
    "categories",
]


def build_sidebar_desktop(
    app,
    nav_data: list,
    sections_def: list,
    nav_index: dict,
    C: dict,
    sidebar_state: dict,
) -> ft.Container:
    """Build the desktop sidebar with sections, search, user card, lang switcher."""

    ls = LangSwitcher.create(
        on_change=lambda lang: asyncio.create_task(app._refresh_nav_badges()),
        controller=app.controller,
        bg_color=C["surface"],
        text_color=C["text_secondary"],
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
            is_active=(route == app._current_route),
            badge=badge,
            on_click=lambda r=route: asyncio.create_task(app._navigate_to(r)),
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
            on_toggle=lambda collapsed, sk=section_key: sidebar_state["collapsed"].__setitem__(
                sk, collapsed
            ),
        )
        section_controls.append(sec.control)

    # Search/quick-switcher filters items across all sections.
    def _apply_filter(query: str) -> None:
        sidebar_state["query"] = query
        q = (query or "").strip().lower()
        for rk, si in items_by_route.items():
            visible = (not q) or (q in si.label.lower())
            si.control.visible = visible
        app.page.update()

    def _jump_to_first_match() -> None:
        q = sidebar_state.get("query", "").strip().lower()
        if not q:
            return
        for entry in nav_data:
            route, _icon, label, _badge = entry
            if q in label.lower():
                asyncio.create_task(app._navigate_to(route))
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
        username=app.current_user or "system",
        role=app.controller.current_user_role or "-",
        colors=C,
        on_settings=lambda: asyncio.create_task(app._navigate_to("settings")),
        on_logout=lambda: asyncio.create_task(app._logout()),
    )

    return ft.Container(
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


def build_sidebar_mobile(
    app,
    nav_data: list,
    mobile_items: list,
    more_items: list,
    C: dict,
    nav_index: dict,
) -> ft.NavigationBar:
    """Build the mobile NavigationBar with destinations and 'Más' overflow sheet."""

    divider_color = C["divider"]

    async def _open_more_sheet(_e):
        rows = []
        for route, icon, label, badge in more_items:

            async def _go(e, r=route):
                app._sidebar_more_sheet.open = False
                app.page.update()
                await app._navigate_to(r)

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
        app._sidebar_more_sheet = ft.BottomSheet(
            content=ft.Container(
                content=ft.Column(rows, tight=True, scroll=ft.ScrollMode.AUTO),
                padding=10,
            ),
        )
        app.page.overlay.append(app._sidebar_more_sheet)
        app._sidebar_more_sheet.open = True
        app.page.update()

    nav_items = []
    for route, icon, label, _badge in mobile_items:
        nav_items.append(ft.NavigationBarDestination(icon=icon, label=label))
    nav_items.append(
        ft.NavigationBarDestination(
            icon=ft.icons.Icons.MORE_HORIZ,
            label="Más",
        )
    )

    async def _navigate_mobile(e):
        idx = e.control.selected_index
        if idx is not None and 0 <= idx < len(mobile_items):
            await app._navigate_to(mobile_items[idx][0])

    return ft.NavigationBar(
        destinations=nav_items,
        on_change=lambda e: (
            asyncio.create_task(_navigate_mobile(e))
            if (e.control.selected_index or 0) < len(mobile_items)
            else asyncio.create_task(_open_more_sheet(None))
        ),
        bgcolor=C["surface"],
        border=ft.border.Border(top=ft.BorderSide(1, divider_color)),
    )
