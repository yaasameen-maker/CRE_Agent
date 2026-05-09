"""Delivery pipeline — SendGrid email digest and Slack notification."""

from __future__ import annotations

import os

import httpx

from src.pipeline.briefs import OpportunityBrief
from src.pipeline.scorer import GoldRecord

_SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"
_SLACK_POST_URL = "https://slack.com/api/chat.postMessage"


def _sendgrid_key() -> str:
    key = os.environ.get("SENDGRID_API_KEY", "")
    if not key:
        raise ValueError(
            "SENDGRID_API_KEY environment variable is required. Get a key at https://sendgrid.com/"
        )
    return key


def _slack_token() -> str:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        raise ValueError(
            "SLACK_BOT_TOKEN environment variable is required. "
            "Create a Slack app at https://api.slack.com/apps"
        )
    return token


def _build_digest_html(brief: OpportunityBrief, records: list[GoldRecord]) -> str:
    rows = "\n".join(
        f"    <tr><td>{r.rank}</td><td>{r.zip_code}</td>"
        f"<td>{r.overall_score}</td><td>{r.rationale[:120]}…</td></tr>"
        for r in records
    )
    evidence = "\n".join(f"      <li>{e}</li>" for e in brief.evidence_points)
    watch = "\n".join(f"      <li>{w}</li>" for w in brief.watch_items)
    return f"""<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;max-width:700px;margin:auto;padding:24px">
  <h1 style="font-size:20px">CRE Signal Digest — ZIP {brief.zip_code}</h1>
  <p style="font-size:15px;font-weight:bold">{brief.headline}</p>
  <p>{brief.summary}</p>
  <h2 style="font-size:15px">Evidence</h2>
  <ul>
{evidence}
  </ul>
  <h2 style="font-size:15px">Watch Items</h2>
  <ul>
{watch}
  </ul>
  <h2 style="font-size:15px">Full Digest</h2>
  <table border="1" cellpadding="6" style="border-collapse:collapse;font-size:13px">
    <tr><th>Rank</th><th>ZIP</th><th>Score</th><th>Rationale</th></tr>
{rows}
  </table>
</body>
</html>"""


def _build_slack_text(brief: OpportunityBrief, records: list[GoldRecord]) -> str:
    lines = [
        f":rotating_light: *CRE Signal Alert — ZIP {brief.zip_code} (rank #{brief.rank})*",
        f"*Score:* {brief.overall_score}/100",
        f"*Headline:* {brief.headline}",
        "",
        "*Top distressed ZIPs:*",
    ]
    for r in records[:5]:
        lines.append(f"  #{r.rank}  {r.zip_code}  score={r.overall_score}  — {r.rationale[:80]}…")
    return "\n".join(lines)


def send_email_digest(
    brief: OpportunityBrief,
    gold_records: list[GoldRecord],
    to_email: str | None = None,
    from_email: str | None = None,
) -> str:
    """Send an HTML digest email via SendGrid.

    Args:
        brief: Top-ranked opportunity brief.
        gold_records: Full ranked digest for the digest table.
        to_email: Recipient address. Falls back to DIGEST_TO_EMAIL env var.
        from_email: Sender address. Falls back to DIGEST_FROM_EMAIL env var.

    Returns:
        SendGrid message ID from the X-Message-Id response header.

    Raises:
        ValueError: If SENDGRID_API_KEY, to_email, or from_email are missing.
        RuntimeError: If SendGrid returns a non-2xx status.
    """
    api_key = _sendgrid_key()
    recipient = to_email or os.environ.get("DIGEST_TO_EMAIL", "")
    sender = from_email or os.environ.get("DIGEST_FROM_EMAIL", "")

    if not recipient:
        raise ValueError("Recipient email required — pass to_email or set DIGEST_TO_EMAIL env var")
    if not sender:
        raise ValueError("Sender email required — pass from_email or set DIGEST_FROM_EMAIL env var")

    html = _build_digest_html(brief, gold_records)
    subject = f"CRE Signal Digest — ZIP {brief.zip_code} score {brief.overall_score}"

    payload = {
        "personalizations": [{"to": [{"email": recipient}]}],
        "from": {"email": sender},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                _SENDGRID_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"SendGrid request failed: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"SendGrid returned HTTP {response.status_code}: {response.text}")

    return str(response.headers.get("X-Message-Id", ""))


def post_slack_message(
    brief: OpportunityBrief,
    gold_records: list[GoldRecord],
    channel: str | None = None,
) -> str:
    """Post a formatted digest notification to a Slack channel.

    Args:
        brief: Top-ranked opportunity brief.
        gold_records: Full ranked digest for the summary list.
        channel: Slack channel ID or name. Falls back to SLACK_CHANNEL env var.

    Returns:
        Slack message timestamp (ts field).

    Raises:
        ValueError: If SLACK_BOT_TOKEN or channel are missing.
        RuntimeError: If the Slack API returns an error.
    """
    token = _slack_token()
    target_channel = channel or os.environ.get("SLACK_CHANNEL", "")

    if not target_channel:
        raise ValueError("Slack channel required — pass channel or set SLACK_CHANNEL env var")

    text = _build_slack_text(brief, gold_records)

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                _SLACK_POST_URL,
                json={"channel": target_channel, "text": text},
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Slack API request failed: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"Slack API returned HTTP {response.status_code}: {response.text}")

    data: dict[str, object] = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")

    return str(data.get("ts", ""))
