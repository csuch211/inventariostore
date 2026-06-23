"""
Admin views (users, backups, settings) extracted from AppView.

Each function takes an ``app`` parameter (the AppView instance) and uses
``app.page``, ``app.controller``, etc. instead of ``self``.
"""

import asyncio

import flet as ft

from config.settings import (
    APP_NAME,
    APP_VERSION,
    THEME_ACCENT_COLOR,
    THEME_PRIMARY_COLOR,
)
from services.permissions import Perm as P
from ui.components import (
    AppHeader,
    DialogHelper,
    FormField,
    SnackBarHelper,
)
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def show_users(app):
    """Display users management view with role + permission editing."""
    can_manage = P.USUARIOS_GESTIONAR in app.controller.current_user_permissions

    usuarios = await app.controller.obtener_usuarios_con_roles()
    roles = await app.controller.obtener_roles()
    catalogo = await app.controller.obtener_permisos_catalogo()

    async def open_new(e):
        await show_user_form(app, None, roles)

    async def handle_edit_perms(e, u):
        await show_user_perms_dialog(app, u, roles, catalogo)

    async def handle_change_role(e, u):
        pass

    def build_rows():
        rows = []
        for u in usuarios:
            roles_text = ", ".join(u.get("roles", [])) or "-"
            perms_count = len(u.get("permisos", []))
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(u.get("username", "")))),
                        ft.DataCell(ft.Text(str(u.get("nombre", "")))),
                        ft.DataCell(ft.Text(roles_text)),
                        ft.DataCell(ft.Text(str(perms_count))),
                        ft.DataCell(
                            ft.Text(
                                t("users.active") if u.get("activo") else t("users.inactive"),
                                color="green" if u.get("activo") else "gray600",
                            )
                        ),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.Icons.EDIT,
                                        icon_color=THEME_PRIMARY_COLOR,
                                        tooltip=t("common.edit"),
                                        on_click=(
                                            lambda e, uu=u: asyncio.create_task(
                                                handle_edit_perms(e, uu)
                                            )
                                        )
                                        if can_manage
                                        else None,
                                    ),
                                ]
                            )
                        ),
                    ]
                )
            )
        return rows

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(t("users.username"))),
            ft.DataColumn(ft.Text(t("users.full_name"))),
            ft.DataColumn(ft.Text(t("users.role"))),
            ft.DataColumn(ft.Text("#")),
            ft.DataColumn(ft.Text(t("common.confirm"))),
            ft.DataColumn(ft.Text("")),
        ],
        rows=build_rows(),
    )

    header_actions = []
    if can_manage:
        header_actions.append(
            ft.Button(
                content=ft.Row(
                    [
                        ft.Icon(ft.icons.Icons.ADD, color="white"),
                        ft.Text(t("users.new"), color="white"),
                    ],
                    spacing=5,
                ),
                on_click=open_new,
                style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
            )
        )

    content = ft.Column(
        [
            AppHeader.create(t("users.title"), t("users.subtitle")),
            ft.Container(
                content=ft.Row(header_actions, alignment=ft.MainAxisAlignment.END),
                padding=20,
            ),
            ft.Container(content=table, padding=20, expand=True)
            if usuarios
            else ft.Container(
                content=ft.Text(t("users.empty"), color="gray600"),
                padding=40,
                alignment="center",
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()


async def show_user_form(app, usuario, roles):
    """Show user add/edit dialog with role selector."""
    is_edit = usuario is not None
    username = FormField.create_text_field(label=t("users.username"), required=True)
    full_name = FormField.create_text_field(label=t("users.full_name"), required=True)
    password = FormField.create_text_field(
        label=t("users.password") if not is_edit else f"{t('users.password')} (opcional)",
        password=True,
        can_reveal_password=True,
    )
    role_dd = ft.Dropdown(
        label=t("users.role"),
        options=[ft.dropdown.Option(key=r["nombre"], text=r["nombre"]) for r in roles],
        border_color=THEME_PRIMARY_COLOR,
        focused_border_color=THEME_ACCENT_COLOR,
        filled=True,
        fill_color="gray50",
    )
    if is_edit:
        username.value = usuario.get("username", "")
        username.disabled = True
        full_name.value = usuario.get("nombre", "")
        if usuario.get("roles"):
            role_dd.value = usuario["roles"][0]

    async def save(e):
        if not username.value or not full_name.value:
            SnackBarHelper.error(app.page, t("common.validation_error"))
            return
        if not is_edit and not password.value:
            SnackBarHelper.error(app.page, t("common.validation_error"))
            return
        if not is_edit:
            ok, res = await app.controller.crear_usuario(
                username=username.value,
                password=password.value,
                nombre=full_name.value,
                rol_nombre=role_dd.value or "operador",
            )
        elif role_dd.value:
            ok, res = await app.controller.asignar_rol(
                usuario_id=usuario["id"], rol_nombre=role_dd.value
            )
        else:
            ok, res = True, {"message": "Sin cambios"}
        app.page.pop_dialog()
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
            await show_users(app)
        else:
            SnackBarHelper.error(app.page, res.get("error", t("common.error")))

    dialog = ft.AlertDialog(
        title=ft.Text(t("users.new") if not is_edit else t("common.edit")),
        content=ft.Column([username, full_name, password, role_dd], tight=True, spacing=10),
        actions=[
            ft.TextButton(t("common.cancel"), on_click=lambda e: app.page.pop_dialog()),
            ft.TextButton(t("common.save"), on_click=save),
        ],
    )
    dialog.open = True
    app.page.show_dialog(dialog)
    app.page.update()


async def show_user_perms_dialog(app, usuario, roles, catalogo):
    """Show dialog with the user's roles and a checkbox matrix of permissions."""
    perms_by_mod: dict = {}
    for p in catalogo:
        perms_by_mod.setdefault(p["modulo"], []).append(p)

    user_perms = set(usuario.get("permisos", []))
    user_extra = set(usuario.get("permisos_extra", []))

    checkboxes = {}
    for mod, perms in perms_by_mod.items():
        for p in perms:
            clave = p["clave"]
            is_extra = clave in user_extra
            checked = clave in user_perms
            cb = ft.Checkbox(
                label=f"{p['descripcion']} ({clave})",
                value=checked,
                disabled=not is_extra and clave in user_perms,
            )
            if checked and not is_extra:
                cb.label = f"{p['descripcion']} (rol)"
            checkboxes[clave] = (cb, is_extra)

    sections = []
    for mod, perms in perms_by_mod.items():
        section_checks = [checkboxes[p["clave"]][0] for p in perms if p["clave"] in checkboxes]
        sections.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            mod.upper(),
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=THEME_PRIMARY_COLOR,
                        ),
                        *section_checks,
                    ],
                    spacing=2,
                ),
                padding=5,
            )
        )

    role_dd = ft.Dropdown(
        label=t("users.role"),
        options=[ft.dropdown.Option(key=r["nombre"], text=r["nombre"]) for r in roles],
        border_color=THEME_PRIMARY_COLOR,
        focused_border_color=THEME_ACCENT_COLOR,
        filled=True,
        fill_color="gray50",
        value=usuario["roles"][0] if usuario.get("roles") else None,
    )

    scroll = ft.Column(sections, spacing=10, scroll=ft.ScrollMode.AUTO, tight=True)

    async def save(e):
        if role_dd.value and (not usuario.get("roles") or role_dd.value != usuario["roles"][0]):
            await app.controller.asignar_rol(usuario_id=usuario["id"], rol_nombre=role_dd.value)
        for clave, (cb, was_extra) in checkboxes.items():
            is_checked = cb.value
            has_perm = clave in user_perms
            if was_extra and not is_checked and has_perm:
                await app.controller.toggle_permiso_extra(usuario["id"], clave, agregar=False)
            elif not was_extra and is_checked and not has_perm:
                await app.controller.toggle_permiso_extra(usuario["id"], clave, agregar=True)
        app.page.pop_dialog()
        SnackBarHelper.success(app.page, t("common.success"))
        await show_users(app)

    dialog = ft.AlertDialog(
        title=ft.Text(f"{usuario.get('username', '')} — {t('users.role')}"),
        content=ft.Container(
            content=ft.Column([role_dd, ft.Divider(), scroll], spacing=10, tight=True),
            width=500,
            height=400,
        ),
        actions=[
            ft.TextButton(t("common.cancel"), on_click=lambda e: app.page.pop_dialog()),
            ft.TextButton(t("common.save"), on_click=save),
        ],
    )
    dialog.open = True
    app.page.show_dialog(dialog)
    app.page.update()


async def show_backups(app):
    """Display backup management view."""
    can_restore = P.BACKUPS_RESTAURAR in app.controller.current_user_permissions
    backups = await app.controller.listar_backups()

    async def handle_create(e):
        result = await app.controller.crear_backup()
        if "error" in result:
            SnackBarHelper.error(app.page, result["error"])
        else:
            SnackBarHelper.success(app.page, t("backups.create_success"))
        await show_backups(app)

    async def handle_restore(e, b):
        if not b.get("file_exists", True):
            SnackBarHelper.error(app.page, t("backups.file_missing"))
            return
        DialogHelper.confirmation_dialog(
            app.page,
            title=t("backups.restore"),
            content=t(
                "backups.restore_confirm", name=b.get("ruta", "").split("\\")[-1].split("/")[-1]
            ),
            on_yes=lambda ev: _do_restore(b),
        )

    async def _do_restore(b):
        app.page.pop_dialog()
        result = await app.controller.restaurar_backup(b.get("ruta", ""))
        if "error" in result:
            SnackBarHelper.error(app.page, result["error"])
        else:
            SnackBarHelper.success(app.page, t("backups.restore_success"))
        await show_backups(app)

    async def handle_delete(e, b):
        DialogHelper.confirmation_dialog(
            app.page,
            title=t("backups.delete"),
            content=t(
                "backups.delete_confirm", name=b.get("ruta", "").split("\\")[-1].split("/")[-1]
            ),
            on_yes=lambda ev: _do_delete_backup(b),
        )

    async def _do_delete_backup(b):
        app.page.pop_dialog()
        ok = await app.controller.eliminar_backup_registro(b.get("id"), ruta=b.get("ruta", ""))
        if ok:
            SnackBarHelper.success(app.page, t("common.success"))
        else:
            SnackBarHelper.error(app.page, t("common.error"))
        await show_backups(app)

    def build_rows():
        rows = []
        for b in backups:
            actions = []
            if can_restore:
                actions.append(
                    ft.IconButton(
                        icon=ft.icons.Icons.RESTORE,
                        icon_color="green",
                        tooltip=t("backups.restore"),
                        on_click=lambda e, bb=b: asyncio.create_task(handle_restore(e, bb)),
                    )
                )
            actions.append(
                ft.IconButton(
                    icon=ft.icons.Icons.DELETE,
                    icon_color=THEME_ACCENT_COLOR,
                    tooltip=t("backups.delete"),
                    on_click=lambda e, bb=b: asyncio.create_task(handle_delete(e, bb)),
                )
            )
            file_icon = (
                ft.icons.Icons.CHECK_CIRCLE if b.get("file_exists", True) else ft.icons.Icons.ERROR
            )
            file_color = "green" if b.get("file_exists", True) else "red"
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(b.get("creado_en", ""))[:16])),
                        ft.DataCell(
                            ft.Text(
                                _format_size(b.get("tamano", 0)),
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                t("backups.type.manual")
                                if b.get("tipo") == "manual"
                                else t("backups.type.scheduled")
                            )
                        ),
                        ft.DataCell(ft.Icon(file_icon, size=16, color=file_color)),
                        ft.DataCell(ft.Row(actions, spacing=2)),
                    ]
                )
            )
        return rows

    def _format_size(bytes_val):
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        else:
            return f"{bytes_val / (1024 * 1024):.1f} MB"

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(t("backups.date"))),
            ft.DataColumn(ft.Text(t("backups.size"))),
            ft.DataColumn(ft.Text(t("backups.type"))),
            ft.DataColumn(ft.Text("")),
            ft.DataColumn(ft.Text("")),
        ],
        rows=build_rows(),
    )

    content = ft.Column(
        [
            AppHeader.create(t("backups.title"), t("backups.subtitle")),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Button(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.icons.Icons.BACKUP, color="white"),
                                    ft.Text(t("backups.create"), color="white"),
                                ],
                                spacing=5,
                            ),
                            on_click=handle_create,
                            style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
                padding=20,
            ),
            ft.Container(content=table, padding=20, expand=True)
            if backups
            else ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.icons.Icons.BACKUP, size=48, color="gray400"),
                        ft.Text(t("backups.empty"), color="gray600"),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=60,
                alignment="center",
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()


async def show_settings(app):
    """Display settings page with theme toggle and notifications config."""
    current_theme = await app.controller.obtener_tema_usuario()

    app._theme_switch = ft.Switch(
        label=t("settings.theme.dark") if current_theme == "light" else t("settings.theme.light"),
        value=current_theme == "dark",
        on_change=app._on_theme_change,
    )

    smtp_cfg = (
        await app.controller.obtener_config_smtp()
        if app.controller.has_permission(P.NOTIFICACIONES_CONFIGURAR)
        else {}
    )
    settings_c = app._get_colors()

    def _settings_field(label, value, width=300, password=False):
        return ft.TextField(
            label=label,
            value=str(value) if value is not None else "",
            width=width,
            password=password,
            border_color=settings_c["input_border"],
            focused_border_color=settings_c["focus_ring"],
            filled=True,
            fill_color=settings_c["input_fill"],
            color=settings_c["text_on_input"],
            cursor_color=settings_c["cursor"],
            selection_color=settings_c["selection"],
            label_style=ft.TextStyle(color=settings_c["text_secondary"]),
            hint_style=ft.TextStyle(color=settings_c["text_muted"]),
            text_style=ft.TextStyle(color=settings_c["text_on_input"], size=14),
        )

    smtp_host = _settings_field(t("notifications.smtp_host"), smtp_cfg.get("host", ""), 300)
    smtp_port = _settings_field(t("notifications.smtp_port"), smtp_cfg.get("port", "587"), 100)
    smtp_user = _settings_field(t("notifications.smtp_user"), smtp_cfg.get("user", ""), 300)
    smtp_pass = _settings_field(
        t("notifications.smtp_password"), smtp_cfg.get("password", ""), 300, password=True
    )
    smtp_from = _settings_field(t("notifications.smtp_from"), smtp_cfg.get("from_email", ""), 300)
    smtp_to = _settings_field(t("notifications.smtp_to"), smtp_cfg.get("to_email", ""), 300)
    low_stock_switch = ft.Switch(
        label=t("notifications.low_stock_enable"), value=smtp_cfg.get("enabled") == "si"
    )

    async def save_smtp(e):
        ok = await app.controller.guardar_config_smtp(
            {
                "smtp_host": smtp_host.value,
                "smtp_port": smtp_port.value,
                "smtp_user": smtp_user.value,
                "smtp_password": smtp_pass.value,
                "smtp_from_email": smtp_from.value,
                "smtp_to_email": smtp_to.value,
                "notify_low_stock": "si" if low_stock_switch.value else "no",
            }
        )
        if ok:
            SnackBarHelper.success(app.page, t("notifications.save_success"))
        else:
            SnackBarHelper.error(app.page, t("common.error"))

    async def test_alert(e):
        result = await app.controller.enviar_alerta_stock()
        if result.get("sent"):
            SnackBarHelper.success(app.page, t("notifications.test_sent"))
        else:
            SnackBarHelper.error(
                app.page, t("notifications.test_failed", reason=result.get("reason", "?"))
            )

    content = ft.Column(
        [
            AppHeader.create(t("nav.settings"), "Ajustes de la aplicación"),
            ft.Container(
                content=ft.Column(
                    [
                        ft.ListTile(
                            title=ft.Text("Información de la Aplicación"),
                            subtitle=ft.Text(f"{APP_NAME} v{APP_VERSION}"),
                        ),
                        ft.Divider(),
                        ft.ListTile(
                            title=ft.Text("Usuario Actual"),
                            subtitle=ft.Text(app.current_user or ""),
                        ),
                        ft.Divider(),
                        ft.ListTile(
                            title=ft.Text(t("settings.theme")),
                            subtitle=ft.Text(current_theme.capitalize()),
                            trailing=app._theme_switch,
                        ),
                        ft.Divider(),
                        ft.ListTile(
                            title=ft.Text("Base de Datos"),
                            subtitle=ft.Text("Conectado"),
                            trailing=ft.Icon(ft.icons.Icons.DONE, color="green"),
                        ),
                        ft.Divider(),
                        ft.ListTile(
                            title=ft.Text(t("notifications.title")),
                            subtitle=ft.Text(t("notifications.subtitle")),
                        ),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row([smtp_host, smtp_port], spacing=10),
                                    smtp_user,
                                    smtp_pass,
                                    ft.Row([smtp_from, smtp_to], spacing=10),
                                    low_stock_switch,
                                    ft.Row(
                                        [
                                            ft.Button(
                                                content=ft.Text(t("common.save")),
                                                on_click=save_smtp,
                                            ),
                                            ft.OutlinedButton(
                                                content=ft.Text(t("notifications.test_btn")),
                                                on_click=test_alert,
                                            ),
                                        ],
                                        spacing=10,
                                    ),
                                ],
                                spacing=8,
                            ),
                            padding=20,
                        )
                        if app.controller.has_permission(P.NOTIFICACIONES_CONFIGURAR)
                        else ft.Container(),
                    ],
                    spacing=10,
                ),
                padding=20,
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    if app.main_view:
        app.main_view.content = content
        app.page.update()
