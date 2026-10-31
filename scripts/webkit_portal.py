#!/usr/bin/env python3
"""Local captive-portal runner for the WebKit n-day assessment.

This wraps ``scripts/captive_portal.py`` with:

* a preflight check for the LAN address, the page file, and ports 53/80;
* a timestamped session log under ``research/hardware-observations/``;
* a bounded run duration so a forgotten server stops itself;
* a loopback self-test that needs neither root nor a console;
* a printed, reversible console runbook.

It serves one local page, or a static site with ``--site`` for a separately
approved PoC run. It does not proxy Nintendo traffic, forward packets, or
capture credentials. W1 is a single reachability page load; serving a PoC is a
separate, explicitly approved step.
"""

from __future__ import annotations

import argparse
import errno
import http.client
import importlib.util
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "scripts" / "captive_portal.py"
DEFAULT_PAGE = ROOT / "scripts" / "webkit_probe.html"
DEFAULT_LOG_DIR = ROOT / "research" / "hardware-observations"


def load_portal():
    """Load the captive-portal module without requiring a package install."""

    spec = importlib.util.spec_from_file_location("captive_portal", PORTAL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {PORTAL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["captive_portal"] = module
    spec.loader.exec_module(module)
    return module


def default_log_path() -> Path:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return DEFAULT_LOG_DIR / f"webkit-portal-{stamp}.local.jsonl"


def parse_default_interface(route_output: str) -> str | None:
    """Extract the interface name from ``route -n get default`` output."""

    for line in route_output.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() == "interface":
            name = value.strip()
            if name:
                return name
    return None


def lan_ip() -> str:
    """Return the IPv4 address on the interface carrying the default route.

    ``captive_portal.detect_ip`` connects a UDP socket to a documentation
    address, which follows whichever route is preferred. On this Mac a VPN
    tunnel wins that lookup and yields a tunnel address the console cannot
    reach, so prefer the default-route interface explicitly.
    """

    try:
        route = subprocess.run(
            ["route", "-n", "get", "default"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        interface = parse_default_interface(route.stdout)
        if interface:
            address = subprocess.run(
                ["ipconfig", "getifaddr", interface],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
            if address and not address.startswith("127."):
                return address
    except (OSError, subprocess.SubprocessError):
        pass
    return load_portal().detect_ip()


def port_status(port: int, kind: str, host: str = "0.0.0.0") -> tuple[bool, str]:
    """Return whether a port can be bound, with a human-readable reason."""

    sock_type = socket.SOCK_DGRAM if kind == "udp" else socket.SOCK_STREAM
    sock = socket.socket(socket.AF_INET, sock_type)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        return True, "available"
    except OSError as exc:
        if exc.errno == errno.EACCES:
            return False, "permission denied; run with sudo"
        if exc.errno == errno.EADDRINUSE:
            return False, "already in use"
        return False, str(exc.strerror or exc)
    finally:
        sock.close()


def preflight(
    args: argparse.Namespace, bind_host: str
) -> tuple[list[str], list[str]]:
    """Return ``(errors, notes)`` for the requested session."""

    errors: list[str] = []
    notes: list[str] = []

    if not args.page.is_file():
        errors.append(f"page file not found: {args.page}")
    if args.site is not None:
        if not args.site.is_dir():
            errors.append(f"site directory not found: {args.site}")
        elif not (args.site / "index.html").is_file():
            errors.append(f"site index not found: {args.site / 'index.html'}")
    if args.entry_query and args.site is None:
        errors.append("--entry-query requires --site")
    if args.duration < 0:
        errors.append("--duration must be zero or greater")
    port_specs: list[tuple[int, str]] = []
    for name, value, kind in (
        ("--dns-port", args.dns_port, "udp"),
        ("--http-port", args.http_port, "tcp"),
    ):
        if not 0 <= value <= 65535:
            errors.append(f"{name} must be between 0 and 65535")
            continue
        port_specs.append((value, kind))

    if args.answer_ip is not None:
        try:
            socket.inet_aton(args.answer_ip)
        except OSError:
            errors.append(f"--answer-ip is not an IPv4 address: {args.answer_ip}")

    for port, kind in port_specs:
        ok, message = port_status(port, kind, bind_host)
        if ok:
            continue
        if (
            "permission denied" in message
            and os.geteuid() != 0
            and port < 1024
        ):
            notes.append(f"{kind.upper()} {port}: {message}")
            continue
        if (
            "already in use" in message
            and bind_host == "0.0.0.0"
            and port == 53
        ):
            notes.append(
                f"{kind.upper()} {port}: {message} on the wildcard address; "
                "a local resolver (for example Cloudflare WARP) may hold "
                "127.0.2.2:53. Omit --bind to bind the LAN address instead."
            )
            continue
        errors.append(f"{kind.upper()} {port}: {message}")

    return errors, notes


def render_runbook(
    answer_ip: str,
    dns_port: int,
    http_port: int,
    page: Path,
    log_path: Path,
    duration: int,
    bind_host: str | None = None,
    site: Path | None = None,
    entry_query: str | None = None,
) -> str:
    duration_text = f"{duration} s (auto-stop)" if duration else "until Ctrl-C"
    lines = [
        "WebKit captive-portal session",
        f"  Mac LAN IP : {answer_ip}",
    ]
    if bind_host is not None:
        lines.append(f"  Bind       : {bind_host}")
    if site is not None:
        lines.append(f"  Site       : {site}")
    if entry_query:
        lines.append(f"  Entry      : /portal?{entry_query.lstrip('?')}")
    lines.extend(
        [
            f"  DNS        : {answer_ip}:{dns_port} (UDP)",
            f"  HTTP       : {answer_ip}:{http_port} (TCP)",
            f"  Page       : {page}",
            f"  Log        : {log_path}",
            f"  Duration   : {duration_text}",
            "",
            "Console steps (reversible):",
            "  1. Settings > Internet > Internet Settings > [active network] > Change Settings.",
            "  2. DNS Settings > Manual. Primary DNS: " + answer_ip + ".",
            "     Secondary DNS: your router address, or leave automatic if allowed.",
            "  3. Save, then Test Connection.",
            "  4. Wait for the page to report 'probe sent' or up to 30 seconds.",
            "  5. Revert DNS Settings to Automatic immediately after the test.",
            "  6. Press Ctrl-C here to stop the server.",
            "",
            "This server answers DNS locally and serves one page. It does not",
            "forward packets, proxy Nintendo services, or capture credentials.",
        ]
    )
    return "\n".join(lines)


def dns_query(name: str, qtype: int = 1) -> bytes:
    question = (
        b"".join(
            bytes([len(part)]) + part.encode("ascii") for part in name.split(".")
        )
        + b"\x00"
    )
    return (
        b"\x12\x34"
        + struct.pack("!HHHHH", 0x0100, 1, 0, 0, 0)
        + question
        + struct.pack("!HH", qtype, 1)
    )


def site_local_test(
    portal, entry_query: str | None = None
) -> tuple[bool, str]:
    """Exercise static-site serving and traversal protection on loopback."""

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "site"
        root.mkdir()
        (root / "index.html").write_text(
            '<!doctype html><script type="module" src="./mod.mjs"></script>',
            encoding="utf-8",
        )
        (root / "mod.mjs").write_text("export const answer = 42;\n", encoding="utf-8")
        (Path(directory) / "secret.txt").write_text("secret\n", encoding="utf-8")
        log_path = Path(directory) / "site.jsonl"
        log = portal.make_logger(log_path, echo=False)
        httpd = portal.HttpServer(
            ("127.0.0.1", 0),
            portal.Handler,
            "127.0.0.1",
            log,
            None,
            None,
            root,
            entry_query,
        )
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        port = httpd.server_address[1]

        def get(path: str):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            try:
                conn.request("GET", path)
                response = conn.getresponse()
                return response.status, dict(response.getheaders()), response.read()
            finally:
                conn.close()

        try:
            status, headers, _ = get("/")
            expected = "/portal"
            if entry_query:
                expected += "?" + entry_query.lstrip("?")
            if status != 302 or not headers.get("Location", "").endswith(expected):
                return False, "site redirect query"
            status, _, body = get("/portal")
            if status != 200 or b"mod.mjs" not in body:
                return False, "site index"
            status, headers, body = get("/mod.mjs")
            if status != 200 or not headers.get("Content-Type", "").startswith(
                "text/javascript"
            ):
                return False, "module MIME type"
            if b"42" not in body:
                return False, "module body"
            status, _, _ = get("/../secret.txt")
            if status != 404:
                return False, "path traversal"
            status, _, _ = get("/.git/config")
            if status != 404:
                return False, "dotfile blocking"
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            try:
                conn.request(
                    "POST",
                    "/fp",
                    body=b'{"event":"site-selftest"}',
                    headers={"Content-Type": "application/json"},
                )
                response = conn.getresponse()
                response.read()
            finally:
                conn.close()
            if response.status != 204:
                return False, "site fingerprint POST"
            entries = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if not any(entry.get("served") == "site" for entry in entries):
                return False, "site request not logged"
            return True, f"site HTTP 127.0.0.1:{port}"
        finally:
            httpd.shutdown()
            httpd.server_close()


def local_test(args: argparse.Namespace) -> int:
    """Exercise DNS and HTTP on loopback high ports, without root."""

    portal = load_portal()
    with tempfile.TemporaryDirectory() as directory:
        log_path = Path(directory) / "selftest.jsonl"
        log = portal.make_logger(log_path, echo=False)
        dns = portal.DnsServer("127.0.0.1", 0, "127.0.0.1", log)
        httpd = portal.HttpServer(
            ("127.0.0.1", 0),
            portal.Handler,
            "127.0.0.1",
            log,
            args.page,
            args.assets,
        )
        dns.start()
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        dns_port = dns.sock.getsockname()[1]
        http_port = httpd.server_address[1]
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            try:
                sock.sendto(
                    dns_query("ctest.cdn.nintendo.net"),
                    ("127.0.0.1", dns_port),
                )
                response, _ = sock.recvfrom(2048)
            finally:
                sock.close()
            if response[-4:] != socket.inet_aton("127.0.0.1"):
                print("local self-test: FAIL (unexpected DNS answer)", file=sys.stderr)
                return 1

            conn = http.client.HTTPConnection("127.0.0.1", http_port, timeout=3)
            try:
                conn.request("GET", "/portal")
                page_response = conn.getresponse()
                body = page_response.read()
            finally:
                conn.close()
            if page_response.status != 200 or b"/fp" not in body:
                print("local self-test: FAIL (portal page)", file=sys.stderr)
                return 1

            conn = http.client.HTTPConnection("127.0.0.1", http_port, timeout=3)
            try:
                conn.request(
                    "POST",
                    "/fp",
                    body=b'{"event":"selftest"}',
                    headers={"Content-Type": "application/json"},
                )
                post_response = conn.getresponse()
                post_response.read()
            finally:
                conn.close()
            if post_response.status != 204:
                print("local self-test: FAIL (fingerprint POST)", file=sys.stderr)
                return 1

            entries = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if not any(entry.get("event") == "dns" for entry in entries):
                print("local self-test: FAIL (DNS not logged)", file=sys.stderr)
                return 1
            if not any(
                entry.get("event") == "http"
                and entry.get("fingerprint", {}).get("event") == "selftest"
                for entry in entries
            ):
                print("local self-test: FAIL (POST not logged)", file=sys.stderr)
                return 1

            print("page self-test: PASS")
            print(f"  DNS  127.0.0.1:{dns_port}")
            print(f"  HTTP 127.0.0.1:{http_port}")
            print(f"  log entries: {len(entries)}")
        finally:
            httpd.shutdown()
            httpd.server_close()
            dns.sock.close()

    ok, message = site_local_test(portal, "autorun=1")
    if not ok:
        print(f"local self-test: FAIL ({message})", file=sys.stderr)
        return 1
    print("site self-test: PASS")
    print(f"  {message}")
    print("local self-test: PASS")
    return 0


def run_session(args: argparse.Namespace) -> int:
    portal = load_portal()
    answer_ip = args.answer_ip
    bind_host = args.bind
    log_path = args.log or default_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = portal.make_logger(log_path, echo=True)
    log(
        {
            "event": "session_start",
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "answer_ip": answer_ip,
            "bind": bind_host,
            "dns_port": args.dns_port,
            "http_port": args.http_port,
            "page": str(args.page),
            "site": str(args.site) if args.site is not None else None,
            "entry_query": args.entry_query,
            "duration": args.duration,
        }
    )

    try:
        dns = portal.DnsServer(bind_host, args.dns_port, answer_ip, log)
    except OSError as exc:
        print(f"cannot bind DNS {bind_host}:{args.dns_port}: {exc}", file=sys.stderr)
        return 1
    try:
        httpd = portal.HttpServer(
            (bind_host, args.http_port),
            portal.Handler,
            answer_ip,
            log,
            args.page,
            args.assets,
            args.site,
            args.entry_query,
        )
    except OSError as exc:
        print(
            f"cannot bind HTTP {bind_host}:{args.http_port}: {exc}",
            file=sys.stderr,
        )
        return 1

    dns.start()
    print(
        render_runbook(
            answer_ip,
            args.dns_port,
            args.http_port,
            args.page,
            log_path,
            args.duration,
            bind_host,
            args.site,
            args.entry_query,
        ),
        flush=True,
    )

    timer = None
    if args.duration:
        timer = threading.Timer(args.duration, httpd.shutdown)
        timer.daemon = True
        timer.start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if timer is not None:
            timer.cancel()
        httpd.server_close()
        log(
            {
                "event": "session_end",
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        print(f"log: {log_path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the local WebKit captive-portal assessment page.",
    )
    parser.add_argument("--page", type=Path, default=DEFAULT_PAGE)
    parser.add_argument("--assets", type=Path, default=None)
    parser.add_argument(
        "--site",
        type=Path,
        default=None,
        help="Serve a static site at /portal and its files at the URL root.",
    )
    parser.add_argument(
        "--entry-query",
        default=None,
        help="Query string appended to the /portal redirect in site mode.",
    )
    parser.add_argument(
        "--bind",
        default=None,
        help="Address to bind; defaults to the Mac LAN address.",
    )
    parser.add_argument("--answer-ip", default=None)
    parser.add_argument("--dns-port", type=int, default=53)
    parser.add_argument("--http-port", type=int, default=80)
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--duration", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--local-test", action="store_true")
    args = parser.parse_args(argv)

    if args.local_test:
        return local_test(args)

    if args.site is not None:
        args.site = args.site.resolve()
        if args.assets is not None:
            print("--site cannot be combined with --assets", file=sys.stderr)
            return 1
        if args.page != DEFAULT_PAGE:
            print("--site cannot be combined with --page", file=sys.stderr)
            return 1
        args.page = args.site / "index.html"

    try:
        answer_ip = args.answer_ip or lan_ip()
    except OSError as exc:
        print(f"cannot determine the Mac LAN address: {exc}", file=sys.stderr)
        return 1
    bind_host = args.bind or answer_ip
    args.answer_ip = answer_ip
    args.bind = bind_host

    errors, notes = preflight(args, bind_host)
    if answer_ip.startswith("127."):
        errors.append(
            "the Mac LAN address is loopback; join the Mac and console to the "
            "same Wi-Fi network"
        )
    log_path = args.log or default_log_path()
    print(
        render_runbook(
            answer_ip,
            args.dns_port,
            args.http_port,
            args.page,
            log_path,
            args.duration,
            bind_host,
            args.site,
            args.entry_query,
        )
    )
    for note in notes:
        print(f"note: {note}")
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    if args.dry_run:
        print("dry run: no server started")
        return 0
    return run_session(args)


if __name__ == "__main__":
    raise SystemExit(main())
