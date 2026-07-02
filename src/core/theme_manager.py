"""
Centralized theme manager.

Goals
-----
- Single source of truth for the active color palette.
- Resolve an effective ThemeMode from "light" / "dark" / "auto"
  (auto follows the OS preference via flet's `page.platform_brightness`).
- Provide a `apply(page, mode)` helper that re-paints the page bg and
  rebuilds ColorScheme tokens for both light and dark variants.
- Expose a stable palette dict that views can read without scattering
  imports of `THEME_DARK_*` constants throughout the codebase.

Keeping this in `core/` (rather than `ui/`) lets controllers and other
non-UI layers query theme state when they need to (e.g. when deciding
the default fill of an exported PDF report).
"""

from __future__ import annotations

import logging
from typing import Literal

import flet as ft

logger = logging.getLogger(__name__)

from config.settings import (
    THEME_ACCENT_COLOR,
    THEME_ACCENT_LIGHT,
    THEME_BACKGROUND_COLOR,
    THEME_DARK_ACCENT_COLOR,
    THEME_DARK_ACCENT_LIGHT,
    THEME_DARK_BACKGROUND_COLOR,
    THEME_DARK_CARD_COLOR,
    THEME_DARK_DANGER,
    THEME_DARK_DIVIDER,
    THEME_DARK_FOCUS_RING,
    THEME_DARK_HOVER_TINT,
    THEME_DARK_INFO_COLOR,
    THEME_DARK_INFO_LIGHT,
    THEME_DARK_INPUT_BORDER,
    THEME_DARK_INPUT_FILL,
    THEME_DARK_OVERLAY,
    THEME_DARK_PRIMARY_COLOR,
    THEME_DARK_PRIMARY_LIGHT,
    THEME_DARK_PRIMARY_TINT,
    THEME_DARK_PURPLE_COLOR,
    THEME_DARK_PURPLE_LIGHT,
    THEME_DARK_SCROLLBAR,
    THEME_DARK_SCROLLBAR_TRACK,
    THEME_DARK_SHADOW,
    THEME_DARK_SHADOW_STRONG,
    THEME_DARK_SIDEBAR_BG,
    THEME_DARK_SUCCESS,
    THEME_DARK_SURFACE_COLOR,
    THEME_DARK_TABLE_HEADING,
    THEME_DARK_TABLE_ROW,
    THEME_DARK_TABLE_ROW_ALT,
    THEME_DARK_TABLE_ROW_HOVER,
    THEME_DARK_TEAL_COLOR,
    THEME_DARK_TEAL_LIGHT,
    THEME_DARK_TEXT_MUTED,
    THEME_DARK_TEXT_PRIMARY,
    THEME_DARK_TEXT_SECONDARY,
    THEME_DARK_WARNING,
    THEME_DIVIDER,
    THEME_FOCUS_RING,
    THEME_HOVER_TINT,
    THEME_INFO_COLOR,
    THEME_INFO_LIGHT,
    THEME_INPUT_BORDER,
    THEME_INPUT_FILL,
    THEME_OVERLAY,
    THEME_PRIMARY_COLOR,
    THEME_PRIMARY_DARK,
    THEME_PRIMARY_LIGHT,
    THEME_PRIMARY_TINT,
    THEME_PURPLE_COLOR,
    THEME_PURPLE_LIGHT,
    THEME_SCROLLBAR,
    THEME_SCROLLBAR_TRACK,
    THEME_SHADOW,
    THEME_SHADOW_STRONG,
    THEME_SIDEBAR_BG,
    THEME_SUCCESS_COLOR,
    THEME_SURFACE_COLOR,
    THEME_TABLE_HEADING,
    THEME_TABLE_ROW,
    THEME_TABLE_ROW_ALT,
    THEME_TABLE_ROW_HOVER,
    THEME_TEAL_COLOR,
    THEME_TEAL_LIGHT,
    THEME_TEXT_MUTED,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    THEME_WARNING_COLOR,
)

ThemeChoice = Literal["light", "dark", "auto"]
Palette = dict[str, str]


class ThemeManager:
    """Resolve and apply the active palette.

    Instances are cheap; the app keeps a single module-level singleton
    via `theme_manager` below.
    """

    def __init__(self) -> None:
        self._system_is_dark: bool | None = None
        self._choice: ThemeChoice = "light"

    # ---------- system probe ----------

    def probe_system(self) -> bool:
        """Best-effort detection of OS dark-mode preference.

        Uses `page.platform_brightness` when a Flet page is available;
        falls back to `platform.system()` heuristics. The result is
        cached because the OS preference does not change at runtime
        unless the user toggles it via the new `apply(..., choice="auto")`
        call (which we re-probe on demand).
        """
        if self._system_is_dark is not None:
            return self._system_is_dark
        try:
            from config.settings import _THEME_PAGE  # type: ignore

            pb = getattr(_THEME_PAGE, "platform_brightness", None)
            if pb is not None:
                self._system_is_dark = str(pb).lower() == "dark"
                return self._system_is_dark
        except Exception:
            logger.debug("Could not detect system brightness, defaulting to light")
        # Fallback: assume light. We deliberately do NOT guess based on
        # OS name — Windows registry / macOS defaults differ between
        # versions and we have no portable, dependency-free way to read
        # them in pure Python here.
        self._system_is_dark = False
        return self._system_is_dark

    def invalidate(self) -> None:
        """Force a re-probe on the next call to `probe_system()`."""
        self._system_is_dark = None

    # ---------- choice -> ThemeMode ----------

    def resolve(self, choice: ThemeChoice, page: ft.Page | None = None) -> ft.ThemeMode:
        """Map a stored choice to the Flet ThemeMode that should be active.

        When `choice == "auto"`, we probe the page (preferred) or fall
        back to the cached OS probe.
        """
        self._choice = choice
        if choice == "dark":
            return ft.ThemeMode.DARK
        if choice == "light":
            return ft.ThemeMode.LIGHT
        # auto
        pb = getattr(page, "platform_brightness", None) if page is not None else None
        if pb is not None:
            self._system_is_dark = str(pb).lower() == "dark"
        return ft.ThemeMode.DARK if self.probe_system() else ft.ThemeMode.LIGHT

    # ---------- palettes ----------

    _palette_cache: dict[ft.ThemeMode | None, Palette] | None = None

    @classmethod
    def palette(
        cls,
        mode: ft.ThemeMode | None = None,
        page: ft.Page | None = None,
    ) -> Palette:
        """Return the resolved palette for a given Flet ThemeMode.

        When `mode is None` and a `page` is provided, the effective mode is
        read from ``page.theme_mode``.  When both are ``None`` (e.g. during
        early init before the page has a theme_mode set), we return the light
        palette as a safe default.  Results are cached per mode.
        """
        if mode is None and page is not None:
            mode = page.theme_mode
        if cls._palette_cache is None:
            cls._palette_cache = {}
        cached = cls._palette_cache.get(mode)
        if cached is not None:
            return cached
        if mode == ft.ThemeMode.DARK:
            pal = {
                "primary": THEME_DARK_PRIMARY_COLOR,
                "primary_light": THEME_DARK_PRIMARY_LIGHT,
                "primary_dark": THEME_DARK_PRIMARY_COLOR,
                "accent": THEME_DARK_ACCENT_COLOR,
                "accent_light": THEME_DARK_ACCENT_LIGHT,
                "background": THEME_DARK_BACKGROUND_COLOR,
                "surface": THEME_DARK_SURFACE_COLOR,
                "card": THEME_DARK_CARD_COLOR,
                "sidebar_bg": THEME_DARK_SIDEBAR_BG,
                "primary_tint": THEME_DARK_PRIMARY_TINT,
                "hover_tint": THEME_DARK_HOVER_TINT,
                "text_primary": THEME_DARK_TEXT_PRIMARY,
                "text_secondary": THEME_DARK_TEXT_SECONDARY,
                "text_muted": THEME_DARK_TEXT_MUTED,
                "text_on_input": THEME_DARK_TEXT_PRIMARY,
                "input_fill": THEME_DARK_INPUT_FILL,
                "input_border": THEME_DARK_INPUT_BORDER,
                "table_heading": THEME_DARK_TABLE_HEADING,
                "table_row": THEME_DARK_TABLE_ROW,
                "table_row_alt": THEME_DARK_TABLE_ROW_ALT,
                "table_row_hover": THEME_DARK_TABLE_ROW_HOVER,
                "divider": THEME_DARK_DIVIDER,
                "shadow": THEME_DARK_SHADOW,
                "shadow_strong": THEME_DARK_SHADOW_STRONG,
                "overlay": THEME_DARK_OVERLAY,
                "focus_ring": THEME_DARK_FOCUS_RING,
                "cursor": THEME_DARK_FOCUS_RING,
                "selection": "#1E3A5F",
                "helper": THEME_DARK_TEXT_SECONDARY,
                "scrollbar": THEME_DARK_SCROLLBAR,
                "scrollbar_track": THEME_DARK_SCROLLBAR_TRACK,
                "success": THEME_DARK_SUCCESS,
                "warning": THEME_DARK_WARNING,
                "danger": THEME_DARK_DANGER,
                "info": THEME_DARK_INFO_COLOR,
                "info_light": THEME_DARK_INFO_LIGHT,
                "purple": THEME_DARK_PURPLE_COLOR,
                "purple_light": THEME_DARK_PURPLE_LIGHT,
                "teal": THEME_DARK_TEAL_COLOR,
                "teal_light": THEME_DARK_TEAL_LIGHT,
            }
            cls._palette_cache[ft.ThemeMode.DARK] = pal
            return pal
        pal = {
            "primary": THEME_PRIMARY_COLOR,
            "primary_light": THEME_PRIMARY_LIGHT,
            "primary_dark": THEME_PRIMARY_DARK,
            "accent": THEME_ACCENT_COLOR,
            "accent_light": THEME_ACCENT_LIGHT,
            "background": THEME_BACKGROUND_COLOR,
            "surface": THEME_SURFACE_COLOR,
            "card": THEME_SURFACE_COLOR,
            "sidebar_bg": THEME_SIDEBAR_BG,
            "primary_tint": THEME_PRIMARY_TINT,
            "hover_tint": THEME_HOVER_TINT,
            "text_primary": THEME_TEXT_PRIMARY,
            "text_secondary": THEME_TEXT_SECONDARY,
            "text_muted": THEME_TEXT_MUTED,
            "text_on_input": THEME_TEXT_PRIMARY,
            "input_fill": THEME_INPUT_FILL,
            "input_border": THEME_INPUT_BORDER,
            "table_heading": THEME_TABLE_HEADING,
            "table_row": THEME_TABLE_ROW,
            "table_row_alt": THEME_TABLE_ROW_ALT,
            "table_row_hover": THEME_TABLE_ROW_HOVER,
            "divider": THEME_DIVIDER,
            "shadow": THEME_SHADOW,
            "shadow_strong": THEME_SHADOW_STRONG,
            "overlay": THEME_OVERLAY,
            "focus_ring": THEME_FOCUS_RING,
            "cursor": THEME_PRIMARY_COLOR,
            "selection": "#BFDBFE",
            "helper": THEME_TEXT_SECONDARY,
            "scrollbar": THEME_SCROLLBAR,
            "scrollbar_track": THEME_SCROLLBAR_TRACK,
            "success": THEME_SUCCESS_COLOR,
            "warning": THEME_WARNING_COLOR,
            "danger": THEME_ACCENT_COLOR,
            "info": THEME_INFO_COLOR,
            "info_light": THEME_INFO_LIGHT,
            "purple": THEME_PURPLE_COLOR,
            "purple_light": THEME_PURPLE_LIGHT,
            "teal": THEME_TEAL_COLOR,
            "teal_light": THEME_TEAL_LIGHT,
        }
        cls._palette_cache[ft.ThemeMode.LIGHT] = pal
        return pal

    # ---------- apply ----------

    def apply(self, page: ft.Page, choice: ThemeChoice) -> ft.ThemeMode:
        """Configure `page.theme`, `page.dark_theme`, `page.theme_mode`
        and `page.bgcolor` for the given choice, returning the resolved
        Flet ThemeMode so callers can use it for re-rendering."""
        mode = self.resolve(choice, page=page)
        page.theme_mode = mode

        page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=THEME_PRIMARY_COLOR,
                primary_container=THEME_PRIMARY_LIGHT,
                secondary=THEME_ACCENT_COLOR,
                secondary_container=THEME_ACCENT_LIGHT,
                surface=THEME_SURFACE_COLOR,
                surface_tint=THEME_PRIMARY_LIGHT,
                on_surface=THEME_TEXT_PRIMARY,
                on_surface_variant=THEME_TEXT_SECONDARY,
            ),
        )
        page.dark_theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=THEME_DARK_PRIMARY_COLOR,
                primary_container=THEME_DARK_PRIMARY_LIGHT,
                secondary=THEME_DARK_ACCENT_COLOR,
                secondary_container=THEME_DARK_ACCENT_LIGHT,
                surface=THEME_DARK_SURFACE_COLOR,
                surface_tint=THEME_DARK_PRIMARY_LIGHT,
                on_surface=THEME_DARK_TEXT_PRIMARY,
                on_surface_variant=THEME_DARK_TEXT_SECONDARY,
            ),
        )

        bg = self.palette(mode)["background"]
        page.bgcolor = bg
        return mode


# Module-level singleton — convenient for views that already import
# this module.
theme_manager = ThemeManager()
