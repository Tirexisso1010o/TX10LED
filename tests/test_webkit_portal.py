"""Tests for the WebKit captive-portal runner.

These run on loopback with ephemeral ports and never touch a console.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "webkit_portal", ROOT / "scripts" / "webkit_portal.py"
)
assert SPEC and SPEC.loader
portal = importlib.util.module_from_spec(SPEC)
sys.modules["webkit_portal"] = portal
SPEC.loader.exec_module(portal)


def make_args(**overrides) -> argparse.Namespace:
    values = {
        "page": portal.DEFAULT_PAGE,
        "assets": None,
        "bind": "127.0.0.1",
        "answer_ip": "127.0.0.1",
        "dns_port": 0,
        "http_port": 0,
        "log": None,
        "duration": 300,
        "dry_run": False,
        "local_test": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class InterfaceTests(unittest.TestCase):
    def test_parses_default_interface(self) -> None:
        output = (
            "   route to: default\n"
            "destination: default\n"
            "       mask: default\n"
            "    gateway: 192.168.178.1\n"
            "  interface: en0\n"
            "      flags: <UP,GATEWAY,DONE,STATIC,PRCLONING>\n"
        )
        self.assertEqual(portal.parse_default_interface(output), "en0")

    def test_parses_interface_with_spaces(self) -> None:
        self.assertEqual(
            portal.parse_default_interface("  interface:   utun4  \n"), "utun4"
        )

    def test_missing_interface_returns_none(self) -> None:
        self.assertIsNone(portal.parse_default_interface("gateway: 192.0.2.1\n"))


class PortTests(unittest.TestCase):
    def test_reports_available_ephemeral_port(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        finally:
            sock.close()
        ok, message = portal.port_status(port, "tcp", "127.0.0.1")
        self.assertTrue(ok, message)

    def test_reports_busy_tcp_port(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            ok, message = portal.port_status(port, "tcp", "127.0.0.1")
        finally:
            listener.close()
        self.assertFalse(ok)
        self.assertIn("already in use", message)


class PreflightTests(unittest.TestCase):
    def test_accepts_valid_high_ports(self) -> None:
        errors, notes = portal.preflight(make_args(), "127.0.0.1")
        self.assertEqual(errors, [])
        self.assertEqual(notes, [])

    def test_rejects_missing_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.html"
            errors, _ = portal.preflight(make_args(page=missing), "127.0.0.1")
        self.assertTrue(any("page file not found" in error for error in errors))

    def test_rejects_negative_duration(self) -> None:
        errors, _ = portal.preflight(make_args(duration=-1), "127.0.0.1")
        self.assertTrue(any("--duration" in error for error in errors))

    def test_rejects_out_of_range_ports(self) -> None:
        errors, _ = portal.preflight(make_args(dns_port=70000), "127.0.0.1")
        self.assertTrue(any("--dns-port" in error for error in errors))

    def test_rejects_invalid_answer_ip(self) -> None:
        errors, _ = portal.preflight(make_args(answer_ip="not-an-ip"), "127.0.0.1")
        self.assertTrue(any("--answer-ip" in error for error in errors))

    @unittest.skipIf(
        not hasattr(os, "geteuid") or os.geteuid() == 0,
        "root can bind low ports",
    )
    def test_low_port_is_a_note_without_root(self) -> None:
        errors, notes = portal.preflight(make_args(dns_port=53), "127.0.0.1")
        self.assertEqual(errors, [])
        self.assertTrue(any("permission denied" in note for note in notes))


class RunbookTests(unittest.TestCase):
    def test_contains_the_reversible_steps(self) -> None:
        text = portal.render_runbook(
            "192.168.178.167",
            53,
            80,
            portal.DEFAULT_PAGE,
            Path("/tmp/session.jsonl"),
            300,
            "192.168.178.167",
        )
        self.assertIn("192.168.178.167", text)
        self.assertIn("DNS", text)
        self.assertIn("HTTP", text)
        self.assertIn("Bind", text)
        self.assertIn("Revert DNS Settings to Automatic", text)
        self.assertIn("does not", text)
        self.assertIn("300 s (auto-stop)", text)

    def test_zero_duration_means_until_interrupted(self) -> None:
        text = portal.render_runbook(
            "192.168.178.167",
            53,
            80,
            portal.DEFAULT_PAGE,
            Path("/tmp/session.jsonl"),
            0,
        )
        self.assertIn("until Ctrl-C", text)


class LocalTestTests(unittest.TestCase):
    def test_local_test_passes(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = portal.local_test(make_args())
        self.assertEqual(code, 0, output.getvalue())
        self.assertIn("local self-test: PASS", output.getvalue())

    def test_main_local_test_passes(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = portal.main(["--local-test"])
        self.assertEqual(code, 0, output.getvalue())
        self.assertIn("local self-test: PASS", output.getvalue())


if __name__ == "__main__":
    unittest.main()
