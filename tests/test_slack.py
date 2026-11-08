import os
import unittest
from unittest.mock import Mock, patch

import requests

import main
import slack


class SlackTests(unittest.TestCase):
    def run_scan(self, responses, **config):
        with patch("main.requests.post", side_effect=responses) as post, \
                patch("main.time.sleep"), \
                self.assertRaises(SystemExit) as result:
            main.main("https://api.example.com", "key", "github-token",
                      "owner/repo", "abc123", "user", "main", "commit", **config)
        return result.exception.code, post

    @staticmethod
    def responses(status, result=None):
        return [
            Mock(status_code=200, json=Mock(return_value={"scan_id": "scan-123"})),
            Mock(status_code=200, json=Mock(return_value={
                "status": status, "result": result,
            })),
        ]

    def test_success_and_warning_never_notify(self):
        for result in ({}, {"status": "WARNING"}):
            with self.subTest(result=result):
                code, post = self.run_scan(self.responses("COMPLETED", result),
                                           slack_bot_token="bot", slack_channel="C123")
                self.assertEqual(code, 0)
                self.assertEqual(post.call_count, 2)

    def test_failure_without_slack_keeps_original_behavior(self):
        code, post = self.run_scan(self.responses("FAILED"))
        self.assertEqual(code, 1)
        self.assertEqual(post.call_count, 2)

    def test_no_fail_preserves_slack_failure_notification(self):
        for status in ("FAILED", "ERROR"):
            with self.subTest(status=status):
                responses = self.responses(status, {
                    "html_url": "https://github.com/owner/repo/issues/1",
                    "report_url": "https://reports.example.com/scan",
                }) + [Mock(status_code=200, text="ok")]
                code, post = self.run_scan(responses, no_fail="true",
                                           slack_webhook_url="https://hooks.slack.com/x")
                self.assertEqual(code, 0)
                self.assertEqual(post.call_count, 3)
                payload = post.call_args.kwargs["json"]
                self.assertIn("FALLA", payload["text"])
                text = payload["attachments"][0]["text"]
                self.assertIn(status, text)
                self.assertIn("https://github.com/owner/repo/issues/1", text)
                self.assertIn("https://reports.example.com/scan", text)

    def test_no_fail_handles_api_failures(self):
        for response in (requests.Timeout(), Mock(status_code=500, text="error"),
                         Mock(status_code=200, json=Mock(side_effect=ValueError))):
            with self.subTest(response=response):
                code, post = self.run_scan([response], no_fail="true")
                self.assertEqual(code, 0)
                self.assertEqual(post.call_count, 1)

    def test_no_fail_false_string_does_not_suppress_failure(self):
        code, _ = self.run_scan(self.responses("FAILED"), no_fail="false")
        self.assertEqual(code, 1)

    def test_no_fail_success_never_notifies(self):
        code, post = self.run_scan(self.responses("COMPLETED", {"status": "WARNING"}),
                                   no_fail="true", slack_bot_token="bot",
                                   slack_channel="C123")
        self.assertEqual(code, 0)
        self.assertEqual(post.call_count, 2)

    @patch.dict(os.environ, {"GITHUB_RUN_ID": "123", "GITHUB_WORKFLOW": "Security",
                             "GITHUB_JOB": "scan", "GITHUB_RUN_ATTEMPT": "2"}, clear=True)
    def test_bot_failure_has_links_context_and_channel(self):
        for status in ("FAILED", "ERROR"):
            with self.subTest(status=status):
                responses = self.responses(status, {
                    "html_url": "https://github.com/owner/repo/issues/1",
                    "report_url": "https://reports.example.com/scan",
                }) + [Mock(status_code=200, json=Mock(return_value={"ok": True}))]
                code, post = self.run_scan(responses, slack_bot_token="bot-secret",
                                           slack_channel="C123")
                self.assertEqual(code, 1)
                self.assertEqual(post.call_count, 3)
                call = post.call_args
                self.assertEqual(call.args[0], "https://slack.com/api/chat.postMessage")
                self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer bot-secret")
                payload = call.kwargs["json"]
                self.assertEqual(payload["channel"], "C123")
                self.assertIn("FALLA", payload["text"])
                self.assertEqual(payload["attachments"][0]["color"], "danger")
                text = payload["attachments"][0]["text"]
                for value in (status, "https://github.com/owner/repo/issues/1",
                              "https://reports.example.com/scan", "commit/abc123",
                              "actions/runs/123", "Security", "scan", "main",
                              "Titvo Code Scanner", "*Intento:* 2"):
                    self.assertIn(value, text)

    def test_webhook_transport(self):
        url = "https://hooks.slack.com/services/secret"
        responses = self.responses("FAILED") + [Mock(status_code=200, text="ok")]
        code, post = self.run_scan(responses, slack_webhook_url=url)
        self.assertEqual(code, 1)
        self.assertEqual(post.call_args.args[0], url)
        self.assertEqual(post.call_args.kwargs["headers"], {})
        self.assertNotIn("channel", post.call_args.kwargs["json"])

    def test_api_errors_notify_once_without_report(self):
        errors = [Mock(status_code=500, text="error"),
                  Mock(status_code=200, json=Mock(return_value={})),
                  Mock(status_code=200, json=Mock(side_effect=ValueError)),
                  Mock(status_code=200, json=Mock(return_value=[])),
                  requests.Timeout("secret endpoint")]
        for error in errors:
            with self.subTest(error=error):
                code, post = self.run_scan(
                    [error, Mock(status_code=200, text="ok")],
                    slack_webhook_url="https://hooks.slack.com/services/secret")
                self.assertEqual(code, 1)
                self.assertEqual(post.call_count, 2)
                text = post.call_args.kwargs["json"]["attachments"][0]["text"]
                self.assertIn("*Reporte:* No disponible", text)
                self.assertIn("*Issue:* No disponible", text)

    def test_polling_error_notifies(self):
        responses = [self.responses("FAILED")[0], requests.ConnectionError(),
                     Mock(status_code=200, text="ok")]
        code, post = self.run_scan(responses, slack_webhook_url="https://hooks.slack.com/x")
        self.assertEqual(code, 1)
        self.assertEqual(post.call_count, 3)

    def test_slack_errors_preserve_failure_and_hide_secrets(self):
        for response in (requests.Timeout("secret"), Mock(status_code=403, text="secret"),
                         Mock(status_code=200, json=Mock(return_value={"ok": False})),
                         Mock(status_code=200, json=Mock(side_effect=ValueError("secret")))):
            with self.subTest(response=response), self.assertLogs(slack.LOGGER) as logs:
                code, post = self.run_scan(self.responses("FAILED") + [response],
                                           slack_bot_token="secret", slack_channel="C123")
                self.assertEqual(code, 1)
                self.assertEqual(post.call_count, 3)
                self.assertNotIn("secret", "\n".join(logs.output))

    def test_invalid_configuration_fails_before_scan(self):
        for config in ({"slack_bot_token": "token"}, {"slack_channel": "C123"},
                       {"slack_webhook_url": "url", "slack_channel": "C123"},
                       {"slack_webhook_url": "url", "slack_channel": " "},
                       {"slack_bot_token": "token", "slack_webhook_url": "url",
                        "slack_channel": "C123"}):
            with self.subTest(config=config):
                code, post = self.run_scan([], **config)
                self.assertEqual(code, 1)
                post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
