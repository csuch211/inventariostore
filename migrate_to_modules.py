"""
Script to create temporary facade files for modular architecture migration.

This script creates facade files in src/modules/ that re-export from the original
locations, allowing for a gradual migration without breaking the system.
"""

import os
import re
from pathlib import Path

# Define module mappings: module_name -> (controller_path, service_path, repo_path, ui_files)
MODULE_MAPPINGS = {
    "auth": {
        "controller": "core.controllers.auth_controller:AuthController",
        "service": "services.auth:AuthService",
        "repo": "services.repository.user_repo:UserRepository",
        "ui": [
            "ui.register_view",
            "ui.forgot_password_view",
            "ui.verify_email_view",
        ],
    },
    "products": {
        "controller": "core.controllers.product_controller:ProductController",
        "service": None,
        "repo": "services.repository.product_repo:ProductRepository",
        "ui": ["ui.entity"],
    },
    "inventory": {
        "controller": "core.controllers.inventory_controller:InventoryController",
        "service": None,
        "repo": "services.repository.inventory_repo:InventoryRepository",
        "ui": ["ui.stock", "ui.inventory_operations"],
    },
    "warehouses": {
        "controller": "core.controllers.warehouse_controller:WarehouseController",
        "service": None,
        "repo": None,
        "ui": [],
    },
    "sales": {
        "controller": "core.controllers.sales_controller:SalesController",
        "service": None,
        "repo": "services.repository.sale_repo:SaleRepository",
        "ui": ["ui.sales"],
    },
    "purchasing": {
        "controller": "core.controllers.purchasing_controller:PurchasingController",
        "service": None,
        "repo": None,
        "ui": ["ui.purchasing_views"],
    },
    "invoicing": {
        "controller": "core.controllers.invoice_controller:InvoiceController",
        "service": None,
        "repo": None,
        "ui": ["ui.invoice_views"],
    },
    "reports": {
        "controller": "core.controllers.report_controller:ReportController",
        "service": "services.export:ExportService",
        "repo": None,
        "ui": ["ui.product_reports", "ui.financial_reports", "ui.charts"],
    },
    "accounting": {
        "controller": "core.controllers.accounting_controller:AccountingController",
        "service": None,
        "repo": None,
        "ui": ["ui.accounting_views"],
    },
    "hr": {
        "controller": "core.controllers.hr_controller:HRController",
        "service": None,
        "repo": None,
        "ui": ["ui.hr_views"],
    },
    "crm": {
        "controller": "core.controllers.crm_controller:CRMController",
        "service": None,
        "repo": None,
        "ui": ["ui.crm_views"],
    },
    "documents": {
        "controller": "core.controllers.document_controller:DocumentController",
        "service": None,
        "repo": None,
        "ui": ["ui.document_views"],
    },
    "notifications": {
        "controller": "core.controllers.notification_controller:NotificationController",
        "service": "services.notifier:Notifier",
        "repo": None,
        "ui": ["ui.notification_views", "ui.messaging_config_view"],
    },
    "automation": {
        "controller": "core.controllers.automation_controller:AutomationController",
        "service": None,
        "repo": None,
        "ui": ["ui.automation_views"],
    },
    "store": {
        "controller": "core.controllers.store_controller:StoreController",
        "service": None,
        "repo": None,
        "ui": ["ui.store_views", "ui.store_public"],
    },
    "admin": {
        "controller": "core.controllers.admin_controller:AdminController",
        "service": "services.backup:BackupService",
        "repo": "services.repository.config_repo:ConfigRepository",
        "ui": ["ui.admin"],
    },
}

# Map of module plural names -> singular stem for controller/service/repo filenames
# (the architecture doc uses singular stems: product_controller, warehouse_controller, etc.)
MODULE_FILE_STEM = {
    "products": "product",
    "warehouses": "warehouse",
    "sales": "sales",
    "purchasing": "purchasing",
    "invoicing": "invoice",
    "reports": "report",
    "accounting": "accounting",
    "notifications": "notification",
    "documents": "document",
    "automation": "automation",
    "store": "store",
    "admin": "admin",
    "crm": "crm",
    "hr": "hr",
    "inventory": "inventory",
    "auth": "auth",
}


def _file_stem(module_name: str) -> str:
    """Return the singular stem for a module's file names."""
    return MODULE_FILE_STEM.get(module_name, module_name)


def create_facade_file(filepath: Path, import_statement: str, exports: list[str]):
    """Create a facade file that re-exports from original location."""
    content = f'''"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
{import_statement}

__all__ = {exports}
'''
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content)
    print(f"Created: {filepath}")


def create_init_file(filepath: Path, content: str):
    """Create an __init__.py file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content)
    print(f"Created: {filepath}")


def main():
    """Create all facade files for modular architecture."""
    base_path = Path("src/modules")

    for module_name, mapping in MODULE_MAPPINGS.items():
        module_path = base_path / module_name
        stem = _file_stem(module_name)

        # Create __init__.py for subdirectories
        for subdir in ["controllers", "services", "repositories"]:
            init_file = module_path / subdir / "__init__.py"
            if not init_file.exists():
                create_init_file(init_file, f'"""Package: {module_name}/{subdir}."""\n')

        # Create controller facade
        if mapping["controller"]:
            import_path, class_name = mapping["controller"].split(":")
            controller_file = module_path / "controllers" / f"{stem}_controller.py"
            create_facade_file(
                controller_file,
                f"from {import_path} import {class_name}",
                [f'"{class_name}"']
            )

        # Create service facade
        if mapping["service"]:
            import_path, class_name = mapping["service"].split(":")
            service_file = module_path / "services" / f"{stem}_service.py"
            create_facade_file(
                service_file,
                f"from {import_path} import {class_name}",
                [f'"{class_name}"']
            )

        # Create repository facade
        if mapping["repo"]:
            import_path, class_name = mapping["repo"].split(":")
            repo_file = module_path / "repositories" / f"{stem}_repository.py"
            create_facade_file(
                repo_file,
                f"from {import_path} import {class_name}",
                [f'"{class_name}"']
            )

        # Create UI __init__.py
        if mapping["ui"]:
            ui_init = module_path / "ui" / "__init__.py"
            if not ui_init.exists() or "{module_name}" in ui_init.read_text():
                ui_init.parent.mkdir(parents=True, exist_ok=True)
                display_name = module_name.replace("_", " ").title()
                ui_init.write_text(f'"""UI module for {display_name}."""\n\n# TODO: Migrate UI views here\n')
                print(f"Created: {ui_init}")

        # Create/update module root __init__.py
        module_init = module_path / "__init__.py"
        controller_imports = []
        if mapping["controller"]:
            _, class_name = mapping["controller"].split(":")
            controller_imports.append(
                f"from modules.{module_name}.controllers.{stem}_controller import {class_name}"
            )
        if mapping["service"]:
            _, class_name = mapping["service"].split(":")
            controller_imports.append(
                f"from modules.{module_name}.services.{stem}_service import {class_name}"
            )

        if controller_imports:
            display_name = module_name.replace("_", " ").title()
            export_names = []
            for imp in controller_imports:
                class_name = imp.split(" import ")[1]
                export_names.append(class_name)
            init_content = (
                f'"""{display_name} module."""\n\n'
                + "\n".join(controller_imports)
                + f"\n\n__all__ = {export_names}\n"
            )
            module_init.write_text(init_content)
            print(f"Updated: {module_init}")

    print("\nMigration facades created successfully!")
    print("Next steps:")
    print("1. Update imports in the codebase to use modules.*")
    print("2. Gradually move actual code from original locations to modules")
    print("3. Remove facade files once migration is complete")


if __name__ == "__main__":
    main()
