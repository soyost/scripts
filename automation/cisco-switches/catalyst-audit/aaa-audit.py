#!/usr/bin/env python3

import csv
from pathlib import Path
from getpass import getpass

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException


INVENTORY_FILE = "inventory.txt"
RESULTS_FILE = "aaa-audit-results.csv"
DEVICE_TYPES = ["cisco_xe", "cisco_ios"]

ALLOWED_AAA_LINES = {
    "aaa authentication login default group TS_TACACS local",
    "aaa authentication login default group TS_TACACS local-case",
}


def read_inventory(filename):
    return [
        line.strip()
        for line in Path(filename).read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def audit_aaa_login(conn):
    output = conn.send_command(
        "show running-config | include ^aaa authentication login default",
        strip_prompt=True,
        strip_command=True,
    )

    lines = [line.strip() for line in output.splitlines() if line.strip()]

    for line in lines:
        if line in ALLOWED_AAA_LINES:
            return "COMPLIANT", line

    if not lines:
        return "MISSING", ""

    return "NONCOMPLIANT", " | ".join(lines)


def main():
    hosts = read_inventory(INVENTORY_FILE)

    username = input("SSH username: ").strip()
    password = getpass("SSH password: ")

    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["host", "status", "device_type", "aaa_login_default", "error"],
        )
        writer.writeheader()

        for host in hosts:
            print(f"{host}: connecting")

            row = {
                "host": host,
                "status": "",
                "device_type": "",
                "aaa_login_default": "",
                "error": "",
            }

            for device_type in DEVICE_TYPES:
                conn = None

                try:
                    conn = ConnectHandler(
                        host=host,
                        username=username,
                        password=password,
                        device_type=device_type,
                        fast_cli=False,
                    )

                    status, aaa_line = audit_aaa_login(conn)

                    row["status"] = status
                    row["device_type"] = device_type
                    row["aaa_login_default"] = aaa_line

                    conn.disconnect()

                    print(f"{host}: {status}")
                    break

                except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
                    row["error"] = str(e)
                    if conn:
                        conn.disconnect()
                    continue

                except Exception as e:
                    row["status"] = "ERROR"
                    row["error"] = str(e)
                    if conn:
                        conn.disconnect()
                    break

            if not row["status"]:
                row["status"] = "UNREACHABLE_OR_UNKNOWN_PLATFORM"

            writer.writerow(row)
            f.flush()

    print(f"\nDone. Results written to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()