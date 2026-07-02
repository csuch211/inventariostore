"""
Authentication controller for login/logout operations
"""

from modules.auth.services.auth_service import AuthService
from services.database import DatabaseManager
from services.export import ExportService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AuthController:
    """Authentication controller"""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Auth Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    async def login(self, username: str, password: str) -> dict:
        """Authenticate user"""
        try:
            session = self.auth_service.authenticate(username, password)
            self.current_user = username
            self.current_user_role = session.get("rol", "operador")
            self.current_user_permissions = set(session.get("permissions", []))
            logger.info(
                f"User {username} logged in as '{self.current_user_role}' "
                f"with {len(self.current_user_permissions)} permissions"
            )
            return session
        except Exception as e:
            logger.exception(f"Login failed: {e}")
            raise

    async def logout(self, token: str):
        """Logout user"""
        self.auth_service.logout(token)
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
