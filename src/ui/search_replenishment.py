"""Search and replenishment views, refactored for clarity.
Advanced inventory views — search and replenishment: advanced search, auto-restock.

Companion to inventory_operations.py and pricing_inventory.py.
Re-exported by ui/advanced_inventory.py.
"""

from __future__ import annotations

import asyncio

import flet as ft

from config.settings import (
    THEME_PRIMARY_COLOR,
    THEME_SUCCESS_COLOR,
)
from core.theme_manager import theme_manager
from ui.components import (
    AppHeader,
    FormField,
    SnackBarHelper,
)
from utils.i18n import t

from ._utils import _fmt_money, get_logger

logger = get_logger(__name__)


def _c(view):
    """Get the active color palette."""
    return theme_manager.palette(page=view.page)


# ============ V8: Búsqueda avanzada ============


async def show_busqueda(view) -> None:
    c = _c(view)
    page = view.page
    main_view = view.main_view
    controller = view.controller

    categorias = await controller.obtener_categorias()
    proveedores = await controller.obtener_proveedores()

    texto = FormField.create_text_field(t("phase1.busqueda.texto"))
    cat_opts = [""] + [c.get("nombre", "") for c in categorias]
    categoria = FormField.create_dropdown(t("phase1.busqueda.categoria"), cat_opts)
    prov_opts = [""] + [str(p.get("id")) for p in proveedores]
    proveedor = FormField.create_dropdown(t("phase1.busqueda.proveedor"), prov_opts)
    precio_min = FormField.create_text_field(t("phase1.busqueda.precio_min"))
    precio_max = FormField.create_text_field(t("phase1.busqueda.precio_max"))
    stock_min = FormField.create_text_field(t("phase1.busqueda.stock_min"))
    stock_max = FormField.create_text_field(t("phase1.busqueda.stock_max"))
    solo_bajo = ft.Checkbox(label=t("phase1.busqueda.solo_bajo"))
    orden = FormField.create_dropdown(
        t("phase1.busqueda.orden"),
        ["nombre", "precio", "cantidad", "creado_en", "actualizado_en"],
    )

    async def do_search(e=None):
        try:
            kwargs = {}
            if texto.value:
                kwargs["texto"] = texto.value
            if categoria.value:
                kwargs["categoria"] = categoria.value
            if proveedor.value:
                kwargs["proveedor_id"] = int(proveedor.value)
            if precio_min.value:
                kwargs["precio_min"] = float(precio_min.value)
            if precio_max.value:
                kwargs["precio_max"] = float(precio_max.value)
            if stock_min.value:
                kwargs["stock_min"] = int(stock_min.value)
            if stock_max.value:
                kwargs["stock_max"] = int(stock_max.value)
            if solo_bajo.value:
                kwargs["solo_bajo_stock"] = True
            if orden.value:
                kwargs["orden"] = orden.value
            res = await controller.buscar_productos_avanzado(**kwargs)
        except Exception:
            SnackBarHelper.error(page, "Error al buscar productos.")
            return
        rows = []
        for p in res:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(p.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(p.get("nombre", "")))),
                        ft.DataCell(ft.Text(str(p.get("cantidad", 0)))),
                        ft.DataCell(ft.Text(_fmt_money(p.get("precio", 0)))),
                        ft.DataCell(ft.Text(str(p.get("categoria", "") or "-"))),
                        ft.DataCell(ft.Text(str(p.get("proveedor_nombre", "") or "-"))),
                    ]
                )
            )
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(t("products.code"))),
                ft.DataColumn(ft.Text(t("phase1.devoluciones.producto"))),
                ft.DataColumn(ft.Text("Stock")),
                ft.DataColumn(ft.Text("Precio")),
                ft.DataColumn(ft.Text(t("phase1.busqueda.categoria"))),
                ft.DataColumn(ft.Text(t("phase1.busqueda.proveedor"))),
            ],
            rows=rows,
            heading_row_color=c["primary_light"],
        )
        results_container.content = (
            ft.Container(content=table, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("Sin resultados", color=c["text_secondary"]),
                padding=20,
            )
        )
        page.update()

    buscar_btn = ft.Button(
        content=ft.Text(t("phase1.busqueda.buscar")),
        on_click=do_search,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )
    results_container = ft.Container(padding=20, expand=True)
    filtros = ft.Container(
        content=ft.Column(
            [
                ft.Row([texto, categoria, proveedor], spacing=10, wrap=True),
                ft.Row(
                    [precio_min, precio_max, stock_min, stock_max, solo_bajo, orden, buscar_btn],
                    spacing=10,
                    wrap=True,
                ),
            ],
            spacing=10,
        ),
        padding=20,
    )
    if main_view:
        main_view.content = ft.Column(
            [
                AppHeader.create(
                    t("phase1.busqueda.title"),
                    t("phase1.busqueda.subtitle"),
                ),
                filtros,
                results_container,
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        page.update()
    await do_search()


# ============ V9: Auto-reaprovisionamiento ============


async def show_reabasto(view) -> None:
    c = _c(view)
    page = view.page
    main_view = view.main_view
    controller = view.controller

    proveedores = await controller.obtener_proveedores()

    sel = ft.Dropdown(
        label=t("phase1.reabasto.proveedor"),
        options=[ft.dropdown.Option(key="ALL", text="Todos (auto-asignar)")]
        + [ft.dropdown.Option(key=str(p.get("id")), text=p.get("nombre", "")) for p in proveedores],
        value="ALL",
        width=300,
        fill_color=c["input_fill"],
        color=c["text_primary"],
        text_style=ft.TextStyle(color=c["text_primary"], size=14),
    )

    last_sugerencias = []

    async def refresh():
        nonlocal last_sugerencias
        kw = {}
        if sel.value and sel.value != "ALL":
            kw["supplier_id"] = int(sel.value)
        sugerencias = await controller.sugerir_reabastecimiento(**kw)
        last_sugerencias = sugerencias
        rows = []
        for s in sugerencias:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(s.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(s.get("nombre", "")))),
                        ft.DataCell(ft.Text(str(s.get("cantidad_actual", 0)))),
                        ft.DataCell(ft.Text(str(s.get("stock_min", 0)))),
                        ft.DataCell(
                            ft.Text(str(s.get("cantidad_sugerida", 0)), weight=ft.FontWeight.BOLD)
                        ),
                        ft.DataCell(ft.Text(str(s.get("proveedor_nombre", "") or "-"))),
                    ]
                )
            )
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(t("products.code"))),
                ft.DataColumn(ft.Text(t("phase1.devoluciones.producto"))),
                ft.DataColumn(ft.Text("Actual")),
                ft.DataColumn(ft.Text("Mín.")),
                ft.DataColumn(ft.Text("Sugerido")),
                ft.DataColumn(ft.Text(t("phase1.reabasto.proveedor"))),
            ],
            rows=rows,
            heading_row_color=c["primary_light"],
        )
        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay productos bajo mínimo", color=c["text_secondary"]),
                padding=40,
            )
        )
        if main_view:
            main_view.content = ft.Column(
                [
                    AppHeader.create(
                        t("phase1.reabasto.title"),
                        t("phase1.reabasto.subtitle"),
                    ),
                    ft.Container(
                        content=ft.Row(
                            [sel, crear_btn],
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

    async def do_create(e):
        if not last_sugerencias:
            SnackBarHelper.error(page, "Sin sugerencias para crear")
            return
        if not sel.value or sel.value == "ALL":
            SnackBarHelper.error(page, "Selecciona un proveedor destino concreto")
            return
        ok, res = await controller.crear_ordenes_desde_sugerencias(
            supplier_id=int(sel.value),
            suggestions=last_sugerencias,
        )
        if ok:
            SnackBarHelper.success(page, f"{res['count']} órdenes creadas")
            await refresh()
        else:
            SnackBarHelper.error(page, (res or {}).get("error", "Error"))

    crear_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.SHOPPING_CART, color="white"),
                ft.Text(t("phase1.reabasto.crear_ordenes"), color="white"),
            ],
            spacing=5,
        ),
        on_click=do_create,
        style=ft.ButtonStyle(bgcolor=THEME_SUCCESS_COLOR),
    )
    await refresh()
