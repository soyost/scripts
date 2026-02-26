#!/usr/bin/env python3
"""
topo_map.py

Topology extractor + multiple export formats.

Supports:
- DOT / CSV (raw)
- Collapsed CSV (device-pair)
- HTML (viz.js CDN) and offline HTML (canvas)
- Draw.io (.drawio XML) export for Lucid import
- Draw.io CSV export (connector-based)

Usage examples:
  python topo_map.py -d ./inv --csv ./inv/topology_edges.csv --collapsed-csv ./inv/topology_collapsed.csv --drawio ./inv/topology.drawio --drawio-csv ./inv/topology_drawiocsv.csv
"""

import argparse
import csv
import math
import re
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

# ---------------------------
# Normalization / helpers
# ---------------------------

_IF_PREFIX_MAP = {
    "gi": "GigabitEthernet",
    "gigabitethernet": "GigabitEthernet",
    "fa": "FastEthernet",
    "fastethernet": "FastEthernet",
    "te": "TenGigabitEthernet",
    "tengigabitethernet": "TenGigabitEthernet",
    "tw": "TwoGigabitEthernet",
    "eth": "Ethernet",
    "ethernet": "Ethernet",
    "po": "Port-channel",
    "port-channel": "Port-channel",
    "portchannel": "Port-channel",
    "lo": "Loopback",
    "loopback": "Loopback",
    "mg": "MgmtEth",
    "mgmt": "MgmtEth",
    "mgmteth": "MgmtEth",
    "hu": "HundredGigE",
    "hundredgige": "HundredGigE",
}

RE_MAC_DOTTED = re.compile(r"^[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}$")

def clean_dev(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"\s*\(.*?\)\s*$", "", name)
    if RE_MAC_DOTTED.match(name):
        return name.lower()
    if "." in name:
        name = name.split(".", 1)[0]
    return name

def is_endpointish(node_name: str) -> bool:
    return bool(RE_MAC_DOTTED.match(node_name or ""))

def norm_ifname(ifname: str) -> str:
    s = (ifname or "").strip()
    if not s:
        return s
    s = s.rstrip(",")
    s = re.sub(r"\s+", "", s)
    m = re.match(r"^([A-Za-z\-]+)(.+)$", s)
    if not m:
        return s
    prefix = m.group(1).lower()
    rest = m.group(2)
    canon = _IF_PREFIX_MAP.get(prefix)
    return f"{canon}{rest}" if canon else s

def short_ifname(ifname: str) -> str:
    s = (ifname or "").strip()
    if not s:
        return s
    return (
        s.replace("TenGigabitEthernet", "Te")
         .replace("GigabitEthernet", "Gi")
         .replace("FastEthernet", "Fa")
         .replace("Ethernet", "Eth")
         .replace("Port-channel", "Po")
         .replace("HundredGigE", "Hu")
         .replace("TwoGigabitEthernet", "Tw")
         .replace("MgmtEth", "Mg")
    )

def norm_status(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("errdisabled", "err-disabled").replace("err-disabled", "err-disabled")
    if s in ("xcvrabsent", "sfpabsent", "xcvr-absent", "sfp-absent"):
        return "notconnect"
    return s

# ---------------------------
# Parsers (LLDP / CDP / status)
# ---------------------------

RE_IOS_LLDPR_DEV   = re.compile(r"^\s*Device ID:\s*(?P<dev>.+?)\s*$", re.IGNORECASE)
RE_IOS_LLDPR_LOCAL = re.compile(r"^\s*Interface:\s*(?P<local>\S+)\s*,", re.IGNORECASE)
RE_IOS_LLDPR_PORT  = re.compile(r"^\s*Port ID\s*\(outgoing port\):\s*(?P<port>.+?)\s*$", re.IGNORECASE)

def parse_lldp_ios_detail(path: Path):
    local_host = path.name.replace("_lldp.txt", "")
    edges = []
    local = remote_dev = remote_port = None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        mdev = RE_IOS_LLDPR_DEV.match(line)
        if mdev:
            if local and remote_dev and remote_port:
                edges.append((local_host, norm_ifname(local), clean_dev(remote_dev), norm_ifname(remote_port)))
            remote_dev = mdev.group("dev")
            local = None
            remote_port = None
            continue
        mloc = RE_IOS_LLDPR_LOCAL.match(line)
        if mloc:
            local = mloc.group("local"); continue
        mport = RE_IOS_LLDPR_PORT.match(line)
        if mport:
            remote_port = mport.group("port"); continue
    if local and remote_dev and remote_port:
        edges.append((local_host, norm_ifname(local), clean_dev(remote_dev), norm_ifname(remote_port)))
    return edges

RE_NX_LLDPR_LOCAL = re.compile(r"^\s*Local\s+Intf:\s*(?P<local>\S+)\s*$", re.IGNORECASE)
RE_NX_LLDPR_PORT  = re.compile(r"^\s*Port\s+id:\s*(?P<port>.+?)\s*$", re.IGNORECASE)
RE_NX_LLDPR_PORT2 = re.compile(r"^\s*Port\s+ID:\s*(?P<port>.+?)\s*$", re.IGNORECASE)
RE_NX_LLDPR_SYS   = re.compile(r"^\s*System\s+Name:\s*(?P<dev>.+?)\s*$", re.IGNORECASE)
RE_NX_LLDPR_SYS2  = re.compile(r"^\s*System\s+name:\s*(?P<dev>.+?)\s*$", re.IGNORECASE)

def parse_lldp_nxos_detail(path: Path):
    local_host = path.name.replace("_lldp.txt", "")
    edges = []
    local = remote_dev = remote_port = None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        mloc = RE_NX_LLDPR_LOCAL.match(line)
        if mloc:
            if local and remote_dev and remote_port:
                edges.append((local_host, norm_ifname(local), clean_dev(remote_dev), norm_ifname(remote_port)))
            local = mloc.group("local"); remote_dev = None; remote_port = None; continue
        msys = RE_NX_LLDPR_SYS.match(line) or RE_NX_LLDPR_SYS2.match(line)
        if msys:
            remote_dev = msys.group("dev"); continue
        mport = RE_NX_LLDPR_PORT.match(line) or RE_NX_LLDPR_PORT2.match(line)
        if mport:
            remote_port = mport.group("port"); continue
    if local and remote_dev and remote_port:
        edges.append((local_host, norm_ifname(local), clean_dev(remote_dev), norm_ifname(remote_port)))
    return edges

def parse_lldp(path: Path):
    for fn in (parse_lldp_ios_detail, parse_lldp_nxos_detail):
        edges = fn(path)
        if edges:
            return edges
    return []

RE_CDP_DEV = re.compile(r"^\s*Device ID:\s*(?P<dev>.+?)\s*$", re.IGNORECASE)
RE_CDP_IF_PORT_SAME_LINE = re.compile(
    r"^\s*Interface:\s*(?P<local>\S+)\s*,\s*Port ID\s*\(outgoing port\):\s*(?P<port>.+?)\s*$",
    re.IGNORECASE,
)
RE_CDP_LOCAL_ONLY = re.compile(r"^\s*Interface:\s*(?P<local>\S+)\s*,\s*$", re.IGNORECASE)
RE_CDP_PORT_ONLY  = re.compile(r"^\s*Port ID\s*\(outgoing port\):\s*(?P<port>.+?)\s*$", re.IGNORECASE)

def parse_cdp_detail(path: Path):
    local_host = path.name.replace("_cdp.txt", "")
    edges = []
    local = remote_dev = remote_port = None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        mdev = RE_CDP_DEV.match(line)
        if mdev:
            if local and remote_dev and remote_port:
                edges.append((local_host, norm_ifname(local), clean_dev(remote_dev), norm_ifname(remote_port)))
            remote_dev = mdev.group("dev"); local = None; remote_port = None; continue
        msame = RE_CDP_IF_PORT_SAME_LINE.match(line)
        if msame:
            local = msame.group("local"); remote_port = msame.group("port"); continue
        mloc = RE_CDP_LOCAL_ONLY.match(line)
        if mloc:
            local = mloc.group("local"); continue
        mport = RE_CDP_PORT_ONLY.match(line)
        if mport:
            remote_port = mport.group("port"); continue
    if local and remote_dev and remote_port:
        edges.append((local_host, norm_ifname(local), clean_dev(remote_dev), norm_ifname(remote_port)))
    return edges

def parse_cdp(path: Path):
    return parse_cdp_detail(path) or []

RE_STATUS_ROW = re.compile(
    r"^\s*(?P<port>\S+)\s+.*?\s+(?P<status>"
    r"connected|notconnect|disabled|err-?disabled|errdisabled|inactive|"
    r"sfpabsent|xcvrabsent|linkflap|monitoring|suspended"
    r")\s+(?P<vlan>\S+)\s+",
    re.IGNORECASE,
)

def parse_status_file(path: Path):
    status_map = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = RE_STATUS_ROW.match(line)
        if m:
            port = norm_ifname(m.group("port"))
            status = norm_status(m.group("status"))
            vlan = m.group("vlan")
            status_map[port] = (status, vlan)
    return status_map

# ---------------------------
# Graph helpers, collapse
# ---------------------------

def edge_key(a_host, a_port, b_host, b_port):
    A = (a_host, a_port)
    B = (b_host, b_port)
    return tuple(sorted([A, B]))

def pick_color(status_a, status_b):
    sa = norm_status(status_a) or "notconnect"
    sb = norm_status(status_b) or "notconnect"
    if sa == "err-disabled" or sb == "err-disabled":
        return "#d62728"
    if sa == "connected" and sb == "connected":
        return "#2ca02c"
    if "connected" in (sa, sb) and sa != sb:
        return "#ffbf00"
    if sa == "notconnect" or sb == "notconnect":
        return "#ff7f0e"
    if sa == "disabled" and sb == "disabled":
        return "#7f7f7f"
    return "#9da0a2"

def collapse_links(raw_edges, status_maps):
    grouped = defaultdict(list)
    for (lh, lp, rh, rp, source) in raw_edges:
        A, B = sorted([lh, rh])
        grouped[(A, B)].append((lh, lp, rh, rp, source))

    collapsed = {}
    for (A, B), links in grouped.items():
        label_lines = []
        link_colors = []
        source_set = set()
        for (lh, lp, rh, rp, source) in links:
            source_set.add(source)
            sa = status_maps.get(lh, {}).get(lp, (None, None))[0]
            sb = status_maps.get(rh, {}).get(rp, (None, None))[0]
            link_colors.append(pick_color(sa, sb))
            label_lines.append(f"{short_ifname(lp)} ↔ {short_ifname(rp)}")
        severity = {"#d62728":5,"#ffbf00":4,"#ff7f0e":3,"#7f7f7f":2,"#2ca02c":1,"#9da0a2":0}
        color = max(link_colors, key=lambda c: severity.get(c,0)) if link_colors else "#9da0a2"
        collapsed[(A, B)] = {
            "A": A, "B": B, "links": links,
            "label": "\\n".join(label_lines), "color": color,
            "source": "+".join(sorted(source_set)) if source_set else ""
        }
    return collapsed

# ---------------------------
# DOT & HTML builders (existing)
# ---------------------------

def build_dot(nodes, collapsed_edges, title="Topology"):
    dot = []
    dot.append("graph topology {")
    dot.append('  graph [fontname="Segoe UI", fontsize=10, overlap=false, splines=polyline, rankdir=LR, concentrate=true, nodesep=0.7, ranksep=1.1, pad=0.2];')
    dot.append('  node  [shape=box, style="rounded,filled", fontname="Segoe UI", fillcolor="#f6f8fa"];')
    dot.append('  edge  [fontname="Consolas", fontsize=9, color="#9da0a2"];')
    dot.append(f'  label="{title}\\ngreen: both connected | amber: mixed | orange: missing/unknown | red: err-disabled";')
    dot.append('  labelloc="t";')
    dot.append('  fontsize=12;')
    for n in sorted(nodes):
        if is_endpointish(n):
            dot.append(f'  "{n}" [shape=ellipse, fillcolor="#fff5cc", fontname="Segoe UI"];')
        else:
            dot.append(f'  "{n}";')
    core_nodes = [n for n in nodes if not is_endpointish(n)]
    if 2 <= len(core_nodes) <= 12:
        dot.append("  { rank=same; " + " ".join(f'"{n}"' for n in sorted(core_nodes)) + " }")
    for (_, _), e in collapsed_edges.items():
        A = e["A"]; B = e["B"]; label = e["label"]; color = e["color"]
        dot.append(f'  "{A}" -- "{B}" [label="{label}", color="{color}"];')
    dot.append("}")
    return "\n".join(dot)

def write_html(dot_text: str, out_path: Path, title="Topology"):
    safe_dot = dot_text.replace("\\", "\\\\").replace("`", "\\`")
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>{title}</title>
<style>body{{margin:0;font-family:Segoe UI,system-ui,-apple-system,sans-serif;background:#0b0f14;color:#e6edf3}}header{{padding:12px 16px;background:#111827;border-bottom:1px solid #1f2937;display:flex;gap:12px;align-items:center;position:sticky;top:0;z-index:10}}header h1{{font-size:14px;margin:0;font-weight:600;opacity:0.95}}header button{{background:#1f2937;color:#e6edf3;border:1px solid #374151;border-radius:8px;padding:8px 10px;cursor:pointer;font-size:12px}}#wrap{padding:12px}#graph{background:#ffffff;border-radius:12px;padding:12px;overflow:auto;max-height:calc(100vh - 70px)}</style></head><body>
<header><h1>{title}</h1><button id="btnSvg">Download SVG</button><button id="btnDot">Download DOT</button><div style="margin-left:auto;font-size:12px;opacity:.8">Tip: Save SVG for sharing</div></header>
<div id="wrap"><div id="graph">Rendering…</div></div>
<script type="module">
import Viz from "https://cdn.jsdelivr.net/npm/viz.js@2.1.2/dist/viz.es.js";
import {{ Module, render }} from "https://cdn.jsdelivr.net/npm/viz.js@2.1.2/dist/full.render.js";
const dot = `{safe_dot}`;
const viz = new Viz({{ Module, render }});
const graphDiv = document.getElementById("graph");
function download(filename, content, mime) {{
  const blob = new Blob([content], {{ type: mime }});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}}
async function main() {{
  try {{
    const svg = await viz.renderString(dot, {{ format: "svg", engine: "dot" }});
    graphDiv.innerHTML = svg;
    document.getElementById("btnSvg").onclick = () => download("topology.svg", svg, "image/svg+xml");
    document.getElementById("btnDot").onclick = () => download("topology.dot", dot, "text/vnd.graphviz");
  }} catch (e) {{
    graphDiv.innerHTML = "<pre style='white-space:pre-wrap'>Render failed:\\n" + (e?.stack || e) + "</pre>";
  }}
}}
main();
</script></body></html>"""
    out_path.write_text(html, encoding="utf-8")

def write_html_offline(nodes, collapsed_edges, out_path: Path, title="Topology (offline)"):
    """
    Single-file OFFLINE HTML renderer:
    - No CDN / no external JS
    - ES5-friendly JavaScript (var/function; no arrow/spread/const/let/template literals)
    - Renders a force-directed graph onto a <canvas>
    """

    # Build data payload for the browser
    node_list = sorted(nodes)
    node_index = {n: i for i, n in enumerate(node_list)}

    links = []
    for e in collapsed_edges.values():
        links.append({
            "source": node_index[e["A"]],
            "target": node_index[e["B"]],
            "label": e["label"].replace("\\n", " | "),
            "color": e["color"],
        })

    data = {
        "title": title,
        "nodes": [{"id": n, "endpoint": bool(RE_MAC_DOTTED.match(n))} for n in node_list],
        "links": links,
    }

    data_json = json.dumps(data)  # safe JS literal

    # IMPORTANT: use .format() and escape braces in CSS/JS with double braces {{ }}
    html = """<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<style>
  body {{
    margin: 0;
    font-family: Segoe UI, Arial, sans-serif;
    background: #0b0f14;
    color: #e6edf3;
  }}
  header {{
    padding: 10px 14px;
    background: #111827;
    border-bottom: 1px solid #1f2937;
    display: flex;
    gap: 10px;
    align-items: center;
  }}
  button {{
    background: #1f2937;
    color: #e6edf3;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 7px 10px;
    cursor: pointer;
    font-size: 12px;
  }}
  button:hover {{
    background: #273549;
  }}
  .hint {{
    margin-left: auto;
    font-size: 12px;
    opacity: 0.8;
  }}
  #wrap {{
    height: calc(100vh - 52px);
  }}
  canvas {{
    display: block;
    width: 100%;
    height: 100%;
  }}
</style>
</head>
<body>
<header>
  <div style="font-weight:600;">{title}</div>
  <button id="reset">Reset view</button>
  <div class="hint">Scroll to zoom • Drag background to pan • Drag nodes to move</div>
</header>

<div id="wrap"><canvas id="c"></canvas></div>

<script type="text/javascript">
(function() {{

  // Embedded data (no network calls)
  var DATA = {data_json};

  var canvas = document.getElementById("c");
  var ctx = canvas.getContext("2d");

  function resize() {{
    var r = canvas.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(r.width * dpr);
    canvas.height = Math.floor(r.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }}

  window.addEventListener("resize", resize);
  resize();

  // View transform
  var panX = 0, panY = 0, scale = 1;

  function worldToScreen(x, y) {{
    return [x * scale + panX, y * scale + panY];
  }}

  function screenToWorld(x, y) {{
    return [(x - panX) / scale, (y - panY) / scale];
  }}

  function resetView() {{
    // center view
    var r = canvas.getBoundingClientRect();
    panX = r.width / 2;
    panY = r.height / 2;
    scale = 1;
  }}

  document.getElementById("reset").onclick = function() {{
    resetView();
  }};

  resetView();

  // Build nodes (ES5, no spread)
  var nodes = [];
  var i;
  for (i = 0; i < DATA.nodes.length; i++) {{
    var dn = DATA.nodes[i];
    nodes.push({{
      id: dn.id,
      endpoint: !!dn.endpoint,
      x: (Math.random() * 2 - 1) * 220,
      y: (Math.random() * 2 - 1) * 140,
      vx: 0,
      vy: 0,
      fx: null,
      fy: null
    }});
  }}

  // Build links
  var links = [];
  for (i = 0; i < DATA.links.length; i++) {{
    var dl = DATA.links[i];
    links.push({{
      source: nodes[dl.source],
      target: nodes[dl.target],
      label: dl.label,
      color: dl.color
    }});
  }}

  // Interaction
  var dragNode = null;
  var dragPan = false;
  var lastX = 0, lastY = 0;

  function hitTestNode(wx, wy) {{
    // iterate backwards so topmost-ish nodes win
    for (var k = nodes.length - 1; k >= 0; k--) {{
      var n = nodes[k];
      var r = n.endpoint ? 16 : 22;
      var dx = wx - n.x;
      var dy = wy - n.y;
      if ((dx * dx + dy * dy) <= (r * r)) {{
        return n;
      }}
    }}
    return null;
  }}

  canvas.addEventListener("mousedown", function(e) {{
    var pt = screenToWorld(e.offsetX, e.offsetY);
    var wx = pt[0], wy = pt[1];
    var n = hitTestNode(wx, wy);
    if (n) {{
      dragNode = n;
      n.fx = n.x;
      n.fy = n.y;
    }} else {{
      dragPan = true;
    }}
    lastX = e.offsetX;
    lastY = e.offsetY;
  }});

  canvas.addEventListener("mousemove", function(e) {{
    if (dragNode) {{
      var pt = screenToWorld(e.offsetX, e.offsetY);
      dragNode.fx = pt[0];
      dragNode.fy = pt[1];
    }} else if (dragPan) {{
      panX += (e.offsetX - lastX);
      panY += (e.offsetY - lastY);
      lastX = e.offsetX;
      lastY = e.offsetY;
    }}
  }});

  window.addEventListener("mouseup", function() {{
    if (dragNode) {{
      dragNode.fx = null;
      dragNode.fy = null;
    }}
    dragNode = null;
    dragPan = false;
  }});

  canvas.addEventListener("wheel", function(e) {{
    e.preventDefault();
    var zoom = Math.exp(-e.deltaY * 0.001);
    var mx = e.offsetX, my = e.offsetY;

    var pt = screenToWorld(mx, my);
    var wx = pt[0], wy = pt[1];

    scale *= zoom;

    var sp = worldToScreen(wx, wy);
    panX += mx - sp[0];
    panY += my - sp[1];
  }}, {{ passive: false }});

  // Force simulation
  function step() {{
    var charge = -1600;
    var linkDist = 150;
    var linkStrength = 0.018;

    // repulsion (O(n^2))
    for (var a = 0; a < nodes.length; a++) {{
      for (var b = a + 1; b < nodes.length; b++) {{
        var na = nodes[a], nb = nodes[b];
        var dx = na.x - nb.x;
        var dy = na.y - nb.y;
        var d2 = dx * dx + dy * dy + 0.01;
        var f = charge / d2;
        var invd = 1 / Math.sqrt(d2);
        dx *= invd;
        dy *= invd;
        na.vx += dx * f;
        na.vy += dy * f;
        nb.vx -= dx * f;
        nb.vy -= dy * f;
      }}
    }}

    // springs
    for (var li = 0; li < links.length; li++) {{
      var l = links[li];
      var s = l.source;
      var t = l.target;
      var dx2 = t.x - s.x;
      var dy2 = t.y - s.y;
      var d = Math.sqrt(dx2 * dx2 + dy2 * dy2) + 1e-6;
      var diff = d - linkDist;
      var f2 = linkStrength * diff;
      dx2 /= d;
      dy2 /= d;
      s.vx += dx2 * f2;
      s.vy += dy2 * f2;
      t.vx -= dx2 * f2;
      t.vy -= dy2 * f2;
    }}

    // integrate
    var damping = 0.85;
    for (var ni = 0; ni < nodes.length; ni++) {{
      var n = nodes[ni];

      if (n.fx !== null && n.fy !== null) {{
        n.x = n.fx;
        n.y = n.fy;
        n.vx = 0;
        n.vy = 0;
        continue;
      }}

      n.vx *= damping;
      n.vy *= damping;

      n.x += n.vx * 0.01;
      n.y += n.vy * 0.01;
    }}
  }}

  function draw() {{
    var r = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, r.width, r.height);

    // links
    for (var li = 0; li < links.length; li++) {{
      var l = links[li];
      var p1 = worldToScreen(l.source.x, l.source.y);
      var p2 = worldToScreen(l.target.x, l.target.y);

      ctx.lineWidth = 2;
      ctx.strokeStyle = l.color || "#9da0a2";
      ctx.beginPath();
      ctx.moveTo(p1[0], p1[1]);
      ctx.lineTo(p2[0], p2[1]);
      ctx.stroke();

      // label
      var mx = (p1[0] + p2[0]) / 2;
      var my = (p1[1] + p2[1]) / 2;
      ctx.fillStyle = "rgba(0,0,0,0.6)";
      ctx.font = "11px Consolas, monospace";
      ctx.fillText(l.label, mx + 6, my - 6);
    }}

    // nodes
    for (var ni = 0; ni < nodes.length; ni++) {{
      var n = nodes[ni];
      var p = worldToScreen(n.x, n.y);
      var rr = n.endpoint ? 16 : 22;

      ctx.beginPath();
      ctx.fillStyle = n.endpoint ? "#fff5cc" : "#f6f8fa";
      ctx.strokeStyle = "#111827";
      ctx.lineWidth = 2;
      ctx.arc(p[0], p[1], rr, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#111827";
      ctx.font = "12px Segoe UI, Arial, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(n.id, p[0], p[1] + rr + 14);
    }}
  }}

  function tick() {{
    step();
    draw();
    window.requestAnimationFrame(tick);
  }}

  tick();

}})();
</script>
</body>
</html>
""".format(title=title, data_json=data_json)

    out_path.write_text(html, encoding="utf-8")


# ---------------------------
# Draw.io exporters 
# ---------------------------

def write_drawio(collapsed_edges, out_path: Path, title="Topology"):
    """
    Draw.io .drawio exporter tuned for Lucid import.
    Produces a simple grid layout with guaranteed on-canvas coordinates.
    """
    nodes = sorted({n for e in collapsed_edges.values() for n in (e["A"], e["B"])})
    idx = {n: i for i, n in enumerate(nodes)}

    # Grid layout (deterministic, on-canvas)
    cols = max(1, int(math.ceil(math.sqrt(len(nodes)))))
    cell_w, cell_h = 180, 80
    gap_x, gap_y = 60, 60
    start_x, start_y = 40, 40

    # mxfile -> diagram -> mxGraphModel -> root -> mxCell...
    mxfile = ET.Element("mxfile", {
        "host": "app.diagrams.net",
        "modified": "1",
        "agent": "topo_map",
        "version": "20.6.0",
        "type": "device"
    })

    diagram = ET.SubElement(mxfile, "diagram", {"id": "diagram1", "name": title})

    model = ET.Element("mxGraphModel", {
        "dx": "1000", "dy": "1000",
        "grid": "1", "gridSize": "10",
        "guides": "1", "tooltips": "1",
        "connect": "1", "arrows": "1",
        "fold": "1",
        "page": "1",
        "pageScale": "1",
        "pageWidth": "1600",
        "pageHeight": "1200",
        "math": "0",
        "shadow": "0"
    })

    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    # Vertices
    for i, name in enumerate(nodes):
        col = i % cols
        row = i // cols
        x = start_x + col * (cell_w + gap_x)
        y = start_y + row * (cell_h + gap_y)

        cell_id = f"n{i+2}"
        if RE_MAC_DOTTED.match(name):
            style = "ellipse;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;"
        else:
            style = "rounded=1;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;"

        cell = ET.SubElement(root, "mxCell", {
            "id": cell_id,
            "value": name,
            "style": style,
            "vertex": "1",
            "parent": "1"
        })

        ET.SubElement(cell, "mxGeometry", {
            "x": str(x),
            "y": str(y),
            "width": str(cell_w),
            "height": str(cell_h),
            "as": "geometry"
        })

    # Edges
    eid = 1000
    for e in collapsed_edges.values():
        a = e["A"]
        b = e["B"]
        src = f"n{idx[a]+2}"
        tgt = f"n{idx[b]+2}"

        eid += 1
        label = e["label"].replace("\\n", " | ")
        color = e["color"]

        edge = ET.SubElement(root, "mxCell", {
            "id": f"e{eid}",
            "value": label,
            "style": f"endArrow=none;html=1;strokeColor={color};",
            "edge": "1",
            "parent": "1",
            "source": src,
            "target": tgt
        })

        ET.SubElement(edge, "mxGeometry", {
            "relative": "1",
            "as": "geometry"
        })

    # IMPORTANT: diagram element content should be the serialized model (as text)
    diagram.text = ET.tostring(model, encoding="unicode")

    out_path.write_text(ET.tostring(mxfile, encoding="unicode"), encoding="utf-8")

    """
    Write a Draw.io (.drawio / mxGraphModel XML) file with nodes & connectors.
    Layout is a simple grid; Lucid can re-layout and style after import.
    """
    nodes = sorted({n for e in collapsed_edges.values() for n in (e["A"], e["B"])})
    idx = {n: i for i, n in enumerate(nodes)}
    cols = max(1, int(math.ceil(math.sqrt(len(nodes)))))
    cell_w, cell_h = 160, 80
    margin_x, margin_y = 40, 40

    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "modified": "", "agent": "topo_map", "etag": "1"})
    diagram = ET.SubElement(mxfile, "diagram", {"name": title, "id": "diagram1"})
    m = ET.Element("mxGraphModel", {"dx":"0","dy":"0","grid":"1","gridSize":"10","guides":"1","tooltips":"1","connect":"1","arrows":"1","fold":"1","page":"1","pageScale":"1","pageWidth":"850","pageHeight":"1100"})
    root = ET.SubElement(m, "root")
    ET.SubElement(root, "mxCell", {"id":"0"})
    ET.SubElement(root, "mxCell", {"id":"1", "parent":"0"})

    for i, name in enumerate(nodes):
        col = i % cols
        row = i // cols
        x = margin_x + col * (cell_w + margin_x)
        y = margin_y + row * (cell_h + margin_y)
        cell_id = f"n{i+2}"
        if RE_MAC_DOTTED.match(name):
            style = "ellipse;whiteSpace=wrap;html=1;perimeter=ellipse;"
        else:
            style = "rounded=1;whiteSpace=wrap;html=1;perimeter=rectangle;"
        v = ET.SubElement(root, "mxCell", {"id": cell_id, "value": name, "style": style, "vertex":"1", "parent":"1"})
        geom = ET.SubElement(v, "mxGeometry", {"x":str(x), "y":str(y), "width":str(cell_w), "height":str(cell_h), "as":"geometry"})
        v.append(geom)

    eid = len(nodes) + 10
    for e in collapsed_edges.values():
        a = e["A"]; b = e["B"]
        src = f"n{idx[a]+2}"; tgt = f"n{idx[b]+2}"
        eid += 1
        style_line = f"strokeColor={e['color']};endArrow=none;"
        val = e["label"].replace("\\n", " | ")
        edge = ET.SubElement(root, "mxCell", {"id": f"e{eid}", "value": val, "style": style_line, "edge":"1", "parent":"1", "source":src, "target":tgt})
        geom = ET.SubElement(edge, "mxGeometry", {"relative":"1", "as":"geometry"})
        edge.append(geom)

    diagram.append(m)
    mxfile_str = ET.tostring(mxfile, encoding="utf-8", method="xml")
    out_path.write_bytes(mxfile_str)

def write_drawio_csv(collapsed_edges, out_path: Path):
    rows = [("From","To","Label","LinkColor","LinkCount","TypeFrom","TypeTo")]
    for e in collapsed_edges.values():
        A = e["A"]; B = e["B"]
        rows.append((
            A,
            B,
            e["label"].replace("\\n", " | "),
            e["color"],
            len(e["links"]),
            "endpoint" if is_endpointish(A) else "switch",
            "endpoint" if is_endpointish(B) else "switch",
        ))
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)

# ---------------------------
# Main
# ---------------------------

def main():
    ap = argparse.ArgumentParser(description="Build topology DOT/HTML/Drawio from LLDP/CDP outputs (optional color from status).")
    ap.add_argument("-d", "--directory", required=True, help="Folder with *_lldp.txt, *_cdp.txt, *_status.txt files")
    ap.add_argument("-o", "--output", default="topology.dot", help="DOT output path")
    ap.add_argument("--csv", help="Optional RAW edges CSV output path (one row per discovered edge)")
    ap.add_argument("--collapsed-csv", help="Optional COLLAPSED edges CSV output path (one row per device-pair)")
    ap.add_argument("--html", default="topology.html", help="HTML output path (renders in browser via viz.js CDN)")
    ap.add_argument("--html-offline", help="Offline HTML output (no CDN, no Graphviz).")
    ap.add_argument("--drawio", help="Write Draw.io .drawio XML output (import into Lucid)")
    ap.add_argument("--drawio-csv", help="Write Draw.io-compatible CSV (connector-based)")
    ap.add_argument("--lucid-csv", help="Lucid CSV (connections-based) shorthand")
    ap.add_argument("--title", default="Topology", help="Title shown in outputs")
    ap.add_argument("--prefer", choices=["lldp", "cdp", "merge"], default="merge", help="If both LLDP & CDP exist, prefer one or merge")
    args = ap.parse_args()

    root = Path(args.directory)

    raw_edges = []
    nodes = set()
    lldp_by_key = defaultdict(list)
    cdp_by_key = defaultdict(list)

    for f in root.glob("*_lldp.txt"):
        for (lh, lp, rh, rp) in parse_lldp(f):
            k = edge_key(lh, lp, rh, rp)
            lldp_by_key[k].append((lh, lp, rh, rp))
            nodes.update([lh, rh])

    for f in root.glob("*_cdp.txt"):
        for (lh, lp, rh, rp) in parse_cdp(f):
            k = edge_key(lh, lp, rh, rp)
            cdp_by_key[k].append((lh, lp, rh, rp))
            nodes.update([lh, rh])

    all_keys = set(lldp_by_key.keys()) | set(cdp_by_key.keys())
    for k in sorted(all_keys, key=lambda x: str(x)):
        l = lldp_by_key.get(k, []); c = cdp_by_key.get(k, [])
        if args.prefer == "lldp" and l:
            chosen = l; source = "lldp"
        elif args.prefer == "cdp" and c:
            chosen = c; source = "cdp"
        else:
            chosen = l or c
            source = "lldp+cdp" if (l and c) else ("lldp" if l else "cdp")
        for (lh, lp, rh, rp) in chosen:
            raw_edges.append((lh, lp, rh, rp, source))

    status_maps = {}
    for f in root.glob("*_status.txt"):
        host = f.name.replace("_status.txt", "")
        status_maps[host] = parse_status_file(f)

    collapsed = collapse_links(raw_edges, status_maps)

    dot_text = build_dot(nodes, collapsed, title=args.title)
    Path(args.output).write_text(dot_text, encoding="utf-8")

    if args.csv:
        csv_rows = [("local_host","local_port","remote_host","remote_port","source","status_color")]
        for (lh, lp, rh, rp, source) in raw_edges:
            sa = status_maps.get(lh, {}).get(lp, (None, None))[0]
            sb = status_maps.get(rh, {}).get(rp, (None, None))[0]
            ecolor = pick_color(sa, sb)
            csv_rows.append((lh, lp, rh, rp, source, ecolor))
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(csv_rows)

    if args.collapsed_csv:
        csv_rows = [("host_a","host_b","link_count","source","status_color","links_label")]
        for e in collapsed.values():
            csv_rows.append((e["A"], e["B"], len(e["links"]), e["source"], e["color"], e["label"].replace("\\n", " | ")))
        with open(args.collapsed_csv, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(csv_rows)

   # if args.html:
    #    write_html(dot_text, Path(args.html), title=args.title)

    if args.html_offline:
        write_html_offline(nodes, collapsed, Path(args.html_offline), title=args.title + " (offline)")

    if args.drawio:
        write_drawio(collapsed, Path(args.drawio), title=args.title)
        print(f"Wrote {args.drawio} (import into Lucid)")

    if args.drawio_csv:
        write_drawio_csv(collapsed, Path(args.drawio_csv))
        print(f"Wrote {args.drawio_csv} (draw.io CSV)")

    if args.lucid_csv:
        write_drawio_csv(collapsed, Path(args.lucid_csv))
        print(f"Wrote {args.lucid_csv} (Lucid/drawio-compatible CSV)")

    print(f"Wrote {args.output}")
    if args.csv:
        print(f"Wrote {args.csv}")
    if args.collapsed_csv:
        print(f"Wrote {args.collapsed_csv}")
    if args.html:
        print(f"Wrote {args.html} (CDN HTML)")
    if args.html_offline:
        print(f"Wrote {args.html_offline} (offline HTML)")
    if args.drawio:
        print(f"Wrote {args.drawio} (Draw.io XML)")
    if args.drawio_csv:
        print(f"Wrote {args.drawio_csv} (Draw.io CSV)")

if __name__ == "__main__":
    main()
