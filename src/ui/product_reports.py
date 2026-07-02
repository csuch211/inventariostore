"""Product reports views, refactored for clarity.
Product reports views — variantes and reportes.

Full implementation with CRUD operations for product variants
and customizable reports.
"""

import asyncio
import json

import flet as ft

from config.settings import THEME_ACCENT_COLOR, THEME_PRIMARY_COLOR, THEME_SUCCESS_COLOR
from core.theme_manager import theme_manager
from ui.components import AppHeader, FormField, SnackBarHelper
from utils.i18n import t

from ._utils import _fmt_money, get_logger

logger = get_logger(__name__)


def _c(app):
    """Get the active color palette."""
    return theme_manager.palette(page=app.page)


# ============ Variantes de Producto ============


async def show_variantes(app):
    """Display product variants management view."""
    c = _c(app)
    controller = app.controller

    async def refresh():
        try:
            variantes = await controller.obtener_variantes()
        except Exception as e:
            logger.error("Error al obtener variantes: %s", e)
            variantes = []

        rows = []
        for v in variantes:
            atributos = v.get("atributos", "")
            if isinstance(atributos, str):
                try:
                    atributos = json.loads(atributos)
                except Exception as e:
                    logger.error("Error al parsear atributos JSON: %s", e)
            attr_str = (
                ", ".join(f"{k}: {v2}" for k, v2 in atributos.items())
                if isinstance(atributos, dict)
                else str(atributos)
            )

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(v.get("id", "")))),
                        ft.DataCell(ft.Text(str(v.get("producto_codigo", "")))),
                        ft.DataCell(ft.Text(str(v.get("sku", "")))),
                        ft.DataCell(ft.Text(attr_str[:50])),
                        ft.DataCell(ft.Text(str(v.get("cantidad", 0)))),
                        ft.DataCell(ft.Text(_fmt_money(v.get("precio_override", 0) or 0))),
                        ft.DataCell(
                            ft.Text(
                                "Activo" if v.get("activo") else "Inactivo",
                                color="green" if v.get("activo") else "gray600",
                            )
                        ),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.Icons.EDIT,
                                        icon_color=THEME_PRIMARY_COLOR,
                                        tooltip="Editar stock",
                                        on_click=lambda ev, vid=v["id"]: asyncio.create_task(
                                            edit_stock(vid)
                                        ),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.Icons.DELETE,
                                        icon_color=THEME_ACCENT_COLOR,
                                        tooltip="Desactivar",
                                        on_click=lambda ev, vid=v["id"]: asyncio.create_task(
                                            delete_variant(vid)
                                        ),
                                    ),
                                ]
                            )
                        ),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text(t("products.code"))),
                ft.DataColumn(ft.Text("SKU")),
                ft.DataColumn(ft.Text("Atributos")),
                ft.DataColumn(ft.Text("Stock")),
                ft.DataColumn(ft.Text("Precio")),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
            heading_row_color=c["primary_light"],
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay variantes registradas", color=c["text_secondary"]),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column(
                [
                    AppHeader.create(
                        t("phase3.variantes.title"), "Gestión de variantes de producto"
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
            app.page.update()

    async def open_new(e):
        productos = await controller.obtener_todos_productos()
        prod_opts = [f"{p.get('id')} — {p.get('codigo')}" for p in productos]
        prod = FormField.create_dropdown("Producto", prod_opts)
        sku = FormField.create_text_field("SKU")
        atributos = FormField.create_text_field(
            "Atributos (JSON)", hint='{"talla":"M","color":"rojo"}'
        )
        cantidad = FormField.create_text_field("Cantidad", hint="0")
        precio = FormField.create_text_field("Precio override", hint="0.00")
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                prod_id = int((prod.value or "0").split(" — ")[0])
                attr_dict = json.loads(atributos.value or "{}") if atributos.value else {}
                precio_val = float(precio.value) if precio.value else None
                ok, res = await controller.crear_variante(
                    producto_id=prod_id,
                    sku=sku.value or "",
                    atributos=attr_dict,
                    cantidad=int(cantidad.value or 0),
                    precio_override=precio_val,
                )
            except json.JSONDecodeError:
                err.value = "JSON de atributos inválido"
                app.page.update()
                return
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, "Variante creada")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Nueva Variante"),
            content=ft.Column(
                [prod, sku, atributos, cantidad, precio, err], tight=True, spacing=10
            ),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: app.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    async def edit_stock(variante_id):
        cantidad = FormField.create_text_field("Nueva cantidad")
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.actualizar_stock_variante(
                    variante_id=variante_id,
                    cantidad=int(cantidad.value or 0),
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, "Stock actualizado")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Actualizar Stock"),
            content=ft.Column([cantidad, err], tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: app.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    async def delete_variant(variante_id):
        ok, res = await controller.eliminar_variante(variante_id)
        if ok:
            SnackBarHelper.success(app.page, "Variante desactivada")
            await refresh()
        else:
            SnackBarHelper.error(app.page, (res or {}).get("error", "Error"))

    new_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.ADD, color="white"),
                ft.Text("Nueva Variante", color="white"),
            ],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    await refresh()


# ============ Reportes Personalizables ============


async def show_reportes(app):
    """Display customizable reports view."""
    c = _c(app)
    controller = app.controller

    async def refresh():
        try:
            plantillas = await controller.obtener_plantillas_reporte()
            await controller.obtener_modulos_reporte()
        except Exception as e:
            logger.error("Error al obtener plantillas/módulos: %s", e)
            plantillas = []

        rows = []
        for p in plantillas:
            columnas = p.get("columnas", "")
            if isinstance(columnas, str):
                try:
                    columnas = json.loads(columnas)
                except Exception as e:
                    logger.error("Error al parsear columnas JSON: %s", e)
            col_str = ", ".join(columnas) if isinstance(columnas, list) else str(columnas)

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(p.get("id", "")))),
                        ft.DataCell(ft.Text(str(p.get("nombre", "")))),
                        ft.DataCell(ft.Text(str(p.get("modulo", "")))),
                        ft.DataCell(ft.Text(col_str[:60])),
                        ft.DataCell(ft.Text(str(p.get("creado_en", "")))),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.Icons.PLAY_ARROW,
                                        icon_color=THEME_SUCCESS_COLOR,
                                        tooltip="Ejecutar",
                                        on_click=lambda ev, pp=p: asyncio.create_task(
                                            run_report(pp)
                                        ),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.Icons.DELETE,
                                        icon_color=THEME_ACCENT_COLOR,
                                        tooltip="Eliminar",
                                        on_click=lambda ev, pid=p["id"]: asyncio.create_task(
                                            delete_template(pid)
                                        ),
                                    ),
                                ]
                            )
                        ),
                    ]
                )
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Nombre")),
                ft.DataColumn(ft.Text("Módulo")),
                ft.DataColumn(ft.Text("Columnas")),
                ft.DataColumn(ft.Text("Creado")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=rows,
            heading_row_color=c["primary_light"],
        )

        body = (
            ft.Container(content=table, padding=20, expand=True)
            if rows
            else ft.Container(
                content=ft.Text("No hay plantillas guardadas", color=c["text_secondary"]),
                padding=40,
            )
        )

        if app.main_view:
            app.main_view.content = ft.Column(
                [
                    AppHeader.create(t("phase3.reportes.title"), "Reportes personalizables"),
                    ft.Container(
                        content=ft.Row([new_btn], alignment=ft.MainAxisAlignment.END),
                        padding=20,
                    ),
                    body,
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            app.page.update()

    async def open_new(e):
        try:
            modulos = await controller.obtener_modulos_reporte()
        except Exception as e:
            logger.error("Error al obtener módulos de reporte: %s", e)
            modulos = []

        nombre = FormField.create_text_field("Nombre del reporte")
        modulo_opts = [m.get("key", "") for m in modulos]
        modulo = FormField.create_dropdown("Módulo", modulo_opts)
        columnas = FormField.create_text_field(
            "Columnas (separadas por coma)", hint="codigo,nombre,precio"
        )
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                cols = [c.strip() for c in (columnas.value or "").split(",") if c.strip()]
                ok, res = await controller.guardar_plantilla_reporte(
                    nombre=nombre.value or "",
                    modulo=modulo.value or "productos",
                    columnas=cols,
                )
            except Exception as ex:
                err.value = str(ex)
                app.page.update()
                return
            if ok:
                app.page.pop_dialog()
                SnackBarHelper.success(app.page, "Plantilla guardada")
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Nueva Plantilla"),
            content=ft.Column([nombre, modulo, columnas, err], tight=True, spacing=10),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=lambda ev: app.page.pop_dialog()),
                ft.TextButton(t("common.save"), on_click=save),
            ],
        )
        dialog.open = True
        app.page.show_dialog(dialog)
        app.page.update()

    async def run_report(plantilla):
        try:
            columnas = plantilla.get("columnas", [])
            if isinstance(columnas, str):
                columnas = json.loads(columnas)
            result = await controller.ejecutar_reporte(
                modulo=plantilla.get("modulo", "productos"),
                columnas=columnas,
            )
            if "error" in result:
                SnackBarHelper.error(app.page, result["error"])
            else:
                data = result.get("data", [])
                SnackBarHelper.success(app.page, f"Reporte: {len(data)} registros")
        except Exception:
            SnackBarHelper.error(app.page, "Error al ejecutar el reporte.")

    async def delete_template(template_id):
        ok, res = await controller.eliminar_plantilla_reporte(template_id)
        if ok:
            SnackBarHelper.success(app.page, "Plantilla eliminada")
            await refresh()
        else:
            SnackBarHelper.error(app.page, (res or {}).get("error", "Error"))

    new_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.ADD, color="white"),
                ft.Text("Nueva Plantilla", color="white"),
            ],
            spacing=5,
        ),
        on_click=open_new,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )

    await refresh()
