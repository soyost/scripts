#!/usr/bin/env python3

import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

TCP_HOST = "0.0.0.0"
TCP_PORT = 5000

WEB_HOST = "0.0.0.0"
WEB_PORT = 8080

MAX_LINES = 10
MAX_LINE_LENGTH = 70

caption_buffer = ["Waiting for captions..."]
buffer_lock = threading.Lock()


def clean_708_text(data: bytes) -> list[str]:
    """
    Assumes vendor/device is sending 708 over TCP as readable text.

    Expected cleanup:
    - Decode TCP bytes as UTF-8-ish text
    - Remove leading -123 from each line
    - Preserve music notes as their own line
    - Remove non-printable junk
    - Normalize spacing without destroying intentional newlines
    """

    text = data.decode("utf-8", errors="ignore")

    # Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove non-printable characters but keep newlines and tabs
    text = re.sub(r"[^\x20-\x7E\n\t]", "", text)

    # Remove leading -123 at beginning of each line
    text = re.sub(r"(?m)^\s*-123\s*", "", text)

    # Censor filter
    text = text.replace("#(", "*")

    # Music notation
    text = text.replace("&-p7", "\n♪\n")

    # Force music on separate line
    text = text.replace("♪", "\n♪\n")

    # Paragraph lines
    text = re.sub(r"&-p\d*", " ", text)

    # Normalize spaces/tabs, but preserve newlines
    text = re.sub(r"[ \t]+", " ", text)

    # Clean each line
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            lines.append(line)

    return lines


def add_caption_line(line: str):
    global caption_buffer

    if not line:
        return

    with buffer_lock:
        if line == "♪":
            caption_buffer.append(line)
        elif not caption_buffer:
            caption_buffer.append(line)
        else:
            last = caption_buffer[-1]

            if last in ("Waiting for captions...", "CC device connected...", "CC device disconnected", "♪"):
                caption_buffer.append(line)
            else:
                combined = f"{last} {line}".strip()

                if len(combined) < MAX_LINE_LENGTH:
                    caption_buffer[-1] = combined
                else:
                    caption_buffer.append(line)

        caption_buffer = caption_buffer[-MAX_LINES:]


def tcp_listener():
    global caption_buffer

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((TCP_HOST, TCP_PORT))
        server.listen(5)

        print(f"TCP listener started on {TCP_HOST}:{TCP_PORT}")

        while True:
            client, address = server.accept()
            print(f"CC device connected from {address}")

            with buffer_lock:
                caption_buffer = ["CC device connected..."]

            try:
                with client:
                    while True:
                        data = client.recv(4096)

                        if not data:
                            break

                        lines = clean_708_text(data)

                        for line in lines:
                            add_caption_line(line)

            except Exception as error:
                print(f"TCP client error: {error}")

            with buffer_lock:
                caption_buffer.append("CC device disconnected")
                caption_buffer = caption_buffer[-MAX_LINES:]

            print("CC device disconnected")


HTML = """
<!doctype html>
<html>

<head>

<title>Closed Captions</title>

<style>

body {
    background: black;
    color: magenta;
    font-family: Arial;
    padding: 20px;
    overflow-x: hidden;
}

#toolbar {
    background: #222;
    color: white;
    padding: 10px;
    margin-bottom: 20px;
    font-size: 16px;
    font-family: Arial;
}

#toolbar select,
#toolbar input {
    margin-right: 20px;
}

#caption {
    color: magenta;
    font-size: 32px;
    font-family: Arial;
    white-space: pre-wrap;
    overflow-wrap: break-word;
    line-height: 1.3;
}

</style>

</head>

<body>

<div id="toolbar">

    Color:
    <select onchange="setColor(this.value)">
        <option value="magenta" selected>Magenta</option>
        <option value="white">White</option>
        <option value="yellow">Yellow</option>
        <option value="lime">Green</option>
        <option value="cyan">Cyan</option>
    </select>

    Font size:
    <input type="range" min="20" max="60" value="32" oninput="setFontSize(this.value)">
    <span id="fontSizeLabel">32px</span>

    Font:
    <select onchange="setFont(this.value)">
        <option value="Arial" selected>Arial</option>
        <option value="Verdana">Verdana</option>
        <option value="Courier New">Courier New</option>
        <option value="Tahoma">Tahoma</option>
    </select>

    Line spacing:
    <input type="range" min="1.0" max="2.0" step="0.1" value="1.3" oninput="setLineHeight(this.value)">
    <span id="lineHeightLabel">1.3</span>

    <button onclick="toggleToolbar()">Hide Toolbar</button>

</div>

<div id="caption">Waiting for captions...</div>

<script>

function setColor(value) {
    document.getElementById('caption').style.color = value;
}

function setFontSize(value) {
    document.getElementById('caption').style.fontSize = value + 'px';
    document.getElementById('fontSizeLabel').innerText = value + 'px';
}

function setFont(value) {
    document.getElementById('caption').style.fontFamily = value;
}

function setLineHeight(value) {
    document.getElementById('caption').style.lineHeight = value;
    document.getElementById('lineHeightLabel').innerText = value;
}

function toggleToolbar() {
    document.getElementById('toolbar').style.display = 'none';
}

async function updateCaption() {
    let response = await fetch('/caption?t=' + Date.now());
    let text = await response.text();
    document.getElementById('caption').innerText = text;
}

setInterval(updateCaption, 500);
updateCaption();

</script>

</body>

</html>
"""


class CaptionWebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/caption":
            with buffer_lock:
                content = "\r\n".join(caption_buffer)

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))

    def log_message(self, format, *args):
        return


def web_server():
    print(f"Web server started on http://{WEB_HOST}:{WEB_PORT}")
    server = HTTPServer((WEB_HOST, WEB_PORT), CaptionWebHandler)
    server.serve_forever()


if __name__ == "__main__":
    tcp_thread = threading.Thread(target=tcp_listener, daemon=True)
    tcp_thread.start()

    web_server()