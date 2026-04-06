#!/usr/bin/env python3
"""
Cisco switch utility: fetch IOS/IOS-XE version and (optionally) filesystem free space.

Dependencies:
  pip install netmiko

Examples:
  python cisco_info.py --host 10.1.1.10 --user admin --version
  python cisco_info.py --host 10.1.1.10 --user admin --space --fs flash:
  python cisco_info.py --host sw1.example.com --user admin --version --space --enable
"""

from __future__ import annotations

import re
import sys
import argparse
from getpass import getpass
from typing import Optional, Tuple

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException, ReadTimeout


VERSION_PATTERNS = [
    r"Cisco IOS XE Software,\s+Version\s+([^\s,]+)",
    r"Cisco IOS Software.*Version\s+([^\s,]+)",
    r"\bVersion\s+([^\s,]+)",
]


def extract_ios_version(show_version_output: str) -> Optional[str]:
    """
    Match common Cisco IOS / IOS XE version lines, for example:
    - Cisco IOS XE Software, Version 17.09.04a
    - Cisco IOS Software [Amsterdam], Catalyst L3 Switch Software ..., Version 15.2(7)E10
    """
    for pattern in VERSION_PATTERNS:
        match = re.search(pattern, show_version_output, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def extract_space_from_dir(output: str) -> Optional[Tuple[int, int]]:
    """
    Parse a 'dir <fs>:' output to get (bytes_free, bytes_total).

    Typical lines:
      32514048 bytes total (22265856 bytes free)

    Returns:
      (bytes_free, bytes_total) if found, else None
    """
    # Look for: "<total> bytes total (<free> bytes free)"
    m = re.search(r"(\d+)\s+bytes\s+total\s*\(\s*(\d+)\s+bytes\s+free\)", output, re.IGNORECASE)
    if m:
        total = int(m.group(1))
        free = int(m.group(2))
        return free, total
    return None


def extract_space_from_show_file_systems(output: str, filesystem: str) -> Optional[Tuple[int, int]]:
    """
    Parse 'show file systems' to derive free/total for a given filesystem (e.g., 'flash:').

    Typical table contains:
      Filesystem      Size(b)   Free(b)  Type  Flags  Prefixes
      flash:          32514048  22265856 disk  rw     flash:

    Returns:
      (bytes_free, bytes_total) if found, else None
    """
    # Normalize target fs (ensure it ends with ':')
    if not filesystem.endswith(":"):
        filesystem = filesystem + ":"

    for line in output.splitlines():
        if line.strip().lower().startswith(filesystem.lower()):
            cols = re.split(r"\s+", line.strip())
            # Expect something like [fs, size, free, type, flags, ...]
            if len(cols) >= 3 and cols[1].isdigit() and cols[2].isdigit():
                total = int(cols[1])
                free = int(cols[2])
                return free, total
    return None


def human_bytes(n: int) -> str:
    """Simple human-readable bytes formatter."""
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(n)
    for u in units:
        if value < 1024.0:
            return f"{value:.2f} {u}"
        value /= 1024.0
    return f"{value:.2f} PB"


def run_commands(
    host: str,
    username: str,
    password: str,
    *,
    enable_secret: Optional[str] = None,
    port: int = 22,
    device_type: str = "cisco_ios",
    session_log: Optional[str] = None,
    conn_timeout: int = 10,
    global_delay_factor: float = 1.0,
) -> ConnectHandler:
    """
    Open a Netmiko connection and return the connection object.
    Caller is responsible for closing it (use context manager ideally).
    """
    device = {
        "device_type": device_type,
        "host": host,
        "username": username,
        "password": password,
        "port": port,
        "fast_cli": False,  # safer defaults
        "timeout": conn_timeout,
        "conn_timeout": conn_timeout,
        "global_delay_factor": global_delay_factor,
        "session_log": session_log,
    }
    if enable_secret:
        device["secret"] = enable_secret

    conn = ConnectHandler(**device)

    # Enter enable mode if secret provided (or if device prompts and we have it)
    if enable_secret:
        try:
            conn.enable()
        except Exception:
            # Some devices don't require it; ignore if already privileged
            pass

    # Disable paging
    try:
        conn.send_command("terminal length 0", expect_string=r"#|>", strip_prompt=False, strip_command=False)
    except Exception:
        # Not fatal; continue
        pass

    return conn


def do_show_version(conn: ConnectHandler) -> Optional[str]:
    output = conn.send_command("show version", expect_string=r"#|>", strip_prompt=False, strip_command=False)
    return extract_ios_version(output)


def do_space(conn: ConnectHandler, filesystem: str = "flash:") -> Optional[Tuple[int, int]]:
    """
    Try 'dir <filesystem>' first; if not parseable, fall back to 'show file systems'.
    Returns (bytes_free, bytes_total) or None.
    """
    # Try "dir"
    try:
        out_dir = conn.send_command(f"dir {filesystem}", expect_string=r"#|>", strip_prompt=False, strip_command=False)
        parsed = extract_space_from_dir(out_dir)
        if parsed:
            return parsed
    except ReadTimeout:
        pass
    except Exception:
        # fall through to show file systems
        pass

    # Fallback: show file systems
    try:
        out_fs = conn.send_command("show file systems", expect_string=r"#|>", strip_prompt=False, strip_command=False)
        parsed = extract_space_from_show_file_systems(out_fs, filesystem)
        if parsed:
            return parsed
    except Exception:
        pass

    return None


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Cisco utility to print IOS/IOS-XE version and filesystem space.")
    p.add_argument("--host", required=True, help="Switch IP or hostname")
    p.add_argument("--user", required=True, help="SSH username")
    p.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    p.add_argument("--device-type", default="cisco_ios", help="Netmiko device_type (default: cisco_ios)")
    p.add_argument("--session-log", default=None, help="Path to session log file (optional)")

    # actions
    p.add_argument("--version", action="store_true", help="Print software version")
    p.add_argument("--space", action="store_true", help="Print filesystem free/total")
    p.add_argument("--fs", default="flash:", help="Filesystem to inspect for --space (default: flash:)")

    # timeouts/delays
    p.add_argument("--timeout", type=int, default=10, help="Connection timeout seconds (default: 10)")
    p.add_argument("--delay-factor", type=float, default=1.0, help="Netmiko global delay factor (default: 1.0)")

    # privilege
    p.add_argument("--enable", action="store_true", help="Prompt for enable secret and enter enable mode")

    return p


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if not args.version and not args.space:
        print("Nothing to do. Use --version and/or --space.", file=sys.stderr)
        sys.exit(2)

    password = getpass("SSH Password: ")
    enable_secret = getpass("Enable Secret: ") if args.enable else None

    try:
        with run_commands(
            host=args.host,
            username=args.user,
            password=password,
            enable_secret=enable_secret,
            port=args.port,
            device_type=args.device_type,
            session_log=args.session_log,
            conn_timeout=args.timeout,
            global_delay_factor=args.delay_factor,
        ) as conn:

            if args.version:
                ver = do_show_version(conn)
                if ver:
                    print(ver)
                else:
                    print("Could not find a software version in 'show version' output.", file=sys.stderr)

            if args.space:
                result = do_space(conn, filesystem=args.fs)
                if result:
                    free, total = result
                    used = total - free
                    print(
                        f"{args.fs} total={total} ({human_bytes(total)}), "
                        f"used={used} ({human_bytes(used)}), "
                        f"free={free} ({human_bytes(free)})"
                    )
                else:
                    print(f"Could not determine free/total space for filesystem '{args.fs}'.", file=sys.stderr)

    except NetmikoAuthenticationException:
        print("Authentication failed.", file=sys.stderr)
        sys.exit(1)
    except NetmikoTimeoutException:
        print("Connection timed out.", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()