"""HR views for human resources management, refactored for clarity.

Provides UI for employees, payroll, attendance, vacations, and evaluations.
"""

import asyncio

import flet as ft

from config.settings import (
    THEME_ACCENT_COLOR,
    THEME_PRIMARY_COLOR,
)
from core.theme_manager import theme_manager
from ui.components import AppHeader, FormField, SnackBarHelper
from utils.i18n import t

from ._utils import _fmt_money, get_logger

logger = get_logger(__name__)


def _c(app):
    """Get the active color palette."""
    return theme_manager.palette(page=app.page)


# ============ Empleados ============


async def show_empleados(app):
    """Display employees management view."""
    c = _c(app)
    controller = app.controller

    dept_filter = ft.Dropdown(
        label="Departamento",
        options=[ft.dropdown.Option(key="", text="Todos")],
        value="",
        width=200,
        fill_color=c["input_fill"],
        color=c["text_primary"],
    )

    async def refresh():
        try:
            departamentos = await controller.obtener_departamentos()
            dept_filter.options = [ft.dropdown.Option(key="", text="Todos")] + [
                ft.dropdown.Option(key=d, text=d) for d in departamentos
            ]
        except Exception as e:
            logger.error("Error al obtener departamentos: %s", e)

        departamento = dept_filter.value or None
        try:
            empleados = await controller.obtener_empleados(departamento=departamento)
        except Exception as e:
            logger.error("Error al obtener empleados: %s", e)
            empleados = []

        rows = []
        for e in empleados:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(e.get("numero_empleado", "")))),
                        ft.DataCell(ft.Text(f"{e.get('nombre', '')} {e.get('apellido', '')}")),
                        ft.DataCell(ft.Text(str(e.get("puesto", "")))),
                        ft.DataCell(ft.Text(str(e.get("departamento", "")))),
                        ft.DataCell(ft.Text(_fmt_money(e.get("salario_base", 0)))),
                        ft.DataCell(ft.Text(str(e.get("fecha_ingreso", "")))),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.Icons.EDIT,
                                    icon_color=THEME_PRIMARY_COLOR,
                                    tooltip="Editar",
                                    on_click=lambda ev, eid=e["id"]: asyncio.create_task(edit_employee(eid)),
                                ),
                                ft.IconButton(
                                    icon=ft.icons.Icons.DELETE,
                                    icon_color=THEME_ACCENT_COLOR,
                                    tooltip="Desactivar",
                                    on_click=lambda ev, eid=e["id"]: asyncio.create_task(deactivate_employee(eid)),
                                ),
                            ])
                        ),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Nombre")),
                ft.DataColumn(ft.Text("Puesto")),
                ft.DataColumn(ft.Text("Departamento")),
                ft.DataColumn(ft.Text("Salario")),
                ft.DataColumn(ft.Text("Ingreso")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
            heading_row_color=c["primary_light"],
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay empleados registrados", color=c["text_secondary"]),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column([
                AppHeader.create("Empleados", "Gestión de personal"),
                ft.Container(
                    content=ft.Row([dept_filter, new_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=20,
                ),
                body,
            ], expand=True, scroll=ft.ScrollMode.AUTO)
            app.page.update()

    dept_filter.on_change = lambda e: asyncio.create_task(refresh())

    async def open_new(e):
        nombre = FormField.create_text_field("Nombre")
        apellido = FormField.create_text_field("Apellido")
        email = FormField.create_text_field("Email")
        telefono = FormField.create_text_field("Teléfono")
        puesto = FormField.create_text_field("Puesto")
        departamento = FormField.create_text_field("Departamento")
        salario = FormField.create_text_field("Salario Base")
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.crear_empleado(
                    nombre=nombre.value or "",
                    apellido=apellido.value or "",
                    email=email.value or "",
                    telefono=telefono.value or "",
                    puesto=puesto.value or "",
                    departamento=departamento.value or "",
                    salario_base=float(salario.value or 0),
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, f"Empleado {res.get('numero_empleado', '')} creado")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Nuevo Empleado"),
            content=ft.Column([nombre, apellido, email, telefono, puesto, departamento, salario, err],
                             tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: app.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    async def edit_employee(empleado_id):
        empleado = await controller.obtener_empleado(empleado_id)
        if not empleado:
            SnackBarHelper.error(app.page, "Empleado no encontrado")
            return

        nombre = FormField.create_text_field("Nombre", value=empleado.get("nombre", ""))
        apellido = FormField.create_text_field("Apellido", value=empleado.get("apellido", ""))
        email = FormField.create_text_field("Email", value=empleado.get("email", ""))
        puesto = FormField.create_text_field("Puesto", value=empleado.get("puesto", ""))
        departamento = FormField.create_text_field("Departamento", value=empleado.get("departamento", ""))
        salario = FormField.create_text_field("Salario Base", value=str(empleado.get("salario_base", 0)))
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.actualizar_empleado(
                    empleado_id,
                    nombre=nombre.value,
                    apellido=apellido.value,
                    email=email.value,
                    puesto=puesto.value,
                    departamento=departamento.value,
                    salario_base=float(salario.value or 0),
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, "Empleado actualizado")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Editar Empleado"),
            content=ft.Column([nombre, apellido, email, puesto, departamento, salario, err],
                             tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: app.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    async def deactivate_employee(empleado_id):
        ok, res = await controller.eliminar_empleado(empleado_id)
        if ok:
            SnackBarHelper.success(app.page, "Empleado desactivado")
            await refresh()
        else:
            SnackBarHelper.error(app.page, (res or {}).get("error", "Error"))

    new_btn = ft.Button(
        content=ft.Row([
            ft.Icon(ft.icons.Icons.ADD, color="white"),
            ft.Text("Nuevo Empleado", color="white"),
        ], spacing=5),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    await refresh()
