"""
Phase 3 UI views — entry point.

Re-exports the per-feature view functions split across:
  - phase3_views_part1.py : variantes, reportes
  - phase3_views_part2.py : push queue, image search

The i18n language picker view was removed; the sidebar `LangSwitcher`
component (ui/components.py) is the single entry point for changing language.

Adding a new view means:
  1) Define `async def show_<feature>(view)` in one of the parts.
  2) Re-export it here.
  3) Add a route to ROUTE_PERMISSIONS in app_view.py and a branch in _navigate_to.
  4) Add nav_data_all entry with an icon and label.
"""

from .phase3_views_part1 import (
    show_reportes,
    show_variantes,
)
from .phase3_views_part2 import (
    show_image_search,
    show_push_queue,
)

__all__ = [
    "show_image_search",
    "show_push_queue",
    "show_reportes",
    "show_variantes",
]
