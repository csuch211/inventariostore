"""Sales / POS views, refactored for clarity.
Sales / POS views extracted from AppView.

Each function takes an ``app`` parameter (the AppView instance) and uses
``app.page``, ``app.controller``, etc. instead of ``self``.
"""

import asyncio
import contextlib

import flet as ft

from config.settings import (
    THEME_ACCENT_COLOR,
    THEME_PRIMARY_COLOR,
)
from services.permissions import Perm
from ui.components import (
    AppHeader,
    DialogHelper,
    FormField,
    SnackBarHelper,
)
from utils.i18n import t

from ._utils import get_logger

logger = get_logger(__name__)


def _find_submit_btn_static(page, label: str, translated_label: str = ""):
    """Walk the live page tree and return the first ft.Button whose
    visible text matches ``label`` (or ``translated_label``).

    Used by the focus chains built in ``_show_stock_management`` and
    ``_show_new_sale`` to land on the submit button without forcing
    the surrounding ``ft.Column`` literal to be split into named
    temporaries. Returns ``None`` if no match is found.

    The Button's ``content`` is often a ``ft.Row`` of (Icon, Text),
    so we descend into ``Row``/``Column`` content and match against
    any descendant ``ft.Text`` whose ``value`` matches.
    """
    if not page:
        return None
    candidates = {label}
    if translated_label:
        candidates.add(translated_label)
    try:
        stack = [page]
        while stack:
            node = stack.pop()
            if isinstance(node, ft.Button):
                content = getattr(node, "content", None)
                txt = getattr(content, "value", None) or getattr(content, "text", None)
                if isinstance(txt, str) and txt.strip() in candidates:
                    return node
                sub = [content]
                sub.extend(getattr(content, "controls", None) or [])
                for item in sub:
                    if isinstance(item, ft.Text):
                        v = getattr(item, "value", None)
                        if isinstance(v, str) and v.strip() in candidates:
                            return node
            inner = getattr(node, "content", None)
            if inner is not None and inner is not node:
                stack.append(inner)
            for c in getattr(node, "controls", None) or []:
                if c is not node:
                    stack.append(c)
    except Exception as e:
        logger.error("Error en _find_submit_btn_static: %s", e)
        return None
    return None


async def show_new_sale_with_cart(app, cart: dict):
    """Open POS with items pre-loaded from a persistent cart."""
    from ui.sales import show_new_sale

    # Override cart items loading by injecting into the function's flow
    # by passing cart items through to the standard POS
    if not cart or not cart.get("items"):
        await show_new_sale(app)
        return

    original_cart_items = cart["items"]
    productos = await app.controller.obtener_todos_productos()
    clientes = await app.controller.obtener_clientes()

    cart_items = []
    for ci in original_cart_items:
        cart_items.append({
            "producto_id": ci["producto_id"],
            "codigo": ci.get("codigo", ""),
            "nombre": ci.get("nombre", ""),
            "cantidad": ci.get("cantidad", 0) or 1,
            "precio_unitario": ci.get("precio_unitario", 0) or 0,
            "subtotal": ((ci.get("precio_unitario", 0) or 0) * (ci.get("cantidad", 0) or 1)),
        })

    total_text = ft.Text("$0.00", size=24, weight=ft.FontWeight.BOLD, color=THEME_PRIMARY_COLOR)
    cart_table_rows = []
    cart_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(t("products.code"))),
            ft.DataColumn(ft.Text(t("products.name"))),
            ft.DataColumn(ft.Text(t("sales.qty"))),
            ft.DataColumn(ft.Text(t("sales.unit_price"))),
            ft.DataColumn(ft.Text(t("sales.subtotal"))),
            ft.DataColumn(ft.Text("")),
        ],
        rows=[],
    )

    cliente_dd = ft.Dropdown(
        label=t("sales.client"),
        options=[ft.dropdown.Option(key="0", text=t("sales.walkin"))]
        + [ft.dropdown.Option(key=str(c["id"]), text=c["nombre"]) for c in clientes],
        value="0",
        border_color=THEME_PRIMARY_COLOR,
        focused_border_color=THEME_ACCENT_COLOR,
        filled=True,
        fill_color="gray50",
    )

    producto_dd = ft.Dropdown(
        label=t("sales.select_product"),
        options=[
            ft.dropdown.Option(
                key=str(p["id"]),
                text=f"{p.get('codigo', '')} - {p.get('nombre', '')} (${p.get('precio', 0):.2f})",
            )
            for p in productos
        ],
        border_color=THEME_PRIMARY_COLOR,
        focused_border_color=THEME_ACCENT_COLOR,
        filled=True,
        fill_color="gray50",
    )
    cantidad_field = FormField.create_text_field(label=t("sales.qty"), hint="1")

    metodo_dd = ft.Dropdown(
        label=t("sales.payment_method"),
        options=[
            ft.dropdown.Option("efectivo", t("sales.payment_cash")),
            ft.dropdown.Option("tarjeta", t("sales.payment_card")),
            ft.dropdown.Option("transferencia", t("sales.payment_transfer")),
            ft.dropdown.Option("otro", t("sales.payment_other")),
        ],
        value="efectivo",
        border_color=THEME_PRIMARY_COLOR,
        focused_border_color=THEME_ACCENT_COLOR,
        filled=True,
        fill_color="gray50",
    )
    referencia_field = FormField.create_text_field(label=t("sales.reference"))

    def rebuild_cart():
        nonlocal cart_table_rows
        rows = []
        for i, item in enumerate(cart_items):
            idx = i
            async def remove_item(e, i=idx):
                cart_items.pop(i)
                rebuild_cart()
                if app.main_view:
                    app.page.update()
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(item.get("codigo", ""))),
                        ft.DataCell(ft.Text(item.get("nombre", "")[:20])),
                        ft.DataCell(ft.Text(str(item["cantidad"]))),
                        ft.DataCell(ft.Text(f"${item['precio_unitario']:.2f}")),
                        ft.DataCell(ft.Text(f"${item['subtotal']:.2f}")),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.icons.Icons.DELETE,
                                icon_color=THEME_ACCENT_COLOR,
                                on_click=remove_item,
                            )
                        ),
                    ]
                )
            )
        cart_table.rows = rows
        total = sum(item["subtotal"] for item in cart_items)
        total_text.value = f"${total:.2f}"

    rebuild_cart()

    async def handle_add_item(e):
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
        if qty <= 0:
            qty = 1
        if qty > prod.get("cantidad", 0):
            SnackBarHelper.error(app.page, f"Stock insuficiente (disponible: {prod.get('cantidad', 0)})")
            return
        unit_price = prod.get("precio", 0)
        cart_items.append({
            "producto_id": pid,
            "codigo": prod.get("codigo", ""),
            "nombre": prod.get("nombre", ""),
            "cantidad": qty,
            "precio_unitario": unit_price,
            "subtotal": qty * unit_price,
        })
        rebuild_cart()
        producto_dd.value = None
        cantidad_field.value = "1"
        app.page.update()

    async def handle_complete_sale(e):
        if not cart_items:
            SnackBarHelper.error(app.page, "Agregue al menos un producto")
            return
        cliente_id = int(cliente_dd.value or "0")
        metodo = metodo_dd.value or "efectivo"
        ref = referencia_field.value or ""
        ok, result = await app.controller.crear_venta(
            cliente_id=cliente_id, items=cart_items, metodo_pago=metodo, referencia=ref,
        )
        if ok:
            # Mark cart as converted
            if cart.get("id"):
                await app.controller.marcar_carrito_convertido(cart["id"])
            app.page.pop_dialog()
            SnackBarHelper.success(app.page, f"Venta #{result['id']} creada — Total: ${result['total']:.2f}")
            await show_sales(app)
        else:
            SnackBarHelper.error(app.page, result.get("error", t("common.error")))

    add_btn = ft.IconButton(
        icon=ft.icons.Icons.ADD_CIRCLE, icon_color="green", icon_size=32,
        on_click=handle_add_item, tooltip=t("sales.add_item"),
    )

    complete_btn = ft.Button(
        content=ft.Row([
            ft.Icon(ft.icons.Icons.CHECK_CIRCLE, color="white"),
            ft.Text(t("sales.complete_sale"), color="white", weight=ft.FontWeight.BOLD),
        ], spacing=5),
        on_click=handle_complete_sale,
        style=ft.ButtonStyle(bgcolor="green700"),
    )

    back_btn = ft.OutlinedButton(
        content=ft.Row([ft.Icon(ft.icons.Icons.ARROW_BACK), ft.Text(t("common.cancel"))], spacing=5),
        on_click=lambda e: app.page.pop_dialog(),
    )

    content = ft.Column([
        AppHeader.create(t("sales.new"), t("sales.subtitle")),
        ft.Container(
            content=ft.Column([
                cliente_dd, ft.Divider(),
                ft.Text(t("sales.items"), size=14, weight=ft.FontWeight.BOLD, color=THEME_PRIMARY_COLOR),
                ft.ResponsiveRow([
                    ft.Container(producto_dd, col={"sm": 12, "md": 5, "lg": 5}),
                    ft.Container(cantidad_field, col={"sm": 6, "md": 2, "lg": 2}),
                    ft.Container(add_btn, col={"sm": 2, "md": 1, "lg": 1}),
                ], columns=12, spacing=10, alignment=ft.MainAxisAlignment.START),
                cart_table,
                ft.Row([ft.Text(t("sales.total"), size=16, weight=ft.FontWeight.BOLD), total_text],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                ft.ResponsiveRow([
                    ft.Container(metodo_dd, col={"sm": 6, "md": 4, "lg": 3}),
                    ft.Container(referencia_field, col={"sm": 6, "md": 4, "lg": 3}),
                ], columns=12, spacing=10),
                ft.Row([back_btn, complete_btn], spacing=10),
            ], spacing=15),
            padding=20, expand=True,
        ),
    ], expand=True, scroll=ft.ScrollMode.AUTO)

    if app.main_view:
        app.main_view.content = content
        app.page.update()


async def show_sales(app):
    """Display sales list and POS interface."""
    ventas = await app.controller.obtener_ventas()

    async def open_new(e):
        await show_new_sale(app)

    async def handle_detail(e, v):
        await show_sale_detail(app, v)

    async def handle_cancel(e, v):
        DialogHelper.confirmation_dialog(
            app.page,
            title=t("sales.cancel"),
            content=t("sales.cancel_confirm", id=v.get("id", "")),
            on_yes=lambda ev: _do_cancel(v),
        )

    async def _do_cancel(v):
        app.page.pop_dialog()
        ok, _ = await app.controller.cancelar_venta(v.get("id"))
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
            await show_sales(app)
        else:
            SnackBarHelper.error(app.page, t("common.error"))

    def status_label(s):
        return {
            "completada": t("sales.status.completed"),
            "cancelada": t("sales.status.cancelled"),
        }.get(s, s)

    def status_color(s):
        return {"completada": "green", "cancelada": "red"}.get(s, "gray600")

    def build_rows():
        rows = []
        for v in ventas:
            can_cancel = (
                v.get("estado") == "completada"
                and Perm.VENTAS_CANCELAR in app.controller.current_user_permissions
            )
            actions = [
                ft.IconButton(
                    icon=ft.icons.Icons.VISIBILITY,
                    icon_color=THEME_PRIMARY_COLOR,
                    tooltip=t("sales.detail"),
                    on_click=lambda e, vv=v: asyncio.create_task(handle_detail(e, vv)),
                ),
            ]
            if can_cancel:
                actions.append(
                    ft.IconButton(
                        icon=ft.icons.Icons.CANCEL,
                        icon_color="red",
                        tooltip=t("sales.cancel"),
                        on_click=lambda e, vv=v: asyncio.create_task(handle_cancel(e, vv)),
                    ),
                )
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f"#{v.get('id', '')}")),
                        ft.DataCell(ft.Text(str(v.get("cliente_nombre", "")) or t("sales.walkin"))),
                        ft.DataCell(ft.Text(f"${v.get('total', 0):.2f}")),
                        ft.DataCell(
                            ft.Text(
                                status_label(v.get("estado", "")),
                                color=status_color(v.get("estado", "")),
                                weight=ft.FontWeight.BOLD,
                            )
                        ),
                        ft.DataCell(ft.Text(str(v.get("creado_en", ""))[:10])),
                        ft.DataCell(ft.Row(actions, spacing=2)),
                    ]
                )
            )
        return rows

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("#")),
            ft.DataColumn(ft.Text(t("sales.client"))),
            ft.DataColumn(ft.Text(t("sales.total"))),
            ft.DataColumn(ft.Text(t("sales.status"))),
            ft.DataColumn(ft.Text(t("sales.date"))),
            ft.DataColumn(ft.Text("")),
        ],
        rows=build_rows(),
    )

    new_btn = ft.Button(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.ADD, color="white"), ft.Text(t("sales.new"), color="white")],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    content = ft.Column(
        [
            AppHeader.create(t("sales.title"), t("sales.subtitle")),
            ft.Container(
                content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                padding=20,
            ),
            ft.Container(content=table, padding=20, expand=True)
            if ventas
            else ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.icons.Icons.SHOPPING_CART, size=48, color="gray400"),
                        ft.Text(t("sales.empty"), color="gray600"),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=60,
                alignment="center",
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()


async def show_new_sale(app):
    """Display POS interface to create a new sale."""
    productos = await app.controller.obtener_todos_productos()
    clientes = await app.controller.obtener_clientes()

    cart_items = []
    total_text = ft.Text("$0.00", size=24, weight=ft.FontWeight.BOLD, color=THEME_PRIMARY_COLOR)
    cart_table_rows = []
    cart_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(t("products.code"))),
            ft.DataColumn(ft.Text(t("products.name"))),
            ft.DataColumn(ft.Text(t("sales.qty"))),
            ft.DataColumn(ft.Text(t("sales.unit_price"))),
            ft.DataColumn(ft.Text(t("sales.subtotal"))),
            ft.DataColumn(ft.Text("")),
        ],
        rows=[],
    )

    cliente_dd = ft.Dropdown(
        label=t("sales.client"),
        options=[ft.dropdown.Option(key="0", text=t("sales.walkin"))]
        + [ft.dropdown.Option(key=str(c["id"]), text=c["nombre"]) for c in clientes],
        value="0",
        border_color=THEME_PRIMARY_COLOR,
        focused_border_color=THEME_ACCENT_COLOR,
        filled=True,
        fill_color="gray50",
    )

    producto_dd = ft.Dropdown(
        label=t("sales.select_product"),
        options=[
            ft.dropdown.Option(
                key=str(p["id"]),
                text=f"{p.get('codigo', '')} - {p.get('nombre', '')} (${p.get('precio', 0):.2f})",
            )
            for p in productos
        ],
        border_color=THEME_PRIMARY_COLOR,
        focused_border_color=THEME_ACCENT_COLOR,
        filled=True,
        fill_color="gray50",
    )
    cantidad_field = FormField.create_text_field(label=t("sales.qty"), hint="1")

    metodo_dd = ft.Dropdown(
        label=t("sales.payment_method"),
        options=[
            ft.dropdown.Option("efectivo", t("sales.payment_cash")),
            ft.dropdown.Option("tarjeta", t("sales.payment_card")),
            ft.dropdown.Option("transferencia", t("sales.payment_transfer")),
            ft.dropdown.Option("otro", t("sales.payment_other")),
        ],
        value="efectivo",
        border_color=THEME_PRIMARY_COLOR,
        focused_border_color=THEME_ACCENT_COLOR,
        filled=True,
        fill_color="gray50",
    )
    referencia_field = FormField.create_text_field(label=t("sales.reference"))

    sale_field_chain = [
        ("cliente", cliente_dd, "producto"),
        ("producto", producto_dd, "cantidad"),
        ("cantidad", cantidad_field, "metodo"),
        ("metodo", metodo_dd, "referencia"),
        ("referencia", referencia_field, "submit"),
    ]
    sale_by_name = {
        "cliente": cliente_dd,
        "producto": producto_dd,
        "cantidad": cantidad_field,
        "metodo": metodo_dd,
        "referencia": referencia_field,
    }

    def _find_sale_submit_btn():
        return _find_submit_btn_static(
            app.main_view, "Complete Sale", t("sales.complete_sale")
        ) or _find_submit_btn_static(app.page, "Complete Sale", t("sales.complete_sale"))

    async def _advance_sale(name): # Made async
        if name == "referencia":
            btn = _find_sale_submit_btn()
            if btn is not None:
                with contextlib.suppress(Exception):
                    await btn.focus() # Added await
            return
        tgt = sale_by_name.get(name)
        if tgt is not None:
            with contextlib.suppress(Exception):
                await tgt.focus() # Added await

    for name, field, _ in sale_field_chain:

        async def _on_submit_sale(_e, _name=name): # Made async
            await _advance_sale(_name) # Added await

        if isinstance(field, ft.Dropdown):
            field.on_select = _on_submit_sale
        else:
            field.on_submit = _on_submit_sale # Corrected from _on_on_submit_sale

        async def _on_key_sale(_e, _name=name): # Made async
            if getattr(_e, "key", "") in ("Tab", "\t") and not getattr(_e, "shift", False):
                await _advance_sale(_name) # Added await
                with contextlib.suppress(Exception):
                    _e.handled = True

        with contextlib.suppress(Exception):
            field.on_key_down = _on_key_sale

    def rebuild_cart():
        nonlocal cart_table_rows
        rows = []
        for i, item in enumerate(cart_items):
            idx = i

            async def remove_item(e, i=idx):
                cart_items.pop(i)
                rebuild_cart()
                if app.main_view:
                    app.page.update()

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(item.get("codigo", ""))),
                        ft.DataCell(ft.Text(item.get("nombre", "")[:20])),
                        ft.DataCell(ft.Text(str(item["cantidad"]))),
                        ft.DataCell(ft.Text(f"${item['precio_unitario']:.2f}")),
                        ft.DataCell(ft.Text(f"${item['subtotal']:.2f}")),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.icons.Icons.DELETE,
                                icon_color=THEME_ACCENT_COLOR,
                                on_click=remove_item,
                            )
                        ),
                    ]
                )
            )
        cart_table.rows = rows
        total = sum(item["subtotal"] for item in cart_items)
        total_text.value = f"${total:.2f}"

    async def handle_add_item(e):
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
        if qty <= 0:
            qty = 1
        if qty > prod.get("cantidad", 0):
            SnackBarHelper.error(
                app.page, f"Stock insuficiente (disponible: {prod.get('cantidad', 0)})"
            )
            return
        unit_price = prod.get("precio", 0)
        cart_items.append(
            {
                "producto_id": pid,
                "codigo": prod.get("codigo", ""),
                "nombre": prod.get("nombre", ""),
                "cantidad": qty,
                "precio_unitario": unit_price,
                "subtotal": qty * unit_price,
            }
        )
        rebuild_cart()
        producto_dd.value = None
        cantidad_field.value = "1"
        app.page.update()

    async def handle_complete_sale(e):
        if not cart_items:
            SnackBarHelper.error(app.page, "Agregue al menos un producto")
            return
        sum(item["subtotal"] for item in cart_items)
        cliente_id = int(cliente_dd.value or "0")
        metodo = metodo_dd.value or "efectivo"
        ref = referencia_field.value or ""
        ok, result = await app.controller.crear_venta(
            cliente_id=cliente_id,
            items=cart_items,
            metodo_pago=metodo,
            referencia=ref,
        )
        if ok:
            app.page.pop_dialog()
            SnackBarHelper.success(
                app.page, f"Venta #{result['id']} creada — Total: ${result['total']:.2f}"
            )
            await show_sales(app)
        else:
            SnackBarHelper.error(app.page, result.get("error", t("common.error")))

    add_btn = ft.IconButton(
        icon=ft.icons.Icons.ADD_CIRCLE,
        icon_color="green",
        icon_size=32,
        on_click=handle_add_item,
        tooltip=t("sales.add_item"),
    )

    complete_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.CHECK_CIRCLE, color="white"),
                ft.Text(t("sales.complete_sale"), color="white", weight=ft.FontWeight.BOLD),
            ],
            spacing=5,
        ),
        on_click=handle_complete_sale,
        style=ft.ButtonStyle(bgcolor="green700"),
    )

    back_btn = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.ARROW_BACK), ft.Text(t("common.cancel"))],
            spacing=5,
        ),
        on_click=lambda e: app.page.pop_dialog(),
    )

    content = ft.Column(
        [
            AppHeader.create(t("sales.new"), t("sales.subtitle")),
            ft.Container(
                content=ft.Column(
                    [
                        cliente_dd,
                        ft.Divider(),
                        ft.Text(
                            t("sales.items"),
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=THEME_PRIMARY_COLOR,
                        ),
                        ft.ResponsiveRow(
                            [
                                ft.Container(producto_dd, col={"sm": 12, "md": 5, "lg": 5}),
                                ft.Container(cantidad_field, col={"sm": 6, "md": 2, "lg": 2}),
                                ft.Container(add_btn, col={"sm": 2, "md": 1, "lg": 1}),
                            ],
                            columns=12,
                            spacing=10,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        cart_table,
                        ft.Row(
                            [
                                ft.Text(t("sales.total"), size=16, weight=ft.FontWeight.BOLD),
                                total_text,
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(),
                        ft.ResponsiveRow(
                            [
                                ft.Container(metodo_dd, col={"sm": 6, "md": 4, "lg": 3}),
                                ft.Container(referencia_field, col={"sm": 6, "md": 4, "lg": 3}),
                            ],
                            columns=12,
                            spacing=10,
                        ),
                        ft.Row([back_btn, complete_btn], spacing=10),
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

    if app.main_view:
        app.main_view.content = content
        app.page.update()


async def show_sale_detail(app, venta: dict):
    """Display detailed view of a sale."""
    full = await app.controller.obtener_venta(venta.get("id"))
    if not full:
        SnackBarHelper.error(app.page, "Venta no encontrada")
        return

    detalles = full.get("detalles", [])
    pagos = full.get("pagos", [])

    detail_rows = []
    for d in detalles:
        detail_rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(d.get("producto_codigo", "")))),
                    ft.DataCell(ft.Text(str(d.get("producto_nombre", "")))),
                    ft.DataCell(ft.Text(str(d.get("cantidad", 0)))),
                    ft.DataCell(ft.Text(f"${d.get('precio_unitario', 0):.2f}")),
                    ft.DataCell(ft.Text(f"${d.get('subtotal', 0):.2f}")),
                ]
            )
        )

    back_btn = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.icons.Icons.ARROW_BACK), ft.Text(t("common.cancel"))],
            spacing=5,
        ),
        on_click=lambda e: asyncio.create_task(show_sales(app)),
    )

    status = full.get("estado", "")
    status_text = (
        t("sales.status.completed") if status == "completada" else t("sales.status.cancelled")
    )
    status_color_st = "green" if status == "completada" else "red"

    content = ft.Column(
        [
            AppHeader.create(f"{t('sales.detail')} #{full.get('id', '')}", ""),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Estado:", weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    status_text, color=status_color_st, weight=ft.FontWeight.BOLD
                                ),
                            ],
                            spacing=10,
                        ),
                        ft.Row(
                            [
                                ft.Text(f"{t('sales.client')}:", weight=ft.FontWeight.BOLD),
                                ft.Text(str(full.get("cliente_nombre", "")) or t("sales.walkin")),
                            ],
                            spacing=10,
                        ),
                        ft.Row(
                            [
                                ft.Text("Fecha:", weight=ft.FontWeight.BOLD),
                                ft.Text(str(full.get("creado_en", ""))[:16]),
                            ],
                            spacing=10,
                        ),
                        ft.Row(
                            [
                                ft.Text("Atendió:", weight=ft.FontWeight.BOLD),
                                ft.Text(str(full.get("creado_por", ""))),
                            ],
                            spacing=10,
                        ),
                        ft.Divider(),
                        ft.Text(
                            t("sales.items"),
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=THEME_PRIMARY_COLOR,
                        ),
                        ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text(t("products.code"))),
                                ft.DataColumn(ft.Text(t("products.name"))),
                                ft.DataColumn(ft.Text(t("sales.qty"))),
                                ft.DataColumn(ft.Text(t("sales.unit_price"))),
                                ft.DataColumn(ft.Text(t("sales.subtotal"))),
                            ],
                            rows=detail_rows,
                        ),
                        ft.Row(
                            [
                                ft.Text(t("sales.total"), size=16, weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    f"${full.get('total', 0):.2f}",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=THEME_PRIMARY_COLOR,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(),
                        ft.Text(
                            "Pagos", size=14, weight=ft.FontWeight.BOLD, color=THEME_PRIMARY_COLOR
                        ),
                        *[
                            ft.Row(
                                [
                                    ft.Text(f"{p.get('metodo', '')}:", weight=ft.FontWeight.BOLD),
                                    ft.Text(f"${p.get('monto', 0):.2f}"),
                                ],
                                spacing=10,
                            )
                            for p in pagos
                        ],
                        ft.Container(height=20),
                        back_btn,
                    ],
                    spacing=10,
                ),
                padding=20,
                expand=True,
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()
