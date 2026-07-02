"""
Bulk operations UI: multi-select delete, category change, export.

All functions receive the AppView instance as first parameter.
"""

import asyncio

import flet as ft

from core.theme_manager import theme_manager
from services.permissions import Perm
from ui.components import SnackBarHelper
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def refresh_toolbar(app_view) -> None:
    """Refresh just the bulk toolbar without rebuilding the entire table."""
    if not app_view._bulk_toolbar_container:
        return
    try:
        C = theme_manager.palette(page=app_view.page)
        sel_count = len(app_view._selected_product_ids)
        new_content = ft.Row(
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
                    on_click=lambda e: asyncio.create_task(bulk_delete(app_view)),
                    style=ft.ButtonStyle(bgcolor=C["accent"], color="white"),
                )
                if app_view.controller.has_permission(Perm.BULK_ELIMINAR)
                else ft.Container(),
                ft.OutlinedButton(
                    content=ft.Text(t("bulk.category_btn")),
                    on_click=lambda e: asyncio.create_task(bulk_change_category(app_view)),
                ),
                ft.OutlinedButton(
                    content=ft.Text(t("bulk.export_btn")),
                    on_click=lambda e: asyncio.create_task(bulk_export(app_view)),
                ),
            ],
            spacing=8,
            wrap=True,
        )
        app_view._bulk_toolbar_container.content = new_content
        app_view._bulk_toolbar_container.visible = bool(sel_count)
        app_view.page.update()
    except Exception:
        SnackBarHelper.error(app_view.page, "Error al actualizar la barra de herramientas.")


async def bulk_delete(app_view) -> None:
    ids = list(app_view._selected_product_ids)
    if not ids:
        SnackBarHelper.info(app_view.page, t("bulk.no_selection"))
        return

    def confirm(e):
        app_view.page.pop_dialog()
        app_view._bulk_task = asyncio.create_task(_do_bulk_delete(app_view, ids))

    dialog = ft.AlertDialog(
        title=ft.Text(t("common.delete")),
        content=ft.Text(t("bulk.delete_confirm", count=len(ids))),
        actions=[
            ft.TextButton(t("common.cancel"), on_click=lambda e: app_view.page.pop_dialog()),
            ft.TextButton(t("common.delete"), on_click=confirm),
        ],
    )
    dialog.open = True
    app_view.page.show_dialog(dialog)
    app_view.page.update()


async def _do_bulk_delete(app_view, ids):
    ok, count = await app_view.controller.bulk_eliminar_productos(ids)
    if ok:
        app_view._selected_product_ids.clear()
        SnackBarHelper.success(app_view.page, t("bulk.delete_success", count=count))
        await app_view._show_products_list()
    else:
        SnackBarHelper.error(app_view.page, t("common.error"))


async def bulk_change_category(app_view) -> None:
    ids = list(app_view._selected_product_ids)
    if not ids:
        SnackBarHelper.info(app_view.page, t("bulk.no_selection"))
        return
    categorias = await app_view.controller.obtener_categorias()
    cat_options = (
        [c["nombre"] for c in categorias]
        if categorias
        else ["Electrónica", "Ropa", "Alimentos", "Otros"]
    )
    dd = ft.Dropdown(
        label=t("bulk.category_placeholder"),
        options=[ft.dropdown.Option(c) for c in cat_options],
        width=250,
    )

    async def save(e):
        if not dd.value:
            SnackBarHelper.error(app_view.page, t("common.validation_error"))
            return
        ok, count = await app_view.controller.bulk_actualizar_categoria(ids, dd.value)
        app_view.page.pop_dialog()
        if ok:
            app_view._selected_product_ids.clear()
            SnackBarHelper.success(
                app_view.page, t("bulk.category_success", count=count, cat=dd.value)
            )
            await app_view._show_products_list()
        else:
            SnackBarHelper.error(app_view.page, t("common.error"))

    dialog = ft.AlertDialog(
        title=ft.Text(t("bulk.category_btn")),
        content=ft.Column(
            [ft.Text(t("bulk.select_products", count=len(ids))), dd], tight=True, spacing=10
        ),
        actions=[
            ft.TextButton(t("common.cancel"), on_click=lambda e: app_view.page.pop_dialog()),
            ft.TextButton(t("common.save"), on_click=save),
        ],
    )
    dialog.open = True
    app_view.page.show_dialog(dialog)
    app_view.page.update()


async def bulk_export(app_view) -> None:
    ids = list(app_view._selected_product_ids)
    if not ids:
        SnackBarHelper.info(app_view.page, t("bulk.no_selection"))
        return
    fmt = ft.Dropdown(
        label=t("bulk.export_format"),
        options=[
            ft.dropdown.Option("csv", "CSV"),
            ft.dropdown.Option("json", "JSON"),
            ft.dropdown.Option("xlsx", "Excel"),
        ],
        value="csv",
        width=200,
    )

    async def do_export(e):
        app_view.page.pop_dialog()
        ok, result = await app_view.controller.bulk_exportar_productos(ids, fmt.value)
        if ok:
            app_view._selected_product_ids.clear()
            SnackBarHelper.success(app_view.page, t("bulk.export_success", path=result))
        else:
            SnackBarHelper.error(app_view.page, result)
        await refresh_toolbar(app_view)

    dialog = ft.AlertDialog(
        title=ft.Text(t("bulk.export_btn")),
        content=ft.Column(
            [ft.Text(t("bulk.select_products", count=len(ids))), fmt], tight=True, spacing=10
        ),
        actions=[
            ft.TextButton(t("common.cancel"), on_click=lambda e: app_view.page.pop_dialog()),
            ft.TextButton(t("common.save"), on_click=do_export),
        ],
    )
    dialog.open = True
    app_view.page.show_dialog(dialog)
    app_view.page.update()
