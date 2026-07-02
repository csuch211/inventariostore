"""
Custom exception classes for better error handling
"""


class InventarioError(Exception):
    """Base exception for the application"""

    pass


# Alias for backward compatibility — used across services/export.py, services/permissions.py
InventarioException = InventarioError


class DatabaseError(InventarioError):
    """Database-related errors"""

    pass


class ValidationError(InventarioError):
    """Validation errors"""

    pass


class AuthenticationError(InventarioError):
    """Authentication errors"""

    pass


class AuthorizationError(InventarioError):
    """Authorization errors"""

    pass


class ProductNotFoundError(InventarioError):
    """Product not found"""

    pass


# TODO: Use ProductNotFoundError in ProductRepository.obtener_producto_por_id
#       and in actualizar_stock / actualizar_producto when product is not found.


class DuplicateProductError(InventarioError):
    """Duplicate product code"""

    pass


# DuplicateProductError is already used in ProductRepository.crear_producto


class StockInsufficientError(InventarioError):
    """Operation would drive stock below zero."""

    pass


class InvalidStateError(InventarioError):
    """Operation is not valid given the current state of the resource."""

    pass


# Backward-compatibility aliases
DatabaseException = DatabaseError
ValidationException = ValidationError
AuthenticationException = AuthenticationError
AuthorizationException = AuthorizationError
ProductNotFoundException = ProductNotFoundError
DuplicateProductException = DuplicateProductError
StockInsufficientException = StockInsufficientError
InvalidStateException = InvalidStateError
