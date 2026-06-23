"""
Custom exception classes for better error handling
"""


class InventarioError(Exception):
    """Base exception for the application"""

    pass


# Alias for backward compatibility — used across services/export.py, services/permissions.py
InventarioException = InventarioError


class DatabaseException(InventarioError):
    """Database-related errors"""

    pass


class ValidationException(InventarioError):
    """Validation errors"""

    pass


class AuthenticationException(InventarioError):
    """Authentication errors"""

    pass


class AuthorizationException(InventarioError):
    """Authorization errors"""

    pass


class ProductNotFoundException(InventarioError):
    """Product not found"""

    pass


class DuplicateProductException(InventarioError):
    """Duplicate product code"""

    pass


class StockInsufficientException(InventarioError):
    """Operation would drive stock below zero."""

    pass


class InvalidStateException(InventarioError):
    """Operation is not valid given the current state of the resource."""

    pass
