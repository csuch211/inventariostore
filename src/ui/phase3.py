"""
Phase 3 UI views — entry point.

Re-exports the per-feature view functions split across:
  - product_reports.py      : variantes, reportes
  - notifications_image.py  : push queue, image search

Adding a new view means:
  1) Define `async def show_<feature>(view)` in one of the parts.
  2) Re-export it here.
  3) Add a route to ROUTE_PERMISSIONS in app_view.py and a branch in _navigate_to.
  4) Add nav_data_all entry with an icon and label.
"""

from .notifications_image import (
    show_image_search,
    show_push_queue,
)
from .product_reports import (
    show_reportes,
    show_variantes,
)

__all__ = [
    "show_image_search",
    "show_push_queue",
    "show_reportes",
    "show_variantes",
]
