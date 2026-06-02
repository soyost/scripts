import subprocess
import os
import sys

VIDEO_DIR = "/home/steven/aquarium"

env = os.environ.copy()
env["DISPLAY"] = ":0"

# Kill previous visuals
subprocess.run("pkill -f mpv", shell=True)
subprocess.run("pkill -f jellyfish.py", shell=True)
subprocess.run("pkill -f particles.py", shell=True)

mode = sys.argv[1]

if mode == "day":

    subprocess.Popen([
        "mpv",
        "--fs",
        "--loop",
        "--no-terminal",
        f"{VIDEO_DIR}/fish-tank.mp4"
    ], env=env)

elif mode == "night":

    subprocess.Popen([
        "python3",
        f"{VIDEO_DIR}/particles.py"
    ], env=env)

elif mode == "jellyfish":

    subprocess.Popen([
        "python3",
        f"{VIDEO_DIR}/jellyfish.py"
    ], env=env)