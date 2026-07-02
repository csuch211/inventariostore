"""Typography system with predefined text styles."""

from __future__ import annotations

from typing import Any

import flet as ft

from core.theme_manager import theme_manager


class T:
    """Text style presets matching the design scale."""

    @staticmethod
    def _colors(page: ft.Page | None = None) -> dict[str, str]:
        """Return the color palette for the given page."""
        return theme_manager.palette(page=page)

    @staticmethod
    def display(text: str, page: ft.Page | None = None, **kwargs: Any) -> ft.Text:
        """Return a Text object with display style (large titles)."""
        c = T._colors(page)
        return ft.Text(
            value=text,
            size=32,
            weight=ft.FontWeight.BOLD,
            color=c["primary"],
            **kwargs,
        )

    @staticmethod
    def h1(text: str, page: ft.Page | None = None, **kwargs: Any) -> ft.Text:
        """Return a Text object with h1 style."""
        c = T._colors(page)
        return ft.Text(
            value=text,
            size=28,
            weight=ft.FontWeight.BOLD,
            color=c["text_primary"],
            **kwargs,
        )

    @staticmethod
    def h2(text: str, page: ft.Page | None = None, **kwargs: Any) -> ft.Text:
        """Return a Text object with h2 style."""
        c = T._colors(page)
        return ft.Text(
            value=text,
            size=22,
            weight=ft.FontWeight.W_600,
            color=c["text_primary"],
            **kwargs,
        )

    @staticmethod
    def h3(text: str, page: ft.Page | None = None, **kwargs: Any) -> ft.Text:
        """Return a Text object with h3 style."""
        c = T._colors(page)
        return ft.Text(
            value=text,
            size=18,
            weight=ft.FontWeight.W_600,
            color=c["text_primary"],
            **kwargs,
        )

    @staticmethod
    def body(text: str, page: ft.Page | None = None, **kwargs: Any) -> ft.Text:
        """Return a Text object with body style."""
        c = T._colors(page)
        return ft.Text(
            value=text,
            size=14,
            color=c.get("text_primary", "#0F172A"),
            **kwargs,
        )

    @staticmethod
    def caption(text: str, page: ft.Page | None = None, **kwargs: Any) -> ft.Text:
        """Return a Text object with caption style."""
        c = T._colors(page)
        return ft.Text(
            value=text,
            size=12,
            color=c["text_muted"],
            **kwargs,
        )

    @staticmethod
    def label(text: str, page: ft.Page | None = None, **kwargs: Any) -> ft.Text:
        """Return a Text object with label style."""
        c = T._colors(page)
        return ft.Text(
            value=text,
            size=13,
            weight=ft.FontWeight.W_500,
            color=c["text_secondary"],
            **kwargs,
        )

    @staticmethod
    def money(value: float, page: ft.Page | None = None, **kwargs: Any) -> ft.Text:
        """Return a Text object with money style."""
        c = T._colors(page)
        return ft.Text(
            value=f"${value:,.2f}",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=c["primary"],
            **kwargs,
        )

    @staticmethod
    def stat(value: str, page: ft.Page | None = None, **kwargs: Any) -> ft.Text:
        """Return a Text object with stat style."""
        c = T._colors(page)
        return ft.Text(
            value=value,
            size=24,
            weight=ft.FontWeight.BOLD,
            color=c["text_primary"],
            **kwargs,
        )
