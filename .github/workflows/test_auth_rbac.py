"""
Tests for the Role-Based Access Control (RBAC) and permissions flow.

Verifies that users can only perform actions for which they have explicit permission.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.controllers.product_controller import ProductController
from core.schemas import ProductData
from services.permissions import Perm, PermissionException


@pytest.fixture
def product_controller_factory(ctrl):
    """
    Factory fixture to create a ProductController instance with a specific
    set of user permissions for testing RBAC.
    """

    def _factory(permissions: set[str]):
        # Mock the product repo to isolate the controller's logic from the DB
        ctrl.db.product_repo = MagicMock()
        return ProductController(
            db=ctrl.db,
            user_repo=ctrl.db.user_repo,
            current_user="test_user",
            current_user_permissions=permissions
        )

    return _factory


@pytest.mark.asyncio
async def test_action_fails_without_required_permission(product_controller_factory):
    """Verify that an action protected by @require_permission fails if the user lacks the permission."""
    # Arrange: Create a controller for a user who can only read products
    viewer_permissions = {Perm.PRODUCTOS_LEER}
    controller = product_controller_factory(viewer_permissions)
    product_data = ProductData(codigo="TEST-001", nombre="Test Product", precio_venta=10.0)

    # Act & Assert: Attempting to create a product must raise PermissionException
    with pytest.raises(PermissionException) as excinfo:
        await controller.crear_producto(product_data)

    assert str(excinfo.value) == f"El usuario no tiene el permiso requerido: {Perm.PRODUCTOS_CREAR}"
    controller.db.product_repo.crear.assert_not_called()


@pytest.mark.asyncio
async def test_action_succeeds_with_required_permission(product_controller_factory):
    """Verify that an action protected by @require_permission succeeds if the user has the permission."""
    # Arrange: Create a controller for a user who can create products
    operator_permissions = {Perm.PRODUCTOS_LEER, Perm.PRODUCTOS_CREAR}
    controller = product_controller_factory(operator_permissions)
    product_data = ProductData(codigo="TEST-001", nombre="Test Product", precio_venta=10.0)

    # Act: Attempt to create a product. No exception should be raised.
    await controller.crear_producto(product_data)

    # Assert: The underlying repository method was called, meaning the permission check passed.
    controller.db.product_repo.crear.assert_called_once_with(product_data)