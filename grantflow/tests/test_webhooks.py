import logging

import httpx
import pytest

from grantflow.api import webhooks


def test_send_job_webhook_event_retries_on_request_error_and_logs(monkeypatch, caplog):
    attempts = {"count": 0}
    sleeps = []

    monkeypatch.setenv("GRANTFLOW_WEBHOOK_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("GRANTFLOW_WEBHOOK_BACKOFF_BASE_MS", "1")
    monkeypatch.setenv("GRANTFLOW_WEBHOOK_BACKOFF_MAX_MS", "2")

    def fake_sleep(delay_s: float):
        sleeps.append(delay_s)

    def fake_post(url, content, headers, timeout):
        attempts["count"] += 1
        request = httpx.Request("POST", url)
        if attempts["count"] == 1:
            raise httpx.ConnectError("network down", request=request)
        return httpx.Response(200, request=request)

    monkeypatch.setattr(webhooks.time, "sleep", fake_sleep)
    monkeypatch.setattr(webhooks.httpx, "post", fake_post)

    with caplog.at_level(logging.INFO):
        webhooks.send_job_webhook_event(
            url="https://example.com/webhook",
            secret="secret123",
            event="job.completed",
            job_id="job-1",
            job={"status": "done"},
        )

    assert attempts["count"] == 2
    assert sleeps and sleeps[0] > 0
    text = caplog.text
    assert "Webhook delivery failed" in text
    assert "Webhook delivery succeeded" in text


def test_send_job_webhook_event_retries_on_http_500_and_gives_up(monkeypatch, caplog):
    attempts = {"count": 0}
    sleeps = []

    monkeypatch.setenv("GRANTFLOW_WEBHOOK_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("GRANTFLOW_WEBHOOK_BACKOFF_BASE_MS", "1")
    monkeypatch.setenv("GRANTFLOW_WEBHOOK_BACKOFF_MAX_MS", "1")

    def fake_sleep(delay_s: float):
        sleeps.append(delay_s)

    def fake_post(url, content, headers, timeout):
        attempts["count"] += 1
        request = httpx.Request("POST", url)
        return httpx.Response(500, request=request)

    monkeypatch.setattr(webhooks.time, "sleep", fake_sleep)
    monkeypatch.setattr(webhooks.httpx, "post", fake_post)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(httpx.HTTPStatusError):
            webhooks.send_job_webhook_event(
                url="https://example.com/webhook",
                secret=None,
                event="job.failed",
                job_id="job-2",
                job={"status": "error"},
            )

    assert attempts["count"] == 2
    assert sleeps and len(sleeps) == 1
    assert "retrying" in caplog.text
    assert "giving up" in caplog.text


def test_send_job_webhook_event_does_not_retry_on_http_400(monkeypatch):
    attempts = {"count": 0}

    monkeypatch.setenv("GRANTFLOW_WEBHOOK_MAX_ATTEMPTS", "3")

    def fake_post(url, content, headers, timeout):
        attempts["count"] += 1
        request = httpx.Request("POST", url)
        return httpx.Response(400, request=request)

    monkeypatch.setattr(webhooks.httpx, "post", fake_post)

    with pytest.raises(httpx.HTTPStatusError):
        webhooks.send_job_webhook_event(
            url="https://example.com/webhook",
            secret=None,
            event="job.pending_hitl",
            job_id="job-3",
            job={"status": "pending_hitl"},
        )

    assert attempts["count"] == 1
