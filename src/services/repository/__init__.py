"""
Repository layer for InventarioStore.

Provides domain-specific data access classes that inherit from
BaseRepository for shared connection pooling and audit logging.
"""

from services.repository.accounting_repo import AccountingRepository
from services.repository.automation_repo import AutomationRepository
from services.repository.base import BaseRepository
from services.repository.cart_repo import CartRepository
from services.repository.config_repo import ConfigRepository
from services.repository.crm_repo import CRMRepository
from services.repository.document_repo import DocumentRepository
from services.repository.employee_repo import EmployeeRepository
from services.repository.hr_repo import HRRepository
from services.repository.inventory_repo import InventoryRepository
from services.repository.invoice_repo import InvoiceRepository
from services.repository.notification_repo import NotificationRepository
from services.repository.product_repo import ProductRepository
from services.repository.purchasing_repo import PurchasingRepository
from services.repository.sale_repo import SaleRepository
from services.repository.sales_enhanced_repo import SalesEnhancedRepository
from services.repository.store_repo import StoreRepository
from services.repository.user_repo import UserRepository

__all__ = [
    "AccountingRepository",
    "AutomationRepository",
    "BaseRepository",
    "CRMRepository",
    "CartRepository",
    "ConfigRepository",
    "DocumentRepository",
    "EmployeeRepository",
    "HRRepository",
    "InventoryRepository",
    "InvoiceRepository",
    "NotificationRepository",
    "ProductRepository",
    "PurchasingRepository",
    "SaleRepository",
    "SalesEnhancedRepository",
    "StoreRepository",
    "UserRepository",
]
