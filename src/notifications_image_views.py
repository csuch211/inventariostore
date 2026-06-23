"""
Phase 3 UI views — part 2: push/email queue and image search.

Companion to phase3_views_part1.py. Re-exported by ui/phase3_views.py.

Note: The i18n language picker view (`show_i18n`) was removed; the sidebar
`LangSwitcher` component is now the single entry point for changing language.
"""

from __future__ import annotations

import asyncio
from typing import Any

import flet as ft

from config.settings import (
    THEME_ACCENT_COLOR,
    THEME_DIVIDER,
    THEME_INPUT_FILL,
    THEME_PRIMARY_COLOR,
    THEME_SUCCESS_COLOR,
    THEME_SURFACE_COLOR,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
)
from ui.components import (
    AppHeader,
    FormField,
    SnackBarHelper,
)
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


# ============ Module-level constants (hoisted allocations) ============


_BORDER_HAIRLINE = ft.border.Border(
    ft.BorderSide(1, THEME_DIVIDER),
    ft.BorderSide(1, THEME_DIVIDER),
    ft.BorderSide(1, THEME_DIVIDER),
    ft.BorderSide(1, THEME_DIVIDER),
)


_STATE_COLORS = {
    "pendiente": THEME_PRIMARY_COLOR,
    "enviado": THEME_SUCCESS_COLOR,
    "fallido": THEME_ACCENT_COLOR,
}


# Reused FilePicker instance — creating one per click leaked into page.overlay.
_image_search_picker: ft.FilePicker | None = None


def _ensure_image_search_picker(page: ft.Page) -> ft.FilePicker:
    """Return a single, persistent FilePicker for image search, ensuring it
    is registered on the current page's overlay.
    """
    global _image_search_picker
    if _image_search_picker is None:
        _image_search_picker = ft.FilePicker()
    # Always keep the picker on the current page. If a previous view on a
    # different page created it, re-parent it here so Flet can route events.
    if page.overlay is None:
        page.overlay = []
    if _image_search_picker not in page.overlay:
        page.overlay.append(_image_search_picker)
    return _image_search_picker


# ============ Push / Email queue ============


def _build_job_card(j: dict[str, Any]) -> ft.Container:
    """Build a single push-job card. Pure function — easy to test/cached."""
    estado = j.get("estado", "")
    color_estado = _STATE_COLORS.get(estado, THEME_TEXT_SECONDARY)
    ultimo_error = j.get("ultimo_error") or ""

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            f"#{j['id']} · {j.get('tipo', '')}",
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Container(
                            content=ft.Text(estado, size=11, color="white"),
                            bgcolor=color_estado,
                            padding=ft.Padding(left=8, right=8, top=2, bottom=2),
                            border_radius=8,
                        ),
                        ft.Container(expand=True),
                        ft.Text(
                            j.get("destinatario", ""),
                            size=11,
                            color=THEME_TEXT_SECONDARY,
                        ),
                    ],
                    spacing=10,
                ),
                ft.Text(j.get("asunto", ""), weight=ft.FontWeight.BOLD),
                ft.Text(
                    j.get("cuerpo", "")[:200],
                    size=11,
                    color=THEME_TEXT_SECONDARY,
                ),
                ft.Row(
                    [
                        ft.Text(
                            f"creado: {j.get('creado_en', '')}",
                            size=10,
                            color=THEME_TEXT_SECONDARY,
                        ),
                        ft.Container(expand=True),
                        ft.Text(
                            f"intentos: {j.get('intentos', 0)}",
                            size=10,
                            color=THEME_TEXT_SECONDARY,
                        ),
                    ],
                    spacing=6,
                ),
                (
                    ft.Text(
                        f"error: {ultimo_error}",
                        size=10,
                        color=THEME_ACCENT_COLOR,
                    )
                    if ultimo_error
                    else ft.Container()
                ),
            ],
            spacing=4,
        ),
        padding=12,
        border_radius=8,
        bgcolor=THEME_SURFACE_COLOR,
        border=_BORDER_HAIRLINE,
    )


async def show_push_queue(view) -> None:
    """List push/email jobs and let the user dispatch pending ones."""
    page = view.page
    main_view = view.main_view
    controller = view.controller

    estado_sel = ft.Dropdown(
        label=t("phase3.push.estado"),
        options=[
            ft.dropdown.Option(key="", text=t("phase3.push.all")),
            ft.dropdown.Option(key="pendiente", text=t("phase3.push.pendiente")),
            ft.dropdown.Option(key="enviado", text=t("phase3.push.enviado")),
            ft.dropdown.Option(key="fallido", text=t("phase3.push.fallido")),
        ],
        value="",
        width=180,
        fill_color=THEME_INPUT_FILL,
        color=THEME_TEXT_PRIMARY,
        text_style=ft.TextStyle(color=THEME_TEXT_PRIMARY, size=14),
    )

    # ListView virtualizes off-screen rows; Column renders everything eagerly.
    jobs_container = ft.ListView(spacing=6, expand=True, auto_scroll=False)

    async def refresh():
        jobs = await controller.obtener_jobs_push(estado=estado_sel.value or None, limit=200)
        if not jobs:
            new_controls: list[ft.Control] = [
                ft.Container(
                    content=ft.Text(t("phase3.push.empty"), color=THEME_TEXT_SECONDARY),
                    padding=40,
                )
            ]
        else:
            new_controls = [_build_job_card(j) for j in jobs]
        # Single assignment → single page update.
        jobs_container.controls = new_controls
        page.update()

    estado_sel.on_change = lambda e: asyncio.create_task(refresh())

    async def open_enqueue(e):
        tipo = FormField.create_dropdown(
            t("phase3.push.tipo"),
            ["low_stock", "sale", "order_received", "custom"],
        )
        destinatario = FormField.create_text_field(t("phase3.push.destinatario"))
        asunto = FormField.create_text_field(t("phase3.push.asunto"))
        cuerpo = FormField.create_text_field(t("phase3.push.cuerpo"), multiline=True)
        err = ft.Text("", color=THEME_ACCENT_COLOR)

        async def save(ev):
            try:
                ok, res = await controller.encolar_push(
                    tipo=tipo.value or "custom",
                    destinatario=destinatario.value or "",
                    asunto=asunto.value or "",
                    cuerpo=cuerpo.value or "",
                )
            except Exception as ex:
                err.value = str(ex)
                page.update()
                return
            if ok:
                page.pop_dialog()
                SnackBarHelper.success(page, t("phase3.push.enqueued"))
                await refresh()
            else:
                err.value = (res or {}).get("error", "Error")
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(t("phase3.push.new")),
            content=ft.Column(
                [tipo, destinatario, asunto, cuerpo, err],
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

    async def do_dispatch(e):
        desp = await controller.despachar_jobs_push(limit=50)
        SnackBarHelper.info(
            page,
            t(
                "phase3.push.dispatch_result",
                procesados=desp.get("procesados", 0),
                enviados=desp.get("enviados", 0),
                fallidos=desp.get("fallidos", 0),
            ),
        )
        await refresh()

    new_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.ADD, color="white"),
                ft.Text(t("phase3.push.new"), color="white"),
            ],
            spacing=5,
        ),
        on_click=open_enqueue,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
    )
    dispatch_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.icons.Icons.SEND, color="white"),
                ft.Text(t("phase3.push.dispatch"), color="white"),
            ],
            spacing=5,
        ),
        on_click=do_dispatch,
        style=ft.ButtonStyle(bgcolor=THEME_SUCCESS_COLOR),
    )

    if main_view:
        main_view.content = ft.Column(
            [
                AppHeader.create(
                    t("phase3.push.title"),
                    t("phase3.push.subtitle"),
                ),
                ft.Container(
                    content=ft.Row(
                        [estado_sel, new_btn, dispatch_btn],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=20,
                ),
                ft.Container(content=jobs_container, padding=20, expand=True),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        page.update()
    await refresh()


# ============ Búsqueda por imagen ============


async def show_image_search(view) -> None:
    """Upload an image and find the closest product by visual similarity."""
    page = view.page
    main_view = view.main_view
    controller = view.controller

    ruta_field = ft.TextField(
        label=t("phase3.image_search.ruta"),
        width=420,
        value="",
        hint_text="C:\\ruta\\a\\imagen.png",
    )

    top_k_field = ft.TextField(
        label="Top K",
        width=80,
        value="5",
    )

    resultados = ft.ListView(spacing=6, expand=True, auto_scroll=False)

    async def do_search(e=None):
        if not ruta_field.value:
            SnackBarHelper.error(page, t("phase3.image_search.path_required"))
            return
        try:
            top_k = int(top_k_field.value or "5")
        except ValueError:
            top_k = 5

        res = await controller.buscar_por_imagen(ruta_imagen=ruta_field.value, top_k=top_k)

        if not res:
            new_controls: list[ft.Control] = [
                ft.Container(
                    content=ft.Text(
                        t("phase3.image_search.no_results"),
                        color=THEME_TEXT_SECONDARY,
                    ),
                    padding=20,
                )
            ]
        else:
            new_controls = [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.icons.Icons.IMAGE, color=THEME_PRIMARY_COLOR),
                            ft.Column(
                                [
                                    ft.Text(
                                        f"{r.get('codigo', '')} — {r.get('nombre', '')}",
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        f"cat: {r.get('categoria', '-')}",
                                        size=11,
                                        color=THEME_TEXT_SECONDARY,
                                    ),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=10,
                    border_radius=6,
                    bgcolor=THEME_SURFACE_COLOR,
                    border=_BORDER_HAIRLINE,
                )
                for r in res
            ]
        resultados.controls = new_controls
        page.update()

    search_btn = ft.Button(
        content=ft.Text(t("phase3.image_search.search")),
        on_click=do_search,
    )

    note = ft.Container(
        content=ft.Text(
            t("phase3.image_search.note"),
            size=11,
            color=THEME_TEXT_SECONDARY,
        ),
        padding=10,
    )

    if main_view:
        main_view.content = ft.Column(
            [
                AppHeader.create(
                    t("phase3.image_search.title"),
                    t("phase3.image_search.subtitle"),
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row([ruta_field, top_k_field], spacing=10),
                            search_btn,
                            note,
                        ],
                        spacing=10,
                    ),
                    padding=20,
                ),
                ft.Container(content=resultados, padding=20, expand=True),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        page.update()
