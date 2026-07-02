"""Cart management and sales configuration views, refactored for clarity."""


import flet as ft

from config.settings import THEME_ACCENT_COLOR, THEME_PRIMARY_COLOR
from core.theme_manager import theme_manager
from ui.components import AppHeader, SnackBarHelper

from ._utils import get_logger

logger = get_logger(__name__)


async def show_cart(app):
    """Display the current user's active shopping cart."""
    theme_manager.palette(page=app.page)
    controller = app.controller

    cart = await controller.obtener_carrito_con_items()
    productos = await controller.obtener_todos_productos()

    items_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Código")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Cant.")),
            ft.DataColumn(ft.Text("P. Unit.")),
            ft.DataColumn(ft.Text("Subtotal")),
            ft.DataColumn(ft.Text("")),
        ],
        rows=[],
    )
    total_text = ft.Text("$0.00", size=24, weight=ft.FontWeight.BOLD, color=THEME_PRIMARY_COLOR)
    iva_text = ft.Text("", size=14, color="#475569")
    status_text = ft.Text("", size=12, color="#475569")

    producto_dd = ft.Dropdown(
        label="Producto",
        options=[
            ft.dropdown.Option(
                key=str(p["id"]),
                text=f"{p.get('codigo', '')} - {p.get('nombre', '')} (${p.get('precio', 0):.2f})",
            )
            for p in productos
        ],
        border_color=THEME_PRIMARY_COLOR,
        filled=True,
        fill_color="#F8FAFC",
    )
    cantidad_field = ft.TextField(
        label="Cantidad",
        value="1",
        width=100,
        filled=True,
        fill_color="#F8FAFC",
        color="#0F172A",
    )

    async def rebuild():
        if not cart or not cart.get("items"):
            items_table.rows = []
            total_text.value = "$0.00"
            iva_text.value = ""
            if cart:
                cart["items"] = []
                cart["total"] = 0
            return

        rows = []
        for i, item in enumerate(cart["items"]):
            idx = i

            async def remove(e, i=idx):
                nonlocal cart
                item_id = cart["items"][i]["id"]
                ok = await controller.eliminar_item_carrito(item_id)
                if ok:
                    cart = await controller.obtener_carrito_con_items()
                    await rebuild()
                    app.page.update()

            async def update_qty(e, i=idx):
                nonlocal cart
                item_id = cart["items"][i]["id"]
                try:
                    new_qty = int(e.control.value)
                except ValueError:
                    return
                if new_qty < 1:
                    return
                ok = await controller.actualizar_item_carrito(item_id, new_qty)
                if ok:
                    cart = await controller.obtener_carrito_con_items()
                    await rebuild()
                    app.page.update()

            unit_price = item.get("precio_unitario", 0) or 0
            qty = item.get("cantidad", 0) or 0
            subtotal = unit_price * qty

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(item.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(item.get("nombre", "")[:25]))),
                        ft.DataCell(
                            ft.TextField(
                                value=str(qty),
                                width=60,
                                height=40,
                                text_align=ft.TextAlign.CENTER,
                                on_submit=update_qty,
                            )
                        ),
                        ft.DataCell(ft.Text(f"${unit_price:.2f}")),
                        ft.DataCell(ft.Text(f"${subtotal:.2f}")),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.icons.Icons.DELETE,
                                icon_color=THEME_ACCENT_COLOR,
                                on_click=remove,
                            )
                        ),
                    ]
                )
            )

        items_table.rows = rows
        total = sum(
            (i.get("precio_unitario", 0) or 0) * (i.get("cantidad", 0) or 0)
            for i in cart["items"]
        )
        cart["total"] = total
        total_text.value = f"${total:.2f}"

        # Show IVA if configured
        iva_rate = await controller.obtener_tasa_iva()
        if iva_rate > 0:
            iva_amount = total * iva_rate
            iva_text.value = f"IVA ({iva_rate*100:.0f}%): ${iva_amount:.2f}  |  Total c/IVA: ${total + iva_amount:.2f}"
        else:
            iva_text.value = ""

    async def handle_add(e):
        nonlocal cart
        if not producto_dd.value:
            return
        pid = int(producto_dd.value)
        prod = next((p for p in productos if p["id"] == pid), None)
        if not prod:
            return
        try:
            qty = int(cantidad_field.value or "1")
        except ValueError:
            qty = 1
        qty = max(qty, 1)
        stock = prod.get("cantidad", 0) or 0
        if qty > stock:
            SnackBarHelper.error(app.page, f"Stock insuficiente (disponible: {stock})")
            return
        unit_price = prod.get("precio", 0) or 0
        ok = await controller.agregar_al_carrito(pid, qty, unit_price)
        if ok:
            SnackBarHelper.success(app.page, f"{prod['nombre']} agregado al carrito")
            cart = await controller.obtener_carrito_con_items()
            await rebuild()
            producto_dd.value = None
            cantidad_field.value = "1"
            app.page.update()

    async def handle_clear(e):
        nonlocal cart
        if not cart or not cart.get("id"):
            return
        ok = await controller.vaciar_carrito(cart["id"])
        if ok:
            cart = await controller.obtener_carrito_con_items()
            await rebuild()
            SnackBarHelper.info(app.page, "Carrito vaciado")
            app.page.update()

    async def handle_checkout(e):
        nonlocal cart
        if not cart or not cart.get("items"):
            SnackBarHelper.error(app.page, "El carrito está vacío")
            return

        # Navigate to POS with cart items pre-loaded
        from ui.sales import show_new_sale_with_cart

        await show_new_sale_with_cart(app, cart)

    if cart and cart.get("items"):
        await rebuild()

    add_btn = ft.Button(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.ADD_CIRCLE, color="white"), ft.Text("Agregar", color="white")],
            spacing=5,
        ),
        on_click=handle_add,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    clear_btn = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.DELETE_SWEEP), ft.Text("Vaciar Carrito")],
            spacing=5,
        ),
        on_click=handle_clear,
    )

    checkout_btn = ft.Button(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.CHECK_CIRCLE, color="white"), ft.Text("Ir a Pagar", color="white", weight=ft.FontWeight.BOLD)],
            spacing=5,
        ),
        on_click=handle_checkout,
        style=ft.ButtonStyle(bgcolor="green700"),
    )

    if app.main_view:
        app.main_view.content = ft.Column(
            [
                AppHeader.create("Carrito de Compra", "Carrito persistente por usuario"),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Agregar Producto", size=14, weight=ft.FontWeight.BOLD, color=THEME_PRIMARY_COLOR),
                            ft.ResponsiveRow(
                                [
                                    ft.Container(producto_dd, col={"sm": 12, "md": 6, "lg": 6}),
                                    ft.Container(cantidad_field, col={"sm": 4, "md": 2, "lg": 1}),
                                    ft.Container(add_btn, col={"sm": 4, "md": 2, "lg": 2}),
                                ],
                                columns=12,
                                spacing=10,
                            ),
                            ft.Divider(),
                            ft.Text("Items en Carrito", size=14, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=items_table,
                                expand=True,
                            ),
                            ft.Row(
                                [
                                    ft.Column(
                                        [
                                            total_text,
                                            iva_text,
                                        ]
                                    ),
                                    ft.Row([clear_btn, checkout_btn], spacing=10),
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


async def show_cart_config(app):
    """Display sales configuration (IVA, default payment, etc.)."""
    theme_manager.palette(page=app.page)
    controller = app.controller

    config = await controller.obtener_config_ventas()
    status_text = ft.Text("", size=12, color="#475569")

    iva_field = ft.TextField(
        label="Tasa de IVA (ej: 0.16 para 16%%)",
        value=config.get("iva_rate", "0.0"),
        width=300,
        filled=True,
        fill_color="#F8FAFC",
        color="#0F172A",
    )
    metodo_dd = ft.Dropdown(
        label="Método de pago predeterminado",
        options=[
            ft.dropdown.Option("efectivo", "Efectivo"),
            ft.dropdown.Option("tarjeta", "Tarjeta"),
            ft.dropdown.Option("transferencia", "Transferencia"),
            ft.dropdown.Option("otro", "Otro"),
        ],
        value=config.get("default_payment_method", "efectivo"),
        width=300,
        fill_color="#F8FAFC",
    )
    discount_field = ft.TextField(
        label="Descuento predeterminado (%)",
        value=config.get("default_discount", "0"),
        width=300,
        filled=True,
        fill_color="#F8FAFC",
        color="#0F172A",
    )
    credit_field = ft.TextField(
        label="Límite de crédito (0 = sin límite)",
        value=config.get("credit_limit", "0"),
        width=300,
        filled=True,
        fill_color="#F8FAFC",
        color="#0F172A",
    )
    auto_clear_switch = ft.Switch(
        label="Limpiar carrito al completar venta",
        value=config.get("auto_clear_cart", "true").lower() == "true",
    )
    enable_discounts_switch = ft.Switch(
        label="Habilitar descuentos en ventas",
        value=config.get("enable_discounts", "true").lower() == "true",
    )

    async def handle_save(e):
        await controller.guardar_config_ventas("iva_rate", iva_field.value)
        await controller.guardar_config_ventas("default_payment_method", metodo_dd.value)
        await controller.guardar_config_ventas("default_discount", discount_field.value)
        await controller.guardar_config_ventas("credit_limit", credit_field.value)
        await controller.guardar_config_ventas("auto_clear_cart", str(auto_clear_switch.value).lower())
        await controller.guardar_config_ventas("enable_discounts", str(enable_discounts_switch.value).lower())
        status_text.value = "Configuración guardada"
        SnackBarHelper.success(app.page, "Configuración de ventas guardada")
        app.page.update()

    save_btn = ft.Button(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.SAVE, color="white"), ft.Text("Guardar", color="white")],
            spacing=5,
        ),
        on_click=handle_save,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    if app.main_view:
        app.main_view.content = ft.Column(
            [
                AppHeader.create("Configuración de Ventas", "IVA, descuentos, métodos de pago"),
                ft.Container(
                    content=ft.Column(
                        [
                            iva_field,
                            metodo_dd,
                            discount_field,
                            credit_field,
                            auto_clear_switch,
                            enable_discounts_switch,
                            ft.Container(height=10),
                            ft.Row([save_btn], spacing=10),
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
