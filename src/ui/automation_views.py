"""Automation dashboard and configuration views, refactored for clarity."""

import asyncio

import flet as ft

from config.settings import THEME_PRIMARY_COLOR
from core.theme_manager import theme_manager
from ui.components import AppHeader, SnackBarHelper

from ._utils import get_logger

logger = get_logger(__name__)


async def show_automation(app):
    """Main automation dashboard."""
    theme_manager.palette(page=app.page)
    controller = app.controller

    config = {}
    try:
        config = await controller.obtener_config_automation()
    except Exception as e:
        logger.error("Error al obtener config automation: %s", e)

    status_text = ft.Text("", size=12, color="#475569")
    results_text = ft.Text("", size=12, color="#475569")
    motor_status = ft.Text("Detenido", size=14, color="#EF4444", weight=ft.FontWeight.BOLD)

    async def refresh_status():
        try:
            running = await controller.motor_automation_activo()
            if running:
                motor_status.value = "En ejecución"
                motor_status.color = "#22C55E"
            else:
                motor_status.value = "Detenido"
                motor_status.color = "#EF4444"
            app.page.update()
        except Exception as e:
            logger.error("Error al refrescar status motor: %s", e)

    async def toggle_motor(e):
        try:
            running = await controller.motor_automation_activo()
            if running:
                await controller.detener_motor_automation()
                SnackBarHelper.info(app.page, "Motor de automatización detenido")
            else:
                await controller.iniciar_motor_automation()
                SnackBarHelper.success(app.page, "Motor de automatización iniciado")
            await refresh_status()
        except Exception:
            SnackBarHelper.error(app.page, "Error al cambiar estado del motor de automatización.")

    async def run_all(e):
        try:
            results_text.value = "Ejecutando..."
            app.page.update()
            results = await controller.ejecutar_todas_automatizaciones()
            parts = [f"{k}: {v}" for k, v in results.items()]
            results_text.value = "Resultados: " + ", ".join(parts) if parts else "Sin resultados"
            SnackBarHelper.success(app.page, "Automatización completada")
            app.page.update()
        except Exception:
            SnackBarHelper.error(app.page, "Error al ejecutar automatizaciones.")

    # Toggle switches
    switches = {}
    toggle_keys = [
        ("auto_reorder_enabled", "Reorden automático"),
        ("auto_store_sync", "Sincronizar stock tienda"),
        ("auto_notify_order_status", "Notificar cambios de pedidos"),
        ("auto_demand_forecast", "Pronóstico de demanda"),
        ("auto_abc_classify", "Clasificación ABC"),
        ("auto_dynamic_pricing", "Precios dinámicos"),
        ("auto_customer_segments", "Segmentación de clientes"),
    ]

    switch_controls = []
    for key, label in toggle_keys:
        sw = ft.Switch(
            label=label,
            value=config.get(key, "false").lower() == "true",
        )
        switches[key] = sw
        switch_controls.append(sw)

    interval_field = ft.TextField(
        label="Intervalo (segundos)",
        value=config.get("auto_run_interval", "3600"),
        width=200,
        filled=True,
        fill_color="#F8FAFC",
        color="#0F172A",
    )

    async def save_config(e):
        try:
            for key, sw in switches.items():
                await controller.guardar_config_automation(key, str(sw.value).lower())
            await controller.guardar_config_automation("auto_run_interval", interval_field.value)
            status_text.value = "Configuración guardada"
            SnackBarHelper.success(app.page, "Configuración guardada")
            app.page.update()
        except Exception:
            SnackBarHelper.error(app.page, "Error al guardar configuración de automatización.")

    if app.main_view:
        await refresh_status()
        app.main_view.content = ft.Column(
            [
                AppHeader.create("Automatización", "Motor de reglas y modelos predictivos"),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Column([
                                        ft.Text("Estado del motor:", size=14, weight=ft.FontWeight.BOLD),
                                        motor_status,
                                        ft.Text(f"Última ejecución: {config.get('auto_last_run', 'Nunca')}", size=11, color="#94A3B8"),
                                    ]),
                                    ft.Row([
                                        ft.Button(
                                            content=ft.Row([ft.Icon(ft.icons.Icons.PLAY_ARROW, color="white"), ft.Text("Iniciar/Detener", color="white")], spacing=5),
                                            on_click=toggle_motor,
                                            style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
                                        ),
                                        ft.OutlinedButton(
                                            content=ft.Row([ft.Icon(ft.icons.Icons.PLAY_CIRCLE), ft.Text("Ejecutar Todo")], spacing=5),
                                            on_click=run_all,
                                        ),
                                    ], spacing=10),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            results_text,
                            ft.Divider(),
                            ft.Text("Tareas Automáticas", size=14, weight=ft.FontWeight.BOLD, color=THEME_PRIMARY_COLOR),
                            *switch_controls,
                            ft.Divider(),
                            ft.ResponsiveRow([
                                ft.Container(interval_field, col={"sm": 12, "md": 4, "lg": 3}),
                            ], columns=12, spacing=10),
                            ft.Divider(),
                            ft.Text("Acciones Manuales", size=14, weight=ft.FontWeight.BOLD, color=THEME_PRIMARY_COLOR),
                            ft.ResponsiveRow([
                                ft.Container(
                                    ft.OutlinedButton("Reorden Automático", on_click=lambda e: asyncio.create_task(_run_action(app, controller.ejecutar_reorden_automatico, "Reorden"))),
                                    col={"sm": 6, "md": 3, "lg": 2}),
                                ft.Container(
                                    ft.OutlinedButton("Sincronizar Stock Tienda", on_click=lambda e: asyncio.create_task(_run_action(app, controller.sincronizar_stock_tienda, "Stock tienda"))),
                                    col={"sm": 6, "md": 3, "lg": 2}),
                                ft.Container(
                                    ft.OutlinedButton("Pronosticar Demanda", on_click=lambda e: asyncio.create_task(_run_action(app, controller.generar_pronosticos_demanda, "Pronóstico"))),
                                    col={"sm": 6, "md": 3, "lg": 2}),
                                ft.Container(
                                    ft.OutlinedButton("Clasificar ABC", on_click=lambda e: asyncio.create_task(_run_action(app, controller.ejecutar_clasificacion_abc, "ABC"))),
                                    col={"sm": 6, "md": 3, "lg": 2}),
                                ft.Container(
                                    ft.OutlinedButton("Sugerir Precios", on_click=lambda e: asyncio.create_task(_run_action(app, controller.generar_sugerencias_precio, "Precios"))),
                                    col={"sm": 6, "md": 3, "lg": 2}),
                                ft.Container(
                                    ft.OutlinedButton("Segmentar Clientes", on_click=lambda e: asyncio.create_task(_run_action(app, controller.ejecutar_segmentacion_clientes, "Segmentos"))),
                                    col={"sm": 6, "md": 3, "lg": 2}),
                            ], columns=12, spacing=10, run_spacing=10),
                            ft.Container(height=10),
                            ft.Row([
                                ft.Button(
                                    content=ft.Row([ft.Icon(ft.icons.Icons.SAVE, color="white"), ft.Text("Guardar Configuración", color="white")], spacing=5),
                                    on_click=save_config,
                                    style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
                                ),
                            ]),
                            status_text,
                        ],
                        spacing=15,
                    ),
                    padding=20,
                    expand=True,
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        app.page.update()


async def _run_action(app, coro_factory, label):
    try:
        result = await coro_factory()
        SnackBarHelper.success(app.page, f"{label}: {result} procesados")
    except Exception:
        SnackBarHelper.error(app.page, f"{label}: Ha ocurrido un error interno.")


async def show_automation_abc(app):
    """View ABC classification results."""
    controller = app.controller
    try:
        abc_data = await controller.obtener_clasificacion_abc()
    except Exception as e:
        logger.error("Error al obtener clasificación ABC: %s", e)
        abc_data = []

    rows = []
    for item in abc_data:
        color = "#22C55E" if item["clasificacion"] == "A" else ("#F59E0B" if item["clasificacion"] == "B" else "#EF4444")
        rows.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(item.get("codigo", ""))),
                ft.DataCell(ft.Text(item.get("nombre", "")[:20])),
                ft.DataCell(ft.Text(f"${item.get('valor_anual', 0):.2f}")),
                ft.DataCell(ft.Text(f"{item.get('porcentaje_acumulado', 0):.1f}%")),
                ft.DataCell(ft.Container(ft.Text(item["clasificacion"], color="white", weight=ft.FontWeight.BOLD), bgcolor=color, padding=5, border_radius=4)),
            ])
        )

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Código")),
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Valor Anual")),
            ft.DataColumn(ft.Text("% Acum.")),
            ft.DataColumn(ft.Text("Clase")),
        ],
        rows=rows,
    )

    if not rows:
        table = ft.Text("Sin datos. Ejecute la clasificación ABC desde Automatización.", color="#94A3B8")

    if app.main_view:
        app.main_view.content = ft.Column(
            [
                AppHeader.create("Clasificación ABC", "Análisis Pareto de productos"),
                ft.Container(content=ft.Column([table], spacing=15), padding=20, expand=True),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        app.page.update()


async def show_automation_forecasts(app):
    """View demand forecasts."""
    controller = app.controller
    try:
        data = await controller.obtener_pronosticos()
    except Exception as e:
        logger.error("Error al obtener pronósticos: %s", e)
        data = []

    rows = []
    for item in data:
        rows.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(item.get("producto_id", "")))),
                ft.DataCell(ft.Text(item.get("periodo", ""))),
                ft.DataCell(ft.Text(f"{item.get('demanda_pronosticada', 0):.1f}")),
                ft.DataCell(ft.Text(f"{item.get('intervalo_inferior', 0):.1f} - {item.get('intervalo_superior', 0):.1f}")),
                ft.DataCell(ft.Text(str(item.get("demanda_real", "") or "—"))),
                ft.DataCell(ft.Text(item.get("modelo", ""))),
            ])
        )

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Producto ID")),
            ft.DataColumn(ft.Text("Período")),
            ft.DataColumn(ft.Text("Pronóstico")),
            ft.DataColumn(ft.Text("Intervalo")),
            ft.DataColumn(ft.Text("Real")),
            ft.DataColumn(ft.Text("Modelo")),
        ],
        rows=rows,
    )

    if not rows:
        table = ft.Text("Sin pronósticos. Ejecute desde Automatización.", color="#94A3B8")

    if app.main_view:
        app.main_view.content = ft.Column(
            [
                AppHeader.create("Pronóstico de Demanda", "Predicciones de ventas"),
                ft.Container(content=ft.Column([table], spacing=15), padding=20, expand=True),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        app.page.update()


async def show_automation_segments(app):
    """View customer segments."""
    controller = app.controller
    try:
        data = await controller.obtener_segmentos_clientes()
    except Exception as e:
        logger.error("Error al obtener segmentos: %s", e)
        data = []

    color_map = {"VIP": "#22C55E", "Frecuente": "#3B82F6", "Regular": "#F59E0B", "Ocasional": "#8B5CF6", "Perdido": "#EF4444"}

    rows = []
    for item in data:
        seg = item.get("segmento", "")
        c = color_map.get(seg, "#94A3B8")
        rows.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(item.get("cliente_nombre", "")[:20])),
                ft.DataCell(ft.Text(item.get("email", ""))),
                ft.DataCell(ft.Container(ft.Text(seg, color="white", size=11, weight=ft.FontWeight.BOLD), bgcolor=c, padding=5, border_radius=4)),
                ft.DataCell(ft.Text(str(item.get("rfm_score", "")))),
                ft.DataCell(ft.Text(f"{item.get('recencia_dias', 0)}d")),
                ft.DataCell(ft.Text(str(item.get("frecuencia", 0)))),
                ft.DataCell(ft.Text(f"${item.get('monetario', 0):.2f}")),
            ])
        )

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Cliente")),
            ft.DataColumn(ft.Text("Email")),
            ft.DataColumn(ft.Text("Segmento")),
            ft.DataColumn(ft.Text("RFM")),
            ft.DataColumn(ft.Text("Recencia")),
            ft.DataColumn(ft.Text("Frec.")),
            ft.DataColumn(ft.Text("Monetario")),
        ],
        rows=rows,
    )

    if not rows:
        table = ft.Text("Sin segmentos. Ejecute la segmentación desde Automatización.", color="#94A3B8")

    if app.main_view:
        app.main_view.content = ft.Column(
            [
                AppHeader.create("Segmentación de Clientes", "RFM Analysis"),
                ft.Container(content=ft.Column([table], spacing=15), padding=20, expand=True),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        app.page.update()


async def show_automation_pricing(app):
    """View pricing suggestions."""
    controller = app.controller

    async def refresh(estado=None):
        try:
            data = await controller.obtener_sugerencias_precio(estado=estado)
        except Exception as e:
            logger.error("Error al obtener sugerencias de precio: %s", e)
            data = []

        rows = []
        for item in data:
            sug_id = item["id"]
            pct = ((item["precio_sugerido"] - item["precio_actual"]) / item["precio_actual"]) * 100
            arrow = "▲" if pct > 0 else "▼"
            color = "#22C55E" if pct > 0 else "#EF4444"

            async def apply(e, sid=sug_id):
                await controller.aplicar_sugerencia_precio(sid)
                SnackBarHelper.success(app.page, "Precio actualizado")
                await refresh(app._current_route)

            async def reject(e, sid=sug_id):
                await controller.rechazar_sugerencia_precio(sid)
                await refresh(app._current_route)

            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(item.get("codigo", ""))),
                    ft.DataCell(ft.Text(item.get("nombre", "")[:15])),
                    ft.DataCell(ft.Text(f"${item['precio_actual']:.2f}")),
                    ft.DataCell(ft.Text(f"${item['precio_sugerido']:.2f}", color=color, weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"{arrow} {abs(pct):.1f}%", color=color)),
                    ft.DataCell(ft.Text(f"{item.get('confianza', 0)*100:.0f}%")),
                    ft.DataCell(ft.Text(item.get("motivo", "")[:25])),
                    ft.DataCell(ft.Row([
                        ft.IconButton(icon=ft.icons.Icons.CHECK_CIRCLE, icon_color="green", on_click=apply, tooltip="Aplicar"),
                        ft.IconButton(icon=ft.icons.Icons.CANCEL, icon_color="red", on_click=reject, tooltip="Rechazar"),
                    ])),
                ])
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Código")),
                ft.DataColumn(ft.Text("Producto")),
                ft.DataColumn(ft.Text("Actual")),
                ft.DataColumn(ft.Text("Sugerido")),
                ft.DataColumn(ft.Text("Cambio")),
                ft.DataColumn(ft.Text("Conf.")),
                ft.DataColumn(ft.Text("Motivo")),
                ft.DataColumn(ft.Text("Acción")),
            ],
            rows=rows,
        )

        if not rows:
            table = ft.Text("Sin sugerencias de precio pendientes.", color="#94A3B8")

        if app.main_view:
            app.main_view.content = ft.Column(
                [
                    AppHeader.create("Sugerencias de Precios", "Precios dinámicos basados en demanda y rotación"),
                    ft.Container(content=ft.Column([
                        ft.Row([
                            ft.OutlinedButton("Pendientes", on_click=lambda e: asyncio.create_task(refresh("pendiente"))),
                            ft.OutlinedButton("Aplicados", on_click=lambda e: asyncio.create_task(refresh("aplicado"))),
                            ft.OutlinedButton("Todos", on_click=lambda e: asyncio.create_task(refresh(None))),
                            ft.Button(
                                content=ft.Row([ft.Icon(ft.icons.Icons.REFRESH, color="white"), ft.Text("Generar Nuevos", color="white")], spacing=5),
                                on_click=lambda e: asyncio.create_task(_run_action(app, controller.generar_sugerencias_precio, "Sugerencias")),
                                style=ft.ButtonStyle(bgcolor=THEME_PRIMARY_COLOR),
                            ),
                        ]),
                        table,
                    ], spacing=15), padding=20, expand=True),
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
            app.page.update()

    await refresh("pendiente")
