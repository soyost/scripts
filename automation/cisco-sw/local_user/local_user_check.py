#!/usr/bin/env python3

import logging
from pathlib import Path
from getpass import getpass

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)

INVENTORY_FILE = "inventory.txt"
LOG_FILE = "user_check.log"

DEVICE_TYPE = "cisco_ios"   # Change if needed
TARGET_USER = "steven"
RESULTS_FILE = "results.txt"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )


def write_result(line):
    with open(RESULTS_FILE, "a") as f:
        f.write(line + "\n")

def load_inventory(filename):
    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"Inventory file not found: {filename}")

    devices = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        devices.append(line)

    return devices


def user_exists(output, username):
    target = f"username {username}".lower()
    for line in output.splitlines():
        if target in line.lower():
            return True
    return False


def check_user(conn, host):
    output = conn.send_command("show run | include ^username")

    matches = [
        line.strip()
        for line in output.splitlines()
        if f"username {TARGET_USER}".lower() in line.lower()
    ]

    if matches:
        result = f"{host},EXISTS"
        logging.info(f"{host}: user '{TARGET_USER}' PRESENT")
    else:
        result = f"{host},NOT_FOUND"
        logging.info(f"{host}: user '{TARGET_USER}' MISSING")

    write_result(result)


def main():
    setup_logging()
    open(RESULTS_FILE, "w").close()

    try:
        devices = load_inventory(INVENTORY_FILE)
    except Exception as e:
        logging.error(f"Failed to load inventory: {e}")
        return

    if not devices:
        logging.warning("No devices found in inventory.txt")
        return

    ssh_username = input("SSH username: ").strip()
    ssh_password = getpass("SSH password: ")
    enable_secret = getpass("Enable secret (press Enter if not needed): ")

    logging.info(f"Loaded {len(devices)} devices from {INVENTORY_FILE}")

    for host in devices:
        logging.info(f"{host}: connecting")

        device = {
            "device_type": DEVICE_TYPE,
            "host": host,
            "username": ssh_username,
            "password": ssh_password,
        }

        if enable_secret:
            device["secret"] = enable_secret

        try:
            conn = ConnectHandler(**device)

            if enable_secret:
                conn.enable()

            check_user(conn, host)
            conn.disconnect()

        except NetmikoAuthenticationException:
            logging.error(f"{host}: authentication failed")
        except NetmikoTimeoutException:
            logging.error(f"{host}: connection timed out")
        except Exception as e:
            logging.error(f"{host}: unexpected error: {e}")


if __name__ == "__main__":
    main()