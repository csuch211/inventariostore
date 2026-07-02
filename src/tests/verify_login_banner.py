"""Regression test for the duplicated login banner bug.

Earlier revisions prepended the login alert banner to main_view.content.
Every time the page rebuilt (route change, monitor poll, theme switch)
the banner was re-prepended, producing stacked duplicates with
overlapping "Ver"/"Cerrar" buttons.

This test enforces the new contract: the banner lives on page._dialogs
(the overlay/dialog stack, like SnackBars) and is never injected into
main_view.content.
"""

import asyncio
import sys
import types
from pathlib import Path

import flet as ft

_REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO / "src"))

fake_charts = types.ModuleType("ui.charts")
fake_charts.BarChart = type("BarChart", (), {"build": staticmethod(lambda *a, **k: None)})
fake_charts.LineChart = type("LineChart", (), {"build": staticmethod(lambda *a, **k: None)})
fake_charts.PieChart = type("PieChart", (), {"build": staticmethod(lambda *a, **k: None)})
sys.modules["ui.charts"] = fake_charts

from ui.app_view import AppView
from utils.i18n import initialize_language

initialize_language("es")


class FakePage:
    def __init__(self):
        self.controls = []
        self._dialogs = []
        self.overlay = []
        self.width = 1280
        self.height = 800
        self.theme_mode = ft.ThemeMode.LIGHT
        self.title = ""
        self.theme = None
        self.dark_theme = None
        self.padding = 0
        self.spacing = 0
        self.bgcolor = "white"

    def clean(self):
        self.controls.clear()

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self, *a, **k):
        pass

    def show_dialog(self, dlg):
        self._dialogs.append(dlg)

    def pop_dialog(self):
        if self._dialogs:
            return self._dialogs.pop()
        return None


async def main():
    page = FakePage()
    app = AppView(page)
    await app.controller.login("admin", "Admin123")
    app.current_user = "admin"
    app.current_token = "fake-token"

    app.main_view = ft.Container(content=ft.Column([], expand=True))

    alertas = [
        {"codigo": "A1", "nombre": "Test low", "cantidad": 0, "alert_level": "critical"},
        {"codigo": "A2", "nombre": "Test low 2", "cantidad": 3, "alert_level": "low"},
    ]

    await app._show_login_alert_banner(alertas)
    print(f"  after first show: dialogs={len(page._dialogs)}")
    assert len(page._dialogs) == 1, "expected exactly one dialog on screen"

    # Simulate route change and a re-show (the path that used to duplicate).
    app.main_view.content = ft.Column([ft.Text("alerts view placeholder")], expand=True)
    page._dialogs.clear()

    await app._show_login_alert_banner(alertas)
    print(f"  after second show: dialogs={len(page._dialogs)}")
    assert len(page._dialogs) == 1, (
        f"banner stacked: got {len(page._dialogs)} dialogs after a second show"
    )

    main_content = app.main_view.content
    if isinstance(main_content, ft.Column):
        banner_in_main = any(c is app._login_alert_banner for c in main_content.controls)
    else:
        banner_in_main = main_content is app._login_alert_banner
    assert not banner_in_main, "banner must not be prepended to main_view.content"
    print("  banner is overlay-only (not in main_view.content): OK")

    app._close_login_banner()
    print(f"  after close: dialogs={len(page._dialogs)}")
    assert app._login_alert_banner is None
    print("  dismiss clears the reference: OK")

    print("\nOK: login banner uses overlay only, never prepended to main_view")


asyncio.run(main())
