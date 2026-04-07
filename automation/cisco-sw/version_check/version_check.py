#!/usr/bin/env python3

import re
from pathlib import Path
from getpass import getpass
from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)

INVENTORY_FILE = "inventory.txt"
RESULTS_FILE = "versions.csv"

DEVICE_TYPES = ["cisco_nxos", "cisco_xe", "cisco_ios"]


def human_readable_bytes(num_bytes):
    """Convert bytes to human-readable format (GiB, TiB, etc.)"""
    for unit in ["bytes", "KiB", "MiB", "GiB", "TiB", "PiB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.2f} EiB"


def parse_version(output, device_type):
    """Parse show version output into normalized fields"""
    data = {
        "os": device_type,
        "platform": "UNKNOWN",
        "version": "UNKNOWN",
        "uptime": "UNKNOWN",
    }

    if device_type in ("cisco_ios", "cisco_xe"):
        if match := re.search(r"Version\s+([\w\.\(\)]+)", output):
            data["version"] = match.group(1)

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
            data["version"] = match.group(1)

        if match := re.search(
            r"cisco\s+(Nexus\d+\s+\S+)\s+chassis",
            output,
            re.IGNORECASE,
        ):
            data["platform"] = match.group(1)

        if match := re.search(
            r"uptime is (.+)", output, re.IGNORECASE
        ):
            data["uptime"] = match.group(1)

    return data


def parse_free_space(conn):
    """Run 'dir' and extract free bytes"""
    dir_output = conn.send_command("dir")
    if match := re.search(
        r"(\d+)\s+bytes\s+free",
        dir_output,
        re.IGNORECASE,
    ):
        bytes_free = int(match.group(1))
        return human_readable_bytes(bytes_free)
    return "UNKNOWN"


def main():
    hosts = [
        h.strip()
        for h in Path(INVENTORY_FILE).read_text().splitlines()
        if h.strip() and not h.startswith("#")
    ]

    # Write CSV header (overwrite file)
    Path(RESULTS_FILE).write_text(
        "host,os,chassis,version,uptime,free_space\n",
        encoding="utf-8",
    )

    username = input("SSH username: ").strip()
    password = getpass("SSH password: ")

    for host in hosts:
        print(f"{host}: connecting")

        for device_type in DEVICE_TYPES:
            try:
                conn = ConnectHandler(
                    host=host,
                    username=username,
                    password=password,
                    device_type=device_type,
                )

                version_output = conn.send_command("show version")
                data = parse_version(version_output, device_type)

                if data["version"] != "UNKNOWN":
                    free_space = parse_free_space(conn)

                    with open(RESULTS_FILE, "a", encoding="utf-8") as f:
                        f.write(
                            f"{host},{device_type},"
                            f"{data['platform']},"
                            f"{data['version']},"
                            f"\"{data['uptime']}\","
                            f"{free_space}\n"
                        )

                    conn.disconnect()
                    print(f"{host}: detected as {device_type}")
                    break

                conn.disconnect()

            except (NetmikoTimeoutException, NetmikoAuthenticationException):
                continue
            except Exception as e:
                print(f"{host}: ERROR - {e}")
                break

        else:
            print(f"{host}: unable to determine platform")


if __name__ == "__main__":
    main()