#!/usr/bin/env python3

import argparse
import csv
import html
import re
import webbrowser
from pathlib import Path
from getpass import getpass
from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)

RE_LLDP_ROW = re.compile(
    r"^(?P<device>\S+)\s+"
    r"(?P<local>\S+)\s+"
    r"(?P<hold>\d+)\s+"
    r"(?P<capability>[A-Z,]*)\s+"
    r"(?P<port>\S+)\s*$"
)

RE_STATUS_ROW = re.compile(
    r"^(?P<port>\S+)\s+"
    r"(?P<name>.*?)\s+"
    r"(?P<status>connected|notconnect|disabled|err-disabled|errdisabled|inactive|suspended)\s+"
    r"(?P<vlan>\S+)\s+"
    r"(?P<duplex>\S+)\s+"
    r"(?P<speed>\S+)\s+"
    r"(?P<type>.+?)\s*$",
    re.IGNORECASE,
)


def is_data_line(line: str) -> bool:
    line = line.strip()
    return bool(line) and not line.lower().startswith((
        "capability codes",
        "device id",
        "port ",
        "----",
    ))


def collect_from_switch():
    host = input("Switch hostname or IP: ").strip()
    username = input("Username: ").strip()
    password = getpass("Password: ")

    device = {
        "device_type": "cisco_ios",
        "host": host,
        "username": username,
        "password": password,
    }

    try:
        conn = ConnectHandler(**device)
        conn.send_command("terminal length 0")

        prompt = conn.find_prompt()
        hostname = prompt.replace("#", "").replace(">", "").strip()

        print(f"Connected to {hostname}")
        print("Collecting LLDP neighbors...")
        lldp_output = conn.send_command("show lldp neighbors")

        print("Collecting interface status...")
        int_status_output = conn.send_command(
            "show interface status | exclude disabled"
        )

        conn.disconnect()

        return hostname, lldp_output, int_status_output

    except NetmikoAuthenticationException:
        raise SystemExit("Authentication failed.")

    except NetmikoTimeoutException:
        raise SystemExit("Connection timed out.")

    except Exception as e:
        raise SystemExit(f"Connection failed: {e}")


def parse_lldp_text(text: str) -> dict:
    neighbors = {}

    for raw in text.splitlines():
        line = raw.strip()
        if not is_data_line(line):
            continue

        m = RE_LLDP_ROW.match(line)
        if not m:
            continue

        local_port = m.group("local")
        neighbors[local_port] = {
            "neighbor": m.group("device"),
            "neighbor_port": m.group("port"),
            "capability": m.group("capability"),
        }

    return neighbors


def parse_int_status_text(text: str) -> dict:
    ports = {}

    for raw in text.splitlines():
        line = raw.rstrip()
        if not is_data_line(line):
            continue

        m = RE_STATUS_ROW.match(line)
        if not m:
            continue

        port = m.group("port")
        ports[port] = {
            "port": port,
            "name": m.group("name").strip(),
            "status": m.group("status"),
            "vlan": m.group("vlan"),
            "duplex": m.group("duplex"),
            "speed": m.group("speed"),
            "type": m.group("type").strip(),
        }

    return ports


def classify_port(row: dict) -> str:
    port = row["port"]
    vlan = row.get("vlan", "")
    neighbor = row.get("neighbor", "")
    capability = row.get("capability", "")

    if port.lower().startswith("po"):
        return "port-channel"

    if vlan.lower() == "trunk":
        return "uplink"

    if "B" in capability or "R" in capability:
        return "uplink"

    if neighbor:
        return "access"

    if row.get("status", "").lower() == "connected":
        return "connected-no-lldp"

    return "other"


def port_sort_key(port: str):
    nums = [int(x) for x in re.findall(r"\d+", port)]
    prefix = re.sub(r"[\d/]+", "", port)
    return (prefix, nums, port)


def build_rows(hostname: str, int_status: dict, lldp: dict) -> list[dict]:
    all_ports = sorted(set(int_status.keys()) | set(lldp.keys()), key=port_sort_key)
    rows = []

    for port in all_ports:
        base = int_status.get(port, {
            "port": port,
            "name": "",
            "status": "",
            "vlan": "",
            "duplex": "",
            "speed": "",
            "type": "",
        })

        nbr = lldp.get(port, {})

        row = {
            "switch": hostname,
            "port": port,
            "name": base.get("name", ""),
            "status": base.get("status", ""),
            "vlan": base.get("vlan", ""),
            "duplex": base.get("duplex", ""),
            "speed": base.get("speed", ""),
            "type": base.get("type", ""),
            "neighbor": nbr.get("neighbor", ""),
            "neighbor_port": nbr.get("neighbor_port", ""),
            "capability": nbr.get("capability", ""),
        }

        row["role"] = classify_port(row)
        rows.append(row)

    return rows


def write_csv(rows: list[dict], path: Path):
    fields = [
        "switch",
        "port",
        "name",
        "status",
        "vlan",
        "neighbor",
        "neighbor_port",
        "capability",
        "role",
        "speed",
        "duplex",
        "type",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_html(hostname: str, rows: list[dict], path: Path):
    connected = [
        r for r in rows
        if r["status"].lower() == "connected" or r["neighbor"]
    ]

    uplinks = [
        r for r in connected
        if r["role"] in ("uplink", "port-channel")
    ]

    endpoints = [
        r for r in connected
        if r["role"] not in ("uplink", "port-channel")
    ]

    width = 1600
    row_gap = 95
    top_y = 220

    # Keep the switch position dynamic. If one side has many more connections,
    # nudge the switch away from the crowded side while keeping it on-canvas.
    left_count = len(endpoints)
    right_count = len(uplinks)
    switch_x = max(650, min(850, 700 + ((left_count - right_count) * 20)))

    switch_w = 280
    switch_h = 160

    max_rows = max(len(endpoints), len(uplinks), 1)
    switch_y = max(300, top_y + max_rows * row_gap / 2 - 70)

    left_x = 60
    left_w = 300
    right_x = 1260
    right_w = 300
    box_h = 70

    height = max(900, int(top_y + max_rows * row_gap + 340))

    def esc(v):
        return html.escape(str(v or ""))

    def target_label(r):
        return r["neighbor"] or r["name"] or "Connected Device"

    svg_parts = []

    svg_parts.append(f"""
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.25"/>
    </filter>
  </defs>

  <rect width="100%" height="100%" fill="#ffffff"/>

  <text x="28" y="42" font-size="34" font-weight="700" font-family="Segoe UI, Arial">{esc(hostname)}</text>
  <text x="28" y="72" font-size="22" font-family="Segoe UI, Arial">Switch Port Map</text>

  <rect x="28" y="95" width="300" height="100" rx="8" fill="#ffffff" stroke="#333"/>
  <line x1="48" y1="125" x2="95" y2="125" stroke="#0057b8" stroke-width="3"/>
  <text x="115" y="131" font-size="16" font-family="Segoe UI, Arial">Uplink / Infrastructure</text>
  <line x1="48" y1="155" x2="95" y2="155" stroke="#16822f" stroke-width="3"/>
  <text x="115" y="161" font-size="16" font-family="Segoe UI, Arial">Endpoint / Access</text>
  <line x1="48" y1="180" x2="95" y2="180" stroke="#0057b8" stroke-width="3" stroke-dasharray="10 8"/>
  <text x="115" y="186" font-size="16" font-family="Segoe UI, Arial">Port-Channel</text>

  <rect x="{switch_x}" y="{switch_y}" width="{switch_w}" height="{switch_h}" rx="10"
        fill="#ffffff" stroke="#111111" stroke-width="2.5" filter="url(#shadow)"/>
  <text x="{switch_x + switch_w / 2}" y="{switch_y + 82}" text-anchor="middle"
        font-size="26" font-weight="700" font-family="Segoe UI, Arial">{esc(hostname)}</text>
  <text x="{switch_x + switch_w / 2}" y="{switch_y + 115}" text-anchor="middle"
        font-size="18" font-family="Segoe UI, Arial">(Switch)</text>
""")

    for i, r in enumerate(endpoints):
        y = top_y + i * row_gap
        color = "#16822f"
        vlan = r["vlan"]
        label = target_label(r)

        start_x = left_x + left_w
        start_y = y + box_h / 2
        end_x = switch_x
        end_y = switch_y + 35 + (i + 1) * (switch_h - 70) / max(1, len(endpoints))
        mid_x = switch_x - 80

        # Anchor the local port/VLAN label near the endpoint box.
        # This scales better than floating labels in the middle of the link bundle.
        label_x = left_x + left_w + 10
        label_y = start_y - 8
        vlan_y = start_y + 18

        svg_parts.append(f"""
  <rect x="{left_x}" y="{y}" width="{left_w}" height="{box_h}" rx="7"
        fill="#f4fff6" stroke="{color}" stroke-width="2"/>
  <text x="{left_x + left_w / 2}" y="{y + 30}" text-anchor="middle"
        font-size="18" font-weight="700" font-family="Segoe UI, Arial">{esc(label)}</text>
  <text x="{left_x + left_w / 2}" y="{y + 55}" text-anchor="middle"
        font-size="14" font-family="Segoe UI, Arial">{esc(r["name"])}</text>

  <polyline points="{start_x},{start_y} {mid_x},{start_y} {end_x},{end_y}"
            fill="none" stroke="{color}" stroke-width="2.5"/>

  <rect x="{label_x - 2}" y="{label_y - 13}" width="105" height="48"
        fill="white" opacity="0.80"/>

  <text x="{label_x}" y="{label_y}" font-size="18" font-weight="700"
        font-family="Consolas, monospace">{esc(r["port"])}</text>
  <text x="{label_x}" y="{vlan_y}" font-size="16"
        fill="{color}" font-family="Segoe UI, Arial">VLAN {esc(vlan)}</text>
""")

    for i, r in enumerate(uplinks):
        y = top_y + i * row_gap
        is_po = r["role"] == "port-channel"
        color = "#0057b8"
        dash = 'stroke-dasharray="10 8"' if is_po else ""
        box_dash = 'stroke-dasharray="10 8"' if is_po else ""
        vlan = r["vlan"]
        label = target_label(r)
        remote = r["neighbor_port"]

        start_x = switch_x + switch_w
        uplink_spacing = switch_h / (len(uplinks) + 1)
        start_y = switch_y + uplink_spacing * (i + 1)

        end_x = right_x
        end_y = y + box_h / 2
        mid_x = switch_x + switch_w + 120

        label_x = right_x - 150
        label_y = end_y - 8
        vlan_y = end_y + 14
        if is_po:
            remote_text = f"Port-Channel {r['port']}"
        else:
            remote_text = f"LLDP Port: {remote}"

        svg_parts.append(f"""
  <rect x="{right_x}" y="{y}" width="{right_w}" height="{box_h}" rx="7"
        fill="#f3f8ff" stroke="{color}" stroke-width="2" {box_dash}/>
  <text x="{right_x + right_w / 2}" y="{y + 30}" text-anchor="middle"
        font-size="18" font-weight="700" font-family="Segoe UI, Arial">{esc(label)}</text>
  <text x="{right_x + right_w / 2}" y="{y + 55}" text-anchor="middle"
        font-size="14" font-family="Segoe UI, Arial">{esc(remote_text)}</text>

  <polyline points="{start_x},{start_y} {mid_x},{start_y} {end_x},{end_y}"
            fill="none" stroke="{color}" stroke-width="2.5" {dash}/>

  <rect x="{label_x - 2}" y="{label_y - 13}" width="75" height="24"
        fill="white" opacity="0.80"/>

  <text x="{label_x}" y="{label_y}" font-size="18" font-weight="700"
        font-family="Consolas, monospace">{esc(r["port"])}</text>
  <text x="{label_x}" y="{vlan_y}" font-size="16"
        fill="{color}" font-family="Segoe UI, Arial">{esc(vlan)}</text>
""")

    table_x = 260
    table_y = height - 245
    table_w = 1080
    row_h = 28

    headers = ["Port", "Description", "Status", "VLAN", "LLDP Neighbor", "LLDP Port", "Role"]
    col_widths = [110, 260, 110, 90, 190, 170, 150]

    svg_parts.append(f"""
  <rect x="{table_x}" y="{table_y}" width="{table_w}" height="{40 + row_h * (len(connected)+1)}"
        fill="#ffffff" stroke="#333" rx="4"/>
  <text x="{table_x + 10}" y="{table_y + 25}" font-size="16" font-weight="700"
        font-family="Segoe UI, Arial">Port Summary</text>
  <line x1="{table_x}" y1="{table_y + 38}" x2="{table_x + table_w}" y2="{table_y + 38}" stroke="#333"/>
""")

    x = table_x
    for h, cw in zip(headers, col_widths):
        svg_parts.append(f"""
  <text x="{x + 8}" y="{table_y + 62}" font-size="13" font-weight="700"
        font-family="Segoe UI, Arial">{esc(h)}</text>
  <line x1="{x}" y1="{table_y + 38}" x2="{x}" y2="{table_y + 40 + row_h * (len(connected)+1)}" stroke="#999"/>
""")
        x += cw

    svg_parts.append(f"""
  <line x1="{table_x + table_w}" y1="{table_y + 38}" x2="{table_x + table_w}" y2="{table_y + 40 + row_h * (len(connected)+1)}" stroke="#999"/>
""")

    for idx, r in enumerate(connected):
        y = table_y + 72 + idx * row_h
        vals = [
            r["port"],
            r["name"],
            r["status"],
            r["vlan"],
            r["neighbor"] or "-",
            r["neighbor_port"] or "-",
            r["role"],
        ]

        svg_parts.append(f"""
  <line x1="{table_x}" y1="{y - 18}" x2="{table_x + table_w}" y2="{y - 18}" stroke="#ccc"/>
""")

        x = table_x
        for val, cw in zip(vals, col_widths):
            svg_parts.append(f"""
  <text x="{x + 8}" y="{y}" font-size="12" font-family="Segoe UI, Arial">{esc(val)}</text>
""")
            x += cw

    svg_parts.append("</svg>")
    svg = "\n".join(svg_parts)

    doc = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{esc(hostname)} switch map</title>
<style>
body {{
  margin: 0;
  background: #e5e7eb;
}}
.wrapper {{
  width: {width}px;
  margin: 0 auto;
  background: white;
}}
</style>
</head>
<body>
<div class="wrapper">
{svg}
</div>
</body>
</html>
"""

    path.write_text(doc, encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(
        description="SSH to one Cisco switch, collect LLDP/interface status, and generate a switch port map."
    )
    ap.add_argument(
        "--output-dir",
        default="./mapping",
        help="Directory for generated HTML and CSV files"
    )
    args = ap.parse_args()

    hostname, lldp_output, int_status_output = collect_from_switch()

    lldp = parse_lldp_text(lldp_output)
    int_status = parse_int_status_text(int_status_output)

    rows = build_rows(hostname, int_status, lldp)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_file = output_dir / f"{hostname}.csv"
    html_file = output_dir / f"{hostname}.html"

    write_csv(rows, csv_file)
    write_html(hostname, rows, html_file)

    print(f"Wrote {html_file}")
    print(f"Wrote {csv_file}")

    webbrowser.open(html_file.resolve().as_uri())

if __name__ == "__main__":
    main()