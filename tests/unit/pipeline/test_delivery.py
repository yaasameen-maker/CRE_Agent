"""Tests for the SendGrid + Slack delivery pipeline."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from src.pipeline.briefs import OpportunityBrief
from src.pipeline.scorer import GoldRecord


def _brief(zip_code: str = "10001", rank: int = 1, score: int = 72) -> OpportunityBrief:
    return OpportunityBrief(
        zip_code=zip_code,
        rank=rank,
        overall_score=score,
        headline="High distress signals in Midtown.",
        summary="Multiple indicators point to elevated risk.",
        evidence_points=("3.8% delinquency", "12 foreclosures", "8% vacancy"),
        watch_items=("Verify ATTOM data", "Check rent trends"),
    )


def _records() -> list[GoldRecord]:
    return [
        GoldRecord("10001", 60, 55, 50, 72, "High risk.", rank=1),
        GoldRecord("10014", 40, 35, 30, 45, "Moderate risk.", rank=2),
    ]


def _mock_http(
    status: int = 202, body: dict | None = None, headers: dict | None = None
) -> MagicMock:  # type: ignore[type-arg]
    resp = MagicMock()
    resp.status_code = status
    resp.text = ""
    resp.json.return_value = body or {"ok": True, "ts": "1234567890.123456"}
    resp.headers = headers or {"X-Message-Id": "sg-msg-001"}
    client = MagicMock()
    client.__enter__ = lambda s: client
    client.__exit__ = MagicMock(return_value=False)
    client.post.return_value = resp
    return client


# ─── send_email_digest ────────────────────────────────────────────────────────


class TestSendEmailDigest:
    def test_returns_message_id_on_success(self) -> None:
        from src.pipeline.delivery import send_email_digest

        client = _mock_http(status=202, headers={"X-Message-Id": "abc-123"})
        with patch("src.pipeline.delivery.httpx.Client", return_value=client):
            with patch.dict(
                os.environ,
                {
                    "SENDGRID_API_KEY": "sg-test",  # pragma: allowlist secret
                    "DIGEST_TO_EMAIL": "analyst@example.com",
                    "DIGEST_FROM_EMAIL": "noreply@cre.example.com",
                },
            ):
                result = send_email_digest(_brief(), _records())
        assert result == "abc-123"

    def test_sends_to_correct_url(self) -> None:
        from src.pipeline.delivery import _SENDGRID_API_URL, send_email_digest

        client = _mock_http(status=202)
        with patch("src.pipeline.delivery.httpx.Client", return_value=client):
            with patch.dict(
                os.environ,
                {
                    "SENDGRID_API_KEY": "sg-test",  # pragma: allowlist secret
                    "DIGEST_TO_EMAIL": "a@b.com",
                    "DIGEST_FROM_EMAIL": "c@d.com",
                },
            ):
                send_email_digest(_brief(), _records())
        client.post.assert_called_once()
        assert client.post.call_args[0][0] == _SENDGRID_API_URL

    def test_auth_header_uses_api_key(self) -> None:
        from src.pipeline.delivery import send_email_digest

        client = _mock_http(status=202)
        with patch("src.pipeline.delivery.httpx.Client", return_value=client):
            with patch.dict(
                os.environ,
                {
                    "SENDGRID_API_KEY": "my-sg-key",  # pragma: allowlist secret
                    "DIGEST_TO_EMAIL": "a@b.com",
                    "DIGEST_FROM_EMAIL": "c@d.com",
                },
            ):
                send_email_digest(_brief(), _records())
        headers = client.post.call_args[1]["headers"]
        assert "my-sg-key" in headers["Authorization"]  # pragma: allowlist secret

    def test_missing_api_key_raises(self) -> None:
        from src.pipeline.delivery import send_email_digest

        clean = {k: v for k, v in os.environ.items() if k != "SENDGRID_API_KEY"}
        with patch.dict(os.environ, clean, clear=True):
            with pytest.raises(ValueError, match="SENDGRID_API_KEY"):
                send_email_digest(_brief(), _records(), to_email="a@b.com", from_email="c@d.com")

    def test_missing_to_email_raises(self) -> None:
        from src.pipeline.delivery import send_email_digest

        clean = {k: v for k, v in os.environ.items() if k != "DIGEST_TO_EMAIL"}
        with patch.dict(
            os.environ,
            {**clean, "SENDGRID_API_KEY": "sg-test"},  # pragma: allowlist secret
            clear=True,
        ):
            with pytest.raises(ValueError, match="to_email"):
                send_email_digest(_brief(), _records(), from_email="c@d.com")

    def test_http_error_raises_runtime_error(self) -> None:
        from src.pipeline.delivery import send_email_digest

        client = _mock_http(status=429)
        with patch("src.pipeline.delivery.httpx.Client", return_value=client):
            with patch.dict(
                os.environ,
                {
                    "SENDGRID_API_KEY": "sg-test",  # pragma: allowlist secret
                    "DIGEST_TO_EMAIL": "a@b.com",
                    "DIGEST_FROM_EMAIL": "c@d.com",
                },
            ):
                with pytest.raises(RuntimeError, match="429"):
                    send_email_digest(_brief(), _records())


# ─── post_slack_message ───────────────────────────────────────────────────────


class TestPostSlackMessage:
    def test_returns_ts_on_success(self) -> None:
        from src.pipeline.delivery import post_slack_message

        client = _mock_http(body={"ok": True, "ts": "1234567890.123456"})
        with patch("src.pipeline.delivery.httpx.Client", return_value=client):
            with patch.dict(
                os.environ,
                {
                    "SLACK_BOT_TOKEN": "xoxb-test",  # pragma: allowlist secret
                    "SLACK_CHANNEL": "#cre-alerts",
                },
            ):
                result = post_slack_message(_brief(), _records())
        assert result == "1234567890.123456"

    def test_sends_to_correct_url(self) -> None:
        from src.pipeline.delivery import _SLACK_POST_URL, post_slack_message

        client = _mock_http(body={"ok": True, "ts": "123"})
        with patch("src.pipeline.delivery.httpx.Client", return_value=client):
            with patch.dict(
                os.environ,
                {
                    "SLACK_BOT_TOKEN": "xoxb-test",  # pragma: allowlist secret
                    "SLACK_CHANNEL": "#alerts",
                },
            ):
                post_slack_message(_brief(), _records())
        assert client.post.call_args[0][0] == _SLACK_POST_URL

    def test_auth_header_uses_token(self) -> None:
        from src.pipeline.delivery import post_slack_message

        client = _mock_http(body={"ok": True, "ts": "123"})
        with patch("src.pipeline.delivery.httpx.Client", return_value=client):
            with patch.dict(
                os.environ,
                {
                    "SLACK_BOT_TOKEN": "xoxb-my-token",  # pragma: allowlist secret
                    "SLACK_CHANNEL": "#alerts",
                },
            ):
                post_slack_message(_brief(), _records())
        headers = client.post.call_args[1]["headers"]
        assert "xoxb-my-token" in headers["Authorization"]  # pragma: allowlist secret

    def test_missing_token_raises(self) -> None:
        from src.pipeline.delivery import post_slack_message

        clean = {k: v for k, v in os.environ.items() if k != "SLACK_BOT_TOKEN"}
        with patch.dict(os.environ, clean, clear=True):
            with pytest.raises(ValueError, match="SLACK_BOT_TOKEN"):
                post_slack_message(_brief(), _records(), channel="#alerts")

    def test_missing_channel_raises(self) -> None:
        from src.pipeline.delivery import post_slack_message

        clean = {k: v for k, v in os.environ.items() if k != "SLACK_CHANNEL"}
        with patch.dict(
            os.environ,
            {**clean, "SLACK_BOT_TOKEN": "xoxb-test"},  # pragma: allowlist secret
            clear=True,
        ):
            with pytest.raises(ValueError, match="channel"):
                post_slack_message(_brief(), _records())

    def test_slack_api_error_raises(self) -> None:
        from src.pipeline.delivery import post_slack_message

        client = _mock_http(body={"ok": False, "error": "channel_not_found"})
        with patch("src.pipeline.delivery.httpx.Client", return_value=client):
            with patch.dict(
                os.environ,
                {
                    "SLACK_BOT_TOKEN": "xoxb-test",  # pragma: allowlist secret
                    "SLACK_CHANNEL": "#nonexistent",
                },
            ):
                with pytest.raises(RuntimeError, match="channel_not_found"):
                    post_slack_message(_brief(), _records())

    def test_http_status_error_raises(self) -> None:
        from src.pipeline.delivery import post_slack_message

        client = _mock_http(status=503)
        with patch("src.pipeline.delivery.httpx.Client", return_value=client):
            with patch.dict(
                os.environ,
                {
                    "SLACK_BOT_TOKEN": "xoxb-test",  # pragma: allowlist secret
                    "SLACK_CHANNEL": "#alerts",
                },
            ):
                with pytest.raises(RuntimeError, match="503"):
                    post_slack_message(_brief(), _records())
