#!/usr/bin/env python3
"""Local, read-only Cisco NX-OS interface monitoring dashboard."""
import argparse
import logging
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from getpass import getpass

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output
from netmiko import ConnectHandler

LOG = logging.getLogger('network-dashboard')
INTERFACE_RE = re.compile(r'^(?:ethernet|eth)\d+(?:/\d+){1,2}$', re.I)
TARGET_RE = re.compile(r'^([A-Za-z0-9][A-Za-z0-9_.-]*):(.+)$')
COUNTERS = ('crc', 'input_errors', 'output_errors', 'input_discards', 'output_discards')
MOCK_OUTPUT = '''Ethernet1/36 is up
admin state is up, Dedicated Interface
  Belongs to Po254
  Description: ATEME TITAN ENCODER 1
  full-duplex, 10 Gb/s, media type is 10G
  Load-Interval #1: 30 seconds
    30 seconds input rate 10893728 bits/sec, 966 packets/sec
    30 seconds output rate 47232 bits/sec, 81 packets/sec
  RX
    434538226 input packets 487930474886 bytes
    0 runts 0 giants 0 CRC 0 no buffer
    0 input error 0 short frame
    0 input with dribble 0 input discard
  TX
    341086514 output packets 56984982010 bytes
    0 output error 0 collision
    0 lost carrier 0 no carrier 0 output discard
'''


def canonical_interface(name):
    if not INTERFACE_RE.fullmatch(name):
        raise ValueError(f'Invalid Ethernet interface: {name}')
    return 'Ethernet' + re.sub(r'^(?:ethernet|eth)', '', name, flags=re.I)


def parse_interface(output, expected_interface=None):
    def find(pattern):
        m = re.search(pattern, output, re.I | re.M)
        return m.group(1).strip() if m else None

    header = re.search(r'^\s*(Ethernet\d+(?:/\d+){1,2}) is (up|down|administratively down)\b', output, re.I | re.M)
    if not header:
        raise ValueError('Missing or invalid NX-OS interface header')
    name = canonical_interface(header.group(1))
    if expected_interface and name.lower() != canonical_interface(expected_interface).lower():
        raise ValueError(f'Unexpected interface in response: {name}')
    rx = find(r'30 seconds input rate\s+(\d+)\s+bits/sec')
    tx = find(r'30 seconds output rate\s+(\d+)\s+bits/sec')
    if rx is None or tx is None:
        raise ValueError('Missing 30-second throughput rates')

    def number(pattern):
        val = find(pattern)
        return int(val) if val is not None else None

    speed = find(r'\bfull-duplex,\s*([\d.]+)\s*Gb/s')
    return dict(
        timestamp=datetime.now(), interface=name, state=header.group(2).lower(),
        description=find(r'^\s*Description:\s*(.+)$'),
        port_channel=find(r'Belongs to\s+(Po\d+)'),
        speed_gbps=float(speed) if speed else None,
        rx_bps=int(rx), tx_bps=int(tx),
        rx_pps=number(r'30 seconds input rate\s+\d+\s+bits/sec,\s*(\d+)\s+packets/sec'),
        tx_pps=number(r'30 seconds output rate\s+\d+\s+bits/sec,\s*(\d+)\s+packets/sec'),
        rx_bytes=number(r'\d+\s+input packets\s+(\d+)\s+bytes'),
        tx_bytes=number(r'\d+\s+output packets\s+(\d+)\s+bytes'),
        crc=number(r'(\d+)\s+CRC\b'),
        input_errors=number(r'(\d+)\s+input error\b'),
        output_errors=number(r'(\d+)\s+output error\b'),
        input_discards=number(r'(\d+)\s+input discard\b'),
        output_discards=number(r'(\d+)\s+output discard\b'),
    )


def calculate_deltas(current, previous):
    deltas = {}
    for key in COUNTERS:
        now = current.get(key)
        old = previous.get(key) if previous else None
        deltas[key] = None if now is None or old is None or now < old else now - old
    return deltas


def build_targets(args, parser):
    result = defaultdict(list)
    if args.switch:
        if not args.interface:
            parser.error('--switch requires at least one --interface')
        for iface in args.interface:
            try:
                iface = canonical_interface(iface)
            except ValueError as exc:
                parser.error(str(exc))
            if iface not in result[args.switch]:
                result[args.switch].append(iface)
    elif args.interface:
        parser.error('--interface requires --switch')
    for item in args.target or []:
        match = TARGET_RE.fullmatch(item)
        if not match:
            parser.error(f'Invalid target {item!r}; use SWITCH:eth1/36')
        host, iface = match.groups()
        try:
            iface = canonical_interface(iface)
        except ValueError as exc:
            parser.error(str(exc))
        if iface not in result[host]:
            result[host].append(iface)
    if not result:
        parser.error('Specify -s SWITCH -i INTERFACE [INTERFACE ...] or --target SWITCH:INTERFACE')
    return dict(result)


class Monitor:
    def __init__(self, targets, interval, username, password, demo=False, max_samples=1440):
        self.targets = targets
        self.interval = interval
        self.username = username
        self.password = password
        self.demo = demo
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.data = {}
        for host, ifaces in targets.items():
            for iface in ifaces:
                self.data[f'{host}:{iface}'] = dict(samples=deque(maxlen=max_samples), latest=None, error=None, last_success=None, previous=None)
        self.cycle = 0
        # Connections are owned exclusively by the polling thread.
        self.connections = {}

    def record_success(self, key, stats):
        with self.lock:
            entry = self.data[key]
            stats['deltas'] = calculate_deltas(stats, entry['previous'])
            entry['previous'] = stats
            entry['latest'] = stats
            entry['last_success'] = stats['timestamp']
            entry['error'] = None
            entry['samples'].append(stats)
        LOG.info('%s RX %.3f Mbps TX %.3f Mbps', key, stats['rx_bps']/1e6, stats['tx_bps']/1e6)

    def record_failure(self, key, exc):
        with self.lock:
            entry = self.data[key]
            entry['error'] = f'{type(exc).__name__}: {exc}'
            entry['samples'].append(dict(timestamp=datetime.now(), rx_bps=None, tx_bps=None))
            # Preserve last counters for deltas across a failed poll, but show gap in graph.
        LOG.warning('%s collection failed: %s', key, type(exc).__name__)

    def close_connection(self, host):
        conn = self.connections.pop(host, None)
        if conn is not None:
            try:
                conn.disconnect()
            except Exception:
                pass

    def get_connection(self, host):
        conn = self.connections.get(host)
        if conn is not None:
            try:
                if conn.is_alive():
                    return conn
            except Exception:
                pass
            LOG.warning('%s SSH session lost; reconnecting', host)
            self.close_connection(host)

        # Authenticate only when starting or replacing a lost session.
        conn = ConnectHandler(
            device_type='cisco_nxos', host=host,
            username=self.username, password=self.password,
            conn_timeout=15, auth_timeout=15,
        )
        self.connections[host] = conn
        LOG.info('%s SSH session established', host)
        return conn

    def poll_once(self):
        for host, ifaces in self.targets.items():
            if self.stop.is_set():
                break
            if self.demo:
                for index, iface in enumerate(ifaces):
                    stats = parse_interface(MOCK_OUTPUT)
                    stats['interface'] = iface
                    factor = 0.86 + ((self.cycle + index * 3) % 12) * 0.025
                    stats['rx_bps'] = int(stats['rx_bps'] * factor)
                    stats['tx_bps'] = int(stats['tx_bps'] * factor)
                    stats['input_discards'] = max(0, self.cycle - 2) if index == 0 else 0
                    self.record_success(f'{host}:{iface}', stats)
                continue

            try:
                conn = self.get_connection(host)
            except Exception as exc:
                LOG.warning('%s SSH connection failed: %s', host, type(exc).__name__)
                for iface in ifaces:
                    self.record_failure(f'{host}:{iface}', exc)
                continue

            for index, iface in enumerate(ifaces):
                if self.stop.is_set():
                    break
                key = f'{host}:{iface}'
                try:
                    output = conn.send_command(f'show interface {iface}', read_timeout=30)
                except Exception as exc:
                    # A command/transport failure may leave the SSH channel unusable.
                    # Reconnect on the next cycle, not repeatedly within this one.
                    self.record_failure(key, exc)
                    LOG.warning('%s SSH command failed; will reconnect next cycle', host)
                    self.close_connection(host)
                    for remaining in ifaces[index + 1:]:
                        self.record_failure(f'{host}:{remaining}', exc)
                    break
                try:
                    stats = parse_interface(output, expected_interface=iface)
                    self.record_success(key, stats)
                except Exception as exc:
                    # Bad CLI output does not require a fresh login.
                    self.record_failure(key, exc)
        self.cycle += 1

    def run(self):
        try:
            while not self.stop.is_set():
                start = time.monotonic()
                self.poll_once()
                self.stop.wait(max(0, self.interval - (time.monotonic() - start)))
        finally:
            for host in list(self.connections):
                self.close_connection(host)

    def snapshot(self):
        with self.lock:
            return {key: dict(samples=list(entry['samples']), latest=entry['latest'],
                              error=entry['error'], last_success=entry['last_success'])
                    for key, entry in self.data.items()}


def format_rate(bps):
    if bps is None:
        return 'N/A'
    if bps >= 1e9:
        return f'{bps / 1e9:.3f} Gbps'
    if bps >= 1e6:
        return f'{bps / 1e6:.3f} Mbps'
    return f'{bps / 1e3:.2f} Kbps'


def format_number(value):
    return f'{value:,}' if value is not None else 'N/A'


def create_app(monitor, port):
    app = Dash(__name__)
    app.title = 'Network Interface Monitor'
    keys = list(monitor.data)
    card_style = {'border': '1px solid #dce1e8', 'borderRadius': '9px', 'padding': '15px',
                  'backgroundColor': '#f8fafc', 'flex': '1', 'minWidth': '155px'}

    def card(label, value):
        return html.Div([html.Div(label, style={'fontSize':'13px', 'color':'#586174'}),
                         html.H2(value, style={'margin':'8px 0 0'})], style=card_style)

    app.layout = html.Div([
        html.H1('Network Interface Monitor'),
        html.Div([
            html.Div([html.Label('Interface'), dcc.Dropdown(id='selected-interface',
                options=[{'label': k, 'value': k} for k in keys], value=keys[0], clearable=False)],
                style={'flex':'2', 'minWidth':'300px'}),
            html.Div([html.Label('Chart mode'), dcc.RadioItems(id='chart-mode',
                options=[{'label':'Dual axes', 'value':'dual'}, {'label':'Single axis', 'value':'single'}],
                value='dual', inline=True)], style={'flex':'1', 'minWidth':'210px'}),
        ], style={'display':'flex','gap':'22px','flexWrap':'wrap','alignItems':'end'}),
        html.Div(id='status', style={'marginTop':'16px'}),
        html.Div(id='description', style={'marginBottom':'15px'}),
        html.Div(id='cards', style={'display':'flex','gap':'12px','flexWrap':'wrap'}),
        html.H3('Interface Throughput'),
        dcc.Checklist(id='traffic-filter', options=[{'label':' Inbound', 'value':'rx'},
            {'label':' Outbound', 'value':'tx'}], value=['rx','tx'], inline=True),
        dcc.Graph(id='traffic-graph'),
        html.H3('Errors and Discards'),
        html.Div(id='error-table'),
        html.P(id='last-updated', style={'color':'#586174'}),
        dcc.Interval(id='refresh', interval=5000, n_intervals=0),
    ], style={'fontFamily':'Arial,sans-serif','maxWidth':'1160px','margin':'30px auto','padding':'0 20px'})

    @app.callback(
        Output('status','children'), Output('description','children'), Output('cards','children'),
        Output('traffic-graph','figure'), Output('error-table','children'), Output('last-updated','children'),
        Input('refresh','n_intervals'), Input('selected-interface','value'),
        Input('traffic-filter','value'), Input('chart-mode','value'))
    def update(_n, key, selected, mode):
        snap = monitor.snapshot()[key]
        stats, err, samples = snap['latest'], snap['error'], snap['samples']
        if err:
            status = html.Strong('Collection unavailable: ' + err, style={'color':'#b91c1c'})
        elif stats:
            status = html.Strong('Interface: ' + stats['state'].upper(),
                                 style={'color':'#15803d' if stats['state']=='up' else '#b45309'})
        else:
            status = 'Waiting for first sample...'
        desc = ('Description: ' + (stats.get('description') or 'N/A') +
                ' | Port-channel: ' + (stats.get('port_channel') or 'None') +
                ' | Speed: ' + (f"{stats['speed_gbps']:g} Gbps" if stats.get('speed_gbps') else 'N/A')) if stats else ''
        current = stats if stats and not err else None
        cards = [card('Inbound (30s)', format_rate(current['rx_bps']) if current else 'N/A'),
                 card('Outbound (30s)', format_rate(current['tx_bps']) if current else 'N/A'),
                 card('RX packets/sec', format_number(current['rx_pps']) if current else 'N/A'),
                 card('TX packets/sec', format_number(current['tx_pps']) if current else 'N/A')]
        dual = mode == 'dual'
        fig = make_subplots(specs=[[{'secondary_y': True}]])
        times = [s['timestamp'] for s in samples]
        for direction, label, axis in [('rx','Inbound Mbps',False),('tx','Outbound Mbps',dual)]:
            if direction in (selected or []):
                fig.add_trace(go.Scatter(x=times,
                    y=[s[f'{direction}_bps']/1e6 if s.get(f'{direction}_bps') is not None else None for s in samples],
                    name=label, mode='lines+markers', connectgaps=False), secondary_y=axis)
        fig.update_yaxes(title_text='Inbound Mbps' if dual else 'Mbps', rangemode='tozero', secondary_y=False)
        if dual:
            fig.update_yaxes(title_text='Outbound Mbps', rangemode='tozero', secondary_y=True)
        fig.update_layout(template='plotly_white', height=450, hovermode='x unified',
                          legend={'orientation':'h', 'y':1.12}, margin={'t':55})
        if stats:
            rows = []
            labels = {'crc':'CRC errors','input_errors':'Input errors','output_errors':'Output errors',
                      'input_discards':'Input discards','output_discards':'Output discards'}
            for counter_name in COUNTERS:
                delta = stats['deltas'].get(counter_name)
                delta_text = 'baseline' if delta is None else f'+{delta:,}'
                rows.append(html.Tr([
                    html.Td(labels[counter_name], style={'padding':'9px'}),
                    html.Td(format_number(stats.get(counter_name)), style={'padding':'9px'}),
                    html.Td(delta_text, style={'padding':'9px', 'fontWeight':'bold' if delta and delta > 0 else 'normal',
                                              'color':'#b91c1c' if delta and delta > 0 else '#475569'})]))
            errors = html.Table([
                html.Thead(html.Tr([html.Th('Counter'), html.Th('Cumulative'), html.Th('Since previous successful poll')])),
                html.Tbody(rows)], style={'borderCollapse':'collapse', 'width':'100%', 'maxWidth':'650px', 'textAlign':'left'})
        else:
            errors = 'No data yet.'
        updated = ('Last successful poll: ' + snap['last_success'].strftime('%Y-%m-%d %H:%M:%S')
                   if snap['last_success'] else 'No successful polls yet')
        if err:
            updated += ' | Current poll failed; values above may be stale.'
        return status, desc, cards, fig, errors, updated

    return app


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only Cisco NX-OS interface dashboard')
    parser.add_argument('-s','--switch', help='Switch hostname or IP')
    parser.add_argument('-i','--interface', nargs='+', help='One or more Ethernet interfaces on --switch')
    parser.add_argument('--target', action='append', help='Repeat SWITCH:INTERFACE to monitor multiple switches')
    parser.add_argument('--interval', type=int, default=60, help='Poll interval seconds (default: 60)')
    parser.add_argument('--port', type=int, default=8051)
    parser.add_argument('--demo', action='store_true', help='Simulate readings; no SSH')
    args = parser.parse_args(argv)
    if args.interval < 15:
        parser.error('--interval must be at least 15 seconds')
    if not 1 <= args.port <= 65535:
        parser.error('--port must be 1-65535')
    targets = build_targets(args, parser)
    username = password = None
    if not args.demo:
        username = input('SSH Username: ').strip()
        if not username:
            parser.error('SSH username required')
        password = getpass('SSH Password: ')
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
    logging.getLogger('paramiko').setLevel(logging.WARNING)
    monitor = Monitor(targets, args.interval, username, password, args.demo)
    thread = threading.Thread(target=monitor.run, daemon=True)
    thread.start()
    print(f'Dashboard: http://127.0.0.1:{args.port}')
    print('Press Ctrl+C to stop.')
    try:
        create_app(monitor, args.port).run(host='127.0.0.1', port=args.port, debug=False, use_reloader=False)
    finally:
        monitor.stop.set()
        thread.join(timeout=3)


if __name__ == '__main__':
    main()
