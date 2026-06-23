"""
Phase 1 UI views.

Each `show_phase1_<feature>` function renders one feature's screen and binds
to the corresponding controller methods. They are designed as drop-in
companions to AppView: each expects `view.page`, `view.controller`,
`view.main_view` and the same color/header helpers from `ui.components`.

The router lives in `app_view.py`: `ROUTE_PERMISSIONS`, `nav_data_all` and
`_navigate_to` must be extended there to point at the methods defined here.
"""

from __future__ import annotations

import asyncio
from typing import Any

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


def _fmt_money(v) -> str:
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "$0.00"


def _kpi_card(title: str, value: str, icon: Any, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [ft.Icon(icon, color=color, size=24), ft.Text(title, size=12)],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=color),
            ],
            spacing=8,
        ),
        padding=16,
        border_radius=10,
        bgcolor="#FFFFFF",
        border=ft.border.Border(
            ft.BorderSide(1, "#E2E8F0"),
            ft.BorderSide(1, "#E2E8F0"),
            ft.BorderSide(1, "#E2E8F0"),
            ft.BorderSide(1, "#E2E8F0"),
        ),
        width=220,
        height=110,
    )


# ============ V1: Devoluciones ============


async def show_devoluciones(view) -> None:
    page = view.page
    main_view = view.main_view
    controller = view.controller

    async def refresh():
        items = await controller.obtener_devoluciones()
        rows = []
        for it in items:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(it.get("id", "")))),
                        ft.DataCell(ft.Text(str(it.get("venta_id", "")))),
                        ft.DataCell(ft.Text(str(it.get("producto_codigo", "")))),
                        ft.DataCell(ft.Text(str(it.get("producto_nombre", "")))),
                        ft.DataCell(ft.Text(str(it.get("cantidad", 0)))),
                        ft.DataCell(ft.Text(_fmt_money(it.get("subtotal", 0)))),
                        ft.DataCell(ft.Text(str(it.get("motivo", "") or ""))),
                        ft.DataCell(ft.Text(str(it.get("creado_en", "")))),
                    ]
                )
            )
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text(t("phase1.devoluciones.venta"))),
                ft.DataColumn(ft.Text(t("products.code"))),
                ft.DataColumn(ft.Text(t("phase1.devoluciones.producto"))),
                ft.DataColumn(ft.Text(t("phase1.devoluciones.cantidad"))),
                ft.DataColumn(ft.Text(t("sales.subtotal"))),
                ft.DataColumn(ft.Text(t("phase1.devoluciones.motivo"))),
                ft.DataColumn(ft.Text("Fecha")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )
        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text(t("phase1.devoluciones.empty"), color="#475569"),
                padding=40,
            )
        )
        if main_view:
            main_view.content = ft.Column(
                [
                    AppHeader.create(
                        t("phase1.devoluciones.title"),
                        t("phase1.devoluciones.subtitle"),
                    ),
                    ft.Container(
                        content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                        padding=20,
                    ),
                    body,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            page.update()

    async def open_new(e):
        sale_id = ft.TextField(label=t("phase1.devoluciones.sale_id"), width=200)
        producto_id = ft.TextField(label="ID producto", width=200)
        cantidad = ft.TextField(label=t("phase1.devoluciones.cantidad"), width=120)
        precio = ft.TextField(label="Precio unit.", width=120)
        motivo = ft.TextField(label=t("phase1.devoluciones.motivo"), width=300)
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.crear_devolucion(
                    venta_id=int(sale_id.value or 0),
                    items=[
                        {
                            "producto_id": int(producto_id.value or 0),
                            "cantidad": int(cantidad.value or 0),
                            "precio_unitario": float(precio.value or 0),
                        }
                    ],
                    motivo=motivo.value or "",
                )
            except Exception as ex:
                err.value = str(ex)
                page.update()
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, "Devolución registrada")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase1.devoluciones.form_title")),
            content=ft.Column(
                [sale_id, producto_id, cantidad, precio, motivo, err],
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
                ft.Text(t("phase1.devoluciones.new"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )
    await refresh()


# ============ V2: Transferencias ============


async def show_transferencias(view) -> None:
    page = view.page
    main_view = view.main_view
    controller = view.controller

    almacenes = await controller.obtener_almacenes()

    async def refresh():
        items = await controller.obtener_transferencias_almacen()
        rows = []
        for it in items:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(it.get("id", "")))),
                        ft.DataCell(ft.Text(str(it.get("almacen_origen", "")))),
                        ft.DataCell(ft.Text("→")),
                        ft.DataCell(ft.Text(str(it.get("almacen_destino", "")))),
                        ft.DataCell(ft.Text(str(it.get("producto_codigo", "")))),
                        ft.DataCell(ft.Text(str(it.get("producto_nombre", "")))),
                        ft.DataCell(ft.Text(str(it.get("cantidad", 0)))),
                        ft.DataCell(ft.Text(str(it.get("nota", "") or ""))),
                        ft.DataCell(ft.Text(str(it.get("creado_en", "")))),
                    ]
                )
            )
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text(t("phase1.transferencias.origen"))),
                ft.DataColumn(ft.Text("")),
                ft.DataColumn(ft.Text(t("phase1.transferencias.destino"))),
                ft.DataColumn(ft.Text(t("products.code"))),
                ft.DataColumn(ft.Text(t("phase1.devoluciones.producto"))),
                ft.DataColumn(ft.Text(t("phase1.transferencias.cantidad"))),
                ft.DataColumn(ft.Text(t("phase1.transferencias.nota"))),
                ft.DataColumn(ft.Text("Fecha")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )
        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text(t("phase1.transferencias.empty"), color="#475569"),
                padding=40,
            )
        )
        if main_view:
            main_view.content = ft.Column(
                [
                    AppHeader.create(
                        t("phase1.transferencias.title"),
                        t("phase1.transferencias.subtitle"),
                    ),
                    ft.Container(
                        content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                        padding=20,
                    ),
                    body,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            page.update()

    async def open_new(e):
        if len(almacenes) < 2:
            SnackBarHelper.error(page, "Necesitas al menos 2 almacenes")
            return
        productos = await controller.obtener_todos_productos()
        opciones = [str(a.get("id")) for a in almacenes]
        origen = FormField.create_dropdown(t("phase1.transferencias.origen"), opciones)
        destino = FormField.create_dropdown(t("phase1.transferencias.destino"), opciones)
        prod_opts = [str(p.get("id")) for p in productos]
        producto = FormField.create_dropdown(t("phase1.devoluciones.producto"), prod_opts)
        cantidad = FormField.create_text_field(t("phase1.transferencias.cantidad"))
        nota = FormField.create_text_field(t("phase1.transferencias.nota"))
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.crear_transferencia_almacen(
                    almacen_origen_id=int(origen.value or 0),
                    almacen_destino_id=int(destino.value or 0),
                    producto_id=int(producto.value or 0),
                    cantidad=int(cantidad.value or 0),
                    nota=nota.value or "",
                )
            except Exception as ex:
                err.value = str(ex)
                page.update()
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, "Transferencia registrada")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase1.transferencias.new")),
            content=ft.Column(
                [origen, destino, producto, cantidad, nota, err],
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
                ft.Icon(ft.icons.Icons.SWAP_HORIZ, color="white"),
                ft.Text(t("phase1.transferencias.new"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )
    await refresh()


# ============ V3: Conteo físico ============


async def show_conteos(view) -> None:
    page = view.page
    main_view = view.main_view
    controller = view.controller

    async def refresh():
        sesiones = await controller.obtener_sesiones_conteo()
        rows = []
        for s in sesiones:
            sid = s.get("id")
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(sid))),
                        ft.DataCell(ft.Text(str(s.get("nombre", "")))),
                        ft.DataCell(ft.Text(str(s.get("almacen_nombre", "") or "-"))),
                        ft.DataCell(ft.Text(str(s.get("estado", "")))),
                        ft.DataCell(ft.Text(str(s.get("items_count", 0)))),
                        ft.DataCell(ft.Text(str(s.get("creado_en", "")))),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.icons.Icons.PLAY_ARROW,
                                tooltip="Abrir",
                                on_click=lambda ev, x=sid: asyncio.create_task(open_session(x)),
                            )
                        ),
                    ]
                )
            )
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text(t("phase1.conteos.nombre"))),
                ft.DataColumn(ft.Text(t("warehouses.location"))),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Items")),
                ft.DataColumn(ft.Text("Creado")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )
        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text(t("phase1.conteos.empty"), color="#475569"),
                padding=40,
            )
        )
        if main_view:
            main_view.content = ft.Column(
                [
                    AppHeader.create(
                        t("phase1.conteos.title"),
                        t("phase1.conteos.subtitle"),
                    ),
                    ft.Container(
                        content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                        padding=20,
                    ),
                    body,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            page.update()

    async def open_session(sesion_id):
        sesion = await controller.obtener_sesion_conteo(sesion_id)
        if not sesion:
            SnackBarHelper.error(page, "Sesión no encontrada")
            return

        async def refresh_items():
            nonlocal sesion
            sesion = await controller.obtener_sesion_conteo(sesion_id)
            rows2 = []
            for it in sesion.get("items", []):
                pid = it.get("producto_id")
                cont = it.get("cantidad_contada")
                cont_str = "" if cont is None else str(cont)
                rows2.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(pid))),
                            ft.DataCell(ft.Text(str(it.get("producto_codigo", "")))),
                            ft.DataCell(ft.Text(str(it.get("producto_nombre", "")))),
                            ft.DataCell(ft.Text(str(it.get("cantidad_sistema", 0)))),
                            ft.DataCell(ft.Text(cont_str)),
                            ft.DataCell(ft.Text(str(it.get("diferencia", "") or ""))),
                            ft.DataCell(
                                ft.TextField(
                                    width=120,
                                    value=cont_str,
                                    on_submit=lambda ev, ppid=pid: asyncio.create_task(
                                        save_item(ppid, ev.control.value)
                                    ),
                                )
                            ),
                        ]
                    )
                )
            table2 = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("#")),
                    ft.DataColumn(ft.Text(t("products.code"))),
                    ft.DataColumn(ft.Text(t("phase1.devoluciones.producto"))),
                    ft.DataColumn(ft.Text(t("phase1.conteo.sistema"))),
                    ft.DataColumn(ft.Text(t("phase1.conteo.contado"))),
                    ft.DataColumn(ft.Text(t("phase1.conteo.diferencia"))),
                    ft.DataColumn(ft.Text("Actualizar")),
                ],
                rows=rows2,
                heading_row_color="#DBEAFE",
            )
            if main_view:
                main_view.content = ft.Column(
                    [
                        AppHeader.create(
                            f"Conteo #{sesion_id} — {sesion.get('nombre', '')}",
                            "Captura cantidades contadas",
                        ),
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Button(
                                        content=ft.Text(t("phase1.conteo.cerrar")),
                                        on_click=lambda ev: asyncio.create_task(close(False)),
                                    ),
                                    ft.Button(
                                        content=ft.Text(t("phase1.conteo.cerrar_ajustar")),
                                        style=ft.ButtonStyle(bgcolor=THEME_SUCCESS_COLOR),
                                        on_click=lambda ev: asyncio.create_task(close(True)),
                                    ),
                                    ft.Button(
                                        content=ft.Text("← Volver"),
                                        on_click=lambda ev: asyncio.create_task(refresh()),
                                    ),
                                ],
                                spacing=10,
                            ),
                            padding=20,
                        ),
                        ft.Container(content=table2, padding=20, expand=True),
                    ],
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                )
                page.update()

        async def save_item(pid, cont):
            try:
                await controller.registrar_conteo_item(
                    sesion_id=sesion_id,
                    producto_id=pid,
                    cantidad_contada=float(cont or 0),
                )
            except Exception as ex:
                SnackBarHelper.error(page, str(ex))
                return
            SnackBarHelper.success(page, "Conteo guardado")
            await refresh_items()

        async def close(aplicar):
            ok, res = await controller.cerrar_sesion_conteo(sesion_id, aplicar_ajustes=aplicar)
            if ok:
                SnackBarHelper.success(
                    page,
                    f"Sesión cerrada (ajustes={aplicar}) — items={res.get('items')}",
                )
                await refresh()
            else:
                SnackBarHelper.error(page, (res or {}).get("error", "Error"))

        await refresh_items()

    async def open_new(e):
        nombre = FormField.create_text_field(t("phase1.conteos.nombre"))
        productos = await controller.obtener_todos_productos()
        prod_opts = [f"{p.get('id')} — {p.get('codigo')}" for p in productos]
        sel = ft.Dropdown(
            label=t("phase1.conteos.productos"),
            options=[ft.dropdown.Option(o) for o in prod_opts],
            fill_color="#F8FAFC",
            color="#0F172A",
            width=420,
            text_style=ft.TextStyle(color="#0F172A", size=14),
        )

        async def save(ev):
            try:
                if sel.value:
                    ids = [int(opt.split(" — ")[0]) for opt in sel.value.split(",") if opt.strip()]
                else:
                    ids = [p.get("id") for p in productos]
                ok, res = await controller.crear_sesion_conteo(
                    nombre=nombre.value or "Conteo",
                    producto_ids=ids,
                )
            except Exception as ex:
                SnackBarHelper.error(page, str(ex))
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, f"Sesión #{res['id']} creada")
                await refresh()
            else:
                SnackBarHelper.error(page, (res or {}).get("error", "Error"))

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase1.conteos.new")),
            content=ft.Column([nombre, sel], tight=True, spacing=10),
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
                ft.Text(t("phase1.conteos.new"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )
    await refresh()
