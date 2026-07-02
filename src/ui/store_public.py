"""Public-facing online store view (embedded in the app), refactored for clarity."""

import asyncio

import flet as ft

from config.settings import THEME_ACCENT_COLOR, THEME_PRIMARY_COLOR
from core.theme_manager import theme_manager
from ui.components import AppHeader, SnackBarHelper

from ._utils import get_logger

logger = get_logger(__name__)


async def show_store_public(app):
    """Display the public online store interface inside the app."""
    theme_manager.palette(page=app.page)
    controller = app.controller

    config = await controller.obtener_config_tienda()
    if config.get("store_enabled", "false").lower() != "true":
        if app.main_view:
            app.main_view.content = ft.Column(
                [
                    AppHeader.create(config.get("store_name", "Tienda Online"), "Tienda desactivada"),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.icons.Icons.SHOPPING_CART, size=64, color="gray400"),
                                ft.Text("La tienda online está desactivada", size=18, color="#475569"),
                                ft.Text("Actívala desde Configuración > Tienda Online", size=14, color="#94A3B8"),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=20,
                        ),
                        padding=60,
                        alignment=ft.alignment.Alignment.CENTER,
                        expand=True,
                    ),
                ],
                expand=True,
            )
            app.page.update()
        return

    currency = config.get("store_currency", "ARS")
    store_name = config.get("store_name", "Tienda Online")
    store_email = config.get("store_email", "")

    productos = await controller.listar_productos_tienda(solo_visibles=True)
    destacados = await controller.obtener_productos_destacados()

    cart_count_text = ft.Text("0", size=12, color="white", weight=ft.FontWeight.BOLD)
    ft.Text("", size=12, color="#475569")
    products_grid = ft.GridView(
        expand=True,
        runs_count=3,
        max_extent=250,
        spacing=10,
        run_spacing=10,
        padding=20,
    )

    # Cart overlay
    cart_overlay = ft.Container(visible=False)
    cart_items_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Cant.")),
            ft.DataColumn(ft.Text("Precio")),
            ft.DataColumn(ft.Text("")),
        ],
        rows=[],
    )
    cart_total_text = ft.Text("$0.00", size=20, weight=ft.FontWeight.BOLD, color=THEME_PRIMARY_COLOR)

    async def refresh_cart_overlay():
        cart = await controller.obtener_carrito_con_items()
        if not cart or not cart.get("items"):
            cart_items_table.rows = []
            cart_total_text.value = "$0.00"
            cart_count_text.value = "0"
            return
        cart_count_text.value = str(len(cart["items"]))
        rows = []
        for item in cart["items"]:
            pid = item.get("producto_id")

            async def remove_from_cart(e, pid=pid):
                cart = await controller.obtener_carrito_con_items()
                if not cart:
                    return
                for ci in cart.get("items", []):
                    if ci["producto_id"] == pid:
                        await controller.eliminar_item_carrito(ci["id"])
                        break
                await refresh_cart_overlay()
                app.page.update()

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(item.get("nombre", "")[:15]))),
                        ft.DataCell(ft.Text(str(item.get("cantidad", 0)))),
                        ft.DataCell(ft.Text(f"${(item.get('precio_unitario', 0) or 0):.2f}")),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.icons.Icons.DELETE,
                                icon_color=THEME_ACCENT_COLOR,
                                on_click=remove_from_cart,
                            )
                        ),
                    ]
                )
            )
        cart_items_table.rows = rows
        total = sum(
            (i.get("precio_unitario", 0) or 0) * (i.get("cantidad", 0) or 0)
            for i in cart["items"]
        )
        cart_total_text.value = f"${total:.2f}"

    async def add_to_cart(producto):
        ok = await controller.agregar_al_carrito(
            producto["producto_id"], 1, producto.get("precio", 0) or 0
        )
        if ok:
            SnackBarHelper.success(app.page, f"{producto.get('nombre', '')} agregado al carrito")
            await refresh_cart_overlay()
            app.page.update()

    def build_product_card(p):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Icon(ft.icons.Icons.IMAGE, size=48, color="#CBD5E1"),
                        height=120,
                        bgcolor="#F1F5F9",
                        border_radius=ft.border_radius.only(top_left=8, top_right=8),
                        alignment=ft.alignment.Alignment.CENTER,
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(str(p.get("nombre", "")), size=14, weight=ft.FontWeight.BOLD, color="#0F172A"),
                                ft.Text(f"{currency} ${p.get('precio', 0):.2f}", size=16, color=THEME_PRIMARY_COLOR, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Stock: {p.get('stock', 0)}", size=11, color="#94A3B8"),
                            ],
                            spacing=4,
                        ),
                        padding=10,
                    ),
                    ft.Container(
                        content=ft.Button(
                            content=ft.Text("Agregar", color="white", size=12),
                            on_click=lambda e, pp=p: asyncio.create_task(add_to_cart(pp)),
                            style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, padding=5),
                            width=120,
                        ),
                        padding=ft.Padding(left=10, right=10, bottom=10, top=0),
                    ),
                ],
                spacing=0,
            ),
            border_radius=8,
            shadow=ft.BoxShadow(blur_radius=4, color="#E2E8F0"),
            bgcolor="white",
        )

    # Build featured section
    featured_cards = []
    for p in destacados:
        featured_cards.append(build_product_card(p))

    # Build all products grid
    products_grid.controls = [build_product_card(p) for p in productos]

    async def toggle_cart(e):
        cart_overlay.visible = not cart_overlay.visible
        if cart_overlay.visible:
            await refresh_cart_overlay()
        app.page.update()

    async def go_checkout(e):
        cart = await controller.obtener_carrito_con_items()
        if not cart or not cart.get("items"):
            SnackBarHelper.error(app.page, "El carrito está vacío")
            return
        await show_store_checkout(app)

    cart_btn = ft.Container(
        content=ft.Stack(
            [
                ft.IconButton(icon=ft.icons.Icons.SHOPPING_CART, icon_color=THEME_PRIMARY_COLOR, on_click=toggle_cart),
                ft.Container(
                    content=cart_count_text,
                    bgcolor="red",
                    border_radius=10,
                    padding=ft.Padding(left=4, right=4, top=2, bottom=2),
                    right=0,
                    top=0,
                ),
            ]
        ),
    )

    checkout_btn = ft.Button(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.CHECK_CIRCLE, color="white"), ft.Text("Finalizar Compra", color="white")],
            spacing=5,
        ),
        on_click=go_checkout,
        style=ft.ButtonStyle(bgcolor="green700"),
    )

    cart_overlay = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [ft.Text("Carrito", size=16, weight=ft.FontWeight.BOLD), ft.IconButton(icon=ft.icons.Icons.CLOSE, on_click=toggle_cart)],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(content=cart_items_table, expand=True),
                ft.Row(
                    [
                        ft.Text("Total:", size=16, weight=ft.FontWeight.BOLD),
                        cart_total_text,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                checkout_btn,
            ],
            spacing=10,
        ),
        bgcolor="white",
        border_radius=8,
        shadow=ft.BoxShadow(blur_radius=10, color="#CBD5E1"),
        padding=15,
        width=350,
        height=400,
        right=20,
        top=60,
        visible=False,
    )

    if app.main_view:
        app.main_view.content = ft.Stack(
            [
                ft.Column(
                    [
                        AppHeader.create(store_name, f"Email: {store_email}" if store_email else "Tienda Online"),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [cart_btn],
                                        alignment=ft.MainAxisAlignment.END,
                                    ),
                                    ft.Divider(),
                                    ft.Text("Productos", size=18, weight=ft.FontWeight.BOLD, color="#0F172A"),
                                    ft.Container(content=products_grid, expand=True),
                                ],
                                spacing=10,
                            ),
                            padding=20,
                            expand=True,
                        ),
                    ],
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                cart_overlay,
            ],
            expand=True,
        )
        app.page.update()


async def show_store_checkout(app):
    """Checkout form for the online store."""
    theme_manager.palette(page=app.page)
    controller = app.controller

    cart = await controller.obtener_carrito_con_items()
    if not cart or not cart.get("items"):
        SnackBarHelper.error(app.page, "El carrito está vacío")
        return

    status_text = ft.Text("", size=12, color="#475569")

    nombre_field = ft.TextField(
        label="Nombre completo",
        value="",
        width=400,
        filled=True,
        fill_color="#F8FAFC",
        color="#0F172A",
    )
    email_field = ft.TextField(
        label="Email",
        value="",
        width=400,
        filled=True,
        fill_color="#F8FAFC",
        color="#0F172A",
    )
    telefono_field = ft.TextField(
        label="Teléfono",
        value="",
        width=400,
        filled=True,
        fill_color="#F8FAFC",
        color="#0F172A",
    )
    direccion_field = ft.TextField(
        label="Dirección de envío",
        value="",
        width=400,
        multiline=True,
        min_lines=2,
        filled=True,
        fill_color="#F8FAFC",
        color="#0F172A",
    )
    notas_field = ft.TextField(
        label="Notas",
        value="",
        width=400,
        multiline=True,
        min_lines=2,
        filled=True,
        fill_color="#F8FAFC",
        color="#0F172A",
    )

    total = sum(
        (i.get("precio_unitario", 0) or 0) * (i.get("cantidad", 0) or 0)
        for i in cart["items"]
    )

    resumen_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Cant.")),
            ft.DataColumn(ft.Text("Subtotal")),
        ],
        rows=[
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(item.get("nombre", "")[:20]))),
                    ft.DataCell(ft.Text(str(item.get("cantidad", 0)))),
                    ft.DataCell(ft.Text(f"${(item.get('precio_unitario', 0) or 0) * (item.get('cantidad', 0) or 0):.2f}")),
                ]
            )
            for item in cart["items"]
        ],
    )

    config_tienda = await controller.obtener_config_tienda()
    currency = config_tienda.get("store_currency", "ARS")

    async def handle_submit(e):
        if not nombre_field.value or not email_field.value:
            SnackBarHelper.error(app.page, "Nombre y email son obligatorios")
            return

        items = [
            {
                "producto_id": i["producto_id"],
                "cantidad": i["cantidad"],
                "precio_unitario": i["precio_unitario"],
                "subtotal": (i.get("precio_unitario", 0) or 0) * (i.get("cantidad", 0) or 0),
            }
            for i in cart["items"]
        ]

        ok, result = await controller.crear_pedido_tienda(
            cliente_nombre=nombre_field.value,
            cliente_email=email_field.value,
            cliente_telefono=telefono_field.value or "",
            direccion_envio=direccion_field.value or "",
            notas=notas_field.value or "",
            total=total,
            items=items,
        )

        if ok:
            await controller.vaciar_carrito(cart["id"])
            SnackBarHelper.success(app.page, f"Pedido #{result['id']} creado. Total: {currency} ${result['total']:.2f}")
            await show_store_public(app)
        else:
            SnackBarHelper.error(app.page, result.get("error", "Error al crear pedido"))

    submit_btn = ft.Button(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.CHECK_CIRCLE, color="white"), ft.Text("Confirmar Pedido", color="white", weight=ft.FontWeight.BOLD)],
            spacing=5,
        ),
        on_click=handle_submit,
        style=ft.ButtonStyle(bgcolor="green700"),
    )

    back_btn = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.ARROW_BACK), ft.Text("Volver")],
            spacing=5,
        ),
        on_click=lambda e: asyncio.create_task(show_store_public(app)),
    )

    if app.main_view:
        app.main_view.content = ft.Column(
            [
                AppHeader.create("Finalizar Compra", "Completa tus datos para recibir el pedido"),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row([back_btn], alignment=ft.MainAxisAlignment.START),
                            nombre_field,
                            email_field,
                            telefono_field,
                            direccion_field,
                            notas_field,
                            ft.Divider(),
                            ft.Text("Resumen del pedido", size=14, weight=ft.FontWeight.BOLD),
                            resumen_table,
                            ft.Row(
                                [
                                    ft.Text("Total:", size=18, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{currency} ${total:.2f}", size=18, color=THEME_PRIMARY_COLOR, weight=ft.FontWeight.BOLD),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Row([submit_btn], alignment=ft.MainAxisAlignment.END),
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
