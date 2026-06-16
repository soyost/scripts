#!/usr/bin/env python3

import csv
import re
from pathlib import Path
from getpass import getpass
from datetime import datetime

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)
from paramiko.ssh_exception import SSHException


INVENTORY_FILE = "inventory.txt"
RESULTS_FILE = "audit-results.csv"

DEVICE_TYPES = ["cisco_xe", "cisco_ios", "cisco_nxos"]


def clean_text(text):
    if text is None:
        return ""
    return " ".join(str(text).split())


def human_readable_bytes(num_bytes):
    for unit in ["bytes", "KiB", "MiB", "GiB", "TiB", "PiB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.2f} EiB"


def read_inventory(filename):
    return [
        line.strip()
        for line in Path(filename).read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def parse_version(output, device_type):
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

        if match := re.search(r"uptime is (.+)", output, re.IGNORECASE):
            data["uptime"] = match.group(1)

    return data


def parse_dir_info(conn):
    dir_output = conn.send_command("dir")

    free_space = "UNKNOWN"
    staged_versions = "NOT_FOUND"

    if match := re.search(r"(\d+)\s+bytes\s+free", dir_output, re.IGNORECASE):
        free_space = human_readable_bytes(int(match.group(1)))

    matches = re.findall(
        r"\.(\d+(?:\.\d+)+)\.SPA\.bin",
        dir_output,
        re.IGNORECASE,
    )

    if matches:
        staged_versions = "|".join(sorted(set(matches)))

    return free_space, staged_versions


def parse_connected_interfaces(conn):
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

    return len(results), " | ".join(results) if results else "NONE"


def save_running_config(conn):
    """
    Known-good copy run start logic.
    Handles the Destination filename prompt and returns status/proof.
    """
    full_output = ""

    output1 = conn.send_command_timing(
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
        output2 = conn.send_command_timing(
            "\n",
            strip_prompt=False,
            strip_command=False,
            cmd_verify=False,
        )
        full_output += output2

    output3 = conn.send_command_timing(
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

    success = any(
        re.search(pattern, full_output, re.IGNORECASE)
        for pattern in success_patterns
    )

    proof = " | ".join(proof_lines)
    if not proof:
        proof = clean_text(full_output)

    return "SUCCESS" if success else "CHECK LOGIC", proof


def backup_running_config(conn, host, scp_user, scp_password):
    scp_server = "10.79.253.15"
    vrf = "OAM"
    date_stamp = datetime.now().strftime("%Y_%m_%d")
    filename = f"{host}_{date_stamp}.txt"

    prompt_timeout = 5
    copy_timeout = 30

    command = (
        f"copy running-config "
        f"scp://{scp_user}@{scp_server}/{filename} "
        f"vrf {vrf}"
    )

    output = ""

    response = conn.send_command_timing(
        command,
        strip_prompt=False,
        strip_command=False,
        read_timeout=prompt_timeout,
    )
    output += response

    for _ in range(10):
        if "Address or name of remote host" in response:
            response = conn.send_command_timing(
                "",
                strip_prompt=False,
                strip_command=False,
                read_timeout=prompt_timeout,
            )

        elif "Destination username" in response:
            response = conn.send_command_timing(
                "",
                strip_prompt=False,
                strip_command=False,
                read_timeout=prompt_timeout,
            )

        elif "Destination filename" in response:
            response = conn.send_command_timing(
                "",
                strip_prompt=False,
                strip_command=False,
                read_timeout=prompt_timeout,
            )

        elif "Password:" in response:
            print(f"{host}: sending SCP password")
            response = conn.send_command_timing(
                scp_password,
                strip_prompt=False,
                strip_command=False,
                read_timeout=copy_timeout,
            )

        elif "bytes copied" in response:
            break

        else:
            response = conn.send_command_timing(
                "",
                strip_prompt=False,
                strip_command=False,
                read_timeout=prompt_timeout,
            )

        output += response

        if "bytes copied" in output:
            break

    success = bool(re.search(r"bytes copied", output, re.IGNORECASE))

    proof = clean_text(output)

    if success:
        return "SUCCESS", filename, proof

    return "CHECK LOGIC", filename, proof


def main():
    hosts = read_inventory(INVENTORY_FILE)

    if not hosts:
        print(f"No devices found in {INVENTORY_FILE}")
        return

    username = input("SSH username: ").strip()
    password = getpass("SSH password: ")

    check_uptime = input("Include uptime? (y/n): ").strip().lower() == "y"

    check_storage = (
        input("Include storage info (free space + staged images)? (y/n): ")
        .strip()
        .lower()
        == "y"
    )

    check_connected_ports = (
        input("Include connected ports? (y/n): ").strip().lower() == "y"
    )

    save_config = (
        input("Copy running-config to startup-config? (y/n): ")
        .strip()
        .lower()
        == "y"
    )

    run_backup = (
        input("Backup running-config to SCP? (y/n): ").strip().lower() == "y"
    )

    scp_user = ""
    scp_password = ""

    if run_backup:
        scp_user = input("SCP username: ").strip()
        scp_password = getpass("SCP password: ")

    headers = [
        "host",
        "status",
        "timestamp",
        "os",
        "chassis",
        "current_os",
    ]

    if check_uptime:
        headers.append("uptime")

    if check_storage:
        headers.extend(["free_space", "staged_versions"])

    if check_connected_ports:
        headers.extend(["connected_count", "connected_interfaces"])

    if save_config:
        headers.extend(["save_status", "save_proof"])

    if run_backup:
        headers.extend(["backup_status", "backup_filename", "backup_proof"])

    headers.append("error")

    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        for host in hosts:
            print(f"{host}: connecting")

            device_found = False
            last_error = ""

            for device_type in DEVICE_TYPES:
                conn = None

                row = {
                    "host": host,
                    "status": "",
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "os": device_type,
                    "chassis": "UNKNOWN",
                    "current_os": "UNKNOWN",
                    "error": "",
                }

                try:
                    conn = ConnectHandler(
                        host=host,
                        username=username,
                        password=password,
                        device_type=device_type,
                        fast_cli=False,
                    )

                    try:
                        conn.enable()
                    except Exception:
                        pass

                    version_output = conn.send_command("show version")
                    data = parse_version(version_output, device_type)

                    if data["current_os"] == "UNKNOWN":
                        conn.disconnect()
                        continue

                    device_found = True

                    row["status"] = "SUCCESS"
                    row["os"] = device_type
                    row["chassis"] = data["platform"]
                    row["current_os"] = data["current_os"]

                    if check_uptime:
                        row["uptime"] = data["uptime"]

                    if check_storage:
                        free_space, staged_versions = parse_dir_info(conn)
                        row["free_space"] = free_space
                        row["staged_versions"] = staged_versions

                    if check_connected_ports:
                        connected_count, connected_interfaces = (
                            parse_connected_interfaces(conn)
                        )
                        row["connected_count"] = connected_count
                        row["connected_interfaces"] = connected_interfaces

                    if save_config:
                        print(f"{host}: saving running-config")
                        save_status, save_proof = save_running_config(conn)
                        row["save_status"] = save_status
                        row["save_proof"] = save_proof

                    if run_backup:
                        print(f"{host}: backing up running-config to SCP")
                        backup_status, backup_filename, backup_proof = (
                            backup_running_config(
                                conn,
                                host,
                                scp_user,
                                scp_password,
                            )
                        )
                        row["backup_status"] = backup_status
                        row["backup_filename"] = backup_filename
                        row["backup_proof"] = backup_proof

                    writer.writerow(row)
                    f.flush()

                    print(f"{host}: detected as {device_type}")

                    conn.disconnect()
                    break

                except (
                    NetmikoTimeoutException,
                    NetmikoAuthenticationException,
                    SSHException,
                    OSError,
                ) as e:
                    last_error = clean_text(e)

                    if conn:
                        try:
                            conn.disconnect()
                        except Exception:
                            pass

                    continue

                except Exception as e:
                    row["status"] = "ERROR"
                    row["error"] = clean_text(e)
                    writer.writerow(row)
                    f.flush()

                    print(f"{host}: ERROR - {e}")

                    if conn:
                        try:
                            conn.disconnect()
                        except Exception:
                            pass

                    device_found = True
                    break

            if not device_found:
                row = {
                    "host": host,
                    "status": "UNREACHABLE_OR_UNKNOWN_PLATFORM",
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "os": "UNKNOWN",
                    "chassis": "UNKNOWN",
                    "current_os": "UNKNOWN",
                    "error": last_error,
                }

                writer.writerow(row)
                f.flush()

                print(f"{host}: unable to determine platform")

    print(f"\nDone. Results written to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()