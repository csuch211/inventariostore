"""
Repository layer for InventarioStore.

Provides domain-specific data access classes that inherit from
BaseRepository for shared connection pooling and audit logging.
"""

from services.repository.accounting_repo import AccountingRepository
from services.repository.base import BaseRepository
from services.repository.config_repo import ConfigRepository
from services.repository.crm_repo import CRMRepository
from services.repository.employee_repo import EmployeeRepository
from services.repository.hr_repo import HRRepository
from services.repository.inventory_repo import InventoryRepository
from services.repository.invoice_repo import InvoiceRepository
from services.repository.product_repo import ProductRepository
from services.repository.purchasing_repo import PurchasingRepository
from services.repository.sale_repo import SaleRepository
from services.repository.user_repo import UserRepository

__all__ = [
    "AccountingRepository",
    "BaseRepository",
    "ConfigRepository",
    "CRMRepository",
    "EmployeeRepository",
    "HRRepository",
    "InventoryRepository",
    "InvoiceRepository",
    "ProductRepository",
    "PurchasingRepository",
    "SaleRepository",
    "UserRepository",
]
