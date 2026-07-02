"""Sales module - Sales and POS management."""

from modules.sales.controllers.sales_controller import SalesController
from modules.sales.controllers.sales_enhanced_controller import SalesEnhancedController

__all__ = ["SalesController", "SalesEnhancedController"]
