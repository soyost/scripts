import pygame
import random
import math

pygame.init()

screen = pygame.display.set_mode((800, 480), pygame.FULLSCREEN)
clock = pygame.time.Clock()

jellyfish = []

for i in range(12):
    jellyfish.append({
        "x": random.randint(0, 800),
        "y": random.randint(0, 480),
        "size": random.randint(20, 60),
        "speed": random.uniform(0.3, 1.0),
        "phase": random.uniform(0, math.pi * 2)
    })


running = True

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 5, 15))

    for j in jellyfish:

        j["y"] -= j["speed"]

        if j["y"] < -50:
            j["y"] = 530
            j["x"] = random.randint(0, 800)

        wobble = math.sin(pygame.time.get_ticks() * 0.002 + j["phase"]) * 20

        pygame.draw.circle(
            screen,
            (100, 180, 255),
            (int(j["x"] + wobble), int(j["y"])),
            j["size"],
            2
        )

    pygame.display.flip()
    clock.tick(60)

pygame.quit()