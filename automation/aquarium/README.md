# Ambient Aquarium

A Raspberry Pi powered ambient display system that can play looping aquarium videos or procedural visualizations (jellyfish, particles, etc.) and be controlled from a phone via a Flask web interface.

---

# Overview

The system consists of three major components:

## 1. Flask Control Server (`ambient.py`)

Runs continuously as a systemd service.

Responsibilities:

* Provides web UI
* Allows mode selection from phone
* Runs on port 5000
* Starts automatically at boot

The Flask server is the "control plane" of the aquarium.

Example:

```bash
http://<raspberrypi-ip>:5000
```

---

## 2. Display Engine (`mode.py`)

Responsible for launching visual modes.

Supported modes:

* day
* night
* jellyfish

When a new mode is selected:

* Existing visual processes are terminated
* New visual process is launched

Current implementation:

### Day Mode

Launches:

(`fish-tank.mp4`)

using mpv fullscreen looping playback.

### Night Mode

Launches:

(`particles.py`)

using pygame.

### Jellyfish Mode

Launches:

(`jellyfish.py`)

using pygame.

---

## 3. Scheduler (cron)

Automatically changes aquarium modes based on time of day.

Current schedule:

06:00 AM -> Day Mode

05:00 PM -> Night Mode

Configured via cron

Current entries:

```bash
0 6 * * * /home/steven/aquarium/day.sh
0 17 * * * /home/steven/aquarium/night.sh
```

---

# Directory Structure

### (`/home/steven/aquarium/`)

ambient.py

mode.py

day.sh

night.sh

fish-tank.mp4

beta-fish.mp4

particles.py

jellyfish.py

tank.py # legacy prototype

---

# Web Interface

Phone connects to:

```bash
http://<raspberrypi-ip>:5000
```

Available actions:

* Play Fish Tank Video
* Play Beta Fish Video
* Jellyfish Generator
* Particle Ocean

The web UI communicates with the display engine to switch modes.

---

# Manual Mode Control

Launch day mode:

python3 /home/steven/aquarium/mode.py day

Launch night mode:

python3 /home/steven/aquarium/mode.py night

Launch jellyfish mode:

python3 /home/steven/aquarium/mode.py jellyfish

# Design Decisions

## Notes

The Raspberry Pi is never powered off automatically.

Reasons:

* Flask remains available
* Faster response
* Simpler architecture
* No SD card wear concerns from repeated shutdowns


(`mode.py`)

Transient display controller.

Handles:

* Launching visuals
* Switching display modes

