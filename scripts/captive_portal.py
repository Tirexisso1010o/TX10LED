#!/usr/bin/env python3
"""Captive-portal fingerprint harness for the Switch browser applet.

Two servers run together:

* a DNS responder that answers every A query with one address and every AAAA
  query with an empty answer, and
* an HTTP server that redirects unknown paths to a small page and records the
  request headers plus a JavaScript fingerprint POST.

This is a research tool. It does not attempt to exploit the browser. Real use
requires binding DNS to port 53 and HTTP to port 80, which needs elevated
privileges; for local checks use ``--dns-port 5353 --http-port 8080``.
"""

from __future__ import annotations

import argparse
import json
import socket
import struct
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "research" / "hardware-observations" / "browser-fingerprint.local.jsonl"

QTYPE_A = 1
QTYPE_AAAA = 28
QCLASS_IN = 1

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Network check</title></head>
<body>
<h1>Network check</h1>
<p id="status">collecting…</p>
<script>
(function () {
  function gl() {
    try {
      var c = document.createElement('canvas');
      var g = c.getContext('webgl') || c.getContext('experimental-webgl');
      if (!g) return null;
      var d = g.getExtension('WEBGL_debug_renderer_info');
      return d ? [g.getParameter(d.UNMASKED_VENDOR_WEBGL),
                  g.getParameter(d.UNMASKED_RENDERER_WEBGL)] : ['masked', 'masked'];
    } catch (e) { return null; }
  }
  var data = {
    ua: navigator.userAgent,
    appVersion: navigator.appVersion,
    platform: navigator.platform,
    vendor: navigator.vendor,
    language: navigator.language,
    languages: navigator.languages || null,
    hardwareConcurrency: navigator.hardwareConcurrency || null,
    deviceMemory: navigator.deviceMemory || null,
    maxTouchPoints: navigator.maxTouchPoints || null,
    screen: [screen.width, screen.height, screen.colorDepth, devicePixelRatio],
    timezone: (function(){ try { return Intl.DateTimeFormat().resolvedOptions().timeZone; } catch(e){ return null; } })(),
    webgl: gl(),
    features: {
      wasm: typeof WebAssembly !== 'undefined',
      promise: typeof Promise !== 'undefined',
      asyncFn: (function(){ try { return Object.prototype.toString.call(async function(){}) === '[object AsyncFunction]'; } catch(e){ return false; } })(),
      optionalChaining: (function(){ try { eval('({})?.a'); return true; } catch(e){ return false; } })(),
      bigint: typeof BigInt !== 'undefined'
    }
  };
  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/fp', true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onload = function () {
    document.getElementById('status').textContent = 'done';
  };
  xhr.onerror = function () {
    document.getElementById('status').textContent = 'done (no reply)';
  };
  xhr.send(JSON.stringify(data));
})();
</script>
</body></html>
"""


def parse_question(data: bytes) -> dict[str, Any] | None:
    """Parse the first DNS question from a query packet."""

    if len(data) < 12:
        return None
    qdcount = struct.unpack_from("!H", data, 4)[0]
    if qdcount < 1:
        return None
    offset = 12
    labels: list[str] = []
    while True:
        if offset >= len(data):
            return None
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if length & 0xC0:
            return None
        label = data[offset + 1 : offset + 1 + length]
        if len(label) != length:
            return None
        labels.append(label.decode("ascii", "replace"))
        offset += 1 + length
    if offset + 4 > len(data):
        return None
    qtype, qclass = struct.unpack_from("!HH", data, offset)
    return {
        "name": ".".join(labels),
        "qtype": qtype,
        "qclass": qclass,
        "question": data[12 : offset + 4],
    }


def build_response(data: bytes, answer_ip: str) -> bytes | None:
    """Build a DNS response: A queries resolve to ``answer_ip``."""

    question = parse_question(data)
    if question is None:
        return None
    transaction_id = data[:2]
    flags = 0x8180  # standard response, recursion available, no error
    answers = b""
    ancount = 0
    if question["qtype"] == QTYPE_A and question["qclass"] == QCLASS_IN:
        answers = b"\xc0\x0c" + struct.pack("!HHIH", QTYPE_A, QCLASS_IN, 0, 4)
        answers += socket.inet_aton(answer_ip)
        ancount = 1
    header = transaction_id + struct.pack("!HHHHH", flags, 1, ancount, 0, 0)
    return header + question["question"] + answers


class DnsServer(threading.Thread):
    def __init__(self, bind: str, port: int, answer_ip: str, log) -> None:
        super().__init__(daemon=True)
        self.bind = bind
        self.port = port
        self.answer_ip = answer_ip
        self.log = log
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((bind, port))

    def run(self) -> None:
        while True:
            try:
                data, peer = self.sock.recvfrom(2048)
            except OSError:
                return
            question = parse_question(data)
            name = question["name"] if question else "?"
            self.log({"event": "dns", "peer": peer[0], "name": name})
            response = build_response(data, self.answer_ip)
            if response:
                self.sock.sendto(response, peer)


class Handler(BaseHTTPRequestHandler):
    server_version = "TX10Lab/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return None

    def _record(self, **extra: Any) -> None:
        entry = {
            "event": "http",
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "method": self.command,
            "path": self.path,
            "client": self.client_address[0],
            "headers": {k: v for k, v in self.headers.items()},
        }
        entry.update(extra)
        self.server.record(entry)  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        if self.path.startswith("/portal"):
            body = self.server.page_bytes()  # type: ignore[attr-defined]
            self._record(served="portal")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._record(served="redirect")
        self.send_response(302)
        self.send_header("Location", f"http://{self.server.answer_ip}/portal")  # type: ignore[attr-defined]
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        payload: Any
        try:
            payload = json.loads(raw.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            payload = {"raw": raw.decode("utf-8", "replace")[:2000]}
        self._record(fingerprint=payload)
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()


class HttpServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(
        self,
        address,
        handler,
        answer_ip: str,
        log,
        page_file: Path | None = None,
    ) -> None:
        super().__init__(address, handler)
        self.answer_ip = answer_ip
        self._log = log
        self.page_file = page_file

    def page_bytes(self) -> bytes:
        if self.page_file is not None:
            return self.page_file.read_bytes()
        return PAGE.encode("utf-8")

    def record(self, entry: dict[str, Any]) -> None:
        self._log(entry)


def make_logger(path: Path, *, echo: bool = True):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()

    def log(entry: dict[str, Any]) -> None:
        line = json.dumps(entry, ensure_ascii=True)
        with lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        if echo:
            print(line, flush=True)

    return log


def detect_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 9))
        return sock.getsockname()[0]
    finally:
        sock.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="DNS and HTTP captive-portal fingerprint harness.",
    )
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--dns-port", type=int, default=53)
    parser.add_argument("--http-port", type=int, default=80)
    parser.add_argument("--answer-ip", default=None)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument(
        "--page-file",
        type=Path,
        default=None,
        help="Serve this HTML file at /portal instead of the built-in page.",
    )
    args = parser.parse_args(argv)

    answer_ip = args.answer_ip or detect_ip()
    log = make_logger(args.log)

    try:
        dns = DnsServer(args.bind, args.dns_port, answer_ip, log)
    except OSError as exc:
        print(
            f"cannot bind DNS {args.bind}:{args.dns_port}: {exc}\n"
            "Ports below 1024 need elevated privileges; try --dns-port 5353 for a local check.",
            file=sys.stderr,
        )
        return 1
    try:
        httpd = HttpServer(
            (args.bind, args.http_port), Handler, answer_ip, log, args.page_file
        )
    except OSError as exc:
        print(
            f"cannot bind HTTP {args.bind}:{args.http_port}: {exc}\n"
            "Ports below 1024 need elevated privileges; try --http-port 8080 for a local check.",
            file=sys.stderr,
        )
        return 1

    dns.start()
    print(f"DNS  {args.bind}:{args.dns_port} -> {answer_ip}", flush=True)
    print(f"HTTP {args.bind}:{args.http_port} -> /portal", flush=True)
    print(f"log  {args.log}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
