"""
Stock / warehouse views extracted from AppView.

Each function takes an ``app`` parameter (the AppView instance) and uses
``app.page``, ``app.controller``, etc. instead of ``self``.
"""

import asyncio

import flet as ft

from config.settings import (
    THEME_ACCENT_COLOR,
    THEME_DANGER,
    THEME_PRIMARY_COLOR,
    THEME_WARNING_COLOR,
)
from ui.components import (
    AppHeader,
    FormField,
    SnackBarHelper,
)
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _kpi_card(label: str, value: str, color: str, bg: str, text_color: str) -> ft.Container:
    """Compact KPI tile used by stock alerts header."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(label, size=11, color=text_color),
                ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=color),
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=ft.padding.Padding(left=18, right=18, top=14, bottom=14),
        bgcolor=bg,
        border=ft.border.Border(
            ft.BorderSide(2, color),
            ft.BorderSide(2, color),
            ft.BorderSide(2, color),
            ft.BorderSide(2, color),
        ),
        border_radius=10,
        width=180,
    )


def _alert_badge(level: str, colors: dict) -> ft.Container:
    """Pill-shaped tag rendering the alert severity."""
    if level == "critical":
        bg = THEME_DANGER
        label = "Sin stock"
    else:
        bg = THEME_WARNING_COLOR
        label = "Bajo"
    return ft.Container(
        content=ft.Text(
            label,
            color="white",
            size=11,
            weight=ft.FontWeight.BOLD,
        ),
        bgcolor=bg,
        padding=ft.padding.Padding(left=10, right=10, top=4, bottom=4),
        border_radius=12,
    )


def _empty_state(colors: dict, filtered: bool = False) -> ft.Container:
    """Empty-state placeholder when there are no alerts (or no matches)."""
    icon = ft.icons.Icons.SEARCH_OFF if filtered else ft.icons.Icons.CHECK_CIRCLE
    icon_color = colors["text_muted"] if filtered else "green"
    msg_key = "stock_alerts.no_matches" if filtered else "stock_alerts.empty"
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(icon, size=48, color=icon_color),
                ft.Text(t(msg_key), color=colors["text_muted"]),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        padding=60,
        alignment=ft.alignment.Alignment.CENTER,
        expand=True,
    )


async def show_stock_alerts(app):
    """Display products with low stock (Critical / Low / All tabs).

    The query returns an ``alert_level`` per row:
      - critical: cantidad == 0
      - low:      cantidad <= stock_min, or stock_min=0 and cantidad <= threshold
      - ok:       everything else (filtered out by the query)
    """
    alertas = await app.controller.obtener_alertas_stock()
    C = app._get_colors()

    criticas = [p for p in alertas if p.get("alert_level") == "critical"]
    bajas = [p for p in alertas if p.get("alert_level") == "low"]

    filter_state = {"tab": "all", "query": ""}

    def _match_filter(p: dict) -> bool:
        if filter_state["tab"] == "critical" and p.get("alert_level") != "critical":
            return False
        if filter_state["tab"] == "low" and p.get("alert_level") != "low":
            return False
        q = filter_state["query"].strip().lower()
        if not q:
            return True
        return (
            q in str(p.get("codigo", "")).lower()
            or q in str(p.get("nombre", "")).lower()
            or q in str(p.get("categoria", "")).lower()
        )

    def build_rows():
        rows = []
        for p in alertas:
            if not _match_filter(p):
                continue
            qty = int(p.get("cantidad", 0) or 0)
            is_critical = p.get("alert_level") == "critical"
            qty_color = THEME_DANGER if is_critical else THEME_ACCENT_COLOR
            qty_text = "0 (sin stock)" if is_critical else str(qty)
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(p.get("codigo", "")), color=C["text_primary"])),
                        ft.DataCell(ft.Text(str(p.get("nombre", "")), color=C["text_primary"])),
                        ft.DataCell(
                            ft.Text(
                                qty_text,
                                color=qty_color,
                                weight=ft.FontWeight.BOLD,
                            )
                        ),
                        ft.DataCell(ft.Text(str(p.get("stock_min", 0)), color=C["text_primary"])),
                        ft.DataCell(
                            ft.Text(str(p.get("categoria", "") or "-"), color=C["text_secondary"])
                        ),
                        ft.DataCell(_alert_badge(p.get("alert_level", "low"), C)),
                    ]
                )
            )
        return rows

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(t("products.code"))),
            ft.DataColumn(ft.Text(t("products.name"))),
            ft.DataColumn(ft.Text(t("products.quantity"))),
            ft.DataColumn(ft.Text(t("products.stock_min"))),
            ft.DataColumn(ft.Text(t("products.category"))),
            ft.DataColumn(ft.Text(t("stock_alerts.alert_level"))),
        ],
        rows=build_rows(),
        heading_row_color=C["table_heading"],
        heading_text_style=ft.TextStyle(color="white", weight=ft.FontWeight.BOLD),
        data_row_color=C["table_row"],
        border=ft.border.Border(
            ft.BorderSide(1, C["divider"]),
            ft.BorderSide(1, C["divider"]),
            ft.BorderSide(1, C["divider"]),
            ft.BorderSide(1, C["divider"]),
        ),
        horizontal_lines=ft.BorderSide(0.5, C["divider"]),
        vertical_lines=ft.BorderSide(0.5, C["divider"]),
        sort_column_index=2,
        sort_ascending=True,
    )

    subtitle = (
        t("stock_alerts.count_badge", count=len(alertas)) if alertas else t("stock_alerts.subtitle")
    )

    kpi_row = ft.Row(
        [
            _kpi_card(
                label=t("stock_alerts.tabs.critical"),
                value=str(len(criticas)),
                color=THEME_DANGER,
                bg=C["surface"],
                text_color=C["text_primary"],
            ),
            _kpi_card(
                label=t("stock_alerts.tabs.low"),
                value=str(len(bajas)),
                color=THEME_WARNING_COLOR,
                bg=C["surface"],
                text_color=C["text_primary"],
            ),
            _kpi_card(
                label=t("stock_alerts.tabs.all"),
                value=str(len(alertas)),
                color=THEME_PRIMARY_COLOR,
                bg=C["surface"],
                text_color=C["text_primary"],
            ),
        ],
        spacing=12,
        wrap=True,
    )

    tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label=t("stock_alerts.tabs.all"), icon=ft.icons.Icons.LIST),
            ft.Tab(label=t("stock_alerts.tabs.critical"), icon=ft.icons.Icons.ERROR),
            ft.Tab(label=t("stock_alerts.tabs.low"), icon=ft.icons.Icons.WARNING_AMBER),
        ],
        on_click=lambda e: _switch_tab(int(e.data or 0)),
    )

    search = FormField.create_text_field(
        label=t("common.search"),
        hint=t("stock_alerts.search_hint"),
        page=app.page,
        colors=C,
    )

    def _switch_tab(idx: int) -> None:
        filter_state["tab"] = ["all", "critical", "low"][idx]
        _rerender_table()

    async def _on_search(e) -> None:
        filter_state["query"] = search.value or ""
        _rerender_table()

    search.on_change = _on_search

    async def _filtered_alerts():
        return [p for p in alertas if _match_filter(p)]

    async def handle_export_csv(_e):
        filtered = await _filtered_alerts()
        if not filtered:
            SnackBarHelper.info(app.page, t("stock_alerts.no_matches"))
            return
        try:
            from services.export import ExportService

            svc = ExportService()
            out = svc.export_to_csv(filtered)
            SnackBarHelper.success(app.page, t("export.success", path=str(out)))
        except Exception as ex:
            SnackBarHelper.error(app.page, str(ex))

    async def handle_export_pdf(_e):
        filtered = await _filtered_alerts()
        if not filtered:
            SnackBarHelper.info(app.page, t("stock_alerts.no_matches"))
            return
        try:
            from services.export import ExportService

            svc = ExportService()
            out = svc.export_to_pdf(
                filtered,
                title=t("stock_alerts.export_title"),
                columns=[
                    ("codigo", t("products.code")),
                    ("nombre", t("products.name")),
                    ("cantidad", t("products.quantity")),
                    ("stock_min", t("products.stock_min")),
                    ("categoria", t("products.category")),
                    ("alert_level", t("stock_alerts.alert_level")),
                ],
            )
            SnackBarHelper.success(app.page, t("export.success", path=str(out)))
        except Exception as ex:
            SnackBarHelper.error(app.page, str(ex))

    async def handle_export_xlsx(_e):
        filtered = await _filtered_alerts()
        if not filtered:
            SnackBarHelper.info(app.page, t("stock_alerts.no_matches"))
            return
        try:
            from services.export import ExportService

            svc = ExportService()
            out = svc.export_to_xlsx(
                filtered,
                title=t("stock_alerts.export_title"),
                columns=[
                    ("codigo", t("products.code")),
                    ("nombre", t("products.name")),
                    ("cantidad", t("products.quantity")),
                    ("stock_min", t("products.stock_min")),
                    ("categoria", t("products.category")),
                    ("alert_level", t("stock_alerts.alert_level")),
                ],
            )
            SnackBarHelper.success(app.page, t("export.success", path=str(out)))
        except Exception as ex:
            SnackBarHelper.error(app.page, str(ex))

    async def handle_email_alert(_e):
        if not alertas:
            SnackBarHelper.info(app.page, t("stock_alerts.empty"))
            return
        res = await app.controller.enviar_alerta_stock()
        if res.get("sent"):
            SnackBarHelper.success(app.page, t("notifications.sent_ok"))
        else:
            SnackBarHelper.error(
                app.page,
                t("notifications.sent_fail", reason=res.get("reason", "?")),
            )

    csv_btn = ft.OutlinedButton(
        content=ft.Text("CSV"),
        icon=ft.icons.Icons.FILE_DOWNLOAD,
        on_click=handle_export_csv,
        tooltip=t("export.csv"),
    )
    pdf_btn = ft.OutlinedButton(
        content=ft.Text("PDF"),
        icon=ft.icons.Icons.PICTURE_AS_PDF,
        on_click=handle_export_pdf,
        tooltip=t("export.pdf"),
    )
    xlsx_btn = ft.OutlinedButton(
        content=ft.Text("Excel"),
        icon=ft.icons.Icons.TABLE_CHART,
        on_click=handle_export_xlsx,
        tooltip=t("export.xlsx"),
    )
    email_btn = ft.OutlinedButton(
        content=ft.Text(t("stock_alerts.send_email")),
        icon=ft.icons.Icons.EMAIL,
        on_click=handle_email_alert,
    )

    toolbar = ft.Row(
        [search, csv_btn, pdf_btn, xlsx_btn, email_btn],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True,
    )
    search.expand = True

    body = ft.Container(
        content=table if alertas else _empty_state(C),
        padding=20,
        expand=True,
    )

    tabs = ft.Tabs(
        length=3,
        selected_index=0,
        content=ft.Column(
            expand=True,
            controls=[
                tab_bar,
                ft.TabBarView(
                    expand=True,
                    controls=[ft.Container(expand=True, content=body)],
                ),
            ],
        ),
    )

    def _rerender_table():
        new_rows = build_rows()
        table.rows = new_rows
        body.content = table if new_rows else _empty_state(C, filtered=True)
        app.page.update()

    content = ft.Column(
        [
            AppHeader.create(t("stock_alerts.title"), subtitle),
            ft.Container(
                content=kpi_row, padding=ft.padding.Padding(left=20, right=20, top=10, bottom=0)
            ),
            ft.Container(
                content=tabs, padding=ft.padding.Padding(left=20, right=20, top=10, bottom=0)
            ),
            ft.Container(
                content=toolbar, padding=ft.padding.Padding(left=20, right=20, top=10, bottom=0)
            ),
            body,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()


async def show_warehouses(app):
    """Display warehouses management view."""
    almacenes = await app.controller.obtener_almacenes()

    async def open_new(e):
        await show_warehouse_form(app, None)

    async def handle_edit(e, alm):
        await show_warehouse_form(app, alm)

    async def handle_delete(e, alm):
        def confirm(ev):
            app.page.pop_dialog()
            asyncio.create_task(_do_delete(alm))

        dialog = ft.AlertDialog(
            title=ft.Text(t("common.delete")),
            content=ft.Text(t("warehouses.delete_confirm", name=alm.get("nombre", ""))),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda e: app.page.pop_dialog()),
                ft.TextButton(t("common.delete"), on_click=confirm),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    async def _do_delete(alm):
        ok, _ = await app.controller.eliminar_almacen(alm.get("id"))
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
            await show_warehouses(app)
        else:
            SnackBarHelper.error(app.page, t("common.error"))

    async def handle_inventory(e, alm):
        await show_warehouse_inventory(app, alm)

    def build_rows():
        rows = []
        for a in almacenes:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(a.get("nombre", "")))),
                        ft.DataCell(ft.Text(str(a.get("ubicacion", "")) or "-")),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.Icons.INVENTORY,
                                        icon_color=THEME_PRIMARY_COLOR,
                                        tooltip=t("warehouses.inventory"),
                                        on_click=lambda e, aa=a: asyncio.create_task(
                                            handle_inventory(e, aa)
                                        ),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.Icons.CREATE,
                                        icon_color=THEME_PRIMARY_COLOR,
                                        on_click=lambda e, aa=a: asyncio.create_task(
                                            handle_edit(e, aa)
                                        ),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.Icons.DELETE,
                                        icon_color=THEME_ACCENT_COLOR,
                                        on_click=lambda e, aa=a: asyncio.create_task(
                                            handle_delete(e, aa)
                                        ),
                                    ),
                                ],
                                spacing=2,
                            )
                        ),
                    ]
                )
            )
        return rows

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(t("warehouses.name"))),
            ft.DataColumn(ft.Text(t("warehouses.location"))),
            ft.DataColumn(ft.Text("Acciones")),
        ],
        rows=build_rows(),
    )

    new_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.ADD, color="white"),
                ft.Text(t("warehouses.new"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    content = ft.Column(
        [
            AppHeader.create(t("warehouses.title"), t("warehouses.subtitle")),
            ft.Container(content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END), padding=20),
            ft.Container(content=table, padding=20, expand=True)
            if almacenes
            else ft.Container(
                content=ft.Text(t("warehouses.empty"), color="gray600"),
                padding=40,
                alignment="center",
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()


async def show_warehouse_form(app, almacen):
    """Show warehouse add/edit dialog."""
    is_edit = almacen is not None
    nombre = FormField.create_text_field(label=t("warehouses.name"), required=True)
    ubicacion = FormField.create_text_field(label=t("warehouses.location_label"))

    if is_edit:
        nombre.value = almacen.get("nombre", "")
        ubicacion.value = almacen.get("ubicacion", "")

    async def save(e):
        if not nombre.value or len(nombre.value) < 2:
            SnackBarHelper.error(app.page, t("common.validation_error"))
            return
        if is_edit:
            ok, _ = await app.controller.actualizar_almacen(
                almacen["id"], nombre=nombre.value, ubicacion=ubicacion.value
            )
        else:
            ok, _ = await app.controller.crear_almacen(
                nombre=nombre.value, ubicacion=ubicacion.value
            )
        app.page.pop_dialog()
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
            await show_warehouses(app)
        else:
            SnackBarHelper.error(app.page, t("common.error"))

    dialog = ft.AlertDialog(
        title=ft.Text(t("warehouses.edit") if is_edit else t("warehouses.new")),
        content=ft.Column([nombre, ubicacion], tight=True, spacing=10),
        actions=[
            ft.TextButton(t("common.cancel"), on_click=lambda e: app.page.pop_dialog()),
            ft.TextButton(t("common.save"), on_click=save),
        ],
    )
    dialog.open = True
    app.page.show_dialog(dialog)
    app.page.update()


async def show_warehouse_stock(app):
    """View all warehouse stock combined."""
    stock = await app.controller.obtener_todo_stock_almacenes()
    rows = []
    for s in stock:
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(s.get("almacen_nombre", "")))),
                    ft.DataCell(ft.Text(str(s.get("producto_codigo", "")))),
                    ft.DataCell(ft.Text(str(s.get("producto_nombre", "")))),
                    ft.DataCell(ft.Text(str(s.get("cantidad", 0)), weight=ft.FontWeight.BOLD)),
                ]
            )
        )

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Almacén")),
            ft.DataColumn(ft.Text("Código")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Cantidad")),
        ],
        rows=rows,
    )

    async def go_back(e):
        await show_warehouses(app)

    content = ft.Column(
        [
            AppHeader.create(t("warehouses.stock"), t("warehouses.subtitle")),
            ft.Container(
                content=ft.Button(content=ft.Text("← Volver"), on_click=go_back), padding=20
            ),
            ft.Container(content=table, padding=20, expand=True),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()


async def show_warehouse_inventory(app, almacen):
    """Display inventory for a specific warehouse."""
    inv = await app.controller.obtener_inventario_almacen(almacen["id"])

    async def adjust_stock(item):
        pid = item["producto_id"]
        wh_c = app._get_colors()
        qty = ft.TextField(
            label=t("warehouses.new_qty"),
            value=str(item.get("cantidad", 0)),
            width=200,
            border_color=wh_c["input_border"],
            focused_border_color=wh_c["focus_ring"],
            filled=True,
            fill_color=wh_c["input_fill"],
            color=wh_c["text_on_input"],
            cursor_color=wh_c["cursor"],
            selection_color=wh_c["selection"],
            label_style=ft.TextStyle(color=wh_c["text_secondary"]),
            text_style=ft.TextStyle(color=wh_c["text_on_input"], size=14),
        )

        async def save(e):
            app.page.pop_dialog()
            try:
                new_qty = int(qty.value)
            except ValueError:
                SnackBarHelper.error(app.page, t("common.validation_error"))
                return
            ok, _ = await app.controller.ajustar_stock_almacen(pid, almacen["id"], new_qty)
            if ok:
                SnackBarHelper.success(app.page, t("common.success"))
                await show_warehouse_inventory(app, almacen)
            else:
                SnackBarHelper.error(app.page, t("common.error"))

        dialog = ft.AlertDialog(
            title=ft.Text(f"{t('warehouses.adjust_stock')}: {item.get('producto_nombre', '')}"),
            content=ft.Column(
                [
                    ft.Text(f"{t('warehouses.current_qty')}: {item.get('cantidad', 0)}"),
                    qty,
                ],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda e: app.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    def build_rows():
        rows = []
        for item in inv:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(item.get("producto_codigo", "")))),
                        ft.DataCell(ft.Text(str(item.get("producto_nombre", "")))),
                        ft.DataCell(
                            ft.Text(str(item.get("cantidad", 0)), weight=ft.FontWeight.BOLD)
                        ),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.icons.Icons.EDIT_SQUARE,
                                icon_color=THEME_PRIMARY_COLOR,
                                on_click=lambda e, it=item: asyncio.create_task(adjust_stock(it)),
                            )
                        ),
                    ]
                )
            )
        return rows

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Código")),
            ft.DataColumn(ft.Text(t("warehouses.product"))),
            ft.DataColumn(ft.Text(t("warehouses.current_qty"))),
            ft.DataColumn(ft.Text("Acción")),
        ],
        rows=build_rows(),
    )

    async def go_back(e):
        await show_warehouses(app)

    content = ft.Column(
        [
            AppHeader.create(
                f"{almacen.get('nombre', '')} - {t('warehouses.inventory')}",
                t("warehouses.subtitle"),
            ),
            ft.Container(
                content=ft.Button(content=ft.Text("← Volver"), on_click=go_back), padding=20
            ),
            ft.Container(content=table, padding=20, expand=True)
            if inv
            else ft.Container(
                content=ft.Text("Sin productos en este almacén", color="gray600"),
                padding=40,
                alignment="center",
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()
