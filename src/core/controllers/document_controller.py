"""Document controller for document management."""

from services.auth import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentController:
    """Controller for document management operations."""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Document Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ Categorías ============

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def crear_categoria_documento(self, **kwargs) -> tuple[bool, dict]:
        """Create document category."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.document_repo.crear_categoria_documento(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error creating category: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_categorias_documento(self) -> list[dict]:
        """List document categories."""
        try:
            return self.db.document_repo.obtener_categorias_documento()
        except Exception as e:
            logger.exception(f"Error fetching categories: {e}")
            return []

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def eliminar_categoria_documento(self, categoria_id: int) -> tuple[bool, dict]:
        """Delete document category."""
        try:
            self.db.document_repo.eliminar_categoria_documento(
                categoria_id, usuario=self.current_user or "system"
            )
            return True, {"message": "Category deleted"}
        except Exception as e:
            logger.exception(f"Error deleting category: {e}")
            return False, {"error": str(e)}

    # ============ Documentos ============

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def crear_documento(self, **kwargs) -> tuple[bool, dict]:
        """Create a new document."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.document_repo.crear_documento(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error creating document: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_documento(self, documento_id: int) -> dict | None:
        """Get document by ID."""
        try:
            return self.db.document_repo.obtener_documento(documento_id)
        except Exception as e:
            logger.exception(f"Error fetching document: {e}")
            return None

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_documentos(
        self,
        categoria_id: int | None = None,
        tipo: str | None = None,
        estado: str | None = None,
        autor: str | None = None,
    ) -> list[dict]:
        """List documents."""
        try:
            return self.db.document_repo.obtener_documentos(
                categoria_id=categoria_id, tipo=tipo, estado=estado, autor=autor
            )
        except Exception as e:
            logger.exception(f"Error fetching documents: {e}")
            return []

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def actualizar_documento(self, documento_id: int, **kwargs) -> tuple[bool, dict]:
        """Update document."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            self.db.document_repo.actualizar_documento(documento_id, **kwargs)
            return True, {"message": "Document updated"}
        except Exception as e:
            logger.exception(f"Error updating document: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def eliminar_documento(self, documento_id: int) -> tuple[bool, dict]:
        """Delete document."""
        try:
            self.db.document_repo.eliminar_documento(
                documento_id, usuario=self.current_user or "system"
            )
            return True, {"message": "Document deleted"}
        except Exception as e:
            logger.exception(f"Error deleting document: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_LEER)
    async def buscar_documentos(self, query: str) -> list[dict]:
        """Search documents."""
        try:
            return self.db.document_repo.buscar_documentos(query)
        except Exception as e:
            logger.exception(f"Error searching documents: {e}")
            return []

    # ============ Versiones ============

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def crear_version(self, **kwargs) -> tuple[bool, dict]:
        """Create document version."""
        try:
            kwargs["usuario"] = self.current_user or "system"
            result = self.db.document_repo.crear_version(**kwargs)
            return True, result
        except Exception as e:
            logger.exception(f"Error creating version: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_versiones(self, documento_id: int) -> list[dict]:
        """List document versions."""
        try:
            return self.db.document_repo.obtener_versiones(documento_id)
        except Exception as e:
            logger.exception(f"Error fetching versions: {e}")
            return []

    # ============ Tags ============

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def agregar_tag(self, documento_id: int, tag: str) -> tuple[bool, dict]:
        """Add tag to document."""
        try:
            self.db.document_repo.agregar_tag(documento_id, tag)
            return True, {"message": "Tag added"}
        except Exception as e:
            logger.exception(f"Error adding tag: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def eliminar_tag(self, documento_id: int, tag: str) -> tuple[bool, dict]:
        """Remove tag from document."""
        try:
            self.db.document_repo.eliminar_tag(documento_id, tag)
            return True, {"message": "Tag removed"}
        except Exception as e:
            logger.exception(f"Error removing tag: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_LEER)
    async def buscar_por_tag(self, tag: str) -> list[dict]:
        """Find documents by tag."""
        try:
            return self.db.document_repo.buscar_por_tag(tag)
        except Exception as e:
            logger.exception(f"Error searching by tag: {e}")
            return []

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_tags_populares(self, limit: int = 20) -> list[dict]:
        """Get popular tags."""
        try:
            return self.db.document_repo.obtener_tags_populares(limit=limit)
        except Exception as e:
            logger.exception(f"Error fetching popular tags: {e}")
            return []
