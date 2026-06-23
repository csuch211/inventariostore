"""
Repository layer for InventarioStore.

Provides domain-specific data access classes that inherit from
BaseRepository for shared connection pooling and audit logging.
"""

from services.repository.base import BaseRepository
from services.repository.config_repo import ConfigRepository
from services.repository.inventory_repo import InventoryRepository
from services.repository.product_repo import ProductRepository
from services.repository.sale_repo import SaleRepository
from services.repository.user_repo import UserRepository

__all__ = [
    "BaseRepository",
    "ProductRepository",
    "UserRepository",
    "SaleRepository",
    "InventoryRepository",
    "ConfigRepository",
]
