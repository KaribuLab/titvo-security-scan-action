"""Optional failure notifications for the GitHub action."""

import logging
import os
from html import escape

import requests

LOGGER = logging.getLogger("titvo-security-scan")


def validate_slack(webhook_url, bot_token, channel):
    """Require an unambiguous transport and a declared destination."""
    if webhook_url and bot_token:
        raise ValueError("Configura solo slack_webhook_url o slack_bot_token.")
    if bot_token and not channel.strip():
        raise ValueError("slack_channel es obligatorio con slack_bot_token.")
    if channel and not bot_token:
        raise ValueError("slack_channel solo es válido con slack_bot_token.")


def notify_failure(webhook_url, bot_token, channel, repo, sha, branch, actor, failure):
    """Best effort: Slack errors must never replace the scan failure."""
    if not (webhook_url or bot_token):
        return

    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    run_repo = os.environ.get("GITHUB_REPOSITORY", repo)
    run_id = os.environ.get("GITHUB_RUN_ID")
    run_url = f"{server}/{run_repo}/actions/runs/{run_id}" if run_id else "No disponible"
    details = {
        "Estado": failure.get("status", "ERROR"),
        "Repositorio": f"{repo} — {server}/{repo}",
        "Commit": f"{sha} — {server}/{repo}/commit/{sha}",
        "Rama": branch,
        "Actor": os.environ.get("GITHUB_ACTOR", actor),
        "Action": "Titvo Code Scanner",
        "Workflow": os.environ.get("GITHUB_WORKFLOW", "No disponible"),
        "Job": os.environ.get("GITHUB_JOB", "No disponible"),
        "Intento": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "Ejecución": run_url,
        "Reporte": failure.get("report_url") or "No disponible",
        "Issue": failure.get("issue_url") or "No disponible",
    }
    if bot_token:
        details["Canal configurado"] = channel
    text = "\n".join(f"*{key}:* {escape(str(value), quote=False)}"
                     for key, value in details.items())
    payload = {
        "text": f"🚨 FALLA — Titvo Security Scan — {escape(repo, quote=False)}",
        "attachments": [{"color": "danger", "text": text, "mrkdwn_in": ["text"]}],
    }
    headers = {}
    url = webhook_url
    if bot_token:
        url = "https://slack.com/api/chat.postMessage"
        headers["Authorization"] = f"Bearer {bot_token}"
        payload.update(channel=channel, unfurl_links=False, unfurl_media=False)

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15,
                                 allow_redirects=False)
        if response.status_code != 200:
            LOGGER.warning("No se pudo notificar a Slack (HTTP %s).", response.status_code)
        elif bot_token and response.json().get("ok") is not True:
            LOGGER.warning("Slack rechazó la notificación.")
        elif not bot_token and response.text.strip() != "ok":
            LOGGER.warning("Respuesta inesperada del webhook de Slack.")
        else:
            LOGGER.info("Notificación de fallo enviada a Slack.")
    except (requests.RequestException, ValueError, AttributeError):
        # Exception messages may contain the secret webhook URL. Never log them.
        LOGGER.warning("No se pudo enviar la notificación a Slack.")
