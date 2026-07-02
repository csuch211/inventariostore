"""Integration tests: messaging + push queue + dispatcher."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import extended_features_db
from services.messaging import create_push_sender_func


def _mock_response(is_success=True, json_data=None, text=""):
    m = MagicMock()
    m.is_success = is_success
    m.json.return_value = json_data or {}
    m.text = text or ""
    return m


@pytest.mark.asyncio
async def test_push_queue_with_whatsapp_sender(seeded_ctrl):
    """Enqueue a job and dispatch with a WhatsApp sender."""
    db = seeded_ctrl.db
    jid = extended_features_db.encolar_job(db, tipo="low_stock", destinatario="+52123",
                                asunto="Test WA", cuerpo="Low stock alert")

    assert jid > 0

    def get_config():
        return {"wa_api_key": "abc", "wa_phone_id": "123", "wa_enabled": "si",
                "wa_api_url": "https://graph.facebook.com/v18.0"}
    sender = create_push_sender_func("whatsapp", get_config)

    mock_resp = _mock_response(is_success=True, json_data={"messages": [{"id": "wamid.int"}]})
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_resp
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = extended_features_db.despachar_jobs_pendientes(db, sender=sender, limit=10)

    assert result["procesados"] >= 1
    assert result["enviados"] >= 1

    jobs = extended_features_db.obtener_jobs(db, estado="enviado", limit=10)
    sent_ids = [j["id"] for j in jobs]
    assert jid in sent_ids


@pytest.mark.asyncio
async def test_push_queue_with_telegram_sender(seeded_ctrl):
    """Enqueue a job and dispatch with a Telegram sender."""
    db = seeded_ctrl.db
    jid = extended_features_db.encolar_job(db, tipo="low_stock", destinatario="-100999",
                                asunto="Test TG", cuerpo="Low stock <b>alert</b>")

    assert jid > 0

    def get_config():
        return {"tg_bot_token": "bot:token", "tg_chat_id": "-100999", "tg_enabled": "si"}
    sender = create_push_sender_func("telegram", get_config)

    mock_resp = _mock_response(is_success=True, json_data={"ok": True, "result": {"message_id": 99}})
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_resp
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = extended_features_db.despachar_jobs_pendientes(db, sender=sender, limit=10)

    assert result["procesados"] >= 1
    assert result["enviados"] >= 1

    jobs = extended_features_db.obtener_jobs(db, estado="enviado", limit=10)
    sent_ids = [j["id"] for j in jobs]
    assert jid in sent_ids


@pytest.mark.asyncio
async def test_push_queue_fallback_to_email(seeded_ctrl):
    """Without a custom sender, the default SMTP path is used (dry-run)."""
    db = seeded_ctrl.db
    jid = extended_features_db.encolar_job(db, tipo="low_stock", destinatario="test@test.com",
                                asunto="Test fallback", cuerpo="Fallback test")

    assert jid > 0

    # No custom sender — will try SMTP, which is not configured, so dry-run
    result = extended_features_db.despachar_jobs_pendientes(db, limit=10)

    assert result["procesados"] >= 1
    assert result["enviados"] >= 1


@pytest.mark.asyncio
async def test_dispatcher_send_via_channel(seeded_ctrl):
    """send_via_channel works end-to-end via mocked HTTP."""
    from services.messaging import send_via_channel

    config_wa = {"wa_api_key": "abc", "wa_phone_id": "123", "wa_enabled": "si",
                 "wa_api_url": "https://graph.facebook.com/v18.0"}
    mock_resp_wa = _mock_response(is_success=True, json_data={"messages": [{"id": "wamid.e2e"}]})
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_resp_wa
    with patch("httpx.AsyncClient", return_value=mock_client):
        r = await send_via_channel("whatsapp", "+52123", "T", "B", config_wa)
    assert r["sent"] is True

    config_tg = {"tg_bot_token": "bot:t", "tg_chat_id": "-100", "tg_enabled": "si"}
    mock_resp_tg = _mock_response(is_success=True, json_data={"ok": True, "result": {"message_id": 7}})
    mock_client2 = AsyncMock()
    mock_client2.__aenter__.return_value = mock_client2
    mock_client2.post.return_value = mock_resp_tg
    with patch("httpx.AsyncClient", return_value=mock_client2):
        r = await send_via_channel("telegram", "-100", "T", "<b>B</b>", config_tg)
    assert r["sent"] is True
