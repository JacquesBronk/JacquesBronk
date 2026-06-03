"""Tests for scripts/render.py — run: python3 -m unittest discover tests -v"""
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from render import SAST, render, render_lab_table  # noqa: E402

NOW = datetime(2026, 6, 3, 16, 0, tzinfo=SAST)

FRESH = {
    "updated_at": "2026-06-03T15:30:00+02:00",
    "rows": [
        {"component": "k3s-cluster", "status": "Ready", "detail": "12 namespaces, 2 nodes"},
        {"component": "claude-tokens", "status": "Burning", "detail": "2.47B year-to-date 🔥"},
    ],
}
STALE = {**FRESH, "updated_at": "2026-06-01T15:30:00+02:00"}
NUGET = {"version": "2027.1.1", "totalDownloads": 1115}
TEMPLATE = ("{{NUGET_DOWNLOADS}}|{{NUGET_VERSION}}|{{LAB_TABLE}}|"
            "{{LAST_SYNC}}|{{LAB_QUIP}}")


class TestLabTable(unittest.TestCase):
    def test_fresh_status_renders_rows(self):
        table, last_sync, quip = render_lab_table(FRESH, NOW)
        self.assertIn("k3s-cluster     Ready     12 namespaces, 2 nodes", table)
        self.assertIn("claude-tokens   Burning   2.47B year-to-date 🔥", table)
        self.assertEqual(last_sync, "2026-06-03 15:30 SAST")
        self.assertIn("probably on fire", quip)

    def test_stale_status_shows_unknown_keeps_sync(self):
        table, last_sync, quip = render_lab_table(STALE, NOW)
        self.assertIn("k3s-cluster     Unknown", table)
        self.assertNotIn("Ready", table)
        self.assertEqual(last_sync, "2026-06-01 15:30 SAST")
        self.assertIn("actually be on fire", quip)

    def test_missing_status_renders_placeholder(self):
        table, last_sync, quip = render_lab_table(None, NOW)
        self.assertIn("Unknown", table)
        self.assertEqual(last_sync, "never")


class TestRender(unittest.TestCase):
    def test_all_placeholders_substituted(self):
        out = render(TEMPLATE, FRESH, NUGET, NOW)
        self.assertNotIn("{{", out)
        self.assertIn("1,115", out)
        self.assertIn("2027.1.1", out)

    def test_renders_with_missing_lab_status(self):
        out = render(TEMPLATE, None, NUGET, NOW)
        self.assertNotIn("{{", out)
        self.assertIn("never", out)


if __name__ == "__main__":
    unittest.main()
