import pygame
import sys
import random

pygame.init()

# Screen
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pong")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (130, 130, 130)

# Timing
FPS = 60
clock = pygame.time.Clock()

# Fonts
TITLE_FONT = pygame.font.SysFont(None, 72)
MENU_FONT = pygame.font.SysFont(None, 42)
SMALL_FONT = pygame.font.SysFont(None, 30)
SCORE_FONT = pygame.font.SysFont(None, 64)

# Game constants
WIN_SCORE = 10
PADDLE_WIDTH = 14
PADDLE_HEIGHT = 110
PADDLE_SPEED = 7
BALL_SIZE = 18
BALL_START_SPEED_X = 6
BALL_START_SPEED_Y = 4
BALL_MAX_SPEED_Y = 10

# Objects
left_paddle = pygame.Rect(30, HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
right_paddle = pygame.Rect(WIDTH - 30 - PADDLE_WIDTH, HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
ball = pygame.Rect(WIDTH // 2 - BALL_SIZE // 2, HEIGHT // 2 - BALL_SIZE // 2, BALL_SIZE, BALL_SIZE)

# State
left_score = 0
right_score = 0
ball_speed_x = 0
ball_speed_y = 0


AI_SETTINGS = {
    "easy": {
        "speed": 4,
        "reaction_frames": 18,
        "aim_error": 70,
        "prediction_strength": 0.45,
    },
    "medium": {
        "speed": 6,
        "reaction_frames": 10,
        "aim_error": 35,
        "prediction_strength": 0.75,
    },
    "hard": {
        "speed": 8,
        "reaction_frames": 4,
        "aim_error": 10,
        "prediction_strength": 1.0,
    }
}

ai_frame_counter = 0
ai_target_y = HEIGHT // 2


def draw_text_center(text, font, color, y):
    surface = font.render(text, True, color)
    rect = surface.get_rect(center=(WIDTH // 2, y))
    screen.blit(surface, rect)


def reset_positions():
    left_paddle.y = HEIGHT // 2 - PADDLE_HEIGHT // 2
    right_paddle.y = HEIGHT // 2 - PADDLE_HEIGHT // 2
    ball.center = (WIDTH // 2, HEIGHT // 2)


def serve_ball(direction=None):
    global ball_speed_x, ball_speed_y
    ball.center = (WIDTH // 2, HEIGHT // 2)

    if direction is None:
        direction = random.choice([-1, 1])

    ball_speed_x = BALL_START_SPEED_X * direction
    ball_speed_y = random.choice([-BALL_START_SPEED_Y, -3, 3, BALL_START_SPEED_Y])


def reset_game():
    global left_score, right_score
    left_score = 0
    right_score = 0
    reset_positions()
    serve_ball()


def clamp_paddles():
    if left_paddle.top < 0:
        left_paddle.top = 0
    if left_paddle.bottom > HEIGHT:
        left_paddle.bottom = HEIGHT
    if right_paddle.top < 0:
        right_paddle.top = 0
    if right_paddle.bottom > HEIGHT:
        right_paddle.bottom = HEIGHT


def start_menu():
    while True:
        screen.fill(BLACK)
        draw_text_center("PONG", TITLE_FONT, WHITE, 150)
        draw_text_center("Press 1 for Single Player", MENU_FONT, WHITE, 260)
        draw_text_center("Press 2 for Two Player", MENU_FONT, WHITE, 320)
        draw_text_center("ESC to Quit", SMALL_FONT, GRAY, 400)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    return "single"
                if event.key == pygame.K_2:
                    return "multi"
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()


def difficulty_menu():
    while True:
        screen.fill(BLACK)
        draw_text_center("SELECT AI DIFFICULTY", MENU_FONT, WHITE, 160)
        draw_text_center("Press 1 for Easy", MENU_FONT, WHITE, 250)
        draw_text_center("Press 2 for Medium", MENU_FONT, WHITE, 310)
        draw_text_center("Press 3 for Hard", MENU_FONT, WHITE, 370)
        draw_text_center("ESC to Quit", SMALL_FONT, GRAY, 450)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    return "easy"
                if event.key == pygame.K_2:
                    return "medium"
                if event.key == pygame.K_3:
                    return "hard"
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()


def winner_screen(winner_text):
    while True:
        screen.fill(BLACK)
        draw_text_center(winner_text, TITLE_FONT, WHITE, 200)
        draw_text_center("Press R to Play Again", MENU_FONT, WHITE, 310)
        draw_text_center("Press M for Main Menu", MENU_FONT, WHITE, 360)
        draw_text_center("Press ESC to Quit", SMALL_FONT, GRAY, 430)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return "restart"
                if event.key == pygame.K_m:
                    return "menu"
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()


def handle_input(game_mode):
    keys = pygame.key.get_pressed()

    # Left paddle
    if keys[pygame.K_w]:
        left_paddle.y -= PADDLE_SPEED
    if keys[pygame.K_s]:
        left_paddle.y += PADDLE_SPEED

    # Right paddle in multiplayer
    if game_mode == "multi":
        if keys[pygame.K_UP]:
            right_paddle.y -= PADDLE_SPEED
        if keys[pygame.K_DOWN]:
            right_paddle.y += PADDLE_SPEED

    clamp_paddles()


def predict_ball_y():
    """
    Predict where the ball will be when it reaches the AI paddle.
    Includes wall bounces for smarter tracking.
    """
    if ball_speed_x <= 0:
        return HEIGHT // 2

    test_x = ball.centerx
    test_y = ball.centery
    vx = ball_speed_x
    vy = ball_speed_y

    target_x = right_paddle.left

    while test_x < target_x:
        test_x += vx
        test_y += vy

        if test_y - BALL_SIZE // 2 <= 0 or test_y + BALL_SIZE // 2 >= HEIGHT:
            vy *= -1
            test_y += vy

    return test_y


def move_ai(difficulty):
    global ai_frame_counter, ai_target_y

    settings = AI_SETTINGS[difficulty]
    ai_frame_counter += 1

    # Only update the AI decision every few frames to simulate reaction time
    if ai_frame_counter >= settings["reaction_frames"]:
        ai_frame_counter = 0

        predicted_y = predict_ball_y()
        current_ball_y = ball.centery

        # Blend between simple tracking and prediction
        target_y = int(
            current_ball_y * (1 - settings["prediction_strength"]) +
            predicted_y * settings["prediction_strength"]
        )

        # Add aiming error for lower difficulties
        target_y += random.randint(-settings["aim_error"], settings["aim_error"])
        ai_target_y = target_y

    paddle_center = right_paddle.centery
    tolerance = 12

    if paddle_center < ai_target_y - tolerance:
        right_paddle.y += settings["speed"]
    elif paddle_center > ai_target_y + tolerance:
        right_paddle.y -= settings["speed"]

    clamp_paddles()


def move_ball():
    global ball_speed_x, ball_speed_y, left_score, right_score

    ball.x += ball_speed_x
    ball.y += ball_speed_y

    # Top/bottom wall collisions
    if ball.top <= 0:
        ball.top = 0
        ball_speed_y *= -1
    elif ball.bottom >= HEIGHT:
        ball.bottom = HEIGHT
        ball_speed_y *= -1

    # Left paddle collision
    if ball.colliderect(left_paddle) and ball_speed_x < 0:
        ball.left = left_paddle.right
        ball_speed_x *= -1

        offset = (ball.centery - left_paddle.centery) / (PADDLE_HEIGHT / 2)
        ball_speed_y = int(offset * BALL_MAX_SPEED_Y)
        if ball_speed_y == 0:
            ball_speed_y = random.choice([-2, 2])

        if abs(ball_speed_x) < 12:
            ball_speed_x += 1

    # Right paddle collision
    if ball.colliderect(right_paddle) and ball_speed_x > 0:
        ball.right = right_paddle.left
        ball_speed_x *= -1

        offset = (ball.centery - right_paddle.centery) / (PADDLE_HEIGHT / 2)
        ball_speed_y = int(offset * BALL_MAX_SPEED_Y)
        if ball_speed_y == 0:
            ball_speed_y = random.choice([-2, 2])

        if abs(ball_speed_x) < 12:
            ball_speed_x -= 1

    # Score
    if ball.left <= 0:
        right_score += 1
        serve_ball(direction=-1)

    elif ball.right >= WIDTH:
        left_score += 1
        serve_ball(direction=1)


def draw_game(game_mode, difficulty):
    screen.fill(BLACK)

    # Center dashed line
    for y in range(0, HEIGHT, 28):
        pygame.draw.rect(screen, GRAY, (WIDTH // 2 - 2, y, 4, 16))

    # Paddles and ball
    pygame.draw.rect(screen, WHITE, left_paddle)
    pygame.draw.rect(screen, WHITE, right_paddle)
    pygame.draw.ellipse(screen, WHITE, ball)

    # Score
    left_surface = SCORE_FONT.render(str(left_score), True, WHITE)
    right_surface = SCORE_FONT.render(str(right_score), True, WHITE)
    screen.blit(left_surface, (WIDTH // 4, 25))
    screen.blit(right_surface, (WIDTH * 3 // 4, 25))

    # Labels
    if game_mode == "single":
        label = f"Single Player - {difficulty.capitalize()}"
    else:
        label = "Two Player"

    label_surface = SMALL_FONT.render(label, True, GRAY)
    screen.blit(label_surface, (20, 20))

    help_text = "R = Restart   M = Menu   ESC = Quit   First to 10 wins"
    help_surface = SMALL_FONT.render(help_text, True, GRAY)
    screen.blit(help_surface, (WIDTH // 2 - help_surface.get_width() // 2, HEIGHT - 35))

    pygame.display.flip()


def main():
    game_mode = start_menu()
    difficulty = difficulty_menu() if game_mode == "single" else None
    reset_game()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                elif event.key == pygame.K_r:
                    reset_game()

                elif event.key == pygame.K_m:
                    game_mode = start_menu()
                    difficulty = difficulty_menu() if game_mode == "single" else None
                    reset_game()

        handle_input(game_mode)

        if game_mode == "single":
            move_ai(difficulty)

        move_ball()
        draw_game(game_mode, difficulty)

        # Winner check
        if left_score >= WIN_SCORE:
            if game_mode == "single":
                result = winner_screen("YOU WIN!")
            else:
                result = winner_screen("LEFT PLAYER WINS!")
        elif right_score >= WIN_SCORE:
            if game_mode == "single":
                result = winner_screen("COMPUTER WINS!")
            else:
                result = winner_screen("RIGHT PLAYER WINS!")
        else:
            result = None

        if result == "restart":
            reset_game()
        elif result == "menu":
            game_mode = start_menu()
            difficulty = difficulty_menu() if game_mode == "single" else None
            reset_game()

        clock.tick(FPS)


if __name__ == "__main__":
    main()