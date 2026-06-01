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

fish-tank.mp4

using mpv fullscreen looping playback.

### Night Mode

Launches:

particles.py

using pygame.

### Jellyfish Mode

Launches:

jellyfish.py

using pygame.

---

## 3. Scheduler (cron)

Automatically changes aquarium modes based on time of day.

Current schedule:

06:00 AM -> Day Mode
05:00 PM -> Night Mode

Configured via:

crontab -e

Current entries:

```bash
0 6 * * * /home/steven/aquarium/day.sh
0 17 * * * /home/steven/aquarium/night.sh
```

---

# Directory Structure

/home/steven/aquarium/

ambient.py
mode.py

day.sh
night.sh

fish-tank.mp4
beta-fish.mp4

particles.py
jellyfish.py

tank.py (legacy prototype)

---

# Systemd Service

Service file:

/etc/systemd/system/aquarium.service

Purpose:

Automatically start Flask server at boot.

Commands:

Check status:

sudo systemctl status aquarium.service

Start:

sudo systemctl start aquarium.service

Stop:

sudo systemctl stop aquarium.service

Restart:

sudo systemctl restart aquarium.service

Enable at boot:

sudo systemctl enable aquarium.service

Reload service definitions:

sudo systemctl daemon-reload

---

# Web Interface

Phone connects to:

http://<raspberrypi-ip>:5000

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

---

# Timezone Configuration

System timezone:

America/Chicago

Check:

timedatectl

Set:

sudo timedatectl set-timezone America/Chicago

Cron schedules depend on correct timezone configuration.

---

# Design Decisions

## Pi Remains On Continuously

The Raspberry Pi is never powered off automatically.

Reasons:

* Flask remains available
* Faster response
* Simpler architecture
* No SD card wear concerns from repeated shutdowns

---

## Display Is Not Powered Off

The display remains powered.

Instead of turning the monitor off:

* Day Mode = active visuals
* Night Mode = low-activity ambient visuals

This approach avoids:

* HDMI power management issues
* Relay hardware
* Display compatibility problems

---

## Separation of Responsibilities

### Flask

Persistent service.

Handles:

* User interface
* Phone control
* Requests

### mode.py

Transient display controller.

Handles:

* Launching visuals
* Switching display modes

### cron

Time-based automation.

Handles:

* Day/night scheduling

This separation keeps the architecture simple and maintainable.

---

# Useful Commands

Check IP address:

hostname -I

Check Flask service:

systemctl status aquarium.service

View cron configuration:

crontab -l

Edit cron configuration:

crontab -e

Reboot:

sudo reboot

Current date/time:

date

Current timezone:

timedatectl
