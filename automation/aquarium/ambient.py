from flask import Flask, redirect
import subprocess
import os
import signal

app = Flask(__name__)

VIDEO_DIR = "/home/steven/aquarium"

current_process = None


# -----------------------------
# Process Management
# -----------------------------

def stop_current():
    global current_process

    if current_process:
        try:
            current_process.terminate()
            current_process.wait(timeout=2)
        except:
            pass

        current_process = None


# -----------------------------
# Video Playback
# -----------------------------

def play_video(filename):
    global current_process

    stop_current()

    filepath = os.path.join(VIDEO_DIR, filename)

    env = os.environ.copy()
    env["DISPLAY"] = ":0"

    current_process = subprocess.Popen([
        "mpv",
        "--fs",
        "--loop",
        "--no-terminal",
        filepath
    ], env=env)


# -----------------------------
# Procedural Modes
# -----------------------------

def run_mode(script_name):
    global current_process

    stop_current()

    env = os.environ.copy()
    env["DISPLAY"] = ":0"

    current_process = subprocess.Popen([
        "python3",
        script_name
    ], env=env)


# -----------------------------
# Web UI
# -----------------------------

@app.route("/")
def home():
    return """
    <html>

    <head>
        <title>Ambient Aquarium</title>

        <style>

            body {
                background-color: #001018;
                color: white;
                font-family: Arial;
                text-align: center;
                padding-top: 30px;
            }

            h1 {
                margin-bottom: 40px;
            }

            button {
                width: 280px;
                height: 70px;
                font-size: 22px;
                margin: 14px;
                border-radius: 14px;
                border: none;
                background-color: #0077aa;
                color: white;
            }

            button:hover {
                background-color: #0099dd;
            }

        </style>
    </head>

    <body>

        <h1>🌊 Ambient Aquarium</h1>

        <form action="/video/fish-tank.mp4">
            <button type="submit">
                Fish Tank Video
            </button>
        </form>

        <form action="/video/beta-fish.mp4">
            <button type="submit">
                Beta Fish Video
            </button>
        </form>

        <form action="/mode/jellyfish">
            <button type="submit">
                Jellyfish Generator
            </button>
        </form>

        <form action="/mode/particles">
            <button type="submit">
                Particle Ocean
            </button>
        </form>

        <form action="/stop">
            <button type="submit">
                Stop
            </button>
        </form>

    </body>
    </html>
    """


@app.route("/video/<filename>")
def video(filename):
    play_video(filename)
    return redirect("/")


@app.route("/mode/<name>")
def mode(name):

    if name == "jellyfish":
        run_mode("/home/steven/aquarium/jellyfish.py")

    elif name == "particles":
        run_mode("/home/steven/aquarium/particles.py")

    return redirect("/")


@app.route("/stop")
def stop():
    stop_current()
    return redirect("/")


app.run(host="0.0.0.0", port=5000)