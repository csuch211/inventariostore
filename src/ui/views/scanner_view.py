"""Scanner view functions extracted from AppView."""

import flet as ft

from config.settings import THEME_PRIMARY_COLOR, THEME_SURFACE_COLOR
from ui.components import AppHeader, SnackBarHelper


async def show_scanner(app) -> None:
    """Display barcode/QR scanner view"""
    C = app._get_colors()

    async def handle_scan_input(e):
        """Handle scanned or typed barcode input"""
        data = scan_field.value.strip()
        if not data:
            return
        try:
            producto = await app.controller.buscar_por_codigo_escaneado(data)
            if producto:
                app._scanner_result_container.content = build_scanner_result(app, producto)
            else:
                app._scanner_result_container.content = ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.Icons.SEARCH_OFF, size=48, color="gray400"),
                            ft.Text("Producto no encontrado", size=16, color="gray600"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=40,
                    alignment="center",
                )
            app.page.update()
        except Exception as ex:
            SnackBarHelper.error(app.page, f"Error: {ex!s}")

    async def handle_pick_file(e):
        SnackBarHelper.info(app.page, "Selector de archivos no disponible en esta versión")

    scan_field = ft.TextField(
        label="Código de barras / QR",
        hint_text="Escanee o ingrese manualmente el código",
        border_color=C["input_border"],
        focused_border_color=C["focus_ring"],
        filled=True,
        fill_color=C["input_fill"],
        color=C["text_on_input"],
        cursor_color=C["cursor"],
        selection_color=C["selection"],
        label_style=ft.TextStyle(color=C["text_secondary"]),
        hint_style=ft.TextStyle(color=C["text_muted"]),
        text_style=ft.TextStyle(color=C["text_on_input"], size=14),
        autofocus=True,
        on_submit=handle_scan_input,
        suffix_icon=ft.icons.Icons.SEARCH,
        expand=True,
    )

    scan_btn = ft.Button(
        content=ft.Text("Buscar"),
        on_click=handle_scan_input,
        style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR, color="white"),
    )

    file_scan_btn = ft.OutlinedButton(
        "Escanear desde imagen",
        icon=ft.icons.Icons.IMAGE_SEARCH,
        on_click=handle_pick_file,
    )

    availability = await app.controller.scanner_disponibilidad()
    status_pills = []
    for name, avail in availability.items():
        status_pills.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.icons.Icons.CHECK_CIRCLE if avail else ft.icons.Icons.CANCEL,
                            size=14,
                            color="green" if avail else "red",
                        ),
                        ft.Text(name, size=11, color="gray600"),
                    ],
                    spacing=3,
                ),
                padding=ft.Padding(right=15),
            )
        )

    app._scanner_result_container = ft.Container(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.Icons.QR_CODE_SCANNER, size=48, color="gray400"),
                    ft.Text("Ingrese o escanee un código", size=14, color="gray600"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=60,
            alignment="center",
        ),
        expand=True,
    )

    content = ft.Column(
        [
            AppHeader.create("Escáner", "Buscar productos por código de barras o QR"),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row([scan_field, scan_btn], spacing=10),
                        ft.Container(height=10),
                        file_scan_btn,
                        ft.Divider(height=1),
                        ft.Row(status_pills, spacing=5),
                    ],
                    spacing=5,
                ),
                padding=20,
            ),
            app._scanner_result_container,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()


def build_scanner_result(app, producto: dict) -> ft.Container:
    """Build product result card for scanner view"""
    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.icons.Icons.CHECK_CIRCLE, color="green", size=24),
                            ft.Text(
                                "Producto encontrado",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color="green",
                            ),
                        ],
                        spacing=5,
                    ),
                    padding=10,
                ),
                ft.Divider(height=1),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Código:", weight=ft.FontWeight.BOLD, size=13),
                                ft.Text(str(producto.get("codigo", "")), size=13),
                            ],
                            spacing=10,
                        ),
                        ft.Row(
                            [
                                ft.Text("Nombre:", weight=ft.FontWeight.BOLD, size=13),
                                ft.Text(str(producto.get("nombre", "")), size=13),
                            ],
                            spacing=10,
                        ),
                        ft.Row(
                            [
                                ft.Text("Stock:", weight=ft.FontWeight.BOLD, size=13),
                                ft.Text(
                                    str(producto.get("cantidad", 0)),
                                    size=13,
                                    color="blue" if producto.get("cantidad", 0) > 0 else "red",
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            spacing=10,
                        ),
                        ft.Row(
                            [
                                ft.Text("Precio:", weight=ft.FontWeight.BOLD, size=13),
                                ft.Text(f"${producto.get('precio', 0):.2f}", size=13),
                            ],
                            spacing=10,
                        ),
                        ft.Row(
                            [
                                ft.Text("Categoría:", weight=ft.FontWeight.BOLD, size=13),
                                ft.Text(str(producto.get("categoria", "N/A")), size=13),
                            ],
                            spacing=10,
                        ),
                    ],
                    spacing=8,
                    padding=15,
                ),
            ],
            spacing=0,
        ),
        bgcolor=THEME_SURFACE_COLOR,
        border_radius=10,
        margin=20,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=3, color="rgba(0,0,0,0.05)"),
    )
