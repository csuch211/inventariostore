"""
Admin controller for users, roles, permissions, theme, backup, and push operations
"""

from pathlib import Path

from services.auth import AuthService
from services.backup import BackupService
from services.database import DatabaseManager
from services.export import ExportService
from services.permissions import Perm, require_permission
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AdminController:
    """Administration controller"""

    def __init__(
        self, db: DatabaseManager, auth_service: AuthService, export_service: ExportService
    ):
        self.db = db
        self.auth_service = auth_service
        self.export_service = export_service
        self.current_user = None
        self.current_user_role = None
        self.current_user_permissions = set()
        logger.info("Admin Controller initialized")

    def has_permission(self, perm_key: str) -> bool:
        return perm_key in self.current_user_permissions

    # ============ User management ============

    @require_permission(Perm.USUARIOS_LEER)
    async def obtener_usuarios_con_roles(self) -> list[dict]:
        """List users with their assigned roles."""
        try:
            usuarios = self.db.obtener_usuarios()
            for u in usuarios:
                roles = self.db.obtener_roles_de_usuario(u["id"])
                u["roles"] = [r["nombre"] for r in roles]
                u["permisos"] = self.db.obtener_permisos_de_usuario(u["id"])
                u["permisos_extra"] = self.db.obtener_permisos_extra(u["id"])
            return usuarios
        except Exception as e:
            logger.error(f"Error fetching users with roles: {e}")
            return []

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def crear_usuario(
        self,
        username: str,
        password: str,
        nombre: str,
        rol_nombre: str = "operador",
    ) -> tuple[bool, dict]:
        """Create a user, hash the password, and assign a role."""
        try:
            password_hash = AuthService.hash_password(password)
            user_id = self.db.crear_usuario(
                username=username,
                password_hash=password_hash,
                nombre=nombre,
                rol=rol_nombre,
                usuario=self.current_user or "system",
            )
            # Also register in the in-memory dict so AuthService can authenticate
            self.auth_service.users[username] = password_hash
            # Assign role
            rol = self.db.obtener_rol_por_nombre(rol_nombre)
            if rol:
                self.db.asignar_rol_a_usuario(
                    user_id, rol["id"], usuario_actor=self.current_user or "system"
                )
            logger.info(f"User created: {username} as {rol_nombre}")
            return True, {"id": user_id, "username": username}
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def asignar_rol(self, usuario_id: int, rol_nombre: str) -> tuple[bool, dict]:
        try:
            rol = self.db.obtener_rol_por_nombre(rol_nombre)
            if not rol:
                return False, {"error": f"Rol '{rol_nombre}' no existe"}
            self.db.asignar_rol_a_usuario(
                usuario_id, rol["id"], usuario_actor=self.current_user or "system"
            )
            return True, {"rol": rol_nombre}
        except Exception as e:
            logger.error(f"Error assigning role: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.USUARIOS_GESTIONAR)
    async def toggle_permiso_extra(
        self, usuario_id: int, permiso_clave: str, agregar: bool
    ) -> tuple[bool, dict]:
        try:
            if agregar:
                self.db.agregar_permiso_extra(
                    usuario_id, permiso_clave, usuario_actor=self.current_user or "system"
                )
            else:
                self.db.quitar_permiso_extra(
                    usuario_id, permiso_clave, usuario_actor=self.current_user or "system"
                )
            return True, {"permiso": permiso_clave, "agregado": agregar}
        except Exception as e:
            logger.error(f"Error toggling extra permission: {e}")
            return False, {"error": str(e)}

    async def obtener_permisos_catalogo(self) -> list[dict]:
        try:
            return self.db.obtener_permisos_catalogo()
        except Exception as e:
            logger.error(f"Error fetching permission catalog: {e}")
            return []

    async def obtener_roles(self) -> list[dict]:
        try:
            return self.db.obtener_roles()
        except Exception as e:
            logger.error(f"Error fetching roles: {e}")
            return []

    # ============ Theme management ============

    async def obtener_tema_usuario(self) -> str:
        """Get the current user's theme preference.

        Returns one of ``"light"``, ``"dark"``, ``"auto"``. Defaults to
        ``"auto"`` so first-time users follow their OS preference.
        """
        try:
            if not self.current_user:
                return "auto"
            user = self.db.obtener_usuario_por_username(self.current_user)
            if user and user.get("theme_mode"):
                return user["theme_mode"]
            return self.db.obtener_config("theme_mode", "auto")
        except Exception:
            return "auto"

    async def cambiar_tema(self, modo: str) -> bool:
        """Change the theme preference for the current user.

        Accepts ``"light"``, ``"dark"`` or ``"auto"`` (follow OS). The
        stored value is the user's *choice* — the resolved effective
        mode is computed by ``ThemeManager`` at render time.
        """
        if modo not in ("light", "dark", "auto"):
            return False
        try:
            # Update the user's theme_mode column directly instead of config
            if self.current_user:
                user = self.db.obtener_usuario_por_username(self.current_user)
                if user and user.get("id"):
                    self.db.actualizar_tema_usuario(user["id"], modo)
            else:
                # Fallback to config if no user is logged in
                self.db.guardar_config("theme_mode", modo)
            return True
        except Exception as e:
            logger.error(f"Error changing theme: {e}")
            return False

    # ============ Backup management ============

    @require_permission(Perm.BACKUPS_CREAR)
    async def crear_backup(self) -> dict:
        """Create a new database backup."""
        try:
            result = BackupService.create_backup(usuario=self.current_user or "system")
            if "error" in result:
                return result
            # Register in DB
            self.db.registrar_backup(
                ruta=result["ruta"],
                tamano=result["tamano"],
                tipo="manual",
                usuario=self.current_user or "system",
            )
            return result
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return {"error": str(e)}

    @require_permission(Perm.BACKUPS_CREAR)
    async def listar_backups(self) -> list[dict]:
        try:
            # Get DB records
            db_backups = self.db.obtener_backups()
            # Merge with files on disk
            file_backups = BackupService.list_backups()
            file_map = {b["nombre"]: b for b in file_backups}
            for b in db_backups:
                nombre = Path(b["ruta"]).name
                if nombre in file_map:
                    b["tamano"] = file_map[nombre]["tamano"]
                    b["file_exists"] = True
                else:
                    b["file_exists"] = False
            return db_backups
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []

    @require_permission(Perm.BACKUPS_RESTAURAR)
    async def restaurar_backup(self, backup_path: str) -> dict:
        """Restore database from a backup file."""
        try:
            return BackupService.restore_backup(backup_path)
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return {"error": str(e)}

    @require_permission(Perm.BACKUPS_CREAR)
    async def eliminar_backup_registro(self, backup_id: int, ruta: str = "") -> bool:
        try:
            if ruta:
                BackupService.delete_backup_file(ruta)
            self.db.eliminar_backup(backup_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting backup: {e}")
            return False

    # ============ Fase 3: Push / Email queue ============

    @require_permission(Perm.PUSH_ENVIAR)
    async def encolar_push(
        self,
        tipo: str,
        destinatario: str,
        asunto: str,
        cuerpo: str,
    ) -> tuple[bool, dict]:
        from services import phase3_db

        try:
            jid = phase3_db.encolar_job(
                self.db,
                tipo=tipo,
                destinatario=destinatario,
                asunto=asunto,
                cuerpo=cuerpo,
            )
            return True, {"id": jid}
        except Exception as e:
            logger.error(f"Error enqueuing push: {e}")
            return False, {"error": str(e)}

    @require_permission(Perm.PUSH_ENVIAR)
    async def obtener_jobs_push(
        self,
        estado: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        from services import phase3_db

        try:
            return phase3_db.obtener_jobs(self.db, estado=estado, limit=limit)
        except Exception as e:
            logger.error(f"Error fetching jobs: {e}")
            return []

    @require_permission(Perm.PUSH_ENVIAR)
    async def despachar_jobs_push(self, limit: int = 25) -> dict:
        from services import phase3_db

        try:
            return phase3_db.despachar_jobs_pendientes(self.db, limit=limit)
        except Exception as e:
            logger.error(f"Error dispatching jobs: {e}")
            return {"procesados": 0, "enviados": 0, "fallidos": 0, "error": str(e)}
