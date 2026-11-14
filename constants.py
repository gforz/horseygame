import math
import random

import pygame

# ============================================================
# SCREEN SETTINGS
# ============================================================

DEFAULT_WIDTH, DEFAULT_HEIGHT = 2560, 1440
if pygame.display.get_init():
    desktop_sizes = pygame.display.get_desktop_sizes()
    WIDTH, HEIGHT = desktop_sizes[0] if desktop_sizes else (DEFAULT_WIDTH, DEFAULT_HEIGHT)
else:
    WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT
FPS_TRACK = 60
FPS_WORLD = 240

BASE_WIDTH, BASE_HEIGHT = 1000, 700
U = min(WIDTH / BASE_WIDTH, HEIGHT / BASE_HEIGHT)

WORLD_SIZE = (1000, 700)
WORLD_WIDTH = 3200
WORLD_HEIGHT = 2000


def s(value):
    """Scale a pixel value designed for 1000 x 700 to this screen."""
    return int(value * U)


# ============================================================
# COLOURS  (track palette wins on conflicts)
# ============================================================

SKY_BLUE    = (135, 206, 235)
GRASS_BG    = (95, 190, 85)
LINE        = (245, 245, 225)

DARK        = (72, 47, 16)
WHITE       = (245, 245, 225)
BLACK       = (25, 25, 20)
GOLD        = (255, 215, 0)
LOSE_RED    = (255, 120, 120)

def get_random_horse_color() -> tuple[int, int, int]:
    """
    Returns a random horse color: black, dark grey, brown,
    orange, and rarely green. No very light horses.
    """
    choice = random.choices(
        ["black", "grey", "brown", "orange", "green"],
        weights=[25, 25, 30, 15, 5],
        k=1
    )[0]

    if choice == "black":
        v = random.randint(20, 60)
        return (v, v, v)

    elif choice == "grey":
        v = random.randint(70, 140)
        return (v, v, v)

    elif choice == "brown":
        r = random.randint(70, 130)
        g = int(r * random.uniform(0.5, 0.7))
        b = int(r * random.uniform(0.2, 0.4))
        return (r, g, b)

    elif choice == "orange":
        r = random.randint(150, 200)
        g = random.randint(75, 130)
        b = random.randint(20, 65)
        return (r, g, b)

    elif choice == "green":
        r = random.randint(40, 80)
        g = random.randint(80, 130)
        b = random.randint(30, 70)
        return (r, g, b)

    return (100, 100, 100)

HORSE_COLORS = [
    get_random_horse_color(),
    get_random_horse_color(),
    get_random_horse_color(),
    get_random_horse_color(),
]

# World colours
GRASS        = (95, 190, 85)   # Matched to TRACK_GREEN
DARK_GRASS   = (80, 140, 60)
LIGHT_GRASS  = (120, 180, 85)

BROWN        = (116, 75, 43)
DARK_BROWN   = (76, 47, 29)
WOOD         = (158, 105, 57)

WORLD_WHITE  = (245, 245, 225)   # world version differs slightly from track WHITE
WORLD_BLACK  = (25, 25, 20)      # world version differs slightly from track BLACK

RED          = (235, 35, 70)
DARK_RED     = (165, 20, 50)

WINDOW_COLOR = (125, 190, 215)
ROOF         = (100, 45, 35)

YELLOW       = (245, 225, 35)

TURQUOISE      = (10, 195, 185)
DARK_TURQUOISE = (5, 135, 130)

TITLE_PURPLE     = (105, 75, 200)
TITLE_BG         = (240, 240, 250)
STAND_GRAY       = (195, 195, 200)
STAND_LIGHT      = (222, 222, 228)
STAND_DARK       = (140, 140, 148)
TRACK_GREEN      = (95, 190, 85)
TRACK_DARK_GREEN = (45, 125, 55)
TRACK_ORANGE     = (240, 150, 60)
TRACK_LIGHT_ORANGE = (250, 190, 110)
FLAG_PINK        = (240, 120, 170)
FLAG_GREEN       = (80, 200, 90)
FLAG_PURPLE      = (110, 70, 200)
FENCE_INNER      = (240, 235, 200)

V_TURQUOISE  = (20, 232, 224)
V_RED        = (238, 55, 90)
V_YELLOW     = (212, 225, 20)
V_WINDOW     = (245, 248, 255)
V_BLACK      = (25, 25, 30)
V_GRAY       = (150, 150, 160)
V_GRAY_LIGHT = (185, 185, 195)


# ============================================================
# TRACK LAYOUT
# ============================================================

LANE_COUNT  = 4
LANE_HEIGHT = s(165)
LANE_PAD    = s(5)

TRACK_LEFT  = s(25)

TRACK_TOP = max(
    s(30),
    (HEIGHT - LANE_COUNT * LANE_HEIGHT) // 2
)

START_LINE_X       = s(75)
HORSE_START_OFFSET = 45 * U

TRACK_LENGTH_MULTIPLIER = 2
FINISH_X = START_LINE_X + TRACK_LENGTH_MULTIPLIER * (
    WIDTH - s(90) - START_LINE_X
)
HALFWAY_X = (START_LINE_X + FINISH_X) // 2
TRACK_RIGHT = FINISH_X + s(65)
FINISH_WIDTH = s(12)

MAX_RACE_TIME = 180000


# ============================================================
# HORSE MODEL AND PHYSICS
# ============================================================

SCALE = 0.5 * U

HORSE_TOP    = -30
HORSE_BOTTOM = 478
HORSE_LEFT   = 71
HORSE_RIGHT  = 514

MODEL_CENTRE_X = 256
MODEL_CENTRE_Y = 288.5

GRAVITY      = 1200 * U
PHYSICS_STEP = 1 / 120

TORSO_MASS = 18.0
DEFAULT_TORSO_LENGTH = 300.0
DEFAULT_TORSO_HEIGHT = 133.0
TORSO_LENGTH_MIN = 240.0
TORSO_LENGTH_MAX = 400.0
TORSO_HEIGHT_MIN = 95.0
TORSO_HEIGHT_MAX = 175.0
TORSO_HIP_INSET = 10.0
HEAD_BOX_LENGTH = 147.0
HEAD_BOX_HEIGHT = 132.0
HEAD_MASS = 2.4
HEAD_FRICTION = 0.8
HEAD_LIMIT_ANGLE = 0.8
HEAD_MIN_ANGLE = -0.8
HEAD_MAX_ANGLE = 0.35
HEAD_SPRING_STIFFNESS = 100.0
HEAD_SPRING_DAMPING = 10.0
HEAD_SPRING_MAX_TORQUE = 60.0
HEAD_SPRING_MAX_SPEED = 10.0
TAIL_LENGTH_MIN = 100.0
TAIL_LENGTH_MAX = 170.0
TAIL_WIDTH_MIN = 16.0
TAIL_WIDTH_MAX = 30.0
TAIL_MASS = 1.2
TAIL_START_ANGLE = 0.55
TAIL_SPRING_STIFFNESS = 320.0
TAIL_SPRING_DAMPING = 64.0
TAIL_SPRING_MAX_TORQUE = 200.0
TAIL_SPRING_MAX_SPEED = 1.5
LEG_MASS   = 1.3

MIN_LEG_LENGTH     = 50
MAX_LEG_LENGTH     = 130
DEFAULT_LEG_LENGTH = 123

LEG_DIFFERENCE_CHANCE = 0.20
MIN_LEG_DIFFERENCE    = -30
MAX_LEG_DIFFERENCE    = 30

LEG_OFFSET_CHANCE = 0.80
MIN_LEG_OFFSET    = 1 * SCALE
MAX_LEG_OFFSET    = 25 * SCALE

LEG_WIDTH = 15 * SCALE
LEG_DRAW_WIDTH = LEG_WIDTH * 1.3
HOOF_FRICTION = 8.0
HOOF_LENGTH_MIN = 30.0
HOOF_LENGTH_MAX = 45.0
HOOF_FORWARD_RECT_LENGTH_MIN = LEG_DRAW_WIDTH / SCALE
HOOF_FORWARD_RECT_LENGTH_MAX = 28.0
HOOF_SHAPE_TAPERED = "tapered"
HOOF_SHAPE_FORWARD_RECT = "forward_rect"
HOOF_SHAPES = (HOOF_SHAPE_TAPERED, HOOF_SHAPE_FORWARD_RECT)

HIP_MIN_ANGLE = -0.2
HIP_MAX_ANGLE = 0.2
BACK_LEG_SWING_SHORT = 0.35
BACK_LEG_SWING_LONG = 0.25
BACK_LEG_SWING_VARIATION = 0.02
BACK_LEG_OUTWARD_SWING = 0.25
BACK_HIP_LIMIT_MARGIN_MIN = 0.02
BACK_HIP_LIMIT_MARGIN_MAX = 0.04

MIN_START_ANGLE = -0.1
MAX_START_ANGLE = 0.1

MIN_FRONT_LEG_FORCE = 30000 * U * U
MAX_FRONT_LEG_FORCE = 60000 * U * U
LEG_MOTOR_TORQUE_SCALE = 22.0
BACK_LEG_MAX_TORQUE = 650.0

LEG_SWING_ANGLE  = 0.4
LEG_ANGLE_SPEED  = 8
LEG_POSITION_GAIN = 48.0
ANGLE_TOLERANCE  = 0.025

MOTOR_DIRECTION     = 1
BACK_LEG_DIRECTION  = -1
FRONT_LEG_DIRECTION = -1

MIN_LEG_WAIT  = 0
MAX_LEG_WAIT  = 0.1
MIN_MOVE_TIME = 0.15
MAX_MOVE_TIME = 0.6


# ============================================================
# BETTING
# ============================================================

STARTING_MONEY = 100
PAYOUT_ODDS    = 1
MIN_BET        = 10
BET_STEP       = 10


# ============================================================
# WORLD / PLAYER
# ============================================================

MOVE_SPEED  = 2.0
HORSE_COUNT = 32

LASSO_MAX_RANGE = 300.0
LASSO_SPEED     = 5.0

# World horse rendering
WORLD_HORSE_SCALE  = 0.22
HORSE_SPEED_WORLD  = MOVE_SPEED * 0.3
TILT_UNEVEN_LEGS   = True
HORSE_SUPERSAMPLE  = 4
HORSE_HOOF         = [(-15, -7.5), (15, -7.5), (22.5, 7.5), (-15, 7.5)]

HORSE_DIRECTIONS = [
    (1, 0), (-1, 0), (0, 1), (0, -1),
    (0.7071, 0.7071), (-0.7071, 0.7071),
    (0.7071, -0.7071), (-0.7071, -0.7071),
]

# Vehicle sprite dimensions
CELL        = 5
SPRITE_COLS = 38
SPRITE_ROWS = 16

# World race-track sprite dimensions
TRACK_CELL = 9
TRACK_COLS = 66
TRACK_ROWS = 50