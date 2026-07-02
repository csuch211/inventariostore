"""
Reusable UI components for professional interface
"""

import asyncio
import contextlib
from collections.abc import Callable
from typing import Any

import flet as ft

from core.theme_manager import theme_manager
from ui.typography import T
from utils.i18n import available_languages, get_locale, set_locale, t
from utils.logger import setup_logger

logger = setup_logger(__name__)


# Module-level reference to the active Page so static helpers (AppHeader,
# FormField, DataTable, etc.) can resolve the current theme without forcing
# every caller to plumb a page argument. Set via `bind_page(page)` from the
# AppView instance after construction.
class _PageRef:
    """Mutable container avoiding global keyword for the active page."""

    active: ft.Page | None = None


def bind_page(page: ft.Page | None) -> None:
    """Register the active Page used by static helpers to resolve theme palette."""
    _PageRef.active = page


class AppHeader:
    """Professional application header"""

    @staticmethod
    def create(
        title: str,
        subtitle: str = "",
        page: ft.Page | None = None,
        colors: dict | None = None,
    ) -> ft.Container:
        """Create header with title and subtitle"""
        c = colors or theme_manager.palette(page=page)
        from ui.typography import T

        return ft.Container(
            content=ft.Column(
                controls=[
                    T.display(title, page=page),
                    T.caption(subtitle, page=page)
                    if subtitle
                    else ft.Container(height=0),
                ],
                spacing=5,
            ),
            padding=20,
            border=ft.border.Border(bottom=ft.BorderSide(1, c["divider"])),
        )


class DataTable:
    """Professional data table component"""

    @staticmethod
    def create_from_products(
        productos: list,
        page: ft.Page | None = None,
        colors: dict | None = None,
    ) -> ft.DataTable:
        """Create data table from products list"""
        c = colors or theme_manager.palette(page=page)
        columns = [
            ft.DataColumn(ft.Text("Código", weight="bold")),
            ft.DataColumn(ft.Text("Nombre", weight="bold")),
            ft.DataColumn(ft.Text("Stock", weight="bold")),
            ft.DataColumn(ft.Text("Precio", weight="bold")),
            ft.DataColumn(ft.Text("Categoría", weight="bold")),
        ]

        rows = []
        for p in productos:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(p.get("codigo", "")))),
                        ft.DataCell(ft.Text(str(p.get("nombre", "")))),
                        ft.DataCell(
                            ft.Text(
                                str(p.get("cantidad", 0)),
                                color=c["primary"] if p.get("cantidad", 0) > 0 else c["accent"],
                                weight="bold",
                            )
                        ),
                        ft.DataCell(ft.Text(f"${p.get('precio', 0):.2f}")),
                        ft.DataCell(ft.Text(str(p.get("categoria", "N/A")))),
                    ]
                )
            )

        return ft.DataTable(
            columns=columns,
            rows=rows,
            border=ft.border.Border(
                ft.BorderSide(1, c["divider"]),
                ft.BorderSide(1, c["divider"]),
                ft.BorderSide(1, c["divider"]),
                ft.BorderSide(1, c["divider"]),
            ),
            border_radius=10,
            heading_row_color=c["table_heading"],
            heading_row_height=50,
            data_row_color=c["table_row"],
            data_row_max_height=40,
            horizontal_lines=ft.BorderSide(0.1, c["divider"]),
            vertical_lines=ft.BorderSide(0.1, c["divider"]),
            divider_thickness=1,
        )


class FormField:
    """Professional form field wrapper"""

    @staticmethod
    def create_text_field(
        label: str,
        hint: str = "",
        required: bool = False,
        multiline: bool = False,
        password: bool = False,
        can_reveal_password: bool = False,
        page: ft.Page | None = None,
        colors: dict | None = None,
    ) -> ft.TextField:
        """Create a professional text field.

        All color values are explicit so the field stays readable in both
        light and dark themes — relying on the global theme color leaves the
        user's typed text invisible against the dark input fill.
        """
        c = colors or theme_manager.palette(page=page)
        return ft.TextField(
            label=label,
            hint_text=hint,
            border_color=c["input_border"],
            focused_border_color=c["focus_ring"],
            filled=True,
            fill_color=c["input_fill"],
            # Explicit input-text color (the global theme can be wrong here).
            color=c["text_on_input"],
            cursor_color=c["cursor"],
            selection_color=c["selection"],
            multiline=multiline,
            min_lines=3 if multiline else 1,
            max_lines=10 if multiline else 1,
            password=password,
            can_reveal_password=can_reveal_password,
            helper="Campo requerido" if required else "",
            label_style=ft.TextStyle(color=c["text_secondary"]),
            hint_style=ft.TextStyle(color=c["text_muted"]),
            helper_style=ft.TextStyle(color=c["helper"], size=11),
            text_style=ft.TextStyle(color=c["text_on_input"], size=14),
        )

    @staticmethod
    def create_dropdown(
        label: str,
        options: list,
        page: ft.Page | None = None,
        colors: dict | None = None,
    ) -> ft.Dropdown:
        """Create a professional dropdown.

        Like the text field, every color is explicit so the option text is
        legible in dark mode (otherwise it inherits a near-white on near-black
        contrast from the global theme that fails WCAG on the dark surface).
        """
        c = colors or theme_manager.palette(page=page)
        return ft.Dropdown(
            label=label,
            options=[ft.dropdown.Option(opt) for opt in options],
            border_color=c["input_border"],
            focused_border_color=c["focus_ring"],
            filled=True,
            fill_color=c["input_fill"],
            color=c["text_on_input"],
            label_style=ft.TextStyle(color=c["text_secondary"]),
            text_style=ft.TextStyle(color=c["text_on_input"], size=14),
            hint_style=ft.TextStyle(color=c["text_muted"]),
        )


class SnackBarHelper:
    """Helper for showing notifications.

    In Flet 0.85, SnackBar is a DialogControl and is shown via
    `page.show_dialog(snack_bar)`. The legacy `page.snack_bar = ...`
    attribute no longer exists and would cause 'unknown control' errors
    in the Flutter client.
    """

    @staticmethod
    def _show(page: ft.Page, snack: ft.SnackBar):
        page.show_dialog(snack)
        page.update()

    @staticmethod
    def success(page: ft.Page, message: str):
        """Show success notification"""
        c = theme_manager.palette(page=page)
        SnackBarHelper._show(
            page,
            ft.SnackBar(
                ft.Row(
                    [
                        ft.Icon(ft.icons.Icons.CHECK_CIRCLE, color="white"),
                        ft.Text(message, color="white"),
                    ],
                    spacing=10,
                ),
                bgcolor=c["success"],
            ),
        )

    @staticmethod
    def error(page: ft.Page, message: str):
        """Show error notification"""
        c = theme_manager.palette(page=page)
        SnackBarHelper._show(
            page,
            ft.SnackBar(
                ft.Row(
                    [
                        ft.Icon(ft.icons.Icons.ERROR, color="white"),
                        ft.Text(message, color="white"),
                    ],
                    spacing=10,
                ),
                bgcolor=c["accent"],
            ),
        )

    @staticmethod
    def info(page: ft.Page, message: str):
        """Show info notification"""
        c = theme_manager.palette(page=page)
        SnackBarHelper._show(
            page,
            ft.SnackBar(
                ft.Row(
                    [
                        ft.Icon(ft.icons.Icons.INFO, color="white"),
                        ft.Text(message, color="white"),
                    ],
                    spacing=10,
                ),
                bgcolor=c["primary"],
            ),
        )

    @staticmethod
    def warning(page: ft.Page, message: str):
        """Show warning notification"""
        c = theme_manager.palette(page=page)
        SnackBarHelper._show(
            page,
            ft.SnackBar(
                ft.Row(
                    [
                        ft.Icon(ft.icons.Icons.WARNING_AMBER, color="white"),
                        ft.Text(message, color="white"),
                    ],
                    spacing=10,
                ),
                bgcolor=c["warning"],
            ),
        )


class DialogHelper:
    """Helper for showing dialogs"""

    @staticmethod
    def confirmation_dialog(
        page: ft.Page,
        title: str,
        content: str,
        on_yes,
        on_no=None,
    ):
        """Show confirmation dialog"""
        c = theme_manager.palette(page=page)
        dialog = ft.AlertDialog(
            title=ft.Text(title, weight="bold"),
            content=ft.Text(content),
            actions=[
                ft.TextButton(
                    content=ft.Text("Cancelar"),
                    on_click=on_no or (lambda e: _close_dialog(page, dialog)),
                ),
                ft.TextButton(
                    content=ft.Text("Aceptar"),
                    on_click=on_yes,
                    style=ft.ButtonStyle(color=c["primary"]),
                ),
            ],
        )
        dialog.open = True
        page.show_dialog(dialog)
        page.update()


def _close_dialog(page: ft.Page, dialog: ft.AlertDialog):
    """Helper to close dialog"""
    dialog.open = False
    page.pop_dialog()
    page.update()


class LoadingSpinner:
    """Loading indicator"""

    @staticmethod
    def create(page=None) -> ft.Container:
        """Create loading spinner"""
        c = theme_manager.palette(page=page)
        return ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(width=40, height=40, stroke_width=4, color=c["primary"]),
                    T.body(t("common.loading"), page=page, color=c["text_muted"]),
                ],
                alignment="center",
                horizontal_alignment="center",
                spacing=10,
            ),
            alignment="center",
            expand=True,
        )


class LangSwitcher:
    """Language selector dropdown. Switches the active i18n locale and
    triggers a UI re-render via an on_change callback.

    When a `controller` is provided the change is persisted per user via
    `controller.cambiar_idioma`. The previously supported standalone
    `show_i18n` view was removed; this is now the single entry point.

    Usage:
        LangSwitcher.create(
            controller=app.controller,
            on_change=lambda lang: page.update(),
        )
    """

    @staticmethod
    def create(
        on_change=None,
        controller=None,
        bg_color="gray100",
        text_color="gray600",
    ) -> ft.Container:
        current = get_locale()

        def handle_change(e):
            lang = e.control.value
            if not lang or lang == get_locale():
                return
            set_locale(lang)
            if controller is not None:
                usuario = getattr(controller, "current_user", None) or "system"
                task = asyncio.create_task(controller.cambiar_idioma(usuario, lang))
                task.add_done_callback(lambda t: None)
            if on_change:
                on_change(lang)

        labels = {"es": t("common.spanish"), "en": t("common.english")}
        options = [
            ft.dropdown.Option(key=lang, text=labels.get(lang, lang))
            for lang in available_languages()
        ]
        dropdown = ft.Dropdown(
            value=current,
            options=options,
            on_select=handle_change,
            width=120,
            dense=True,
            border_color="transparent",
            filled=True,
            fill_color=bg_color,
        )
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.Icons.LANGUAGE, size=16, color=text_color),
                    dropdown,
                ],
                spacing=5,
                alignment=ft.MainAxisAlignment.START,
            ),
            padding=ft.Padding(left=10, right=10, top=5, bottom=5),
        )


class EmptyState:
    @staticmethod
    def create(
        icon=None,
        title="Sin datos",
        description="",
        action_text=None,
        on_action=None,
        page=None,
    ) -> ft.Container:
        mode = page.theme_mode if page else None
        c = theme_manager.palette(mode)
        controls = []
        controls.append(
            ft.Container(
                content=ft.Icon(
                    icon or ft.icons.Icons.INBOX_OUTLINED,
                    size=64,
                    color=c["text_muted"],
                ),
                alignment=ft.alignment.Alignment(0, 0),
            )
        )
        controls.append(
            ft.Text(
                title,
                size=18,
                weight=ft.FontWeight.SEMI_BOLD,
                color=c["text_secondary"],
                text_align=ft.TextAlign.CENTER,
            )
        )
        if description:
            controls.append(
                ft.Text(
                    description,
                    size=14,
                    color=c["text_muted"],
                    text_align=ft.TextAlign.CENTER,
                )
            )
        if action_text and on_action:
            controls.append(
                ft.ElevatedButton(
                    text=action_text,
                    on_click=on_action,
                    style=ft.ButtonStyle(
                        color="white",
                        bgcolor=c["primary"],
                    ),
                )
            )
        return ft.Container(
            content=ft.Column(
                controls,
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.Alignment(0, 0),
            expand=True,
            padding=40,
        )


class LoadingButton:
    """Button with built-in loading spinner."""

    @staticmethod
    def create(
        text: str,
        on_click=None,
        icon=None,
        variant="primary",  # "primary" | "secondary" | "text"
        expand=False,
        page=None,
    ) -> ft.Container:
        mode = page.theme_mode if page else None
        c = theme_manager.palette(mode)

        btn_bg = c["primary"] if variant == "primary" else None
        btn_color = "white" if variant == "primary" else c["text_primary"]

        spinner = ft.ProgressRing(width=16, height=16, stroke_width=2, color=btn_color, visible=False)
        text_widget = ft.Text(text, size=14, color=btn_color)

        row = ft.Row(
            [spinner, text_widget],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        async def _on_click(e):
            btn = e.control
            spinner.visible = True
            text_widget.visible = False
            btn.disabled = True
            btn.update()
            try:
                if on_click:
                    await on_click(e)
            finally:
                spinner.visible = False
                text_widget.visible = True
                btn.disabled = False
                btn.update()

        btn = ft.ElevatedButton(
            content=row,
            on_click=_on_click,
            style=ft.ButtonStyle(
                bgcolor=btn_bg,
                color=btn_color,
                padding=ft.Padding(left=20, right=20, top=12, bottom=12),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            expand=expand,
        )
        btn._spinner = spinner
        btn._text_widget = text_widget
        return btn


class KpiCard:
    @staticmethod
    def create(
        title: str,
        value: str,
        icon,
        color: str | None = None,
        light_color: str | None = None,
        trend: str | None = None,  # "+12%" or "-5%"
        col_size: int = 3,
        page=None,
    ) -> ft.Container:
        mode = page.theme_mode if page else None
        c = theme_manager.palette(mode)

        color = color or c["primary"]
        light_color = light_color or c["primary_light"]

        trend_color = c["success"] if trend and trend.startswith("+") else c["accent"] if trend else None

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(icon, color=color, size=22),
                                bgcolor=light_color,
                                padding=10,
                                border_radius=8,
                            ),
                            ft.Column(
                                [
                                    T.caption(title, page=page, size=11),
                                    ft.Row(
                                        [
                                            T.stat(value, page=page, color=color, size=20),
                                            ft.Text(
                                                trend,
                                                size=11,
                                                color=trend_color,
                                                weight=ft.FontWeight.SEMI_BOLD,
                                            ) if trend else ft.Container(height=0),
                                        ],
                                        spacing=6,
                                        alignment=ft.MainAxisAlignment.END,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                            ),
                        ],
                        spacing=12,
                    ),
                ]
            ),
            col={"sm": 6, "md": col_size, "xl": col_size},
            padding=16,
            bgcolor=c["surface"],
            border_radius=12,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=4, color=c["shadow"]),
        )


class AppDataTable:
    """Reusable data table with consistent theming and mobile card fallback.

    Usage:
        AppDataTable(
            columns=[ColumnDef("Nombre", "nombre"), ColumnDef("Precio", "precio")],
            rows=[{"nombre": "Prod A", "precio": 100}],
            on_select=lambda row: ...,
            page=page,
        )
    """

    @staticmethod
    def create(
        columns: list[tuple[str, str]],  # (header_label, data_key)
        rows: list[dict],
        on_select=None,
        selected_ids: set | None = None,
        id_key: str = "id",
        empty_message: str = "No hay datos",
        empty_action_text: str | None = None,
        empty_action=None,
        page=None,
    ) -> ft.Control:
        mode = page.theme_mode if page else None
        c = theme_manager.palette(mode)

        if not rows:
            return EmptyState.create(
                title=empty_message,
                action_text=empty_action_text,
                on_action=empty_action,
                page=page,
            )

        selected_ids = selected_ids or set()

        data_cols = [
            ft.DataColumn(ft.Text(header, weight="bold"))
            for header, _ in columns
        ]

        data_rows = []
        for row in rows:
            row_id = row.get(id_key, "")
            is_selected = row_id in selected_ids
            cells = []
            for _, key in columns:
                val = row.get(key, "")
                if isinstance(val, float):
                    text = f"${val:,.2f}"
                else:
                    text = str(val) if val is not None else ""
                cells.append(
                    ft.DataCell(
                        ft.Text(text, size=13, color=c["text_primary"]),
                    )
                )

            row_color = c["table_row_alt"] if len(data_rows) % 2 == 0 else c["table_row"]

            data_rows.append(
                ft.DataRow(
                    cells=cells,
                    color=row_color,
                    on_select_changed=lambda e, r=row: on_select(r) if on_select else None,
                    selected=is_selected,
                )
            )

        return ft.DataTable(
            columns=data_cols,
            rows=data_rows,
            border=ft.border.Border(
                ft.BorderSide(1, c["divider"]),
                ft.BorderSide(1, c["divider"]),
                ft.BorderSide(1, c["divider"]),
                ft.BorderSide(1, c["divider"]),
            ),
            border_radius=10,
            heading_row_color=c["table_heading"],
            heading_row_height=50,
            data_row_max_height=40,
            horizontal_lines=ft.BorderSide(0.1, c["divider"]),
            vertical_lines=ft.BorderSide(0.1, c["divider"]),
            divider_thickness=1,
        )

    @staticmethod
    def create_mobile_cards(
        columns: list[tuple[str, str, int]],  # (label, key, flex)
        rows: list[dict],
        on_select=None,
        page=None,
    ) -> ft.Column:
        """Mobile-friendly card list as alternative to DataTable."""
        mode = page.theme_mode if page else None
        c = theme_manager.palette(mode)

        if not rows:
            return EmptyState.create(page=page)

        cards = []
        for row in rows:
            card_content = []
            for label, key, flex in columns:
                val = row.get(key, "")
                if isinstance(val, float):
                    text = f"${val:,.2f}"
                else:
                    text = str(val) if val is not None else ""
                card_content.append(
                    ft.Row(
                        [
                            ft.Text(label + ":", size=11, color=c["text_muted"], weight="bold"),
                            ft.Text(text, size=13, color=c["text_primary"], expand=True),
                        ],
                        spacing=4,
                    )
                )

            card = ft.Container(
                content=ft.Column(card_content, spacing=4),
                padding=12,
                bgcolor=c["surface"],
                border_radius=8,
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=2, color=c["shadow"]),
                on_click=lambda e, r=row: on_select(r) if on_select else None,
            )
            cards.append(card)

        return ft.Column(cards, spacing=8, scroll=ft.ScrollMode.AUTO)


class DialogBase:
    """Base dialog with consistent styling."""

    @staticmethod
    def create(
        title: str,
        content: ft.Control,
        actions: list[ft.Control] | None = None,
        width: int | None = None,
        height: int | None = None,
        page=None,
    ) -> ft.AlertDialog:
        mode = page.theme_mode if page else None
        c = theme_manager.palette(mode)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, weight=ft.FontWeight.BOLD, color=c["text_primary"]),
            content=ft.Container(
                content=content,
                width=width,
                height=height,
                padding=10,
            ),
            actions=actions or [],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=c["surface"],
        )
        return dialog

    @staticmethod
    def show(page: ft.Page, dialog: ft.AlertDialog):
        dialog.open = True
        page.show_dialog(dialog)
        page.update()

    @staticmethod
    def close(page: ft.Page, dialog: ft.AlertDialog):
        dialog.open = False
        page.pop_dialog()
        page.update()


# ============================================================================
# Sidebar components — modern, grouped, sectioned design.
#
# The previous sidebar painted every item with a solid brand color, had no
# section grouping, no search, and dumped 24 destinations into a single
# unreadable list. The replacement follows the pattern used by Linear, Notion,
# Stripe Dashboard, Vercel, and GitHub:
#
#   - Neutral surface (no per-item solid fill).
#   - Items grouped into named, collapsible sections with section headers.
#   - Outlined icons by default, filled icon for the active item.
#   - Subtle hover (light tint), strong active highlight (accent strip + tinted bg).
#   - Optional badge only where there's a real count (stock alerts).
#   - Search/quick-switcher (Ctrl+K) that filters items across all sections.
#   - User card footer with avatar initial, role pill, settings + logout actions.
# ============================================================================


def _resolve_outlined(icon) -> Any:
    """Return the outlined variant of an icon. If the caller already passed
    an outlined icon, return it unchanged.

    Accepts both shapes used in the codebase:
      - uppercase enum from ft.icons.Icons  (e.g. "INVENTORY_2_OUTLINED")
      - lowercase strings                    (e.g. "inventory_2_outlined")
    """
    if isinstance(icon, str):
        if icon.endswith("_OUTLINED") or icon.endswith("_outlined"):
            return icon
        # Try uppercase form first (what ft.icons.Icons exposes).
        if hasattr(ft.icons, "Icons"):
            out = f"{icon}_OUTLINED"
            if hasattr(ft.icons.Icons, out):
                return getattr(ft.icons.Icons, out)
        # Fallback: return the lowercase _outlined form.
        return f"{icon}_outlined"
    return icon


def _filled_variant(icon) -> Any:
    """Return the filled (non-outlined) variant of an icon when possible."""
    if isinstance(icon, str):
        if icon.endswith("_OUTLINED"):
            return icon[: -len("_OUTLINED")]
        if icon.endswith("_outlined"):
            return icon[: -len("_outlined")]
        # If already in uppercase enum form (e.g. "INVENTORY_2"), try
        # the lowercase variant for completeness.
        if hasattr(ft.icons, "Icons") and hasattr(ft.icons.Icons, icon):
            return icon
    return icon


class SidebarItem:
    """A single sidebar row.

    Visual rules:
      - Inactive: neutral bg, outlined icon, normal text.
      - Hover:    light tinted bg (5-8% opacity), icon and text brighten.
      - Active:   accent-colored 3px vertical strip on the left, tinted
                  bg, filled (non-outlined) icon, bold text.
      - Badge:    small pill (max 2 chars rendered, full count on tooltip).
      - Shortcut: small muted text on the right (e.g. "Ctrl+K").
    """

    def __init__(
        self,
        route: str,
        icon: Any,
        label: str,
        colors: dict[str, str],
        is_active: bool = False,
        badge: int | None = None,
        shortcut: str | None = None,
        on_click: Callable[[], None] | None = None,
        on_hover: Callable[[bool], None] | None = None,
    ) -> None:
        self.route = route
        self.icon = icon
        self.label = label
        self.colors = colors
        self.is_active = is_active
        self.badge = badge
        self.shortcut = shortcut
        self.on_click = on_click
        self.on_hover = on_hover
        self._hovered = False
        self._build()

    def _build(self) -> None:
        _colors = self.colors
        active = self.is_active
        hovered = self._hovered

        # Background logic: active wins, then hover, else transparent.
        if active:
            bg = _colors["primary_tint"]
        elif hovered:
            bg = _colors["hover_tint"]
        else:
            bg = "transparent"

        icon_name = _filled_variant(self.icon) if active else _resolve_outlined(self.icon)
        icon_color = _colors["primary"] if active else _colors["text_primary"]
        text_color = _colors["primary"] if active else _colors["text_primary"]
        text_weight = ft.FontWeight.BOLD if active else ft.FontWeight.W_500

        row_controls: list[ft.Control] = [
            # Active indicator strip on the left.
            ft.Container(
                width=3,
                height=20,
                border_radius=2,
                bgcolor=_colors["primary"] if active else "transparent",
            ),
            ft.Icon(icon_name, size=18, color=icon_color),
            ft.Text(
                self.label,
                size=13,
                color=text_color,
                weight=text_weight,
                expand=True,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1,
            ),
        ]

        if self.badge:
            badge_text = str(self.badge) if self.badge < 100 else "99+"
            row_controls.append(
                ft.Container(
                    content=ft.Text(
                        badge_text,
                        size=10,
                        color="white",
                        weight=ft.FontWeight.BOLD,
                    ),
                    bgcolor=_colors["accent"],
                    padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                    border_radius=10,
                )
            )

        if self.shortcut:
            row_controls.append(
                ft.Text(
                    self.shortcut,
                    size=10,
                    color=_colors["text_muted"],
                )
            )

        self.control = ft.Container(
            content=ft.Row(
                row_controls,
                spacing=10,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=10, right=10, top=10, bottom=10),
            on_click=lambda _e: self.on_click() if self.on_click else None,
            bgcolor=bg,
            border_radius=8,
            ink=True,
            animate=ft.Animation(duration=120, curve=ft.AnimationCurve.EASE_OUT),
        )

        def _on_hover(e):
            self._hovered = e.data == "true"
            self._build()
            if self.on_hover:
                with contextlib.suppress(Exception):
                    self.on_hover(self._hovered)

        self.control.on_hover = _on_hover


class SidebarSection:
    """A grouped, collapsible section of SidebarItems.

    Collapsed state hides the items but keeps the header visible so the
    user can see the section exists. A chevron rotates 90° to indicate
    state. The collapsed state can be persisted via the optional
    `state_key` (caller stores/loads in their own storage).
    """

    def __init__(
        self,
        title: str,
        items: list[SidebarItem],
        colors: dict[str, str],
        collapsed: bool = False,
        on_toggle: Callable[[bool], None] | None = None,
    ) -> None:
        self.title = title
        self.items = items
        self.colors = colors
        self._collapsed = collapsed
        self.on_toggle = on_toggle
        self._build()

    def _build(self) -> None:
        _colors = self.colors
        chevron_icon = (
            ft.icons.Icons.CHEVRON_RIGHT if self._collapsed else ft.icons.Icons.EXPAND_MORE
        )

        def _toggle(_e):
            self._collapsed = not self._collapsed
            self._build()
            if self.on_toggle:
                with contextlib.suppress(Exception):
                    self.on_toggle(self._collapsed)

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        chevron_icon,
                        size=14,
                        color=_colors["text_muted"],
                    ),
                    ft.Text(
                        self.title.upper(),
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=_colors["text_muted"],
                    ),
                ],
                spacing=4,
            ),
            padding=ft.Padding(left=10, right=10, top=10, bottom=4),
            on_click=_toggle,
            ink=True,
            # Don't intercept hover/clicks on the text itself.
        )

        if self._collapsed:
            body: ft.Control = ft.Container(height=0)
        else:
            body = ft.Column(
                [item.control for item in self.items],
                spacing=1,
            )

        self.control = ft.Column(
            [header, body],
            spacing=0,
        )

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, value: bool) -> None:
        if value != self._collapsed:
            self._collapsed = value
            self._build()


class SidebarSearch:
    """Quick-switcher input that filters items across all sections.

    On text change, calls `on_filter(query)` with the current query; the
    caller is responsible for hiding/showing items. On Enter or click on
    the first result, calls `on_submit(route)`.
    """

    def __init__(
        self,
        colors: dict[str, str],
        placeholder: str = "Buscar... (Ctrl+K)",
        on_filter: Callable[[str], None] | None = None,
        on_submit: Callable[[], None] | None = None,
    ) -> None:
        self.colors = colors
        self.placeholder = placeholder
        self.on_filter = on_filter
        self.on_submit = on_submit
        self._build()

    def _build(self) -> None:
        _colors = self.colors

        def _on_change(e):
            if self.on_filter:
                with contextlib.suppress(Exception):
                    self.on_filter(self._field.value or "")

        def _on_submit(e):
            if self.on_submit:
                with contextlib.suppress(Exception):
                    self.on_submit()

        self._field = ft.TextField(
            hint_text=self.placeholder,
            prefix_icon=ft.icons.Icons.SEARCH,
            border_radius=8,
            filled=True,
            bgcolor=_colors["surface"],
            border_color="transparent",
            focused_border_color=_colors["primary"],
            text_size=13,
            content_padding=ft.Padding(left=10, right=10, top=4, bottom=4),
            on_change=_on_change,
            on_submit=_on_submit,
            expand=True,
        )

        self.control = ft.Container(
            content=self._field,
            padding=ft.Padding(left=10, right=10, top=8, bottom=4),
        )


class SidebarUserCard:
    """Actionable user card footer.

    Replaces the previous 3 lines of plain text ("Usuario: ...", "Rol: ...",
    "Permisos: N") with a clickable card showing:
      - Avatar (colored circle with the initial).
      - Name + role pill (color-coded by role).
      - Two icon buttons: settings, logout.
    """

    def __init__(
        self,
        username: str,
        role: str,
        colors: dict[str, str],
        on_settings: Callable[[], None] | None = None,
        on_logout: Callable[[], None] | None = None,
    ) -> None:
        self.username = username or "system"
        self.role = role or "-"
        self.colors = colors
        self.on_settings = on_settings
        self.on_logout = on_logout
        self._build()

    def _build(self) -> None:
        _colors = self.colors
        initial = (self.username[:1] or "?").upper()
        # Stable color from username so the same user always sees the same avatar.
        palette = [
            "#2563EB",
            "#16A34A",
            "#DC2626",
            "#7C3AED",
            "#D97706",
            "#0891B2",
            "#DB2777",
        ]
        avatar_color = palette[sum(ord(c) for c in self.username) % len(palette)]

        role_colors = {
            "admin": _colors["accent"],
            "operador": _colors["primary"],
            "viewer": _colors["text_muted"],
        }
        role_pill_bg = role_colors.get(self.role.lower(), _colors["text_muted"])

        def _settings(_e):
            if self.on_settings:
                with contextlib.suppress(Exception):
                    self.on_settings()

        def _logout(_e):
            if self.on_logout:
                with contextlib.suppress(Exception):
                    self.on_logout()

        self.control = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(
                            initial,
                            size=14,
                            color="white",
                            weight=ft.FontWeight.BOLD,
                        ),
                        width=32,
                        height=32,
                        border_radius=16,
                        bgcolor=avatar_color,
                        alignment=ft.alignment.Alignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                self.username,
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=_colors["text_primary"],
                                overflow=ft.TextOverflow.ELLIPSIS,
                                max_lines=1,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    self.role,
                                    size=10,
                                    color="white",
                                    weight=ft.FontWeight.BOLD,
                                ),
                                bgcolor=role_pill_bg,
                                padding=ft.Padding(left=8, right=8, top=2, bottom=2),
                                border_radius=8,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.icons.Icons.SETTINGS_OUTLINED,
                        icon_size=16,
                        icon_color=_colors["text_secondary"],
                        tooltip="Configuración",
                        on_click=_settings,
                    ),
                    ft.IconButton(
                        icon=ft.icons.Icons.LOGOUT,
                        icon_size=16,
                        icon_color=_colors["accent"],
                        tooltip="Cerrar sesión",
                        on_click=_logout,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=10, right=6, top=8, bottom=8),
            border=ft.border.Border(
                top=ft.BorderSide(1, _colors["divider"]),
            ),
            bgcolor=_colors["surface"],
        )
