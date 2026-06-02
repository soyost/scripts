from flask import Flask, redirect
import subprocess
import os

app = Flask(__name__)

VIDEO_DIR = "/home/steven/aquarium"

current_process = None


def stop_video():
    global current_process

    if current_process:
        try:
            current_process.terminate()
            current_process.wait(timeout=2)
        except Exception as e:
            print(f"Error stopping video: {e}")

        current_process = None


def play_video(filename):
    global current_process

    stop_video()

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


@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>Aquarium Control</title>

        <style>
            body {
                background-color: #001018;
                color: white;
                font-family: Arial;
                text-align: center;
                padding-top: 40px;
            }

            h1 {
                margin-bottom: 40px;
            }

            button {
                width: 260px;
                height: 70px;
                font-size: 22px;
                margin: 15px;
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

        <h1>🐠 Aquarium Control</h1>

        <form action="/play/fish-tank.mp4">
            <button type="submit">
                Play Fish Tank
            </button>
        </form>

        <form action="/play/beta-fish.mp4">
            <button type="submit">
                Play Beta Fish
            </button>
        </form>

        <form action="/stop">
            <button type="submit">
                Stop Video
            </button>
        </form>

    </body>
    </html>
    """


@app.route("/play/<filename>")
def play(filename):
    play_video(filename)
    return redirect("/")


@app.route("/stop")
def stop():
    stop_video()
    return redirect("/")


import sys

if len(sys.argv) > 1:

    mode = sys.argv[1]

    if mode == "night":
        run_mode("/home/steven/aquarium/particles.py")

    elif mode == "day":
        play_video("fish-tank.mp4")

else:
    app.run(host="0.0.0.0", port=5000)