import unittest
from unittest.mock import Mock, patch

import main


class ScanResultTests(unittest.TestCase):
    def run_scan(self, status, result):
        responses = [
            Mock(status_code=200, json=Mock(return_value={"scan_id": "scan-123"})),
            Mock(status_code=200, json=Mock(return_value={
                "status": status, "result": result,
            })),
        ]
        with patch("main.requests.post", side_effect=responses), \
                patch("main.time.sleep"), \
                self.assertLogs(main.LOGGER, level="INFO") as logs, \
                self.assertRaises(SystemExit) as exit_result:
            main.main("https://api.example.com", "key", "token", "owner/repo",
                      "sha", "user", "main", "commit")
        return exit_result.exception.code, "\n".join(logs.output)

    def test_warning_preserves_issue_and_report_and_succeeds(self):
        code, logs = self.run_scan("COMPLETED", {
            "status": "WARNING",
            "html_url": "https://github.com/owner/repo/issues/1",
            "report_url": "https://reports.example.com/scan.html",
            "issues_count": 4,
            "scaned_files": 6,
        })
        self.assertEqual(code, 0)
        self.assertIn("URL del issue: https://github.com/owner/repo/issues/1", logs)
        self.assertIn("URL del reporte: https://reports.example.com/scan.html", logs)
        self.assertIn("advertencias informativas (WARNING)", logs)

    def test_warning_without_issue_still_shows_report(self):
        code, logs = self.run_scan("COMPLETED", {
            "status": "WARNING",
            "code_insights_url": "https://api.bitbucket.org/report",
            "report_url": "https://reports.example.com/scan.html",
        })
        self.assertEqual(code, 0)
        self.assertIn("URL del reporte: https://reports.example.com/scan.html", logs)
        self.assertIn("URL del issue: No disponible", logs)

    def test_execution_failure_is_not_overridden_by_result_warning(self):
        for status in ("FAILED", "ERROR"):
            with self.subTest(status=status):
                code, logs = self.run_scan(status, {
                    "status": "WARNING",
                    "html_url": "https://github.com/owner/repo/issues/1",
                    "report_url": "https://reports.example.com/scan.html",
                })
                self.assertEqual(code, 1)
                self.assertIn("URL del issue: https://github.com/owner/repo/issues/1", logs)
                self.assertIn("URL del reporte: https://reports.example.com/scan.html", logs)


if __name__ == "__main__":
    unittest.main()
