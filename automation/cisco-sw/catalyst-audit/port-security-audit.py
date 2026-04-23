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

DEVICE_TYPE = "cisco_ios"


def csv_escape(value):
    return str(value).replace('"', '""')


def parse_version(output):
    data = {
        "platform": "UNKNOWN",
        "current_os": "UNKNOWN",
    }

    if match := re.search(r"Version\s+([\w\.\(\)]+)", output):
        data["current_os"] = match.group(1)

    if match := re.search(r"Model Number\s+:\s+(\S+)", output):
        data["platform"] = match.group(1)

    return data


def is_physical_interface(interface_name):
    physical_prefixes = (
        "FastEthernet",
        "GigabitEthernet",
        "TenGigabitEthernet",
        "TwentyFiveGigE",
        "FortyGigabitEthernet",
        "HundredGigE",
    )
    return interface_name.startswith(physical_prefixes)


def parse_interface_blocks(config_text):
    interfaces = {}
    current_interface = None
    current_lines = []

    for raw_line in config_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("interface "):
            if current_interface:
                interfaces[current_interface] = current_lines
            current_interface = stripped[len("interface "):].strip()
            current_lines = []
            continue

        if stripped == "!" and current_interface:
            interfaces[current_interface] = current_lines
            current_interface = None
            current_lines = []
            continue

        if current_interface:
            current_lines.append(stripped)

    if current_interface:
        interfaces[current_interface] = current_lines

    return interfaces


def extract_description(lines):
    for line in lines:
        if line.lower().startswith("description "):
            return line[len("description "):].strip()
    return ""


def audit_interfaces_missing_security(conn):
    output = conn.send_command("show running-config | section ^interface")
    interface_blocks = parse_interface_blocks(output)

    results = []

    for interface, lines in interface_blocks.items():
        if not is_physical_interface(interface):
            continue

        normalized = [line.lower() for line in lines]

        mab_enabled = any(line == "mab" for line in normalized)
        port_security_enabled = any(
            line.startswith("switchport port-security")
            for line in normalized
        )
        shutdown = any(line == "shutdown" for line in normalized)

        if shutdown:
            continue
        
        if mab_enabled or port_security_enabled:
            continue

        results.append(
            {
                "interface": interface,
                "description": extract_description(lines),
            }
        )

    return results


def main():
    hosts = [
        h.strip()
        for h in Path(INVENTORY_FILE).read_text().splitlines()
        if h.strip() and not h.startswith("#")
    ]

    username = input("SSH username: ").strip()
    password = getpass("SSH password: ")

    headers = [
        "host",
        "chassis",
        "current_os",
        "interface",
        "description",
    ]

    Path(RESULTS_FILE).write_text(
        ",".join(headers) + "\n",
        encoding="utf-8",
    )

    for host in hosts:
        print(f"{host}: connecting")
        conn = None

        try:
            conn = ConnectHandler(
                host=host,
                username=username,
                password=password,
                device_type=DEVICE_TYPE,
            )

            version_output = conn.send_command("show version")
            data = parse_version(version_output)

            missing_security = audit_interfaces_missing_security(conn)

            with open(RESULTS_FILE, "a", encoding="utf-8") as f:
                for item in missing_security:
                    row = [
                        host,
                        data["platform"],
                        data["current_os"],
                        item["interface"],
                        f"\"{csv_escape(item['description'])}\"",
                    ]
                    f.write(",".join(row) + "\n")

            print(
                f"{host}: found {len(missing_security)} interfaces missing both "
                f"MAB and port-security"
            )

            conn.disconnect()

        except (
            NetmikoTimeoutException,
            NetmikoAuthenticationException,
            SSHException,
            OSError,
        ) as e:
            print(f"{host}: connection failed - {e}")
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass

        except Exception as e:
            print(f"{host}: ERROR - {e}")
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass


if __name__ == "__main__":
    main()