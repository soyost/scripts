import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

fig, ax = plt.subplots()
ax.set_aspect('equal')
ax.set_xlim(-20, 20)
ax.set_ylim(-20, 20)
line, = ax.plot([], [], color='blue')

def update(frame):
    num_points = 1000
    a = 0.1 + 0.01 * frame  # Varying 'a' for evolving spiral
    b = 0.5
    theta = np.linspace(0, 4 * np.pi, num_points)
    r = a + b * theta

    x = r * np.cos(theta)
    y = r * np.sin(theta)

    line.set_data(x, y)
    return line,

ani = FuncAnimation(fig, update, frames=200, interval=50, blit=True)
plt.title('Swirly')
plt.xlabel('Up')
plt.ylabel('Across')
plt.grid(False)
plt.show()
