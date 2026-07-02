"""Stress and load tests for the messaging module.

Tests the system under load: bulk enqueue, concurrent dispatch,
retry resilience, and large payload handling.

Run with:  uv run pytest src/tests/test_messaging_stress.py -v
For slower tests:  uv run pytest src/tests/test_messaging_stress.py -v --run-slow
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import extended_features_db
from services.messaging import send_via_channel

# Number of iterations for bulk operations
SMALL_BATCH = 20
MEDIUM_BATCH = 50
LARGE_BATCH = 100


# =========================================================================
# Helpers
# =========================================================================

def _mock_response(is_success: bool = True, json_data: dict | None = None,
                   text: str = ""):
    m = MagicMock()
    m.is_success = is_success
    m.json.return_value = json_data or {}
    m.text = text
    return m


def _async_client_mock(post_return_value=None):
    client = AsyncMock()
    client.__aenter__.return_value = client
    if post_return_value is not None:
        client.post.return_value = post_return_value
    return client


def _fast_sender(cfg, asunto, cuerpo):
    return {"sent": True, "message_id": "fast-1"}


def _clean_jobs(db):
    """Remove all rows from jobs_push for test isolation."""
    from services.extended_features_db import _conn
    with _conn(db) as conn:
        conn.execute("DELETE FROM jobs_push")
        conn.commit()


@pytest.fixture(autouse=True)
def _clean_jobs_fixture(ctrl):
    """Clean jobs_push table before each stress test for isolation."""
    _clean_jobs(ctrl.db)
    yield


# =========================================================================
# Stress: Bulk Enqueue
# =========================================================================

class TestBulkEnqueue:
    """Enqueue many jobs and verify they all persist correctly."""

    def test_enqueue_50_jobs(self, ctrl):
        db = ctrl.db
        ids = []
        t0 = time.monotonic()
        for i in range(MEDIUM_BATCH):
            jid = extended_features_db.encolar_job(
                db, tipo="low_stock",
                destinatario=f"u{i}@test.com",
                asunto=f"Bulk job {i}",
                cuerpo=f"Body for job number {i}",
            )
            ids.append(jid)
        elapsed = time.monotonic() - t0

        assert len(ids) == MEDIUM_BATCH
        assert all(j > 0 for j in ids)
        assert len(set(ids)) == MEDIUM_BATCH
        assert elapsed < 5.0, f"Enqueue {MEDIUM_BATCH} jobs took {elapsed:.2f}s"

        pendientes = extended_features_db.obtener_jobs(db, estado="pendiente", limit=LARGE_BATCH)
        pendientes_ids = {j["id"] for j in pendientes}
        for jid in ids:
            assert jid in pendientes_ids

    def test_enqueue_100_jobs_consecutive_ids(self, ctrl):
        db = ctrl.db
        ids = []
        for i in range(LARGE_BATCH):
            jid = extended_features_db.encolar_job(
                db, tipo="alerta",
                destinatario=f"b{i}@test.com",
                asunto=f"Batch {i}", cuerpo=f"Body {i}",
            )
            ids.append(jid)

        for i in range(1, len(ids)):
            assert ids[i] > ids[i - 1], "Job IDs must be strictly increasing"

    def test_enqueue_con_destinatarios_variados(self, ctrl):
        db = ctrl.db
        destinatarios = [
            "+521234567890",
            "+59899123456",
            "user@email.com",
            "-1001234567890",
            "@channel_username",
            "",
        ]
        for dest in destinatarios:
            jid = extended_features_db.encolar_job(
                db, tipo="test", destinatario=dest,
                asunto="Dest test", cuerpo="Testing various destinations",
            )
            assert jid > 0


# =========================================================================
# Stress: Bulk Dispatch
# =========================================================================

class TestBulkDispatch:
    """Dispatch many jobs rapidly with a fast mock sender."""

    def test_dispatch_50_jobs_with_fast_sender(self, ctrl):
        db = ctrl.db
        for i in range(MEDIUM_BATCH):
            extended_features_db.encolar_job(
                db, tipo="test", destinatario=f"d{i}@test.com",
                asunto=f"Dispatch {i}", cuerpo=f"Body {i}",
            )

        t0 = time.monotonic()
        result = extended_features_db.despachar_jobs_pendientes(db, sender=_fast_sender, limit=MEDIUM_BATCH)
        elapsed = time.monotonic() - t0

        assert result["procesados"] == MEDIUM_BATCH
        assert result["enviados"] == MEDIUM_BATCH
        assert result["fallidos"] == 0
        assert elapsed < 3.0, f"Dispatch {MEDIUM_BATCH} jobs took {elapsed:.2f}s"

    def test_dispatch_100_jobs_in_multiple_batches(self, ctrl):
        db = ctrl.db
        for i in range(LARGE_BATCH):
            extended_features_db.encolar_job(
                db, tipo="test", destinatario=f"m{i}@test.com",
                asunto=f"Multi {i}", cuerpo=f"Body {i}",
            )

        total_enviados = 0
        batch_size = 25
        t0 = time.monotonic()
        for _ in range(LARGE_BATCH // batch_size):
            result = extended_features_db.despachar_jobs_pendientes(
                db, sender=_fast_sender, limit=batch_size
            )
            total_enviados += result["enviados"]
        elapsed = time.monotonic() - t0

        assert total_enviados == LARGE_BATCH
        assert elapsed < 10.0, f"Dispatch {LARGE_BATCH} jobs took {elapsed:.2f}s"

    def test_dispatch_mixto_exitosos_y_fallidos(self, ctrl):
        db = ctrl.db
        n = SMALL_BATCH
        for i in range(n):
            extended_features_db.encolar_job(
                db, tipo="test", destinatario=f"x{i}@test.com",
                asunto=f"Mixed {i}", cuerpo=f"Body {i}",
            )

        call_count = 0

        def mixed_sender(cfg, asunto, cuerpo):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                return {"sent": False, "reason": "Simulated error every 3rd"}
            return {"sent": True, "message_id": f"m-{call_count}"}

        result = extended_features_db.despachar_jobs_pendientes(db, sender=mixed_sender, limit=n)
        assert result["procesados"] == n
        assert result["enviados"] + result["fallidos"] == n
        assert result["fallidos"] > 0

        fallidos = extended_features_db.obtener_jobs(db, estado="fallido", limit=n)
        assert len(fallidos) == result["fallidos"]


# =========================================================================
# Stress: Concurrent Operations
# =========================================================================

class TestConcurrentOperations:
    """Run multiple messaging operations concurrently."""

    @pytest.mark.asyncio
    async def test_concurrent_whatsapp_sends(self):
        config = {
            "wa_api_key": "key", "wa_phone_id": "ph",
            "wa_api_url": "https://graph.facebook.com/v18.0",
            "wa_enabled": "si",
        }
        n = MEDIUM_BATCH
        mock_resp = _mock_response(is_success=True,
                                   json_data={"messages": [{"id": "wamid.c"}]})
        mock_client = _async_client_mock(post_return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            t0 = time.monotonic()
            tasks = [
                send_via_channel("whatsapp", f"+52123{i:03d}", "Test", "Hello", config)
                for i in range(n)
            ]
            results = await asyncio.gather(*tasks)
            elapsed = time.monotonic() - t0

        sent = [r for r in results if r.get("sent")]
        assert len(sent) == n
        assert elapsed < 10.0, f"{n} concurrent sends took {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_concurrent_telegram_sends(self):
        config = {
            "tg_bot_token": "bot:token", "tg_chat_id": "-100999",
            "tg_enabled": "si",
        }
        n = MEDIUM_BATCH
        mock_resp = _mock_response(is_success=True,
                                   json_data={"ok": True, "result": {"message_id": 1}})
        mock_client = _async_client_mock(post_return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            t0 = time.monotonic()
            tasks = [
                send_via_channel("telegram", "-100999", "Test", "<b>Hello</b>", config)
                for _ in range(n)
            ]
            results = await asyncio.gather(*tasks)
            elapsed = time.monotonic() - t0

        sent = [r for r in results if r.get("sent")]
        assert len(sent) == n
        assert elapsed < 10.0, f"{n} concurrent TG sends took {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_concurrent_mixed_whatsapp_telegram(self, ctrl):
        config_wa = {
            "wa_api_key": "key", "wa_phone_id": "ph",
            "wa_api_url": "https://graph.facebook.com/v18.0",
            "wa_enabled": "si",
        }
        config_tg = {
            "tg_bot_token": "bot:t", "tg_chat_id": "-100",
            "tg_enabled": "si",
        }
        n = SMALL_BATCH
        mock_resp_wa = _mock_response(is_success=True,
                                      json_data={"messages": [{"id": "wamid.m"}]})
        mock_resp_tg = _mock_response(is_success=True,
                                      json_data={"ok": True, "result": {"message_id": 1}})
        mock_client_wa = _async_client_mock(post_return_value=mock_resp_wa)
        mock_client_tg = _async_client_mock(post_return_value=mock_resp_tg)

        async def send_wa(i):
            with patch("httpx.AsyncClient", return_value=mock_client_wa):
                return await send_via_channel("whatsapp", f"+52123{i:04d}", "T", "B", config_wa)

        async def send_tg(i):
            with patch("httpx.AsyncClient", return_value=mock_client_tg):
                return await send_via_channel("telegram", "-100", "T", "<b>B</b>", config_tg)

        t0 = time.monotonic()
        wa_tasks = [send_wa(i) for i in range(n)]
        tg_tasks = [send_tg(i) for i in range(n)]
        results = await asyncio.gather(*(wa_tasks + tg_tasks))
        elapsed = time.monotonic() - t0

        sent = [r for r in results if r.get("sent")]
        assert len(sent) == n * 2
        assert elapsed < 15.0, f"{n*2} mixed sends took {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_concurrent_enqueue_and_dispatch(self, ctrl):
        db = ctrl.db
        n = SMALL_BATCH

        async def enqueuer(i):
            return extended_features_db.encolar_job(
                db, tipo="stress", destinatario=f"s{i}@test.com",
                asunto=f"Concurrent {i}", cuerpo=f"Body {i}",
            )

        t0 = time.monotonic()
        enqueue_tasks = [enqueuer(i) for i in range(n)]
        ids = await asyncio.gather(*enqueue_tasks)
        enqueue_elapsed = time.monotonic() - t0

        assert len(ids) == n
        assert all(i > 0 for i in ids)
        assert enqueue_elapsed < 3.0, f"Concurrent enqueue took {enqueue_elapsed:.2f}s"


# =========================================================================
# Stress: Retry and Resilience
# =========================================================================

class TestRetryResilience:
    """Verify retry counts and resilience under repeated failures."""

    def test_retry_count_increments_on_failure(self, ctrl):
        db = ctrl.db
        jid = extended_features_db.encolar_job(
            db, tipo="test", destinatario="retry@test.com",
            asunto="Retry test", cuerpo="Will fail",
        )

        attempt = 0

        def failing_sender(cfg, asunto, cuerpo):
            nonlocal attempt
            attempt += 1
            return {"sent": False, "reason": f"Attempt {attempt} failed"}

        extended_features_db.despachar_jobs_pendientes(db, sender=failing_sender, limit=10)

        job = extended_features_db.obtener_jobs(db, estado="fallido", limit=10)
        job_data = next(j for j in job if j["id"] == jid)
        assert job_data["intentos"] == 1

        extended_features_db.encolar_job(
            db, tipo="test", destinatario="retry2@test.com",
            asunto="Retry 2", cuerpo="Will fail again",
        )

    def test_retry_eventualmente_exitoso(self, ctrl):
        db = ctrl.db
        jid = extended_features_db.encolar_job(
            db, tipo="test", destinatario="eventual@test.com",
            asunto="Eventual success", cuerpo="Fails then succeeds",
        )

        call_count = 0

        def eventual_sender(cfg, asunto, cuerpo):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                extended_features_db.marcar_job_fallido(db, jid, f"Fail #{call_count}")
                return {"sent": False, "reason": f"Fail #{call_count}"}
            return {"sent": True, "message_id": "eventual-ok"}

        extended_features_db.despachar_jobs_pendientes(db, sender=eventual_sender, limit=10)
        # After first dispatch it failed, re-enqueue or check
        extended_features_db.encolar_job(
            db, tipo="test", destinatario="eventual@test.com",
            asunto="Retry eventual", cuerpo="Should succeed now",
        )
        extended_features_db.despachar_jobs_pendientes(db, sender=eventual_sender, limit=10)

        assert call_count >= 2

    def test_marcar_job_enviado_y_verificar_contador(self, ctrl):
        db = ctrl.db
        jid = extended_features_db.encolar_job(
            db, tipo="test", destinatario="counter@test.com",
            asunto="Counter", cuerpo="Check intentos",
        )

        extended_features_db.marcar_job_enviado(db, jid)
        jobs = extended_features_db.obtener_jobs(db, estado="enviado", limit=10)
        job_data = next((j for j in jobs if j["id"] == jid), None)
        assert job_data is not None
        assert job_data["intentos"] == 1
        assert job_data["estado"] == "enviado"

    def test_marcar_job_fallido_repetidamente(self, ctrl):
        db = ctrl.db
        jid = extended_features_db.encolar_job(
            db, tipo="test", destinatario="multi-fail@test.com",
            asunto="Multi fail", cuerpo="Fail many times",
        )

        for i in range(3):
            extended_features_db.marcar_job_fallido(db, jid, f"Error #{i + 1}")

        jobs = extended_features_db.obtener_jobs(db, estado="fallido", limit=10)
        job_data = next((j for j in jobs if j["id"] == jid), None)
        assert job_data is not None
        assert job_data["intentos"] == 3
        assert "Error #3" in (job_data.get("ultimo_error") or "")


# =========================================================================
# Stress: Large Payload Handling
# =========================================================================

class TestLargePayloads:
    """Handle messages with large bodies without failure."""

    @pytest.mark.asyncio
    async def test_large_whatsapp_payload(self):
        config = {
            "wa_api_key": "key", "wa_phone_id": "ph",
            "wa_api_url": "https://graph.facebook.com/v18.0",
            "wa_enabled": "si",
        }
        cuerpo = "X" * 10_000
        mock_resp = _mock_response(is_success=True,
                                   json_data={"messages": [{"id": "wamid.large"}]})
        mock_client = _async_client_mock(post_return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await send_via_channel("whatsapp", "+52123", "Large payload", cuerpo, config)

        assert result["sent"] is True
        assert result["message_id"] == "wamid.large"

    @pytest.mark.asyncio
    async def test_large_telegram_payload(self):
        config = {
            "tg_bot_token": "bot:t", "tg_chat_id": "-100",
            "tg_enabled": "si",
        }
        cuerpo = "<b>" + "X" * 10_000 + "</b>"
        mock_resp = _mock_response(is_success=True,
                                   json_data={"ok": True, "result": {"message_id": 999}})
        mock_client = _async_client_mock(post_return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await send_via_channel("telegram", "-100", "Large", cuerpo, config)

        assert result["sent"] is True

    @pytest.mark.asyncio
    async def test_many_concurrent_large_payloads(self):
        config = {
            "wa_api_key": "key", "wa_phone_id": "ph",
            "wa_api_url": "https://graph.facebook.com/v18.0",
            "wa_enabled": "si",
        }
        n = 10
        cuerpo = "A" * 50_000
        mock_resp = _mock_response(is_success=True,
                                   json_data={"messages": [{"id": "wamid.big"}]})
        mock_client = _async_client_mock(post_return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            t0 = time.monotonic()
            tasks = [
                send_via_channel("whatsapp", f"+52123{i:03d}", "Big", cuerpo, config)
                for i in range(n)
            ]
            results = await asyncio.gather(*tasks)
            elapsed = time.monotonic() - t0

        sent = [r for r in results if r.get("sent")]
        assert len(sent) == n
        assert elapsed < 10.0, f"{n} large payload sends took {elapsed:.2f}s"


# =========================================================================
# Stress: Rapid Enqueue/Dispatch Cycles
# =========================================================================

class TestRapidCycles:
    """Rapid cycles of enqueue + dispatch to test queue stability."""

    def test_rapid_cycles(self, ctrl):
        db = ctrl.db
        n_cycles = 10
        jobs_per_cycle = 10

        t0 = time.monotonic()
        total_enqueued = 0
        total_dispatched = 0

        for cycle in range(n_cycles):
            for i in range(jobs_per_cycle):
                extended_features_db.encolar_job(
                    db, tipo="cycle", destinatario=f"c{cycle}_{i}@test.com",
                    asunto=f"Cycle {cycle} job {i}",
                    cuerpo=f"Body {cycle}_{i}",
                )
                total_enqueued += 1

            result = extended_features_db.despachar_jobs_pendientes(
                db, sender=_fast_sender, limit=jobs_per_cycle
            )
            total_dispatched += result["enviados"]

        elapsed = time.monotonic() - t0

        assert total_enqueued == n_cycles * jobs_per_cycle
        assert total_dispatched == n_cycles * jobs_per_cycle
        assert elapsed < 10.0, f"{n_cycles} rapid cycles took {elapsed:.2f}s"

    def test_enqueue_muchos_luego_despachar_todo(self, ctrl):
        db = ctrl.db
        for i in range(LARGE_BATCH):
            extended_features_db.encolar_job(
                db, tipo="bulk", destinatario=f"bulk{i}@test.com",
                asunto=f"Bulk {i}", cuerpo=f"Body {i}",
            )

        result = extended_features_db.despachar_jobs_pendientes(
            db, sender=_fast_sender, limit=LARGE_BATCH
        )
        assert result["procesados"] == LARGE_BATCH
        assert result["enviados"] == LARGE_BATCH

        restantes = extended_features_db.obtener_jobs(db, estado="pendiente", limit=10)
        assert len(restantes) == 0


# =========================================================================
# Stress: Edge Cases
# =========================================================================

class TestEdgeCases:
    """Edge case stress tests."""

    def test_despachar_con_lista_vacia(self, ctrl):
        db = ctrl.db
        result = extended_features_db.despachar_jobs_pendientes(db, sender=_fast_sender, limit=10)
        assert result["procesados"] == 0
        assert result["enviados"] == 0
        assert result["fallidos"] == 0

    def test_encolar_con_destinatario_vacio(self, ctrl):
        db = ctrl.db
        jid = extended_features_db.encolar_job(
            db, tipo="test", destinatario="",
            asunto="Empty dest", cuerpo="Test",
        )
        assert jid > 0

    def test_obtener_jobs_sin_filtro_retorna_todos(self, ctrl):
        db = ctrl.db
        for i in range(5):
            extended_features_db.encolar_job(
                db, tipo="list", destinatario=f"l{i}@test.com",
                asunto=f"List {i}", cuerpo=f"Body {i}",
            )

        jobs = extended_features_db.obtener_jobs(db, limit=100)
        assert len(jobs) >= 5

    @pytest.mark.asyncio
    async def test_send_via_channel_con_config_vacio(self):
        result = await send_via_channel("whatsapp", "+52123", "T", "B", {})
        assert result["sent"] is False
        assert "Missing config" in result["reason"]
