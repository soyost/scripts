
from machine import Pin, PWM
import time

# --- Servo setup ---
SERVO_PIN = 15
servo = PWM(Pin(SERVO_PIN))
servo.freq(50)  # 50Hz standard for hobby servos

# SG90 typical safe pulse range (microseconds).
# Many SG90s accept ~500-2400us, but safer is ~700-2300us to avoid hard stops.
MIN_US = 700
MAX_US = 2300
MID_US = 1500

# 50 Hz = 20,000 microseconds period
PERIOD_US = 20000

def us_to_duty_u16(us):
    return int(us * 65535 / PERIOD_US)

def write_us(us):
    servo.duty_u16(us_to_duty_u16(us))

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def move_smooth(start_us, end_us, step_us=10, step_delay=0.01):
    """Move servo smoothly from start to end to reduce jerk/jitter."""
    if end_us < start_us:
        step_us = -abs(step_us)
    else:
        step_us = abs(step_us)

    us = start_us
    while (step_us > 0 and us <= end_us) or (step_us < 0 and us >= end_us):
        write_us(clamp(us, MIN_US, MAX_US))
        time.sleep(step_delay)
        us += step_us

    write_us(clamp(end_us, MIN_US, MAX_US))

# --- Startup: center ---
current = MID_US
write_us(current)
time.sleep(0.8)

# --- Nudge loop ---
while True:
    # Small wiggle around center; adjust these values to change "nudge strength"
    targets = [1400, 1600, 1450, 1550, 1500]

    for t in targets:
        move_smooth(current, t, step_us=10, step_delay=0.01)
        current = t
        time.sleep(0.15)

    # Rest between cycles
    time.sleep(2.0)
