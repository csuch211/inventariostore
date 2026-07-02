"""Shared utilities for the UI view modules."""

import flet as ft

from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_logger(name: str):
    """Get a logger instance for a UI module."""
    return setup_logger(name)


def _fmt_money(v) -> str:
    """Format a number as currency."""
    try:
        return f"${float(v):,.2f}"
    except (ValueError, TypeError):
        return "$0.00"


def find_submit_btn(page, label: str, translated_label: str = ""):
    """Walk the live page tree and return the first ft.Button whose
    visible text matches ``label`` (or ``translated_label``).

    Returns ``None`` if no match is found.
    """
    if not page:
        return None
    candidates = {label}
    if translated_label:
        candidates.add(translated_label)
    try:
        stack = [page]
        while stack:
            node = stack.pop()
            if isinstance(node, ft.Button):
                content = getattr(node, "content", None)
                txt = getattr(content, "value", None) or getattr(content, "text", None)
                if isinstance(txt, str) and txt.strip() in candidates:
                    return node
                sub = [content]
                sub.extend(getattr(content, "controls", None) or [])
                for item in sub:
                    if isinstance(item, ft.Text):
                        v = getattr(item, "value", None)
                        if isinstance(v, str) and v.strip() in candidates:
                            return node
            inner = getattr(node, "content", None)
            if inner is not None and inner is not node:
                stack.append(inner)
            for c in getattr(node, "controls", None) or []:
                if c is not node:
                    stack.append(c)
    except Exception as e:
        logger.error("Error en find_submit_btn: %s", e)
        return None
    return None
