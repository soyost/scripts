#!/usr/bin/env python3

import re
from pathlib import Path
from getpass import getpass
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

INVENTORY_FILE = "inventory.txt"
RESULTS_FILE = "versions.csv"

DEVICE_TYPES = ["cisco_nxos", "cisco_xe", "cisco_ios"]

def parse_version(output, device_type):
    data = {
        "os": device_type,
        "version": "UNKNOWN",
        "platform": "UNKNOWN",
        "uptime": "UNKNOWN"
    }

    if device_type in ("cisco_ios", "cisco_xe"):
        if match := re.search(r"Version ([\w\.\(\)]+)", output):
            data["version"] = match.group(1)
        if match := re.search(r"Model Number\s+:\s+(\S+)", output):
            data["platform"] = match.group(1)
        if match := re.search(r"uptime is (.+)", output):
            data["uptime"] = match.group(1)

    elif device_type == "cisco_nxos":
        if match := re.search(
            r"NXOS:\s+version\s+([\w\.\(\)]+)",
            output,
            re.IGNORECASE
    ):
            data["version"] = match.group(1)
    if match := re.search(
            r"cisco\s+(Nexus\d+\s+\S+)\s+chassis",
            output,
            re.IGNORECASE
    ):
            data["platform"] = match.group(1)
    if match := re.search(
            r"uptime is (.+)",
            output,
            re.IGNORECASE
    ):
            data["uptime"] = match.group(1)
    return data


def main():
    hosts = Path(INVENTORY_FILE).read_text().splitlines()
    Path(RESULTS_FILE).write_text("host,os,platform,version,uptime\n")

    username = input("SSH username: ")
    password = getpass("SSH password: ")

    for host in hosts:
        for device_type in DEVICE_TYPES:
            try:
                conn = ConnectHandler(
                    host=host,
                    username=username,
                    password=password,
                    device_type=device_type,
                )
                output = conn.send_command("show version")
                data = parse_version(output, device_type)

                if data["version"] != "UNKNOWN":
                    with open(RESULTS_FILE, "a") as f:
                        f.write(
                            f"{host},{device_type},{data['platform']},{data['version']},{data['uptime']}\n"
                        )
                    conn.disconnect()
                    print(f"{host}: detected as {device_type}")
                    break

                conn.disconnect()

            except (NetmikoTimeoutException, NetmikoAuthenticationException):
                continue
            except Exception as e:
                print(f"{host}: error - {e}")
                break

        else:
            print(f"{host}: unable to determine OS")


if __name__ == "__main__":
    main()
