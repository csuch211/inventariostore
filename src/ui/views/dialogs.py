"""Standalone dialog functions extracted from AppView."""

import asyncio
import contextlib

import flet as ft

from config.settings import (
    THEME_ACCENT_COLOR,
    THEME_PRIMARY_COLOR,
    THEME_SURFACE_COLOR,
)
from ui.components import (
    AppHeader,
    FormField,
    SnackBarHelper,
)
from utils.i18n import t


async def show_stock_management(app):
    """Display stock management interface"""
    products = await app.controller.obtener_todos_productos()

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
            history = await app.controller.obtener_historial_stock(selected_product.get("id", 0))
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
            app.page.update()

    product_dropdown = ft.Dropdown(
        label="Selecciona un producto",
        options=[
            ft.dropdown.Option(key=str(p.get("id", "")), text=p.get("nombre", "")) for p in products
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
        from ui.app_view import AppView

        return AppView._find_submit_btn_static(
            app.main_view, label
        ) or AppView._find_submit_btn_static(app.page, label)

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
            SnackBarHelper.error(app.page, "Selecciona un producto")
            return

        if not cantidad_ajuste.value or not tipo_movimiento.value:
            SnackBarHelper.error(app.page, "Completa todos los campos")
            return

        try:
            success, result = await app.controller.actualizar_stock(
                producto_id=selected_product.get("id", 0),
                cantidad_nueva=cantidad_ajuste.value,
                tipo_movimiento=tipo_movimiento.value,
                razon=razon_field.value,
            )

            if success:
                SnackBarHelper.success(app.page, "Stock actualizado")
                razon_field.value = ""
                selected_product = result if isinstance(result, dict) else selected_product
                history = await app.controller.obtener_historial_stock(
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
                app.page.update()

        except Exception as ex:
            SnackBarHelper.error(app.page, f"Error: {ex!s}")

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
                on_click=lambda e: app.page.pop_dialog(),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    app.page.show_dialog(dialog)
    app.page.update()


async def show_export_options(app):
    """Display export options"""
    export_status = ft.Text("", size=12)

    async def handle_export_csv(e):
        """Export to CSV"""
        try:
            export_status.value = "Exportando CSV..."
            export_btn_csv.disabled = True
            app.page.update()

            success, path = await app.controller.exportar_csv()
            if success:
                SnackBarHelper.success(app.page, f"CSV exportado: {path}")
                export_status.value = f"✓ Exportado a: {path}"
            else:
                SnackBarHelper.error(app.page, f"Error: {path}")
                export_status.value = f"✗ Error: {path}"

        except Exception as ex:
            SnackBarHelper.error(app.page, f"Error: {ex!s}")
            export_status.value = f"✗ Error: {ex!s}"
        finally:
            export_btn_csv.disabled = False
            app.page.update()

    async def handle_export_json(e):
        """Export to JSON"""
        try:
            export_status.value = "Exportando JSON..."
            export_btn_json.disabled = True
            app.page.update()

            success, path = await app.controller.exportar_json()
            if success:
                SnackBarHelper.success(app.page, f"JSON exportado: {path}")
                export_status.value = f"✓ Exportado a: {path}"
            else:
                SnackBarHelper.error(app.page, f"Error: {path}")
                export_status.value = f"✗ Error: {path}"

        except Exception as ex:
            SnackBarHelper.error(app.page, f"Error: {ex!s}")
            export_status.value = f"✗ Error: {ex!s}"
        finally:
            export_btn_json.disabled = False
            app.page.update()

    async def handle_export_report(e):
        """Export summary report"""
        try:
            export_status.value = "Generando reporte..."
            export_btn_report.disabled = True
            app.page.update()

            success, path = await app.controller.exportar_reporte()
            if success:
                SnackBarHelper.success(app.page, f"Reporte exportado: {path}")
                export_status.value = f"✓ Exportado a: {path}"
            else:
                SnackBarHelper.error(app.page, f"Error: {path}")
                export_status.value = f"✗ Error: {path}"

        except Exception as ex:
            SnackBarHelper.error(app.page, f"Error: {ex!s}")
            export_status.value = f"✗ Error: {ex!s}"
        finally:
            export_btn_report.disabled = False
            app.page.update()

    async def handle_export_pdf(e):
        """Export to PDF"""
        try:
            export_status.value = "Exportando PDF..."
            export_btn_pdf.disabled = True
            app.page.update()

            success, path = await app.controller.exportar_pdf()
            if success:
                SnackBarHelper.success(app.page, f"PDF exportado: {path}")
                export_status.value = f"✓ Exportado a: {path}"
            else:
                SnackBarHelper.error(app.page, f"Error: {path}")
                export_status.value = f"✗ Error: {path}"

        except Exception as ex:
            SnackBarHelper.error(app.page, f"Error: {ex!s}")
            export_status.value = f"✗ Error: {ex!s}"
        finally:
            export_btn_pdf.disabled = False
            app.page.update()

    async def handle_export_xlsx(e):
        """Export to Excel"""
        try:
            export_status.value = "Exportando Excel..."
            export_btn_xlsx.disabled = True
            app.page.update()

            success, path = await app.controller.exportar_xlsx()
            if success:
                SnackBarHelper.success(app.page, f"Excel exportado: {path}")
                export_status.value = f"✓ Exportado a: {path}"
            else:
                SnackBarHelper.error(app.page, f"Error: {path}")
                export_status.value = f"✗ Error: {path}"

        except Exception as ex:
            SnackBarHelper.error(app.page, f"Error: {ex!s}")
            export_status.value = f"✗ Error: {ex!s}"
        finally:
            export_btn_xlsx.disabled = False
            app.page.update()

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
        C = app._get_colors()
        path_field = FormField.create_text_field(
            label=t("export.import_path_label"),
            hint=t("export.import_path_hint"),
            page=app.page,
            colors=C,
        )
        path_field.width = 480

        async def do_import(_e):
            path = (path_field.value or "").strip()
            if not path:
                SnackBarHelper.error(app.page, t("export.import_path_label"))
                return
            path = path.strip('"').strip("'")
            lower = path.lower()
            app.page.pop_dialog()
            if lower.endswith(".xlsx"):
                success, errors = await app.controller.importar_productos_xlsx(path)
            else:
                success, errors = await app.controller.importar_productos_csv(path)
            if errors:
                SnackBarHelper.success(
                    app.page,
                    t(
                        "export.import_partial",
                        success=success,
                        errors=len(errors),
                    ),
                )
                preview = "; ".join(errors[:3])
                if len(errors) > 3:
                    preview += f" (+{len(errors) - 3} más)"
                export_status.value = preview
            else:
                SnackBarHelper.success(app.page, t("export.import_success", success=success))
                export_status.value = f"✓ Importados: {success}"
            app.page.update()
            if app._current_route in ("products", "dashboard"):
                with contextlib.suppress(Exception):
                    await app._navigate_to(app._current_route)

        dialog = ft.AlertDialog(
            title=ft.Text(t("export.import_dialog_title")),
            content=ft.Container(content=path_field, padding=10),
            actions=[
                ft.TextButton(
                    t("common.cancel"),
                    on_click=lambda e: app.page.pop_dialog(),
                ),
                ft.TextButton(t("common.save"), on_click=do_import),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

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

    if app.main_view:
        app.main_view.content = content
        app.page.update()


async def show_purchase_orders(app):
    """Display purchase orders view."""
    ordenes = await app.controller.obtener_ordenes_compra()

    async def open_new(e):
        await show_order_form(app)

    async def handle_receive(e, orden):
        ok, result = await app.controller.recibir_orden(orden.get("id"))
        if ok:
            SnackBarHelper.success(
                app.page, t("purchase_orders.received_success", id=orden.get("id"))
            )
            await app._refresh_nav_badges()
            await show_purchase_orders(app)
        else:
            SnackBarHelper.error(app.page, result.get("error", t("common.error")))

    async def handle_cancel(e, orden):
        ok, _ = await app.controller.cancelar_orden(orden.get("id"))
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
            await show_purchase_orders(app)
        else:
            SnackBarHelper.error(app.page, t("common.error"))

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

    if app.main_view:
        app.main_view.content = content
        app.page.update()


async def show_order_form(app):
    """Show new purchase order form."""
    proveedores = await app.controller.obtener_proveedores()
    productos = await app.controller.obtener_todos_productos()

    if not proveedores or not productos:
        SnackBarHelper.error(
            app.page,
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
            SnackBarHelper.error(app.page, t("common.validation_error"))
            return
        if not proveedor_dd.value or not producto_dd.value or qty <= 0:
            SnackBarHelper.error(app.page, t("common.validation_error"))
            return
        ok, result = await app.controller.crear_orden_compra(
            proveedor_id=int(proveedor_dd.value),
            producto_id=int(producto_dd.value),
            cantidad=qty,
        )
        app.page.pop_dialog()
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
            await show_purchase_orders(app)
        else:
            SnackBarHelper.error(app.page, result.get("error", t("common.error")))

    dialog = ft.AlertDialog(
        title=ft.Text(t("purchase_orders.new")),
        content=ft.Column([proveedor_dd, producto_dd, cantidad], tight=True, spacing=10),
        actions=[
            ft.TextButton(t("common.cancel"), on_click=lambda e: app.page.pop_dialog()),
            ft.TextButton(t("common.save"), on_click=save),
        ],
    )
    dialog.open = True
    app.page.show_dialog(dialog)
    app.page.update()
