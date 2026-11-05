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