from getpass import getpass
import argparse
import logging
from netmiko import ConnectHandler


INVENTORY_FILE = "inventory.txt"
LOG_FILE = "mac_route_update.log"

ROUTES = [
    {
        "dest_net": "10.79.172.0/24",
        "test_ip": "10.79.172.10",
        "gateway": "192.168.5.1",
    },
    {
        "dest_net": "10.79.69.0/24",
        "test_ip": "10.79.69.10",
        "gateway": "192.168.5.1",
    },
]

REMOTE_SCRIPT = "/usr/local/sbin/add-evo-routes.sh"
REMOTE_PLIST = "/Library/LaunchDaemons/com.company.evo-routes.plist"
LAUNCHD_LABEL = "com.company.evo-routes"


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def load_inventory(file_path):
    with open(file_path) as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]


def run_sudo(conn, sudo_password, command):
    output = conn.send_command_timing(
        f"sudo -S {command}",
        strip_prompt=False,
        strip_command=False,
        read_timeout=20,
    )

    if "password" in output.lower():
        output += conn.send_command_timing(
            sudo_password,
            strip_prompt=False,
            strip_command=False,
            read_timeout=20,
        )

    output += conn.send_command_timing(
        "",
        strip_prompt=False,
        strip_command=False,
        read_timeout=5,
    )

    return output


def route_present(conn, route):
    cmd = f"route -n get {route['test_ip']}"

    output = conn.send_command_timing(
        cmd,
        strip_prompt=False,
        strip_command=False,
        read_timeout=20,
    )

    expected = f"gateway: {route['gateway']}"
    return expected in output, output

def check_routes(conn, host):
    results = []

    for route in ROUTES:
        present, output = route_present(conn, route)

        if present:
            msg = f"{host} OK {route['dest_net']} via {route['gateway']}"
            print(msg)
            logging.info(msg)
        else:
            msg = f"{host} MISSING_OR_DIFFERENT {route['dest_net']} via {route['gateway']}"
            print(msg)
            logging.warning(f"{msg}\n{output}")

        results.append((route, present, output))

    return results


def add_missing_routes(conn, host, sudo_password):
    results = check_routes(conn, host)

    for route, present, _ in results:
        if present:
            continue

        cmd = f"route -n add -net {route['dest_net']} {route['gateway']}"
        msg = f"{host} ADDING {route['dest_net']} via {route['gateway']}"
        print(msg)
        logging.info(msg)

        output = run_sudo(conn, sudo_password, cmd)
        logging.info(f"{host} route add output for {route['dest_net']}:\n{output}")

    print(f"{host} verifying after add...")
    check_routes(conn, host)


def install_persistence(conn, host, sudo_password):
    route_script = """#!/bin/bash

ROUTES=(
"10.79.172.0/24 10.79.172.10 192.168.5.1"
"10.79.69.0/24 10.79.69.10 192.168.5.1"
)

for item in "${ROUTES[@]}"; do
  DEST_NET=$(echo "$item" | awk '{print $1}')
  TEST_IP=$(echo "$item" | awk '{print $2}')
  GATEWAY=$(echo "$item" | awk '{print $3}')

  if /sbin/route -n get "$TEST_IP" 2>/dev/null | /usr/bin/grep -q "gateway: $GATEWAY"; then
    continue
  fi

  /sbin/route -n add -net "$DEST_NET" "$GATEWAY"
done

exit 0
"""

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>{LAUNCHD_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
      <string>{REMOTE_SCRIPT}</string>
    </array>

    <key>RunAtLoad</key>
    <true/>
  </dict>
</plist>
"""

    print(f"{host} installing persistence")
    logging.info(f"{host} installing persistence")

    run_sudo(conn, sudo_password, "mkdir -p /usr/local/sbin")

    conn.send_command_timing(f"cat > /tmp/add-evo-routes.sh <<'EOF'\n{route_script}\nEOF")
    conn.send_command_timing(f"cat > /tmp/com.company.evo-routes.plist <<'EOF'\n{plist}\nEOF")

    run_sudo(conn, sudo_password, f"mv /tmp/add-evo-routes.sh {REMOTE_SCRIPT}")
    run_sudo(conn, sudo_password, f"mv /tmp/com.company.evo-routes.plist {REMOTE_PLIST}")

    run_sudo(conn, sudo_password, f"chown root:wheel {REMOTE_SCRIPT}")
    run_sudo(conn, sudo_password, f"chmod 755 {REMOTE_SCRIPT}")

    run_sudo(conn, sudo_password, f"chown root:wheel {REMOTE_PLIST}")
    run_sudo(conn, sudo_password, f"chmod 644 {REMOTE_PLIST}")

    # If already loaded, bootout may error. That's okay.
    run_sudo(conn, sudo_password, f"launchctl bootout system {REMOTE_PLIST}")
    run_sudo(conn, sudo_password, f"launchctl bootstrap system {REMOTE_PLIST}")
    run_sudo(conn, sudo_password, f"launchctl kickstart -k system/{LAUNCHD_LABEL}")

    print(f"{host} persistence installed")
    logging.info(f"{host} persistence installed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--add", action="store_true", help="Add missing routes")
    parser.add_argument("--persistent", action="store_true", help="Install LaunchDaemon persistence")
    args = parser.parse_args()

    username = input("Username: ")
    password = getpass("SSH password: ")

    sudo_password = None
    if args.add or args.persistent:
        sudo_password = getpass("sudo password: ")

    hosts = load_inventory(INVENTORY_FILE)

    for host in hosts:
        print(f"\n=== {host} ===")
        logging.info(f"{host} connecting")

        device = {
            "device_type": "terminal_server",
            "host": host,
            "username": username,
            "password": password,
            "timeout": 15,
            "banner_timeout": 20,
            "auth_timeout": 15,
        }

        try:
            conn = ConnectHandler(**device)

            if args.add:
                add_missing_routes(conn, host, sudo_password)
            else:
                check_routes(conn, host)

            if args.persistent:
                install_persistence(conn, host, sudo_password)
                check_routes(conn, host)

            conn.disconnect()

        except Exception as e:
            msg = f"{host} CONNECTION_FAILED {e}"
            print(msg)
            logging.exception(msg)


if __name__ == "__main__":
    main()