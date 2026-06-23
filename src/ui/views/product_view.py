"""
Product-related view functions extracted from app_view.py.
"""

import asyncio
import contextlib

import flet as ft

from config.settings import (
    ITEMS_PER_PAGE,
    THEME_ACCENT_COLOR,
    THEME_PRIMARY_COLOR,
    THEME_SURFACE_COLOR,
)
from services.permissions import Perm
from ui.components import AppHeader, DialogHelper, FormField, SnackBarHelper
from utils.i18n import t


async def show_products_list(app):
    """Display products list with search and pagination"""
    try:
        app.all_products = await app.controller.obtener_todos_productos()
        app.filtered_products = app.all_products
        app.current_page = 0
        update_products_table(app)

    except Exception as e:
        SnackBarHelper.error(app.page, f"Error al cargar productos: {e!s}")


def update_products_table(app):
    """Update the products table based on current filters and pagination"""
    try:
        app.total_pages = max(
            1, (len(app.filtered_products) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        )
        start_idx = app.current_page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_products = app.filtered_products[start_idx:end_idx]

        rows = []
        can_bulk = (
            app.controller.has_permission(Perm.BULK_ELIMINAR)
            or app.controller.has_permission(Perm.BULK_CATEGORIA)
            or app.controller.has_permission(Perm.BULK_EXPORTAR)
        )
        for product in page_products:

            async def handle_edit(e, p=product):
                await show_product_form(app, p)

            async def handle_delete(e, p=product):
                await confirm_delete_product(app, p)

            def make_handler(p):
                def handle_select(e):
                    pid = p["id"]
                    if pid in app._selected_product_ids:
                        app._selected_product_ids.discard(pid)
                    else:
                        app._selected_product_ids.add(pid)
                    app._refresh_bulk_task = asyncio.create_task(app._refresh_bulk_toolbar())

                return handle_select

            stock = product.get("cantidad", 0)
            stock_min = product.get("stock_min", 0)
            is_low_stock = stock_min > 0 and stock <= stock_min
            pid = product.get("id")
            checked = pid in app._selected_product_ids
            cells = []
            if can_bulk:
                cells.append(
                    ft.DataCell(ft.Checkbox(value=checked, on_change=make_handler(product)))
                )
            cells.extend(
                [
                    ft.DataCell(ft.Text(str(product.get("codigo", "")))),
                    ft.DataCell(ft.Text(str(product.get("nombre", ""))[:30])),
                    ft.DataCell(
                        ft.Text(
                            str(stock),
                            color="red" if stock <= 0 else ("orange" if is_low_stock else "blue"),
                            weight=ft.FontWeight.BOLD,
                        )
                    ),
                    ft.DataCell(ft.Text(f"${product.get('precio', 0):.2f}")),
                    ft.DataCell(ft.Text(str(product.get("categoria", "N/A")))),
                    ft.DataCell(ft.Text(str(product.get("proveedor_nombre", "")) or "-", size=12)),
                    ft.DataCell(
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.icons.Icons.CREATE,
                                    icon_color=THEME_PRIMARY_COLOR,
                                    on_click=handle_edit,
                                    tooltip="Editar",
                                ),
                                ft.IconButton(
                                    icon=ft.icons.Icons.REMOVE_CIRCLE,
                                    icon_color=THEME_ACCENT_COLOR,
                                    on_click=handle_delete,
                                    tooltip="Eliminar",
                                ),
                            ],
                            spacing=5,
                        )
                    ),
                ]
            )
            rows.append(ft.DataRow(cells=cells))

        bulk_cols = [ft.DataColumn(ft.Text(t("bulk.select_label")))] if can_bulk else []
        table = ft.DataTable(
            columns=[
                *bulk_cols,
                ft.DataColumn(ft.Text("Código")),
                ft.DataColumn(ft.Text("Nombre")),
                ft.DataColumn(ft.Text("Stock")),
                ft.DataColumn(ft.Text("Precio")),
                ft.DataColumn(ft.Text("Categoría")),
                ft.DataColumn(ft.Text("Proveedor")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
        )

        app.page_info_text.value = f"Página {app.current_page + 1} de {app.total_pages} | Total: {len(app.filtered_products)} productos"

        async def handle_prev(e):
            if app.current_page > 0:
                app.current_page -= 1
                update_products_table(app)

        async def handle_next(e):
            if app.current_page < app.total_pages - 1:
                app.current_page += 1
                update_products_table(app)

        page_btns = []
        max_visible = 5
        half = max_visible // 2
        start_page = max(0, app.current_page - half)
        end_page = min(app.total_pages, start_page + max_visible)
        if end_page - start_page < max_visible:
            start_page = max(0, end_page - max_visible)

        for p in range(start_page, end_page):
            is_current = p == app.current_page

            async def go_to_page(e, page_num=p):
                if 0 <= page_num < app.total_pages:
                    app.current_page = page_num
                    update_products_table(app)

            page_btns.append(
                ft.Container(
                    content=ft.Text(
                        str(p + 1),
                        size=13,
                        weight=ft.FontWeight.BOLD if is_current else ft.FontWeight.NORMAL,
                        color="white" if is_current else THEME_PRIMARY_COLOR,
                    ),
                    padding=8,
                    bgcolor=THEME_PRIMARY_COLOR if is_current else "transparent",
                    border_radius=4,
                    on_click=go_to_page,
                    ink=True,
                )
            )

        pagination_row = ft.Row(
            [
                ft.IconButton(
                    icon=ft.icons.Icons.ARROW_BACK_IOS,
                    on_click=handle_prev,
                    disabled=app.current_page == 0,
                ),
                *page_btns,
                ft.IconButton(
                    icon=ft.icons.Icons.ARROW_FORWARD_IOS,
                    on_click=handle_next,
                    disabled=app.current_page >= app.total_pages - 1,
                ),
                ft.Container(expand=True),
                app.page_info_text,
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=4,
        )

        app._bulk_toolbar_container = None
        if can_bulk:
            sel_count = len(app._selected_product_ids)
            bulk_content = ft.Row(
                [
                    ft.Text(
                        t("bulk.select_products", count=sel_count),
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Button(
                        content=ft.Text(
                            t("bulk.delete_btn", default="").replace(
                                "{count}", str(max(sel_count, 1))
                            )
                            or "Eliminar"
                        ),
                        on_click=lambda e: asyncio.create_task(app._bulk_delete()),
                        style=ft.ButtonStyle(bgcolor=THEME_ACCENT_COLOR, color="white"),
                    )
                    if app.controller.has_permission(Perm.BULK_ELIMINAR)
                    else ft.Container(),
                    ft.OutlinedButton(
                        content=ft.Text(t("bulk.category_btn")),
                        on_click=lambda e: asyncio.create_task(app._bulk_change_category()),
                    ),
                    ft.OutlinedButton(
                        content=ft.Text(t("bulk.export_btn")),
                        on_click=lambda e: asyncio.create_task(app._bulk_export()),
                    ),
                ],
                spacing=8,
                wrap=True,
            )
            app._bulk_toolbar_container = ft.Container(
                content=bulk_content,
                padding=20,
                visible=bool(app._selected_product_ids),
            )

        content = ft.Column(
            [
                AppHeader.create("Productos", "Gestión del catálogo"),
                ft.Container(
                    content=ft.ResponsiveRow(
                        [
                            ft.Container(
                                app.search_field,
                                col={"sm": 12, "md": 8, "lg": 9},
                            ),
                            ft.Container(
                                ft.Button(
                                    content=ft.Text("+ Nuevo Producto"),
                                    on_click=lambda e: asyncio.create_task(handle_new_product(e)),
                                    style=ft.ButtonStyle(
                                        bgcolor=THEME_PRIMARY_COLOR,
                                        color="white",
                                    ),
                                ),
                                col={"sm": 12, "md": 4, "lg": 3},
                            ),
                        ],
                        columns=12,
                        spacing=10,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=20,
                ),
                app._bulk_toolbar_container if app._bulk_toolbar_container else ft.Container(),
                ft.Container(
                    content=table,
                    padding=20,
                    expand=True,
                ),
                ft.Container(
                    content=pagination_row,
                    padding=10,
                    bgcolor=THEME_SURFACE_COLOR,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        if app.main_view:
            app.main_view.content = content
            app.page.update()

    except Exception as e:
        SnackBarHelper.error(app.page, f"Error actualizando tabla: {e!s}")


async def show_product_form(app, product: dict | None = None):
    """Display form for adding/editing products"""
    app.current_product_edit = product
    is_edit = product is not None

    proveedores = await app.controller.obtener_proveedores()
    categorias = await app.controller.obtener_categorias()
    cat_options = (
        [c["nombre"] for c in categorias]
        if categorias
        else ["Electrónica", "Ropa", "Alimentos", "Otros"]
    )

    codigo_field = FormField.create_text_field(
        label="Código",
        hint="Código único del producto",
        required=True,
    )
    nombre_field = FormField.create_text_field(
        label="Nombre",
        hint="Nombre del producto",
        required=True,
    )
    cantidad_field = FormField.create_text_field(
        label="Cantidad",
        hint="0",
        required=True,
    )
    precio_field = FormField.create_text_field(
        label="Precio",
        hint="0.00",
        required=True,
    )
    categoria_field = FormField.create_dropdown(
        label="Categoría",
        options=cat_options,
    )
    stock_min_field = FormField.create_text_field(
        label="Stock Mínimo",
        hint="0",
    )
    unidad_field = ft.Dropdown(
        label="Unidad de Medida",
        options=[
            ft.dropdown.Option("unidad", "Unidad"),
            ft.dropdown.Option("kg", "Kilogramo"),
            ft.dropdown.Option("g", "Gramo"),
            ft.dropdown.Option("l", "Litro"),
            ft.dropdown.Option("ml", "Mililitro"),
            ft.dropdown.Option("m", "Metro"),
            ft.dropdown.Option("caja", "Caja"),
            ft.dropdown.Option("pack", "Pack"),
        ],
        value="unidad",
        border_color=THEME_PRIMARY_COLOR,
        focused_border_color=THEME_ACCENT_COLOR,
        filled=True,
        fill_color="gray50",
    )
    proveedor_field = ft.Dropdown(
        label="Proveedor",
        options=[ft.dropdown.Option(key=str(p["id"]), text=p["nombre"]) for p in proveedores],
        border_color=THEME_PRIMARY_COLOR,
        focused_border_color=THEME_ACCENT_COLOR,
        filled=True,
        fill_color="gray50",
    )
    descripcion_field = FormField.create_text_field(
        label="Descripción",
        hint="Descripción del producto",
        multiline=True,
    )

    field_chain = [
        ("codigo", codigo_field, "nombre"),
        ("nombre", nombre_field, "cantidad"),
        ("cantidad", cantidad_field, "precio"),
        ("precio", precio_field, "stock_min"),
        ("stock_min", stock_min_field, "categoria"),
        ("categoria", categoria_field, "unidad"),
        ("unidad", unidad_field, "proveedor"),
        ("proveedor", proveedor_field, "descripcion"),
        ("descripcion", descripcion_field, "save"),
    ]
    by_name = {
        "codigo": codigo_field,
        "nombre": nombre_field,
        "cantidad": cantidad_field,
        "precio": precio_field,
        "stock_min": stock_min_field,
        "categoria": categoria_field,
        "unidad": unidad_field,
        "proveedor": proveedor_field,
        "descripcion": descripcion_field,
    }
    next_field = {name: by_name.get(target) for name, _, target in field_chain}
    save_btn_ref: list = [None]

    def _advance(name: str):
        if name == "descripcion":
            if save_btn_ref[0] is not None:
                save_btn_ref[0].focus()
            return
        target = next_field.get(name)
        if target is not None:
            with contextlib.suppress(Exception):
                target.focus()

    for name, field, _ in field_chain:
        if name != "descripcion":

            def _on_submit(_e, _name=name):
                _advance(_name)

            field.on_submit = _on_submit

        def _on_key(_e, _name=name):
            if getattr(_e, "key", "") in ("Tab", "\t") and not getattr(_e, "shift", False):
                _advance(_name)
                with contextlib.suppress(Exception):
                    _e.handled = True

        try:
            field.on_key_down = _on_key
        except Exception:
            pass

    if is_edit:
        codigo_field.value = product.get("codigo", "")
        codigo_field.disabled = True
        nombre_field.value = product.get("nombre", "")
        cantidad_field.value = str(product.get("cantidad", ""))
        precio_field.value = str(product.get("precio", ""))
        categoria_field.value = product.get("categoria", "")
        stock_min_field.value = str(product.get("stock_min", 0))
        proveedor_field.value = (
            str(product.get("proveedor_id", "")) if product.get("proveedor_id") else None
        )
        unidad_field.value = product.get("unidad_medida", "unidad")
        descripcion_field.value = product.get("descripcion", "")

    error_text = ft.Text("", color=THEME_ACCENT_COLOR, size=12)

    async def handle_save(e):
        error_text.value = ""

        if not codigo_field.value:
            error_text.value = "El código es requerido"
            app.page.update()
            return

        if not nombre_field.value:
            error_text.value = "El nombre es requerido"
            app.page.update()
            return

        if not cantidad_field.value:
            error_text.value = "La cantidad es requerida"
            app.page.update()
            return

        if not precio_field.value:
            error_text.value = "El precio es requerido"
            app.page.update()
            return

        save_btn.disabled = True
        try:
            proveedor_id = (
                int(proveedor_field.value)
                if proveedor_field.value and proveedor_field.value != "None"
                else None
            )
            if is_edit:
                success, result = await app.controller.actualizar_producto(
                    producto_id=product.get("id", 0),
                    nombre=nombre_field.value,
                    cantidad=cantidad_field.value,
                    precio=precio_field.value,
                    descripcion=descripcion_field.value,
                    categoria=categoria_field.value or "Otros",
                    stock_min=stock_min_field.value or "0",
                    proveedor_id=proveedor_id,
                )
            else:
                success, result = await app.controller.crear_producto(
                    codigo=codigo_field.value,
                    nombre=nombre_field.value,
                    cantidad=cantidad_field.value,
                    precio=precio_field.value,
                    descripcion=descripcion_field.value,
                    categoria=categoria_field.value or "Otros",
                    stock_min=stock_min_field.value or "0",
                    proveedor_id=proveedor_id,
                )

            if success:
                msg = "Producto actualizado" if is_edit else "Producto creado"
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, msg)
                await show_products_list(app)
            else:
                SnackBarHelper.error(app.page, result.get("error", "Error desconocido"))
                save_btn.disabled = False

        except Exception as ex:
            SnackBarHelper.error(app.page, f"Error: {ex!s}")
            save_btn.disabled = False

    save_btn = ft.Button(
        content=ft.Text("Guardar"),
        width=150,
        on_click=handle_save,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, color="white"),
    )
    save_btn_ref[0] = save_btn

    cancel_btn = ft.OutlinedButton(
        content=ft.Text("Cancelar"),
        width=150,
        on_click=lambda e: app.page.pop_dialog(),
    )

    code_section = ft.Container(visible=False)

    async def _build_code_cards(codigo):
        b64_barcode = await app.controller.obtener_codigo_barras_base64(codigo)
        b64_qr = await app.controller.obtener_qr_base64(codigo)
        cards = []
        if b64_barcode:
            img = ft.Image(src="", width=200, height=60, fit=ft.BoxFit.CONTAIN)
            img.src_base64 = b64_barcode
            cards.append(
                ft.Container(
                    content=ft.Column(
                        [ft.Text("Código de Barras", size=11, color="gray600"), img],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                    ),
                    col={"sm": 6, "md": 6, "lg": 6},
                    padding=10,
                    bgcolor="gray50",
                    border_radius=8,
                )
            )
        if b64_qr:
            img = ft.Image(src="", width=100, height=100, fit=ft.BoxFit.CONTAIN)
            img.src_base64 = b64_qr
            cards.append(
                ft.Container(
                    content=ft.Column(
                        [ft.Text("Código QR", size=11, color="gray600"), img],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                    ),
                    col={"sm": 6, "md": 6, "lg": 6},
                    padding=10,
                    bgcolor="gray50",
                    border_radius=8,
                )
            )
        return cards

    if is_edit:
        cards = await _build_code_cards(product.get("codigo", ""))
        if cards:
            code_section.content = ft.ResponsiveRow(cards, columns=12, spacing=15)
            code_section.visible = True

    async def handle_generate_codes(e):
        code = codigo_field.value.strip()
        if not code:
            SnackBarHelper.error(app.page, "Primero ingrese un código de producto")
            return
        await app.controller.generar_codigos_producto(code)
        cards = await _build_code_cards(code)
        if cards:
            code_section.content = ft.ResponsiveRow(cards, columns=12, spacing=15)
            code_section.visible = True
        else:
            code_section.visible = False
        app.page.update()
        SnackBarHelper.success(app.page, "Códigos generados")

    gen_codes_btn = ft.TextButton(
        content=ft.Text("Generar códigos de barras y QR"),
        icon=ft.icons.Icons.QR_CODE,
        on_click=handle_generate_codes,
    )

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(
            "Editar Producto" if is_edit else "Nuevo Producto",
            weight=ft.FontWeight.BOLD,
            size=20,
        ),
        content=ft.Container(
            content=ft.Column(
                [
                    codigo_field,
                    nombre_field,
                    ft.ResponsiveRow(
                        [cantidad_field, precio_field],
                        columns=12,
                        spacing=15,
                    ),
                    ft.ResponsiveRow(
                        [stock_min_field, categoria_field],
                        columns=12,
                        spacing=15,
                    ),
                    ft.ResponsiveRow(
                        [unidad_field, proveedor_field],
                        columns=12,
                        spacing=15,
                    ),
                    descripcion_field,
                    code_section,
                    gen_codes_btn,
                    error_text,
                ],
                spacing=15,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=560,
        ),
        actions=[
            ft.TextButton(
                "Cancelar",
                on_click=cancel_btn.on_click,
            ),
            ft.Button(
                content=ft.Text("Guardar"),
                on_click=save_btn.on_click,
                style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, color="white"),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    app.page.show_dialog(dialog)
    app.page.update()


async def confirm_delete_product(app, product: dict):
    """Show confirmation dialog before deleting product"""

    async def handle_delete(e):
        app.page.pop_dialog()
        try:
            success, result = await app.controller.eliminar_producto(product.get("id", 0))
            if success:
                SnackBarHelper.success(app.page, "Producto eliminado")
                await show_products_list(app)
            else:
                SnackBarHelper.error(app.page, result.get("error", "Error al eliminar"))
        except Exception as ex:
            SnackBarHelper.error(app.page, f"Error: {ex!s}")

    DialogHelper.confirmation_dialog(
        app.page,
        title="Eliminar Producto",
        content=f"¿Estás seguro de que deseas eliminar '{product.get('nombre')}'?",
        on_yes=handle_delete,
    )


async def handle_new_product(app, e=None):
    """Handle new product button click"""
    await show_product_form(app)
