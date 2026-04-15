#!/usr/bin/env python3

import re
from pathlib import Path
from getpass import getpass

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)
from paramiko.ssh_exception import SSHException

INVENTORY_FILE = "inventory.txt"
RESULTS_FILE = "audit-results.csv"

DEVICE_TYPES = ["cisco_xe", "cisco_ios", "cisco_nxos"]


def human_readable_bytes(num_bytes):
    """Convert bytes to human-readable format (GiB, TiB, etc.)"""
    for unit in ["bytes", "KiB", "MiB", "GiB", "TiB", "PiB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.2f} EiB"


def csv_escape(value):
    """Escape double quotes for safe CSV output"""
    return str(value).replace('"', '""')


def parse_version(output, device_type):
    """Parse show version output into normalized fields"""
    data = {
        "os": device_type,
        "platform": "UNKNOWN",
        "current_os": "UNKNOWN",
        "uptime": "UNKNOWN",
    }

    if device_type in ("cisco_ios", "cisco_xe"):
        if match := re.search(r"Version\s+([\w\.\(\)]+)", output):
            data["current_os"] = match.group(1)

        if match := re.search(r"Model Number\s+:\s+(\S+)", output):
            data["platform"] = match.group(1)

        if match := re.search(r"uptime is (.+)", output):
            data["uptime"] = match.group(1)

    elif device_type == "cisco_nxos":
        if match := re.search(
            r"NXOS:\s+version\s+([\w\.\(\)]+)",
            output,
            re.IGNORECASE,
        ):
            data["current_os"] = match.group(1)

        if match := re.search(
            r"cisco\s+(Nexus\d+\s+\S+)\s+chassis",
            output,
            re.IGNORECASE,
        ):
            data["platform"] = match.group(1)

        if match := re.search(
            r"uptime is (.+)",
            output,
            re.IGNORECASE,
        ):
            data["uptime"] = match.group(1)

    return data


def parse_dir_info(conn):
    """Run 'dir' and extract free space + all staged SPA.bin versions"""
    dir_output = conn.send_command("dir")

    free_space = "UNKNOWN"
    staged_versions = "NOT_FOUND"

    if match := re.search(
        r"(\d+)\s+bytes\s+free",
        dir_output,
        re.IGNORECASE,
    ):
        bytes_free = int(match.group(1))
        free_space = human_readable_bytes(bytes_free)

    matches = re.findall(
        r"\.(\d+(?:\.\d+)+)\.SPA\.bin",
        dir_output,
        re.IGNORECASE,
    )

    if matches:
        unique_versions = sorted(set(matches))
        staged_versions = "|".join(unique_versions)

    return free_space, staged_versions


def parse_connected_interfaces(conn):
    """Get connected interfaces as port:description"""
    output = conn.send_command("show interface status | include connected")

    results = []

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split("connected")
        if len(parts) < 2:
            continue

        left = parts[0].rstrip()
        tokens = left.split()

        if not tokens:
            continue

        interface = tokens[0]
        description = " ".join(tokens[1:]) if len(tokens) > 1 else ""

        if description:
            results.append(f"{interface}:{description}")
        else:
            results.append(interface)

    connected_count = len(results)
    connected_interfaces = " | ".join(results) if results else "NONE"

    return connected_count, connected_interfaces


def main():
    hosts = [
        h.strip()
        for h in Path(INVENTORY_FILE).read_text().splitlines()
        if h.strip() and not h.startswith("#")
    ]

    username = input("SSH username: ").strip()
    password = getpass("SSH password: ")

    check_uptime = input("Include uptime? (y/n): ").strip().lower() == "y"
    check_storage = input(
        "Include storage info (free space + staged images)? (y/n): "
    ).strip().lower() == "y"
    check_connected_ports = (
        input("Include connected ports? (y/n): ").strip().lower() == "y"
    )

    headers = ["host", "os", "chassis", "current_os"]

    if check_uptime:
        headers.append("uptime")
    if check_storage:
        headers.extend(["free_space", "staged_versions"])
    if check_connected_ports:
        headers.extend(["connected_count", "connected_interfaces"])

    Path(RESULTS_FILE).write_text(
        ",".join(headers) + "\n",
        encoding="utf-8",
    )

    for host in hosts:
        print(f"{host}: connecting")

        for device_type in DEVICE_TYPES:
            conn = None
            try:
                conn = ConnectHandler(
                    host=host,
                    username=username,
                    password=password,
                    device_type=device_type,
                )

                version_output = conn.send_command("show version")
                data = parse_version(version_output, device_type)

                if data["current_os"] != "UNKNOWN":
                    free_space = "SKIPPED"
                    staged_versions = "SKIPPED"
                    connected_count = "SKIPPED"
                    connected_interfaces = "SKIPPED"

                    if check_storage:
                        free_space, staged_versions = parse_dir_info(conn)

                    if check_connected_ports:
                        connected_count, connected_interfaces = (
                            parse_connected_interfaces(conn)
                        )

                    row = [
                        host,
                        device_type,
                        data["platform"],
                        data["current_os"],
                    ]

                    if check_uptime:
                        row.append(f"\"{csv_escape(data['uptime'])}\"")
                    if check_storage:
                        row.append(free_space)
                        row.append(staged_versions)
                    if check_connected_ports:
                        row.append(str(connected_count))
                        row.append(f"\"{csv_escape(connected_interfaces)}\"")

                    with open(RESULTS_FILE, "a", encoding="utf-8") as f:
                        f.write(",".join(row) + "\n")

                    print(f"{host}: detected as {device_type}")
                    conn.disconnect()
                    break

                conn.disconnect()

            except (
                NetmikoTimeoutException,
                NetmikoAuthenticationException,
                SSHException,
                OSError,
            ):
                if conn:
                    try:
                        conn.disconnect()
                    except Exception:
                        pass
                continue

            except Exception as e:
                print(f"{host}: ERROR - {e}")
                if conn:
                    try:
                        conn.disconnect()
                    except Exception:
                        pass
                break

        else:
            print(f"{host}: unable to determine platform")


if __name__ == "__main__":
    main()