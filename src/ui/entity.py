"""Entity CRUD views (categories, suppliers, clients) refactored for clarity.
Entity CRUD views (categories, suppliers, clients) extracted from AppView.

Each function takes an ``app`` parameter (the AppView instance) and uses
``app.page``, ``app.controller``, etc. instead of ``self``.
"""

import asyncio

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


async def show_categories(app):
    """Display categories CRUD view."""
    categorias = await app.controller.obtener_categorias()

    async def open_new(e):
        await show_category_form(app, None, categorias)

    async def handle_edit(e, cat):
        await show_category_form(app, cat, categorias)

    async def handle_delete(e, cat):
        DialogHelper.confirmation_dialog(
            app.page,
            title=t("common.delete"),
            content=t("categories.delete_confirm", name=cat.get("nombre", "")),
            on_yes=lambda ev: _do_delete(cat),
        )

    async def _do_delete(cat):
        app.page.pop_dialog()
        ok, _ = await app.controller.eliminar_categoria(cat.get("id"))
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
            await show_categories(app)
        else:
            SnackBarHelper.error(app.page, t("common.error"))

    def build_rows():
        rows = []
        for c in categorias:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(c.get("id", "")))),
                        ft.DataCell(ft.Text(str(c.get("nombre", "")))),
                        ft.DataCell(ft.Text(str(c.get("descripcion", "")) or "-")),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.Icons.CREATE,
                                        icon_color=THEME_PRIMARY_COLOR,
                                        on_click=lambda e, cc=c: asyncio.create_task(
                                            handle_edit(e, cc)
                                        ),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.Icons.DELETE,
                                        icon_color=THEME_ACCENT_COLOR,
                                        on_click=lambda e, cc=c: asyncio.create_task(
                                            handle_delete(e, cc)
                                        ),
                                    ),
                                ],
                                spacing=5,
                            )
                        ),
                    ]
                )
            )
        return rows

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text(t("categories.name"))),
            ft.DataColumn(ft.Text(t("categories.description"))),
            ft.DataColumn(ft.Text(t("common.edit") + " / " + t("common.delete"))),
        ],
        rows=build_rows(),
    )

    new_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.ADD, color="white"),
                ft.Text(t("categories.new"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    empty_msg = (
        ft.Container(
            content=ft.Text(t("categories.empty"), color="gray600"),
            padding=40,
            alignment="center",
        )
        if not categorias
        else ft.Container()
    )

    content = ft.Column(
        [
            AppHeader.create(t("categories.title"), t("categories.subtitle")),
            ft.Container(
                content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                padding=20,
            ),
            ft.Container(content=table, padding=20, expand=True) if categorias else empty_msg,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()


async def show_category_form(app, categoria, categorias):
    """Show category add/edit dialog."""
    is_edit = categoria is not None
    nombre = FormField.create_text_field(
        label=t("categories.name"), hint=t("categories.name"), required=True
    )
    descripcion = FormField.create_text_field(label=t("categories.description"), multiline=True)
    if is_edit:
        nombre.value = categoria.get("nombre", "")
        descripcion.value = categoria.get("descripcion", "")

    async def save(e):
        if not nombre.value or len(nombre.value) < 3:
            SnackBarHelper.error(app.page, t("common.validation_error"))
            return
        if is_edit:
            ok, _ = await app.controller.actualizar_categoria(
                categoria_id=categoria.get("id"),
                nombre=nombre.value,
                descripcion=descripcion.value or "",
            )
        else:
            ok, _ = await app.controller.crear_categoria(
                nombre=nombre.value, descripcion=descripcion.value or ""
            )
        app.page.pop_dialog()
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
            await show_categories(app)
        else:
            SnackBarHelper.error(app.page, t("common.error"))

    dialog = ft.AlertDialog(
        title=ft.Text(t("categories.new") if not is_edit else t("common.edit")),
        content=ft.Column([nombre, descripcion], tight=True, spacing=10),
        actions=[
            ft.TextButton(t("common.cancel"), on_click=lambda e: app.page.pop_dialog()),
            ft.TextButton(t("common.save"), on_click=save),
        ],
    )
    dialog.open = True
    app.page.show_dialog(dialog)
    app.page.update()


async def show_suppliers(app):
    """Display suppliers CRUD view."""
    proveedores = await app.controller.obtener_proveedores()

    async def open_new(e):
        await show_supplier_form(app, None)

    async def handle_edit(e, sup):
        await show_supplier_form(app, sup)

    async def handle_delete(e, sup):
        DialogHelper.confirmation_dialog(
            app.page,
            title=t("common.delete"),
            content=t("suppliers.delete_confirm", name=sup.get("nombre", "")),
            on_yes=lambda ev: _do_delete(sup),
        )

    async def _do_delete(sup):
        app.page.pop_dialog()
        ok, _ = await app.controller.eliminar_proveedor(sup.get("id"))
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
            await show_suppliers(app)
        else:
            SnackBarHelper.error(app.page, t("common.error"))

    def build_rows():
        rows = []
        for s in proveedores:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(s.get("nombre", "")))),
                        ft.DataCell(ft.Text(str(s.get("contacto", "")) or "-")),
                        ft.DataCell(ft.Text(str(s.get("telefono", "")) or "-")),
                        ft.DataCell(ft.Text(str(s.get("email", "")) or "-")),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.Icons.CREATE,
                                        icon_color=THEME_PRIMARY_COLOR,
                                        on_click=lambda e, ss=s: asyncio.create_task(
                                            handle_edit(e, ss)
                                        ),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.Icons.DELETE,
                                        icon_color=THEME_ACCENT_COLOR,
                                        on_click=lambda e, ss=s: asyncio.create_task(
                                            handle_delete(e, ss)
                                        ),
                                    ),
                                ],
                                spacing=5,
                            )
                        ),
                    ]
                )
            )
        return rows

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(t("suppliers.name"))),
            ft.DataColumn(ft.Text(t("suppliers.contact"))),
            ft.DataColumn(ft.Text(t("suppliers.phone"))),
            ft.DataColumn(ft.Text(t("suppliers.email"))),
            ft.DataColumn(ft.Text(t("common.edit") + " / " + t("common.delete"))),
        ],
        rows=build_rows(),
    )

    new_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.ADD, color="white"),
                ft.Text(t("suppliers.new"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    content = ft.Column(
        [
            AppHeader.create(t("suppliers.title"), t("suppliers.subtitle")),
            ft.Container(
                content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                padding=20,
            ),
            ft.Container(content=table, padding=20, expand=True)
            if proveedores
            else ft.Container(
                content=ft.Text(t("suppliers.empty"), color="gray600"),
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


async def show_supplier_form(app, proveedor):
    """Show supplier add/edit dialog."""
    is_edit = proveedor is not None
    nombre = FormField.create_text_field(label=t("suppliers.name"), required=True)
    contacto = FormField.create_text_field(label=t("suppliers.contact"))
    telefono = FormField.create_text_field(label=t("suppliers.phone"))
    email = FormField.create_text_field(label=t("suppliers.email"))
    direccion = FormField.create_text_field(label=t("suppliers.address"), multiline=True)

    if is_edit:
        nombre.value = proveedor.get("nombre", "")
        contacto.value = proveedor.get("contacto", "")
        telefono.value = proveedor.get("telefono", "")
        email.value = proveedor.get("email", "")
        direccion.value = proveedor.get("direccion", "")

    async def save(e):
        if not nombre.value or len(nombre.value) < 3:
            SnackBarHelper.error(app.page, t("common.validation_error"))
            return
        if is_edit:
            ok, _ = await app.controller.actualizar_proveedor(
                proveedor_id=proveedor.get("id"),
                nombre=nombre.value,
                contacto=contacto.value or "",
                telefono=telefono.value or "",
                email=email.value or "",
                direccion=direccion.value or "",
            )
        else:
            ok, _ = await app.controller.crear_proveedor(
                nombre=nombre.value,
                contacto=contacto.value or "",
                telefono=telefono.value or "",
                email=email.value or "",
                direccion=direccion.value or "",
            )
        app.page.pop_dialog()
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
            await show_suppliers(app)
        else:
            SnackBarHelper.error(app.page, t("common.error"))

    dialog = ft.AlertDialog(
        title=ft.Text(t("suppliers.new") if not is_edit else t("common.edit")),
        content=ft.Column(
            [nombre, contacto, telefono, email, direccion],
            tight=True,
            spacing=10,
        ),
        actions=[
            ft.TextButton(t("common.cancel"), on_click=lambda e: app.page.pop_dialog()),
            ft.TextButton(t("common.save"), on_click=save),
        ],
    )
    dialog.open = True
    app.page.show_dialog(dialog)
    app.page.update()


async def show_clients(app):
    """Display customers CRUD view."""
    clientes = await app.controller.obtener_clientes()

    async def open_new(e):
        await show_client_form(app, None)

    async def handle_edit(e, c):
        await show_client_form(app, c)

    async def handle_delete(e, c):
        DialogHelper.confirmation_dialog(
            app.page,
            title=t("common.delete"),
            content=t("clients.delete_confirm", name=c.get("nombre", "")),
            on_yes=lambda ev: _do_delete(c),
        )

    async def _do_delete(c):
        app.page.pop_dialog()
        ok, _ = await app.controller.eliminar_cliente(c.get("id"))
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
            await show_clients(app)
        else:
            SnackBarHelper.error(app.page, t("common.error"))

    can_manage = Perm.CLIENTES_GESTIONAR in app.controller.current_user_permissions

    def build_rows():
        rows = []
        for c in clientes:
            actions = []
            if can_manage:
                actions.append(
                    ft.IconButton(
                        icon=ft.icons.Icons.CREATE,
                        icon_color=THEME_PRIMARY_COLOR,
                        on_click=lambda e, cc=c: asyncio.create_task(handle_edit(e, cc)),
                    )
                )
                actions.append(
                    ft.IconButton(
                        icon=ft.icons.Icons.DELETE,
                        icon_color=THEME_ACCENT_COLOR,
                        on_click=lambda e, cc=c: asyncio.create_task(handle_delete(e, cc)),
                    )
                )
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(c.get("nombre", "")))),
                        ft.DataCell(ft.Text(str(c.get("telefono", "")) or "-")),
                        ft.DataCell(ft.Text(str(c.get("email", "")) or "-")),
                        ft.DataCell(ft.Text(str(c.get("direccion", "")) or "-")),
                        ft.DataCell(ft.Row(actions, spacing=2)),
                    ]
                )
            )
        return rows

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(t("clients.name"))),
            ft.DataColumn(ft.Text(t("clients.phone"))),
            ft.DataColumn(ft.Text(t("clients.email"))),
            ft.DataColumn(ft.Text(t("clients.address"))),
            ft.DataColumn(ft.Text("")),
        ],
        rows=build_rows(),
    )

    header_actions = []
    if can_manage:
        header_actions.append(
            ft.Button(
                content=ft.Row(
                    [
                        ft.Icon(ft.icons.Icons.ADD, color="white"),
                        ft.Text(t("clients.new"), color="white"),
                    ],
                    spacing=5,
                ),
                on_click=open_new,
                style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
            )
        )

    content = ft.Column(
        [
            AppHeader.create(t("clients.title"), t("clients.subtitle")),
            ft.Container(
                content=ft.Row(header_actions, alignment=ft.MainAxisAlignment.END),
                padding=20,
            ),
            ft.Container(content=table, padding=20, expand=True)
            if clientes
            else ft.Container(
                content=ft.Text(t("clients.empty"), color="gray600"),
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


async def show_client_form(app, cliente):
    """Show customer add/edit dialog."""
    is_edit = cliente is not None
    nombre = FormField.create_text_field(label=t("clients.name"), required=True)
    telefono = FormField.create_text_field(label=t("clients.phone"))
    email = FormField.create_text_field(label=t("clients.email"))
    direccion = FormField.create_text_field(label=t("clients.address"), multiline=True)

    if is_edit:
        nombre.value = cliente.get("nombre", "")
        telefono.value = cliente.get("telefono", "")
        email.value = cliente.get("email", "")
        direccion.value = cliente.get("direccion", "")

    async def save(e):
        if not nombre.value or len(nombre.value) < 2:
            SnackBarHelper.error(app.page, t("common.validation_error"))
            return
        if is_edit:
            ok, _ = await app.controller.actualizar_cliente(
                cliente_id=cliente.get("id"),
                nombre=nombre.value,
                telefono=telefono.value or "",
                email=email.value or "",
                direccion=direccion.value or "",
            )
        else:
            ok, _ = await app.controller.crear_cliente(
                nombre=nombre.value,
                telefono=telefono.value or "",
                email=email.value or "",
                direccion=direccion.value or "",
            )
        app.page.pop_dialog()
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
            await show_clients(app)
        else:
            SnackBarHelper.error(app.page, t("common.error"))

    dialog = ft.AlertDialog(
        title=ft.Text(t("clients.new") if not is_edit else t("common.edit")),
        content=ft.Column([nombre, telefono, email, direccion], tight=True, spacing=10),
        actions=[
            ft.TextButton(t("common.cancel"), on_click=lambda e: app.page.pop_dialog()),
            ft.TextButton(t("common.save"), on_click=save),
        ],
    )
    dialog.open = True
    app.page.show_dialog(dialog)
    app.page.update()
