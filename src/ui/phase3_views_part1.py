"""
Phase 3 UI views — part 1: variants, customizable reports.

Companion to phase3_views_part2.py. Re-exported by ui/phase3_views.py.
"""

from __future__ import annotations

import asyncio

import flet as ft

from config.settings import (
    THEME_ACCENT_COLOR,
    THEME_PRIMARY_COLOR,
    THEME_SUCCESS_COLOR,
)
from ui.components import (
    AppHeader,
    FormField,
    SnackBarHelper,
)
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


# ============ Variantes de producto ============


async def show_variantes(view) -> None:
    """List variants of a chosen product, with create/delete."""
    page = view.page
    main_view = view.main_view
    controller = view.controller

    productos = await controller.obtener_todos_productos()
    prod_opts = [f"{p.get('id')} — {p.get('codigo')} ({p.get('nombre')})" for p in productos]
    sel = ft.Dropdown(
        label=t("phase3.variantes.producto"),
        options=[ft.dropdown.Option(o) for o in prod_opts],
        value=prod_opts[0] if prod_opts else None,
        width=420,
        fill_color="#F8FAFC",
        color="#0F172A",
        text_style=ft.TextStyle(color="#0F172A", size=14),
    )

    async def refresh():
        if not sel.value:
            if main_view:
                main_view.content = ft.Column(
                    [
                        AppHeader.create(
                            t("phase3.variantes.title"),
                            t("phase3.variantes.subtitle"),
                        ),
                        ft.Container(
                            content=ft.Text(
                                t("phase3.variantes.no_products"),
                                color="#475569",
                            ),
                            padding=20,
                        ),
                    ],
                    expand=True,
                )
                page.update()
            return
        producto_id = int(sel.value.split(" — ")[0])
        variantes = await controller.obtener_variantes(producto_id=producto_id)
        rows = []
        for v in variantes:
            vid = v.get("id")
            attrs = v.get("atributos_dict", {})
            attrs_str = ", ".join(f"{k}={v}" for k, v in attrs.items())
            precio = v.get("precio_override")
            precio_str = f"${precio:,.2f}" if precio is not None else "(base)"
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(v.get("sku", "")))),
                        ft.DataCell(ft.Text(attrs_str)),
                        ft.DataCell(ft.Text(str(v.get("cantidad", 0)), weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(precio_str)),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.Icons.EDIT,
                                        tooltip=t("phase3.variantes.ajustar"),
                                        on_click=lambda ev, x=vid: asyncio.create_task(
                                            open_adjust(x)
                                        ),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.Icons.DELETE,
                                        icon_color=THEME_ACCENT_COLOR,
                                        tooltip=t("phase3.variantes.eliminar"),
                                        on_click=lambda ev, x=vid: asyncio.create_task(
                                            do_delete(x)
                                        ),
                                    ),
                                ],
                                spacing=2,
                            )
                        ),
                    ]
                )
            )
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("SKU")),
                ft.DataColumn(ft.Text(t("phase3.variantes.atributos"))),
                ft.DataColumn(ft.Text(t("phase3.variantes.cantidad"))),
                ft.DataColumn(ft.Text(t("phase3.variantes.precio"))),
                ft.DataColumn(ft.Text(t("common.actions"))),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )
        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text(t("phase3.variantes.empty"), color="#475569"),
                padding=40,
            )
        )
        if main_view:
            main_view.content = ft.Column(
                [
                    AppHeader.create(
                        t("phase3.variantes.title"),
                        t("phase3.variantes.subtitle"),
                    ),
                    ft.Container(
                        content=ft.Row(
                            [sel, new_btn],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=20,
                    ),
                    body,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            page.update()

    sel.on_change = lambda e: asyncio.create_task(refresh())

    async def open_adjust(vid: int):
        cantidad = FormField.create_text_field(t("phase3.variantes.cantidad"))
        precio = FormField.create_text_field(t("phase3.variantes.precio_override"))
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, _ = await controller.actualizar_stock_variante(
                    variante_id=vid,
                    cantidad=int(cantidad.value or 0),
                )
            except Exception as ex:
                err.value = str(ex)
                page.update()
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, t("phase3.variantes.stock_updated"))
                await refresh()
            else:
                SnackBarHelper.error(page, t("common.error"))

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase3.variantes.ajustar")),
            content=ft.Column([cantidad, precio, err], tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        page.show_dialog(dialog)
        page.update()

    async def do_delete(vid: int):
        ok, _ = await controller.eliminar_variante(vid)
        if ok:
            SnackBarHelper.success(page, t("phase3.variantes.deleted"))
            await refresh()
        else:
            SnackBarHelper.error(page, t("common.error"))

    async def open_new(e):
        sku = FormField.create_text_field("SKU")
        atributos = FormField.create_text_field(
            t("phase3.variantes.atributos"),
            hint="talla=M,color=rojo",
        )
        cantidad = FormField.create_text_field(t("phase3.variantes.cantidad"))
        precio_override = FormField.create_text_field(t("phase3.variantes.precio_override"))
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            if not sel.value:
                err.value = "Selecciona un producto"
                page.update()
                return
            try:
                attrs_dict = {}
                for pair in (atributos.value or "").split(","):
                    pair = pair.strip()
                    if not pair or "=" not in pair:
                        continue
                    k, v = pair.split("=", 1)
                    attrs_dict[k.strip()] = v.strip()
                if not attrs_dict:
                    err.value = "Atributos vacíos"
                    page.update()
                    return
                ok, res = await controller.crear_variante(
                    producto_id=int(sel.value.split(" — ")[0]),
                    sku=sku.value or "",
                    atributos=attrs_dict,
                    cantidad=int(cantidad.value or 0),
                    precio_override=float(precio_override.value) if precio_override.value else None,
                )
            except Exception as ex:
                err.value = str(ex)
                page.update()
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, t("phase3.variantes.created"))
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase3.variantes.new")),
            content=ft.Column(
                [sku, atributos, cantidad, precio_override, err],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        page.show_dialog(dialog)
        page.update()

    new_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.ADD, color="white"),
                ft.Text(t("phase3.variantes.new"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )
    await refresh()


# ============ Reportes personalizables ============


async def show_reportes(view) -> None:
    """Build and run reports from saved templates, or ad-hoc."""
    page = view.page
    main_view = view.main_view
    controller = view.controller

    modulos = await controller.obtener_modulos_reporte()
    modulo_sel = ft.Dropdown(
        label=t("phase3.reportes.modulo"),
        options=[ft.dropdown.Option(key=m["key"], text=m["key"]) for m in modulos],
        value=modulos[0]["key"] if modulos else None,
        width=180,
        fill_color="#F8FAFC",
        color="#0F172A",
        text_style=ft.TextStyle(color="#0F172A", size=14),
    )
    columnas_sel: dict[str, ft.Checkbox] = {}
    col_checkboxes = ft.Row(wrap=True, spacing=10)

    resultados_container = ft.Container(padding=20, expand=True)

    async def rebuild_column_choices():
        if not modulo_sel.value:
            return
        mod = next((m for m in modulos if m["key"] == modulo_sel.value), None)
        if not mod:
            return
        col_checkboxes.controls.clear()
        columnas_sel.clear()
        for col in mod["columns"]:
            cb = ft.Checkbox(label=col)
            columnas_sel[col] = cb
            col_checkboxes.controls.append(cb)
        page.update()

    modulo_sel.on_change = lambda e: asyncio.create_task(rebuild_column_choices())

    agrup_sel = ft.Dropdown(
        label=t("phase3.reportes.agrupar_por"),
        options=[ft.dropdown.Option(key="", text="(sin grupo)")],
        width=200,
        fill_color="#F8FAFC",
        color="#0F172A",
        text_style=ft.TextStyle(color="#0F172A", size=14),
    )
    orden_sel = ft.Dropdown(
        label=t("phase3.reportes.ordenar_por"),
        options=[ft.dropdown.Option(key="", text="(defecto)")],
        width=200,
        fill_color="#F8FAFC",
        color="#0F172A",
        text_style=ft.TextStyle(color="#0F172A", size=14),
    )

    async def update_grouping_options():
        if not modulo_sel.value:
            return
        mod = next((m for m in modulos if m["key"] == modulo_sel.value), None)
        if not mod:
            return
        opts = [ft.dropdown.Option(key="", text="(sin grupo)")] + [
            ft.dropdown.Option(key=c, text=c) for c in mod["columns"]
        ]
        agrup_sel.options = opts
        orden_sel.options = [ft.dropdown.Option(key="", text="(defecto)")] + [
            ft.dropdown.Option(key=c, text=c) for c in mod["columns"]
        ]
        page.update()

    modulo_sel.on_change = lambda e: asyncio.create_task(_chain_update())

    async def _chain_update():
        await rebuild_column_choices()
        await update_grouping_options()

    async def do_run(e=None):
        cols = [k for k, cb in columnas_sel.items() if cb.value]
        if not cols:
            SnackBarHelper.error(page, t("phase3.reportes.no_columns"))
            return
        filtros = {}
        # Filtro rápido: stock_min (productos)
        if modulo_sel.value == "productos":
            stock_min_v = stock_min_filter.value.strip()
            if stock_min_v:
                try:
                    filtros["stock_min"] = int(stock_min_v)
                except ValueError:
                    SnackBarHelper.error(page, t("phase3.reportes.invalid_stock"))
                    return
        res = await controller.ejecutar_reporte(
            modulo=modulo_sel.value,
            columnas=cols,
            filtros=filtros,
            agrupacion=agrup_sel.value or None,
            ordenado_por=orden_sel.value or None,
        )
        if "error" in res:
            SnackBarHelper.error(page, res["error"])
            return
        rows = res.get("rows", [])
        if not rows:
            resultados_container.content = ft.Container(
                content=ft.Text(t("phase3.reportes.no_results"), color="#475569"),
                padding=20,
            )
        else:
            data_cols = [ft.DataColumn(ft.Text(c)) for c in cols]
            data_rows = [
                ft.DataRow(cells=[ft.DataCell(ft.Text(str(r.get(c, "")))) for c in cols])
                for r in rows[:500]
            ]
            table = ft.DataTable(
                columns=data_cols,
                rows=data_rows,
                heading_row_color="#DBEAFE",
            )
            resultados_container.content = ft.Column(
                [
                    ft.Text(
                        f"{t('phase3.reportes.total_rows')}: {res.get('total', 0)}",
                        size=12,
                        color="#475569",
                    ),
                    ft.Container(content=table, padding=10, expand=True),
                ],
                scroll=ft.ScrollMode.AUTO,
            )
        page.update()

    stock_min_filter = ft.TextField(
        label=t("phase3.reportes.stock_min_filter"),
        width=140,
        value="",
        hint_text="0",
    )

    async def open_save_template(e):
        nombre = FormField.create_text_field(t("phase3.reportes.template_name"))
        cols = [k for k, cb in columnas_sel.items() if cb.value]
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            if not nombre.value:
                err.value = t("phase3.reportes.name_required")
                page.update()
                return
            filtros = {}
            if modulo_sel.value == "productos" and stock_min_filter.value.strip():
                try:
                    filtros["stock_min"] = int(stock_min_filter.value.strip())
                except ValueError:
                    err.value = t("phase3.reportes.invalid_stock")
                    page.update()
                    return
            ok, res = await controller.guardar_plantilla_reporte(
                nombre=nombre.value,
                modulo=modulo_sel.value,
                columnas=cols,
                filtros=filtros,
                agrupacion=agrup_sel.value or None,
                ordenado_por=orden_sel.value or None,
            )
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, t("phase3.reportes.template_saved"))
                await load_templates()
            else:
                err.value = (res or {}).get("error", "Error")
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase3.reportes.save_template")),
            content=ft.Column([nombre, err], tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        page.show_dialog(dialog)
        page.update()

    template_list = ft.Column(spacing=6)

    async def load_templates():
        plantillas = await controller.obtener_plantillas_reporte()
        template_list.controls.clear()
        if not plantillas:
            template_list.controls.append(
                ft.Text(t("phase3.reportes.no_templates"), color="#475569", size=12)
            )
        for pl in plantillas:
            pid = pl.get("id")
            cols_short = ", ".join(pl.get("columnas", [])[:4])
            template_list.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        pl.get("nombre", ""),
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        f"{pl.get('modulo')} · {cols_short}",
                                        size=11,
                                        color="#475569",
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.icons.Icons.PLAY_ARROW,
                                tooltip=t("phase3.reportes.run"),
                                on_click=lambda ev, p=pl: asyncio.create_task(run_template(p)),
                            ),
                            ft.IconButton(
                                icon=ft.icons.Icons.DELETE,
                                icon_color=THEME_ACCENT_COLOR,
                                tooltip=t("phase3.reportes.delete"),
                                on_click=lambda ev, x=pid: asyncio.create_task(
                                    do_delete_template(x)
                                ),
                            ),
                        ]
                    ),
                    padding=10,
                    border_radius=6,
                    bgcolor="#FFFFFF",
                    border=ft.border.Border(
                        ft.BorderSide(1, "#E2E8F0"),
                        ft.BorderSide(1, "#E2E8F0"),
                        ft.BorderSide(1, "#E2E8F0"),
                        ft.BorderSide(1, "#E2E8F0"),
                    ),
                )
            )
        page.update()

    async def run_template(pl):
        res = await controller.ejecutar_reporte(
            modulo=pl["modulo"],
            columnas=pl.get("columnas", []),
            filtros=pl.get("filtros") or None,
            agrupacion=pl.get("agrupacion"),
            ordenado_por=pl.get("ordenado_por"),
        )
        if "error" in res:
            SnackBarHelper.error(page, res["error"])
            return
        rows = res.get("rows", [])
        cols = pl.get("columnas", [])
        if not rows:
            resultados_container.content = ft.Container(
                content=ft.Text(t("phase3.reportes.no_results"), color="#475569"),
                padding=20,
            )
        else:
            data_cols = [ft.DataColumn(ft.Text(c)) for c in cols]
            data_rows = [
                ft.DataRow(cells=[ft.DataCell(ft.Text(str(r.get(c, "")))) for c in cols])
                for r in rows[:500]
            ]
            table = ft.DataTable(
                columns=data_cols,
                rows=data_rows,
                heading_row_color="#DBEAFE",
            )
            resultados_container.content = ft.Column(
                [
                    ft.Text(
                        f"{pl['nombre']} — {res.get('total', 0)} filas",
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Container(content=table, padding=10, expand=True),
                ],
                scroll=ft.ScrollMode.AUTO,
            )
        page.update()

    async def do_delete_template(pid):
        ok, _ = await controller.eliminar_plantilla_reporte(pid)
        if ok:
            SnackBarHelper.success(page, t("phase3.reportes.template_deleted"))
            await load_templates()
        else:
            SnackBarHelper.error(page, t("common.error"))

    run_btn = ft.Button(
        content=ft.Text(t("phase3.reportes.run")),
        on_click=do_run,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )
    save_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.SAVE, color="white"),
                ft.Text(t("phase3.reportes.save_template"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_save_template,
        style=ft.ButtonStyle(bgcolor=THEME_SUCCESS_COLOR),
    )

    if main_view:
        main_view.content = ft.Column(
            [
                AppHeader.create(
                    t("phase3.reportes.title"),
                    t("phase3.reportes.subtitle"),
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [modulo_sel, stock_min_filter, agrup_sel, orden_sel],
                                spacing=10,
                                wrap=True,
                            ),
                            col_checkboxes,
                            ft.Row([run_btn, save_btn], spacing=10),
                        ],
                        spacing=10,
                    ),
                    padding=20,
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(content=resultados_container, expand=True),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text(
                                            t("phase3.reportes.saved_templates"),
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        template_list,
                                    ],
                                    spacing=6,
                                ),
                                width=320,
                                padding=10,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=10,
                    expand=True,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        page.update()

    await rebuild_column_choices()
    await update_grouping_options()
    await load_templates()
