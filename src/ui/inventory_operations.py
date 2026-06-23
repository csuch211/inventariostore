"""
Phase 1 UI views — entry point.

Re-exports the per-feature view functions split across:
  - inventory_operations_views.py  : devoluciones, transferencias, conteos
  - pricing_inventory_views.py     : lotes, precios, impuestos, caja
  - search_replenishment_views.py  : búsqueda, reabastecimiento

The split is mechanical (size, not behavior). Adding a new view means:
  1) Define `async def show_<feature>(view)` in one of the parts.
  2) Re-export it here.
  3) Add a route to ROUTE_PERMISSIONS in app_view.py and a branch in _navigate_to.
"""

from .inventory_operations_views import (
    show_conteos,
    show_devoluciones,
    show_transferencias,
)
from .pricing_inventory_views import (
    show_caja,
    show_impuestos,
    show_lotes,
    show_precios,
)
from .search_replenishment_views import (
    show_busqueda,
    show_reabasto,
)

__all__ = [
    "show_busqueda",
    "show_caja",
    "show_conteos",
    "show_devoluciones",
    "show_impuestos",
    "show_lotes",
    "show_precios",
    "show_reabasto",
    "show_transferencias",
]
