#!/usr/bin/env python3
"""
topo_map.py
Build a simple L2/L1 topology graph from Cisco LLDP/CDP and color edges using 'show interface status'.
- Pure standard library
- Input files: <hostname>_lldp.txt, <hostname>_status.txt 
- Output: topology.dot (Graphviz), topology_edges.csv (optional)

Usage examples:
    python topo_map.py -d ./inv -o topology.dot --csv topology_edges.csv
    dot -Tsvg topology.dot -o topology.svg
"""

import argparse
import glob
import re
from pathlib import Path

# --- Regex patterns (kept resilient to minor spacing/format variations)
RE_LLDPR_DEV   = re.compile(r'^\s*Device ID:\s*(?P<dev>.+?)\s*$')
RE_LLDPR_LOCAL = re.compile(r'^\s*Interface:\s*(?P<local>\S+),')
RE_LLDPR_PORT  = re.compile(r'^\s*Port ID \(outgoing port\):\s*(?P<port>.+?)\s*$')

RE_CDPR_DEV    = re.compile(r'^\s*Device ID:\s*(?P<dev>.+?)\s*$')
RE_CDPR_LOCAL  = re.compile(r'^\s*Interface:\s*(?P<local>\S+),\s*Port ID\s*\(outgoing port\):\s*(?P<port>.+?)\s*$')

# 'show interface status' (Catalyst style)
# Port  Name  Status  Vlan  Duplex Speed Type
RE_STATUS_ROW = re.compile(
    r'^\s*(?P<port>\S+)\s+.*?\s+(?P<status>connected|notconnect|disabled|err-disabled)\s+(?P<vlan>\S+)\s+',
    re.IGNORECASE
)

# Some neighbor Device IDs include FQDNs or mgmt interface hints; normalize a bit
def clean_dev(name: str) -> str:
    name = name.strip()
    # Strip parentheses or trailing interface hints sometimes appended by CDP
    name = re.sub(r'\s*\(.*?\)\s*$', '', name)
    # Shorten FQDN to hostname
    if '.' in name:
        name = name.split('.')[0]
    return name

def norm_ifname(ifname: str) -> str:
    return ifname.strip()

def parse_neighbors_file(path: Path, is_lldp: bool):
    """Yield (local_intf, remote_dev, remote_port) tuples for one file."""
    local_host = path.name.replace('_lldp.txt', '').replace('_cdp.txt', '')
    local = None
    remote_dev = None
    remote_port = None
    edges = []

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line in lines:
        if is_lldp:
            mdev = RE_LLDPR_DEV.match(line)
            if mdev:
                # if we have a pending edge (local+remote), flush
                if local and remote_dev and remote_port:
                    edges.append((local_host, local, clean_dev(remote_dev), remote_port.strip()))
                # start new neighbor block
                remote_dev = mdev.group('dev')
                local = None
                remote_port = None
                continue

            mloc = RE_LLDPR_LOCAL.match(line)
            if mloc:
                local = norm_ifname(mloc.group('local'))
                continue

            mport = RE_LLDPR_PORT.match(line)
            if mport:
                remote_port = norm_ifname(mport.group('port'))
                continue

        else:
            # CDP combined line often contains both local and remote
            m = RE_CDPR_LOCAL.match(line)
            if m:
                local = norm_ifname(m.group('local'))
                remote_port = norm_ifname(m.group('port'))
                continue
            mdev = RE_CDPR_DEV.match(line)
            if mdev:
                # flush prior neighbor if accumulated
                if local and remote_dev and remote_port:
                    edges.append((local_host, local, clean_dev(remote_dev), remote_port.strip()))
                remote_dev = mdev.group('dev')
                # Reset local/port; next lines may bring them
                local = None
                remote_port = None
                continue

    # Flush trailing neighbor in case the last block had values
    if local and remote_dev and remote_port:
        edges.append((local_host, local, clean_dev(remote_dev), remote_port.strip()))
    return edges

def parse_status_file(path: Path):
    """Return dict port->(status, vlan)."""
    status_map = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = RE_STATUS_ROW.match(line)
        if m:
            status_map[m.group('port')] = (m.group('status').lower(), m.group('vlan'))
    return status_map

def edge_key(a_host, a_port, b_host, b_port):
    """Undirected key so A<->B and B<->A are merged."""
    A = (a_host, a_port)
    B = (b_host, b_port)
    return tuple(sorted([A, B]))

def pick_color(status_a, status_b):
    """Choose an edge color based on interface status on each side."""
    # Normalize to lowercase or None
    sa = (status_a or '').lower()
    sb = (status_b or '').lower()
    # Priority: err-disabled (red), connected (green), notconnect (orange), disabled (gray)
    if 'err-disabled' in (sa, sb):
        return "#d62728"  # red
    if 'connected' in (sa, sb):
        return "#2ca02c"  # green
    if 'notconnect' in (sa, sb):
        return "#ff7f0e"  # orange
    if 'disabled' in (sa, sb):
        return "#7f7f7f"  # gray
    return "#9da0a2"      # neutral gray

def main():
    ap = argparse.ArgumentParser(description="Build topology.dot from LLDP/CDP outputs (optional color from status).")
    ap.add_argument("-d", "--directory", required=True, help="Folder with *_lldp.txt, *_cdp.txt, *_status.txt files")
    ap.add_argument("-o", "--output", default="topology.dot", help="DOT output path")
    ap.add_argument("--csv", help="Optional CSV adjacency output path")
    ap.add_argument("--prefer", choices=["lldp", "cdp", "merge"], default="merge",
                    help="If both LLDP & CDP exist, prefer one or merge")
    args = ap.parse_args()

    root = Path(args.directory)

    # Load neighbor edges
    all_edges = {}  # key -> data dict
    nodes = set()
    # Parse LLDP
    for f in root.glob("*_lldp.txt"):
        for (lh, lp, rh, rp) in parse_neighbors_file(f, is_lldp=True):
            k = edge_key(lh, lp, rh, rp)
            data = all_edges.get(k, {"lldp": set(), "cdp": set()})
            data["lldp"].add((lh, lp, rh, rp))
            all_edges[k] = data
            nodes.update([lh, rh])
    # Parse CDP
    for f in root.glob("*_cdp.txt"):
        for (lh, lp, rh, rp) in parse_neighbors_file(f, is_lldp=False):
            k = edge_key(lh, lp, rh, rp)
            data = all_edges.get(k, {"lldp": set(), "cdp": set()})
            data["cdp"].add((lh, lp, rh, rp))
            all_edges[k] = data
            nodes.update([lh, rh])

    # Load status maps (optional)
    status_maps = {}  # hostname -> {port: (status, vlan)}
    for f in root.glob("*_status.txt"):
        host = f.name.replace("_status.txt", "")
        status_maps[host] = parse_status_file(f)

    # Build DOT
    dot = []
    dot.append("graph topology {")
    dot.append('  graph [fontname="Segoe UI", fontsize=10, overlap=false, splines=true];')
    dot.append('  node  [shape=box, style="rounded,filled", fontname="Segoe UI", fillcolor="#f6f8fa"];')
    dot.append('  edge  [fontname="Consolas", color="#9da0a2"];')

    # Nodes
    for n in sorted(nodes):
        dot.append(f'  "{n}";')

    # Edges
    csv_rows = [("local_host","local_port","remote_host","remote_port","source","status_color")]
    for k, data in all_edges.items():
        # Decide which tuple(s) to use
        tuples = None
        source = None
        if args.prefer == "lldp" and data["lldp"]:
            tuples = list(data["lldp"])
            source = "lldp"
        elif args.prefer == "cdp" and data["cdp"]:
            tuples = list(data["cdp"])
            source = "cdp"
        else:
            # merge: prefer LLDP tuples if present, else CDP
            tuples = list(data["lldp"] or data["cdp"])
            source = "lldp+cdp" if (data["lldp"] and data["cdp"]) else ("lldp" if data["lldp"] else "cdp")

        # Take the first tuple as representative (undirected unique edge)
        lh, lp, rh, rp = tuples[0]

        # Edge label
        label = f"{lp} ⟷ {rp}"

        # Color from status maps (optional)
        sa = status_maps.get(lh, {}).get(lp, (None, None))[0]
        sb = status_maps.get(rh, {}).get(rp, (None, None))[0]
        ecolor = pick_color(sa, sb)

        dot.append(f'  "{lh}" -- "{rh}" [label="{label}", color="{ecolor}"];')
        csv_rows.append((lh, lp, rh, rp, source, ecolor))

    dot.append("}")
    Path(args.output).write_text("\n".join(dot), encoding="utf-8")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerows(csv_rows)

    print(f"Wrote {args.output}")
    if args.csv:
        print(f"Wrote {args.csv}")

if __name__ == "__main__":
    main()

