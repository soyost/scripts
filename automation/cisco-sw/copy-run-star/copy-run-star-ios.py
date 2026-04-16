#!/usr/bin/env python3

import csv
import getpass
import re
from datetime import datetime
from pathlib import Path

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException


INVENTORY_FILE = "ios-inventory.txt"
OUTPUT_FILE = "ios_results.csv"
DEVICE_TYPE = "cisco_ios"

CSV_COLUMNS = [
    "host",
    "status",
    "timestamp",
    "device_hostname",
    "device_clock",
    "proof",
    "error",
]


def read_inventory(filename):
    devices = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            devices.append(line)
    return devices


def clean_text(text):
    if text is None:
        return ""
    return " ".join(str(text).split())


def load_existing_results(csv_file):
    results = {}

    path = Path(csv_file)
    if not path.exists():
        return results

    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            host = row.get("host", "").strip()
            if host:
                results[host] = {col: row.get(col, "") for col in CSV_COLUMNS}

    return results


def write_results(csv_file, results):
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for host in sorted(results.keys()):
            writer.writerow(results[host])


def extract_hostname(connection):
    output = connection.send_command(
        "show run | include ^hostname",
        strip_prompt=True,
        strip_command=True,
    )
    match = re.search(r"hostname\s+(\S+)", output)
    if match:
        return match.group(1)
    return clean_text(output)


def get_device_clock(connection):
    output = connection.send_command(
        "show clock",
        strip_prompt=True,
        strip_command=True,
    )
    return clean_text(output)


def run_save_config(connection):
    """
    Runs 'copy running-config startup-config' and handles the interactive prompt.
    Returns:
        full_output (str)
        proof (str)
        success (bool)
    """
    full_output = ""

    output1 = connection.send_command_timing(
        "copy running-config startup-config",
        strip_prompt=False,
        strip_command=False,
        cmd_verify=False,
        delay_factor=2,
    )
    full_output += output1

    if (
        "Destination filename" in output1
        or "destination filename" in output1
        or "]?" in output1
    ):
        output2 = connection.send_command_timing(
            "\n",
            strip_prompt=False,
            strip_command=False,
            cmd_verify=False,
        )
        full_output += output2

    output3 = connection.send_command_timing(
        "\n",
        strip_prompt=False,
        strip_command=False,
        cmd_verify=False,
    )
    full_output += output3

    proof_lines = []
    for line in full_output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if (
            "Destination filename" in stripped
            or "Building configuration" in stripped
            or "[OK]" in stripped
            or "Copy complete" in stripped
            or "bytes copied" in stripped
        ):
            proof_lines.append(stripped)

    success_patterns = [
        r"\[OK\]",
        r"Building configuration",
        r"Copy complete",
        r"bytes copied",
    ]
    success = any(re.search(pattern, full_output, re.IGNORECASE) for pattern in success_patterns)

    proof = " | ".join(proof_lines)
    if not proof:
        proof = clean_text(full_output)

    return full_output, proof, success


def main():
    inventory = read_inventory(INVENTORY_FILE)
    if not inventory:
        print("No devices found in inventory.")
        return

    existing_results = load_existing_results(OUTPUT_FILE)

    username = input("SSH username: ").strip()
    password = getpass.getpass("SSH password: ")

    for host in inventory:
        print(f"{host}: connecting")

        row = {
            "host": host,
            "status": "",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "device_hostname": "",
            "device_clock": "",
            "proof": "",
            "error": "",
        }

        device = {
            "device_type": DEVICE_TYPE,
            "host": host,
            "username": username,
            "password": password,
            "fast_cli": False,
        }

        try:
            conn = ConnectHandler(**device)
            conn.enable()

            try:
                row["device_hostname"] = extract_hostname(conn)
            except Exception as e:
                row["error"] = clean_text(f"Hostname check failed: {e}")

            try:
                row["device_clock"] = get_device_clock(conn)
            except Exception as e:
                if row["error"]:
                    row["error"] += f" | Show clock failed: {clean_text(e)}"
                else:
                    row["error"] = clean_text(f"Show clock failed: {e}")

            _, proof, success = run_save_config(conn)
            row["proof"] = proof
            row["status"] = "SUCCESS" if success else "CHECK LOGIC"

            conn.disconnect()
            print(f"{host}: {row['status']}")

        except NetmikoAuthenticationException as e:
            row["status"] = "AUTH FAILURE"
            row["error"] = clean_text(e)
            print(f"{host}: AUTH FAILURE")

        except NetmikoTimeoutException as e:
            row["status"] = "TIMEOUT"
            row["error"] = clean_text(e)
            print(f"{host}: TIMEOUT")

        except Exception as e:
            row["status"] = "ERROR"
            row["error"] = clean_text(e)
            print(f"{host}: ERROR")

        existing_results[host] = row

    write_results(OUTPUT_FILE, existing_results)
    print(f"\nDone. Results written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()