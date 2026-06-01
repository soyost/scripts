import pygame
import random

pygame.init()

screen = pygame.display.set_mode((800, 480), pygame.FULLSCREEN)
clock = pygame.time.Clock()

particles = []

for i in range(200):
    particles.append({
        "x": random.randint(0, 800),
        "y": random.randint(0, 480),
        "speed": random.uniform(0.2, 1.2),
        "size": random.randint(1, 4)
    })

running = True

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 10, 20))

    for p in particles:

        p["y"] -= p["speed"]

        if p["y"] < 0:
            p["y"] = 480
            p["x"] = random.randint(0, 800)

        pygame.draw.circle(
            screen,
            (120, 180, 255),
            (int(p["x"]), int(p["y"])),
            p["size"]
        )

    pygame.display.flip()
    clock.tick(60)

pygame.quit()