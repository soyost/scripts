#!/usr/bin/env python3

import csv
import getpass
import re
from datetime import datetime
from pathlib import Path

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException


INVENTORY_FILE = "nxos-inventory.txt"
OUTPUT_FILE = "nxos_results.csv"
DEVICE_TYPE = "cisco_nxos"

CSV_COLUMNS = [
    "host",
    "status",
    "timestamp",
    "device_hostname",
    "device_clock",
    "proof",
    "error",
]


# ---------------- Inventory ----------------

def read_inventory(filename):
    devices = []
    path = Path(filename)

    if not path.exists():
        return devices

    with open(path, "r", encoding="utf-8") as f:
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


# ---------------- CSV Helpers ----------------

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


# ---------------- Device Info ----------------

def extract_hostname(connection):
    output = connection.send_command(
        "show hostname",
        strip_prompt=True,
        strip_command=True,
    )
    return clean_text(output)


def get_device_clock(connection):
    output = connection.send_command(
        "show clock",
        strip_prompt=True,
        strip_command=True,
    )
    return clean_text(output)


# ---------------- NX‑OS Save Config ----------------

def run_save_config(connection):
    """
    NX-OS save config:
    - Waits for disk-save confirmation
    - Success = disk-save OR final 'Copy complete.'
    - Proof prefers final confirmation when available
    """
    import time
    import re

    full_output = ""

    # Start the copy operation
    output = connection.send_command_timing(
        "copy running-config startup-config",
        strip_prompt=False,
        strip_command=False,
        cmd_verify=False,
        delay_factor=2,
    )
    full_output += output

    # Patterns
    error_patterns = [
        r"%Error",
        r"failed",
        r"Invalid",
        r"Permission denied",
        r"No space",
        r"not allowed",
    ]

    disk_save_pattern = r"now saving to disk"
    final_copy_pattern = r"\bCopy complete\.\b"

    # Drain output until we see success state, error, or timeout
    start_time = time.time()
    timeout = 20  # seconds

    while time.time() - start_time < timeout:
        # Stop immediately if an error appears
        if any(re.search(p, full_output, re.IGNORECASE) for p in error_patterns):
            break

        # Stop once we see disk-save or final completion
        if (
            re.search(disk_save_pattern, full_output, re.IGNORECASE)
            or re.search(final_copy_pattern, full_output, re.IGNORECASE)
        ):
            break

        # Read more output
        output = connection.send_command_timing(
            "",
            strip_prompt=False,
            strip_command=False,
        )

        if output:
            full_output += output
        else:
            time.sleep(0.5)

    # ---- Final evaluation ----
    has_error = any(
        re.search(p, full_output, re.IGNORECASE)
        for p in error_patterns
    )

    has_success = (
        re.search(disk_save_pattern, full_output, re.IGNORECASE)
        or re.search(final_copy_pattern, full_output, re.IGNORECASE)
    )

    success = bool(has_success and not has_error)

    # ---- Proof output (prefer strongest confirmation) ----
    final_copy_lines = []
    disk_save_lines = []

    for line in full_output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if re.search(final_copy_pattern, stripped, re.IGNORECASE):
            final_copy_lines.append(stripped)
        elif re.search(disk_save_pattern, stripped, re.IGNORECASE):
            disk_save_lines.append(stripped)

    # Prefer final completion if NX-OS printed it
    if final_copy_lines:
        proof = " | ".join(final_copy_lines)
    elif disk_save_lines:
        proof = " | ".join(disk_save_lines)
    else:
        proof = " ".join(full_output.split())

    return full_output, proof, success


# ---------------- Main ----------------

def main():
    inventory = read_inventory(INVENTORY_FILE)
    if not inventory:
        print(f"No devices found in {INVENTORY_FILE}")
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

            # NX‑OS is already privileged
            conn.send_command("terminal length 0")

            try:
                row["device_hostname"] = extract_hostname(conn)
            except Exception as e:
                row["error"] = clean_text(f"Hostname check failed: {e}")

            try:
                row["device_clock"] = get_device_clock(conn)
            except Exception as e:
                msg = f"Show clock failed: {clean_text(e)}"
                row["error"] = f"{row['error']} | {msg}" if row["error"] else msg

            _, proof, success = run_save_config(conn)
            row["proof"] = proof
            row["status"] = "SUCCESS" if success else "ERROR"

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