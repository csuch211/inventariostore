"""
Phase 1 views — pricing and inventory: lots, prices, taxes, cash.

Companion to inventory_operations.py. Re-exported by ui/phase1.py.
"""

from __future__ import annotations

import asyncio

import flet as ft

from config.settings import (
    THEME_ACCENT_COLOR,
    THEME_PRIMARY_COLOR,
    THEME_SUCCESS_COLOR,
    THEME_WARNING_COLOR,
)
from ui.components import (
    AppHeader,
    FormField,
    SnackBarHelper,
)
from utils.i18n import t


def _fmt_money(v) -> str:
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "$0.00"


# ============ V4: Lotes ============


async def show_lotes(view) -> None:
    page = view.page
    main_view = view.main_view
    controller = view.controller

    ventana = ft.Dropdown(
        label=t("phase1.lotes.vencen_pronto"),
        options=[
            ft.dropdown.Option(key="0", text="Todos"),
            ft.dropdown.Option(key="7", text="7 días"),
            ft.dropdown.Option(key="30", text="30 días"),
            ft.dropdown.Option(key="60", text="60 días"),
        ],
        value="0",
        width=180,
        fill_color="#F8FAFC",
        color="#0F172A",
        text_style=ft.TextStyle(color="#0F172A", size=14),
    )

    async def refresh():
        dias = int(ventana.value or "0")
        kw = {"proximos_vencer_dias": dias} if dias > 0 else {}
        items = await controller.obtener_lotes(**kw)
        rows = []
        for it in items:
            d_vencer = it.get("dias_para_vencer")
            estado = ""
            estado_color = None
            if d_vencer is not None:
                if d_vencer < 0:
                    estado = "VENCIDO"
                    estado_color = THEME_ACCENT_COLOR
                elif d_vencer <= 7:
                    estado = f"Vence en {d_vencer}d"
                    estado_color = THEME_WARNING_COLOR
                else:
                    estado = f"{d_vencer}d"
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(it.get("id", "")))),
                        ft.DataCell(ft.Text(str(it.get("producto_codigo", "")))),
                        ft.DataCell(ft.Text(str(it.get("producto_nombre", "")))),
                        ft.DataCell(ft.Text(str(it.get("codigo_lote", "")))),
                        ft.DataCell(ft.Text(str(it.get("serie", "") or ""))),
                        ft.DataCell(ft.Text(str(it.get("cantidad_actual", 0)))),
                        ft.DataCell(ft.Text(str(it.get("fecha_fabricacion", "") or ""))),
                        ft.DataCell(ft.Text(str(it.get("fecha_vencimiento", "") or ""))),
                        ft.DataCell(ft.Text(estado, color=estado_color)),
                    ]
                )
            )
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text(t("products.code"))),
                ft.DataColumn(ft.Text(t("phase1.devoluciones.producto"))),
                ft.DataColumn(ft.Text(t("phase1.lotes.codigo"))),
                ft.DataColumn(ft.Text(t("phase1.lotes.serie"))),
                ft.DataColumn(ft.Text("Cant.")),
                ft.DataColumn(ft.Text(t("phase1.lotes.fab"))),
                ft.DataColumn(ft.Text(t("phase1.lotes.venc"))),
                ft.DataColumn(ft.Text("Estado")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )
        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text(t("phase1.lotes.empty"), color="#475569"),
                padding=40,
            )
        )
        if main_view:
            main_view.content = ft.Column(
                [
                    AppHeader.create(
                        t("phase1.lotes.title"),
                        t("phase1.lotes.subtitle"),
                    ),
                    ft.Container(
                        content=ft.Row(
                            [ventana, new_btn],
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

    ventana.on_change = lambda e: asyncio.create_task(refresh())

    async def open_new(e):
        productos = await controller.obtener_todos_productos()
        prod_opts = [f"{p.get('id')} — {p.get('codigo')}" for p in productos]
        prod = FormField.create_dropdown(t("phase1.precios.producto"), prod_opts)
        codigo = FormField.create_text_field(t("phase1.lotes.codigo"))
        serie = FormField.create_text_field(t("phase1.lotes.serie"))
        cantidad = FormField.create_text_field(t("phase1.transferencias.cantidad"))
        fab = FormField.create_text_field(t("phase1.lotes.fab"), hint="YYYY-MM-DD")
        venc = FormField.create_text_field(t("phase1.lotes.venc"), hint="YYYY-MM-DD")
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.crear_lote(
                    producto_id=int((prod.value or "0").split(" — ")[0]),
                    codigo_lote=codigo.value or "",
                    cantidad_inicial=int(cantidad.value or 0),
                    serie=serie.value or None,
                    fecha_fabricacion=fab.value or None,
                    fecha_vencimiento=venc.value or None,
                )
            except Exception as ex:
                err.value = str(ex)
                page.update()
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, "Lote creado")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase1.lotes.new")),
            content=ft.Column(
                [prod, codigo, serie, cantidad, fab, venc, err],
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
                ft.Text(t("phase1.lotes.new"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )
    await refresh()


# ============ V5: Precios multi-nivel ============


async def show_precios(view) -> None:
    page = view.page
    main_view = view.main_view
    controller = view.controller

    async def refresh():
        listas = await controller.obtener_listas_precios()
        cards = ft.Row(wrap=True, spacing=15, run_spacing=15)
        for lst in listas:
            lid = lst.get("id")
            lname = lst.get("nombre", "")
            card = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(lname, size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            lst.get("descripcion", "") or "",
                            size=12,
                            color="#475569",
                        ),
                        ft.Container(height=8),
                        ft.Button(
                            content=ft.Text(t("phase1.precios.asignar")),
                            on_click=lambda ev, x=lid, n=lname: asyncio.create_task(
                                open_assign(x, n)
                            ),
                        ),
                    ],
                    spacing=4,
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
                width=240,
            )
            cards.controls.append(card)
        if main_view:
            main_view.content = ft.Column(
                [
                    AppHeader.create(
                        t("phase1.precios.title"),
                        t("phase1.precios.subtitle"),
                    ),
                    ft.Container(
                        content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                        padding=20,
                    ),
                    ft.Container(content=cards, padding=20),
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            page.update()

    async def open_assign(lista_id, lista_nombre):
        productos = await controller.obtener_todos_productos()
        prod_opts = [f"{p.get('id')} — {p.get('codigo')} ({p.get('nombre')})" for p in productos]
        prod = FormField.create_dropdown(t("phase1.precios.producto"), prod_opts)
        precio = FormField.create_text_field(t("phase1.precios.precio"))
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.asignar_precio(
                    producto_id=int((prod.value or "0").split(" — ")[0]),
                    lista_id=lista_id,
                    precio=float(precio.value or 0),
                )
            except Exception as ex:
                err.value = str(ex)
                page.update()
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, "Precio asignado")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(f"{t('phase1.precios.asignar')} — {lista_nombre}"),
            content=ft.Column([prod, precio, err], tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        page.show_dialog(dialog)
        page.update()

    async def open_new(e):
        nombre = FormField.create_text_field(t("phase1.precios.nombre"))
        descripcion = FormField.create_text_field("Descripción")
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.crear_lista_precio(
                    nombre=nombre.value or "",
                    descripcion=descripcion.value or "",
                )
            except Exception as ex:
                err.value = str(ex)
                page.update()
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, "Lista creada")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase1.precios.new")),
            content=ft.Column([nombre, descripcion, err], tight=True, spacing=10),
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
                ft.Text(t("phase1.precios.new"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )
    await refresh()


# ============ V6: Impuestos ============


async def show_impuestos(view) -> None:
    page = view.page
    main_view = view.main_view
    controller = view.controller

    base = ft.TextField(label="Precio base", width=200, value="1000")
    pct = ft.TextField(label=t("phase1.impuestos.porcentaje"), width=200, value="19")
    out_total = ft.Text("", size=20, weight=ft.FontWeight.BOLD, color=THEME_PRIMARY_COLOR)
    out_break = ft.Text("", size=12, color="#475569")

    async def refresh():
        items = await controller.obtener_impuestos()
        rows = []
        for it in items:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(it.get("id", "")))),
                        ft.DataCell(ft.Text(str(it.get("nombre", "")))),
                        ft.DataCell(ft.Text(f"{it.get('porcentaje', 0)}%")),
                        ft.DataCell(ft.Text(str(it.get("tipo", "")))),
                    ]
                )
            )
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text(t("phase1.impuestos.nombre"))),
                ft.DataColumn(ft.Text(t("phase1.impuestos.porcentaje"))),
                ft.DataColumn(ft.Text("Tipo")),
            ],
            rows=rows,
            heading_row_color="#DBEAFE",
        )
        calc_card = ft.Container(
            content=ft.Column(
                [
                    ft.Text(t("phase1.impuestos.calc"), size=16, weight=ft.FontWeight.BOLD),
                    ft.Row([base, pct], spacing=10),
                    ft.Container(height=8),
                    out_total,
                    out_break,
                ],
                spacing=6,
            ),
            padding=16,
            border_radius=10,
            bgcolor="#F8FAFC",
            border=ft.border.Border(
                ft.BorderSide(1, "#E2E8F0"),
                ft.BorderSide(1, "#E2E8F0"),
                ft.BorderSide(1, "#E2E8F0"),
                ft.BorderSide(1, "#E2E8F0"),
            ),
            width=460,
        )
        body_table = ft.Container(content=table, expand=True) if rows else ft.Container()
        if main_view:
            main_view.content = ft.Column(
                [
                    AppHeader.create(
                        t("phase1.impuestos.title"),
                        t("phase1.impuestos.subtitle"),
                    ),
                    ft.Container(
                        content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                        padding=20,
                    ),
                    ft.Container(
                        content=ft.Row([calc_card, body_table], spacing=20),
                        padding=20,
                        expand=True,
                    ),
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            page.update()

    async def recalc(e=None):
        try:
            res = await controller.calcular_precio_con_impuesto(
                float(base.value or 0), float(pct.value or 0)
            )
            out_total.value = f"Total: {_fmt_money(res.get('total', 0))}"
            out_break.value = (
                f"Base {_fmt_money(res.get('base', 0))} + "
                f"Impuesto {_fmt_money(res.get('impuesto', 0))} "
                f"({res.get('porcentaje', 0)}%)"
            )
        except Exception as ex:
            out_break.value = str(ex)
        page.update()

    base.on_change = recalc
    pct.on_change = recalc

    async def open_new(e):
        nombre = FormField.create_text_field(t("phase1.impuestos.nombre"))
        porcentaje = FormField.create_text_field(t("phase1.impuestos.porcentaje"))
        tipo = FormField.create_dropdown("Tipo", ["iva", "otro"])
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.crear_impuesto(
                    nombre=nombre.value or "",
                    porcentaje=float(porcentaje.value or 0),
                    tipo=tipo.value or "iva",
                )
            except Exception as ex:
                err.value = str(ex)
                page.update()
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, "Impuesto creado")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase1.impuestos.new")),
            content=ft.Column([nombre, porcentaje, tipo, err], tight=True, spacing=10),
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
                ft.Text(t("phase1.impuestos.new"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )
    await refresh()
    await recalc()


# ============ V7: Caja POS ============


async def show_caja(view) -> None:
    page = view.page
    main_view = view.main_view
    controller = view.controller

    usuario = controller.current_user or "system"

    async def refresh():
        turno = await controller.obtener_turno_abierto(usuario)
        content_body = None
        if not turno:
            content_body = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(t("phase1.caja.turno_cerrado"), size=18),
                        ft.Container(height=12),
                        abrir_btn,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=40,
            )
        else:
            contenido = await controller.obtener_turno_caja(turno["id"])
            mov_rows = []
            for m in contenido.get("movimientos", []):
                mov_rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(m.get("tipo", "")))),
                            ft.DataCell(ft.Text(_fmt_money(m.get("monto", 0)))),
                            ft.DataCell(ft.Text(str(m.get("concepto", "") or ""))),
                            ft.DataCell(ft.Text(str(m.get("creado_en", "")))),
                        ]
                    )
                )
            mov_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Tipo")),
                    ft.DataColumn(ft.Text("Monto")),
                    ft.DataColumn(ft.Text("Concepto")),
                    ft.DataColumn(ft.Text("Fecha")),
                ],
                rows=mov_rows,
                heading_row_color="#DBEAFE",
            )
            ventas_rows = []
            for v in contenido.get("ventas", []):
                ventas_rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(v.get("id", "")))),
                            ft.DataCell(ft.Text(_fmt_money(v.get("total", 0)))),
                            ft.DataCell(ft.Text(str(v.get("cliente_nombre", "") or "-"))),
                            ft.DataCell(ft.Text(str(v.get("creado_en", "")))),
                        ]
                    )
                )
            ventas_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("#")),
                    ft.DataColumn(ft.Text("Total")),
                    ft.DataColumn(ft.Text("Cliente")),
                    ft.DataColumn(ft.Text("Fecha")),
                ],
                rows=ventas_rows,
                heading_row_color="#DBEAFE",
            )
            content_body = ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.icons.Icons.POINT_OF_SALE, color=THEME_SUCCESS_COLOR),
                                ft.Text(
                                    f"{t('phase1.caja.turno_abierto')} #{turno['id']}",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Container(expand=True),
                                ft.Button(
                                    content=ft.Text(t("phase1.caja.movimiento")),
                                    on_click=lambda ev: asyncio.create_task(open_mov()),
                                ),
                                ft.Button(
                                    content=ft.Text(t("phase1.caja.cerrar")),
                                    style=ft.ButtonStyle(bgcolor=THEME_ACCENT_COLOR),
                                    on_click=lambda ev: asyncio.create_task(close_shift()),
                                ),
                            ],
                        ),
                        padding=20,
                    ),
                    ft.Container(
                        content=ft.Text(
                            f"Inicial: {_fmt_money(turno.get('monto_inicial', 0))}",
                            size=14,
                        ),
                        padding=ft.Padding(left=20, right=20, top=0, bottom=10),
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Movimientos", weight=ft.FontWeight.BOLD),
                                ft.Container(content=mov_table)
                                if mov_rows
                                else ft.Text("Sin movimientos"),
                                ft.Container(height=10),
                                ft.Text(t("phase1.caja.ventas_turno"), weight=ft.FontWeight.BOLD),
                                ft.Container(content=ventas_table)
                                if ventas_rows
                                else ft.Text("Sin ventas"),
                            ]
                        ),
                        padding=20,
                        expand=True,
                    ),
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )

        if main_view:
            main_view.content = ft.Column(
                [
                    AppHeader.create(
                        t("phase1.caja.title"),
                        t("phase1.caja.subtitle"),
                    ),
                    content_body,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            page.update()

    async def open_mov():
        abierto = await controller.obtener_turno_abierto(usuario)
        tipo = FormField.create_dropdown("Tipo", ["ingreso", "egreso"])
        monto = FormField.create_text_field("Monto")
        concepto = FormField.create_text_field("Concepto")
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.registrar_movimiento_caja(
                    turno_id=abierto["id"],
                    tipo=tipo.value or "ingreso",
                    monto=float(monto.value or 0),
                    concepto=concepto.value or "",
                )
            except Exception as ex:
                err.value = str(ex)
                page.update()
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, "Movimiento registrado")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase1.caja.movimiento")),
            content=ft.Column([tipo, monto, concepto, err], tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        page.show_dialog(dialog)
        page.update()

    async def close_shift():
        abierto = await controller.obtener_turno_abierto(usuario)
        monto_final = ft.TextField(label=t("phase1.caja.final"), width=200)
        notas = ft.TextField(label="Notas", width=300)
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.cerrar_turno_caja(
                    turno_id=abierto["id"],
                    monto_final=float(monto_final.value or 0),
                    notas=notas.value or "",
                )
            except Exception as ex:
                err.value = str(ex)
                page.update()
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(
                    page,
                    f"Cerrado: esperado {_fmt_money(res.get('monto_esperado', 0))} "
                    f"real {_fmt_money(res.get('monto_final', 0))} "
                    f"dif {_fmt_money(res.get('diferencia', 0))}",
                )
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase1.caja.cerrar")),
            content=ft.Column([monto_final, notas, err], tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        page.show_dialog(dialog)
        page.update()

    async def open_abrir(e):
        inicial = FormField.create_text_field(t("phase1.caja.inicial"))
        notas = FormField.create_text_field("Notas")
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.abrir_turno_caja(
                    monto_inicial=float(inicial.value or 0),
                    notas=notas.value or "",
                )
            except Exception as ex:
                err.value = str(ex)
                page.update()
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, f"Turno #{res['id']} abierto")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase1.caja.abrir")),
            content=ft.Column([inicial, notas, err], tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        page.show_dialog(dialog)
        page.update()

    abrir_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.PLAY_ARROW, color="white"),
                ft.Text(t("phase1.caja.abrir"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_abrir,
        style=ft.ButtonStyle(bgcolor=THEME_SUCCESS_COLOR),
    )
    await refresh()
