"""Tests for the captive-portal fingerprint harness.

These run entirely on loopback and never touch a console.
"""

from __future__ import annotations

import http.client
import importlib.util
import json
import socket
import struct
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "captive_portal", ROOT / "scripts" / "captive_portal.py"
)
assert SPEC and SPEC.loader
captive = importlib.util.module_from_spec(SPEC)
sys.modules["captive_portal"] = captive
SPEC.loader.exec_module(captive)


def dns_query(name: str, qtype: int = 1) -> bytes:
    question = b"".join(
        bytes([len(part)]) + part.encode("ascii") for part in name.split(".")
    ) + b"\x00"
    return (
        b"\x12\x34"
        + struct.pack("!HHHHH", 0x0100, 1, 0, 0, 0)
        + question
        + struct.pack("!HH", qtype, 1)
    )


class DnsTests(unittest.TestCase):
    def test_a_query_resolves_to_the_answer_ip(self) -> None:
        response = captive.build_response(dns_query("ctest.example"), "192.168.1.5")
        self.assertIsNotNone(response)
        assert response is not None
        ancount = struct.unpack_from("!H", response, 6)[0]
        self.assertEqual(ancount, 1)
        self.assertEqual(response[-4:], socket.inet_aton("192.168.1.5"))
        self.assertEqual(response[:2], b"\x12\x34")

    def test_aaaa_query_returns_no_answers(self) -> None:
        response = captive.build_response(
            dns_query("ctest.example", captive.QTYPE_AAAA), "192.168.1.5"
        )
        assert response is not None
        self.assertEqual(struct.unpack_from("!H", response, 6)[0], 0)

    def test_malformed_query_is_ignored(self) -> None:
        self.assertIsNone(captive.build_response(b"\x00" * 4, "192.168.1.5"))

    def test_question_is_echoed(self) -> None:
        query = dns_query("a.b.example")
        response = captive.build_response(query, "10.0.0.2")
        assert response is not None
        question_length = len(query) - 12
        self.assertEqual(
            response[12 : 12 + question_length], query[12:]
        )


class HttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.log_path = Path(self.tempdir.name) / "fp.jsonl"
        self.log = captive.make_logger(self.log_path, echo=False)
        self.server = captive.HttpServer(
            ("127.0.0.1", 0), captive.Handler, "192.168.1.5", self.log
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.tempdir.cleanup()

    def request(self, method: str, path: str, body: bytes | None = None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, path, body=body)
        response = conn.getresponse()
        payload = response.read()
        conn.close()
        return response, payload

    def test_unknown_path_redirects_to_the_portal(self) -> None:
        response, _ = self.request("GET", "/generate_204")
        self.assertEqual(response.status, 302)
        self.assertIn("/portal", response.getheader("Location") or "")

    def test_portal_page_has_the_fingerprint_probe(self) -> None:
        response, body = self.request("GET", "/portal")
        self.assertEqual(response.status, 200)
        self.assertIn(b"navigator.userAgent", body)
        self.assertIn(b"/fp", body)

    def test_fingerprint_post_is_recorded(self) -> None:
        payload = json.dumps({"ua": "test-agent"}).encode()
        response, _ = self.request("POST", "/fp", body=payload)
        self.assertEqual(response.status, 204)
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        entries = [json.loads(line) for line in lines]
        self.assertTrue(
            any(entry.get("fingerprint", {}).get("ua") == "test-agent" for entry in entries)
        )

    def test_headers_are_recorded(self) -> None:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/portal", headers={"User-Agent": "Probe/1.0"})
        conn.getresponse().read()
        conn.close()
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        self.assertTrue(any("Probe/1.0" in line for line in lines))


class PageFileTests(unittest.TestCase):
    def test_page_file_is_served_instead_of_the_builtin_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "deep.html"
            page.write_text("<html>DEEP-MARKER</html>", encoding="utf-8")
            log = captive.make_logger(Path(directory) / "log.jsonl", echo=False)
            server = captive.HttpServer(
                ("127.0.0.1", 0), captive.Handler, "192.168.1.5", log, page
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection(
                    "127.0.0.1", server.server_address[1], timeout=5
                )
                conn.request("GET", "/portal")
                body = conn.getresponse().read()
                conn.close()
                self.assertIn(b"DEEP-MARKER", body)
            finally:
                server.shutdown()
                server.server_close()


class AssetTests(unittest.TestCase):
    def test_serves_an_asset_and_blocks_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.bin").write_bytes(b"ASSET-BYTES")
            (root / "secret.txt").write_text("SECRET", encoding="utf-8")
            log = captive.make_logger(root / "log.jsonl", echo=False)
            server = captive.HttpServer(
                ("127.0.0.1", 0), captive.Handler, "192.168.1.5", log,
                None, root,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection(
                    "127.0.0.1", server.server_address[1], timeout=5
                )
                conn.request("GET", "/assets/sample.bin")
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), b"ASSET-BYTES")
                conn.close()

                conn = http.client.HTTPConnection(
                    "127.0.0.1", server.server_address[1], timeout=5
                )
                conn.request("GET", "/assets/../secret.txt")
                response = conn.getresponse()
                self.assertEqual(response.status, 404)
                response.read()
                conn.close()
            finally:
                server.shutdown()
                server.server_close()


class LoggerTests(unittest.TestCase):
    def test_logger_appends_json_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "log.jsonl"
            log = captive.make_logger(path, echo=False)
            log({"a": 1})
            log({"b": 2})
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual([json.loads(line) for line in lines], [{"a": 1}, {"b": 2}])


if __name__ == "__main__":
    unittest.main()
