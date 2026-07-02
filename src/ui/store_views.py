"""Online store management views, refactored for clarity."""

import asyncio

import flet as ft

from config.settings import (
    THEME_ACCENT_COLOR,
    THEME_PRIMARY_COLOR,
    THEME_SUCCESS_COLOR,
    THEME_WARNING_COLOR,
)
from core.theme_manager import theme_manager
from ui.components import AppHeader, SnackBarHelper

from ._utils import get_logger

logger = get_logger(__name__)


def _c(app):
    """Get the active color palette."""
    return theme_manager.palette(page=app.page)


async def show_store_config(app):
    """Display online store configuration."""
    c = _c(app)
    controller = app.controller

    config = await controller.obtener_config_tienda()
    status_text = ft.Text("", size=12, color=c["text_secondary"])

    enabled_switch = ft.Switch(
        label="Tienda Online Activada",
        value=config.get("store_enabled", "false").lower() == "true",
    )
    name_field = ft.TextField(
        label="Nombre de la tienda",
        value=config.get("store_name", "Mi Tienda"),
        width=400,
        filled=True,
        fill_color=c["input_fill"],
        color=c["text_primary"],
    )
    email_field = ft.TextField(
        label="Email de contacto",
        value=config.get("store_email", ""),
        width=400,
        filled=True,
        fill_color=c["input_fill"],
        color=c["text_primary"],
    )
    currency_field = ft.TextField(
        label="Moneda (ej: ARS, USD)",
        value=config.get("store_currency", "ARS"),
        width=200,
        filled=True,
        fill_color=c["input_fill"],
        color=c["text_primary"],
    )

    async def handle_save(e):
        await controller.guardar_config_tienda("store_enabled", str(enabled_switch.value).lower())
        await controller.guardar_config_tienda("store_name", name_field.value)
        await controller.guardar_config_tienda("store_email", email_field.value)
        await controller.guardar_config_tienda("store_currency", currency_field.value)
        status_text.value = "Configuración guardada"
        SnackBarHelper.success(app.page, "Configuración de tienda guardada")
        app.page.update()

    async def go_products(e):
        await show_store_products(app)

    async def go_orders(e):
        await show_store_orders(app)

    save_btn = ft.Button(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.SAVE, color="white"), ft.Text("Guardar", color="white")],
            spacing=5,
        ),
        on_click=handle_save,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    products_btn = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.INVENTORY_2), ft.Text("Gestionar Productos")],
            spacing=5,
        ),
        on_click=go_products,
    )

    orders_btn = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.LIST_ALT), ft.Text("Ver Pedidos")],
            spacing=5,
        ),
        on_click=go_orders,
    )

    if app.main_view:
        app.main_view.content = ft.Column(
            [
                AppHeader.create("Tienda Online", "Configuración de la tienda online"),
                ft.Container(
                    content=ft.Column(
                        [
                            enabled_switch,
                            name_field,
                            email_field,
                            currency_field,
                            ft.Container(height=10),
                            ft.Row([save_btn, products_btn, orders_btn], spacing=10),
                            status_text,
                        ],
                        spacing=15,
                    ),
                    padding=20,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        app.page.update()


async def show_store_products(app):
    """Manage which products are visible in the online store."""
    c = _c(app)
    controller = app.controller

    productos = await controller.obtener_todos_productos()
    tienda_prods = await controller.listar_productos_tienda(solo_visibles=False)
    tienda_map = {tp["producto_id"]: tp for tp in tienda_prods}

    status_text = ft.Text("", size=12, color=c["text_secondary"])
    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Código")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Precio")),
            ft.DataColumn(ft.Text("Stock")),
            ft.DataColumn(ft.Text("Visible")),
            ft.DataColumn(ft.Text("Destacado")),
            ft.DataColumn(ft.Text("")),
        ],
        rows=[],
    )

    def rebuild():
        rows = []
        for p in productos:
            pid = p["id"]
            tp = tienda_map.get(pid, {})
            visible = tp.get("visible", 0) if tp else 0
            destacado = tp.get("destacado", 0) if tp else 0

            async def toggle_visible(e, pid=pid):
                nonlocal tienda_map
                current = tienda_map.get(pid, {})
                new_visible = not (current.get("visible", 0) if current else 0)
                ok = await controller.sincronizar_producto(
                    producto_id=pid, visible=new_visible,
                    destacado=current.get("destacado", 0) if current else False,
                )
                if ok:
                    tienda_prods = await controller.listar_productos_tienda(solo_visibles=False)
                    tienda_map.clear()
                    tienda_map.update({tp["producto_id"]: tp for tp in tienda_prods})
                    rebuild()
                    app.page.update()

            async def toggle_featured(e, pid=pid):
                nonlocal tienda_map
                current = tienda_map.get(pid, {})
                new_destacado = not (current.get("destacado", 0) if current else 0)
                ok = await controller.sincronizar_producto(
                    producto_id=pid, visible=current.get("visible", 0) if current else False,
                    destacado=new_destacado,
                )
                if ok:
                    tienda_prods = await controller.listar_productos_tienda(solo_visibles=False)
                    tienda_map.clear()
                    tienda_map.update({tp["producto_id"]: tp for tp in tienda_prods})
                    rebuild()
                    app.page.update()

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(p.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(p.get("nombre", "")[:20]))),
                        ft.DataCell(ft.Text(f"${p.get('precio', 0):.2f}")),
                        ft.DataCell(ft.Text(str(p.get("cantidad", 0)))),
                        ft.DataCell(
                            ft.Icon(
                                ft.icons.Icons.CHECK_CIRCLE if visible else ft.icons.Icons.CANCEL,
                                color="green" if visible else "red",
                            )
                        ),
                        ft.DataCell(
                            ft.Icon(
                                ft.icons.Icons.STAR if destacado else ft.icons.Icons.STAR_BORDER,
                                color="amber" if destacado else "gray",
                            )
                        ),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.Icons.VISIBILITY if visible else ft.icons.Icons.VISIBILITY_OFF,
                                        icon_color=THEME_PRIMARY_COLOR,
                                        tooltip="Visible en tienda" if visible else "Oculto en tienda",
                                        on_click=toggle_visible,
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.Icons.STAR if destacado else ft.icons.Icons.STAR_OUTLINE,
                                        icon_color="amber" if destacado else "gray",
                                        tooltip="Destacado" if destacado else "Marcar como destacado",
                                        on_click=toggle_featured,
                                    ),
                                ],
                                spacing=2,
                            )
                        ),
                    ]
                )
            )
        table.rows = rows

    rebuild()

    back_btn = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.ARROW_BACK), ft.Text("Volver")],
            spacing=5,
        ),
        on_click=lambda e: asyncio.create_task(show_store_config(app)),
    )

    if app.main_view:
        app.main_view.content = ft.Column(
            [
                AppHeader.create("Productos en Tienda", "Selecciona productos visibles en la tienda online"),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row([back_btn], alignment=ft.MainAxisAlignment.START),
                            ft.Container(content=table, expand=True),
                            status_text,
                        ],
                        spacing=15,
                    ),
                    padding=20,
                    expand=True,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        app.page.update()


async def show_store_orders(app):
    """Manage online store orders."""
    c = _c(app)
    controller = app.controller

    pedidos = await controller.obtener_pedidos_tienda()
    status_text = ft.Text("", size=12, color=c["text_secondary"])

    estado_filter = ft.Dropdown(
        label="Filtrar por estado",
        options=[
            ft.dropdown.Option(key="", text="Todos"),
            ft.dropdown.Option(key="pendiente", text="Pendiente"),
            ft.dropdown.Option(key="confirmado", text="Confirmado"),
            ft.dropdown.Option(key="enviado", text="Enviado"),
            ft.dropdown.Option(key="entregado", text="Entregado"),
            ft.dropdown.Option(key="cancelado", text="Cancelado"),
        ],
        value="",
        width=200,
        fill_color=c["input_fill"],
        color=c["text_primary"],
    )

    async def refresh():
        nonlocal pedidos
        estado = estado_filter.value or None
        pedidos = await controller.obtener_pedidos_tienda(estado=estado)
        rebuild()
        app.page.update()

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("#")),
            ft.DataColumn(ft.Text("Cliente")),
            ft.DataColumn(ft.Text("Email")),
            ft.DataColumn(ft.Text("Total")),
            ft.DataColumn(ft.Text("Estado")),
            ft.DataColumn(ft.Text("Fecha")),
            ft.DataColumn(ft.Text("")),
        ],
        rows=[],
    )

    def estado_color(estado):
        return {
            "pendiente": THEME_WARNING_COLOR,
            "confirmado": THEME_PRIMARY_COLOR,
            "enviado": THEME_ACCENT_COLOR,
            "entregado": THEME_SUCCESS_COLOR,
            "cancelado": "red",
        }.get(estado, c["text_secondary"])

    def rebuild():
        rows = []
        for p in pedidos:
            async def ver_detalle(e, pid=p["id"]):
                await show_store_order_detail(app, pid)

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f"#{p.get('id', '')}")),
                        ft.DataCell(ft.Text(str(p.get("cliente_nombre", ""))[:15])),
                        ft.DataCell(ft.Text(str(p.get("cliente_email", "")[:20]))),
                        ft.DataCell(ft.Text(f"${p.get('total', 0):.2f}")),
                        ft.DataCell(
                            ft.Text(p.get("estado", ""), color=estado_color(p.get("estado", "")))
                        ),
                        ft.DataCell(ft.Text(str(p.get("creado_en", ""))[:10])),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.icons.Icons.VISIBILITY,
                                icon_color=THEME_PRIMARY_COLOR,
                                on_click=ver_detalle,
                            )
                        ),
                    ]
                )
            )
        table.rows = rows

    rebuild()

    async def handle_refresh(e):
        await refresh()

    refresh_btn = ft.Button(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.REFRESH, color="white"), ft.Text("Actualizar", color="white")],
            spacing=5,
        ),
        on_click=handle_refresh,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    back_btn = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.ARROW_BACK), ft.Text("Volver")],
            spacing=5,
        ),
        on_click=lambda e: asyncio.create_task(show_store_config(app)),
    )

    if app.main_view:
        app.main_view.content = ft.Column(
            [
                AppHeader.create("Pedidos Tienda Online", "Gestiona los pedidos recibidos"),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row([back_btn, estado_filter, refresh_btn], spacing=10),
                            ft.Container(content=table, expand=True),
                            status_text,
                        ],
                        spacing=15,
                    ),
                    padding=20,
                    expand=True,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        app.page.update()


async def show_store_order_detail(app, pedido_id: int):
    """Show detail of a store order and allow status changes."""
    c = _c(app)
    controller = app.controller

    pedido = await controller.obtener_pedido_tienda(pedido_id)
    if not pedido:
        SnackBarHelper.error(app.page, "Pedido no encontrado")
        return

    status_text = ft.Text("", size=12, color=c["text_secondary"])

    estado_dd = ft.Dropdown(
        label="Estado",
        options=[
            ft.dropdown.Option("pendiente", "Pendiente"),
            ft.dropdown.Option("confirmado", "Confirmado"),
            ft.dropdown.Option("enviado", "Enviado"),
            ft.dropdown.Option("entregado", "Entregado"),
            ft.dropdown.Option("cancelado", "Cancelado"),
        ],
        value=pedido.get("estado", "pendiente"),
        width=200,
        fill_color=c["input_fill"],
    )

    items_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Código")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Cant.")),
            ft.DataColumn(ft.Text("P. Unit.")),
            ft.DataColumn(ft.Text("Subtotal")),
        ],
        rows=[
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(item.get("codigo", "")))),
                    ft.DataCell(ft.Text(str(item.get("nombre", "")[:20]))),
                    ft.DataCell(ft.Text(str(item.get("cantidad", 0)))),
                    ft.DataCell(ft.Text(f"${item.get('precio_unitario', 0):.2f}")),
                    ft.DataCell(ft.Text(f"${item.get('subtotal', 0):.2f}")),
                ]
            )
            for item in (pedido.get("items") or [])
        ],
    )

    async def handle_update_status(e):
        ok = await controller.actualizar_estado_pedido(pedido_id, estado_dd.value)
        if ok:
            status_text.value = f"Estado actualizado a: {estado_dd.value}"
            SnackBarHelper.success(app.page, "Estado actualizado")
            app.page.update()

    update_btn = ft.Button(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.UPDATE, color="white"), ft.Text("Actualizar Estado", color="white")],
            spacing=5,
        ),
        on_click=handle_update_status,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    back_btn = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.ARROW_BACK), ft.Text("Volver")],
            spacing=5,
        ),
        on_click=lambda e: asyncio.create_task(show_store_orders(app)),
    )

    if app.main_view:
        app.main_view.content = ft.Column(
            [
                AppHeader.create(f"Pedido #{pedido_id}", ""),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row([back_btn], alignment=ft.MainAxisAlignment.START),
                            ft.Row(
                                [
                                    ft.Text("Cliente:", weight=ft.FontWeight.BOLD),
                                    ft.Text(str(pedido.get("cliente_nombre", ""))),
                                ],
                                spacing=10,
                            ),
                            ft.Row(
                                [
                                    ft.Text("Email:", weight=ft.FontWeight.BOLD),
                                    ft.Text(str(pedido.get("cliente_email", ""))),
                                ],
                                spacing=10,
                            ),
                            ft.Row(
                                [
                                    ft.Text("Teléfono:", weight=ft.FontWeight.BOLD),
                                    ft.Text(str(pedido.get("cliente_telefono", ""))),
                                ],
                                spacing=10,
                            ),
                            ft.Row(
                                [
                                    ft.Text("Dirección:", weight=ft.FontWeight.BOLD),
                                    ft.Text(str(pedido.get("direccion_envio", ""))),
                                ],
                                spacing=10,
                            ),
                            ft.Row(
                                [
                                    ft.Text("Método de pago:", weight=ft.FontWeight.BOLD),
                                    ft.Text(str(pedido.get("metodo_pago", ""))),
                                ],
                                spacing=10,
                            ),
                            ft.Divider(),
                            ft.Row(
                                [
                                    estado_dd,
                                    update_btn,
                                ],
                                spacing=10,
                            ),
                            items_table,
                            ft.Row(
                                [
                                    ft.Text("Total:", size=16, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"${pedido.get('total', 0):.2f}", size=16, color=THEME_PRIMARY_COLOR, weight=ft.FontWeight.BOLD),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            status_text,
                        ],
                        spacing=15,
                    ),
                    padding=20,
                    expand=True,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        app.page.update()
