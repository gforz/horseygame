"""horse_model.py — The horse's measurements.

Everything here is pure maths on the horse "model space" (a 512 x 512-ish
sketch of a horse with its centre at MODEL_CENTRE_X/Y). Physics bodies and
drawing both derive their shapes from these helpers, so the picture and the
collideable body always agree.
"""

import random

from game import constants as C


def get_back_leg_swing(back_length: float) -> float:
    length_ratio = (back_length - C.MIN_LEG_LENGTH) / (
        C.MAX_LEG_LENGTH - C.MIN_LEG_LENGTH
    )
    length_ratio = max(0.0, min(1.0, length_ratio))
    base_swing = C.BACK_LEG_SWING_SHORT + (
        C.BACK_LEG_SWING_LONG - C.BACK_LEG_SWING_SHORT
    ) * length_ratio
    return base_swing + random.uniform(
        -C.BACK_LEG_SWING_VARIATION,
        C.BACK_LEG_SWING_VARIATION,
    )


def get_random_hoof() -> tuple[float, str]:
    hoof_shape = random.choice(C.HOOF_SHAPES)
    if hoof_shape == C.HOOF_SHAPE_FORWARD_RECT:
        hoof_length = random.uniform(
            C.HOOF_FORWARD_RECT_LENGTH_MIN,
            C.HOOF_FORWARD_RECT_LENGTH_MAX,
        )
    else:
        hoof_length = random.uniform(C.HOOF_LENGTH_MIN, C.HOOF_LENGTH_MAX)
    return hoof_length, hoof_shape


def hoof_vertices(hoof_length: float, hoof_shape: str) -> tuple[tuple[float, float], ...]:
    half_height = 7.5
    if hoof_shape == C.HOOF_SHAPE_FORWARD_RECT:
        rear_edge = -(C.LEG_DRAW_WIDTH / C.SCALE) / 2
        front_edge = rear_edge + hoof_length
        return (
            (rear_edge, -half_height),
            (front_edge, -half_height),
            (front_edge, half_height),
            (rear_edge, half_height),
        )
    return (
        (-0.4 * hoof_length, -half_height),
        (0.4 * hoof_length, -half_height),
        (0.6 * hoof_length, half_height),
        (-0.4 * hoof_length, half_height),
    )


def torso_mass_for_size(torso_length: float, torso_height: float) -> float:
    area_ratio = (
        torso_length * torso_height
        / (C.DEFAULT_TORSO_LENGTH * C.DEFAULT_TORSO_HEIGHT)
    )
    return C.TORSO_MASS * area_ratio


def horse_body_geometry(torso_length: float, torso_height: float) -> tuple:
    """Return ( rump, torso, neck, head, ear, muzzle, eye, pupil, nose, mouth )."""
    body_left = C.MODEL_CENTRE_X - torso_length / 2
    body_right = C.MODEL_CENTRE_X + torso_length / 2
    body_top = C.MODEL_CENTRE_Y - torso_height / 2
    body_bottom = C.MODEL_CENTRE_Y + torso_height / 2
    front_dx = body_right - 386
    top_dy = body_top - 222

    def translate(points, dx: float, dy: float):
        return tuple((x + dx, y + dy) for x, y in points)

    return (
        translate(((127, 222), (71, 301), (87, 310), (127, 222)), body_left - 126, top_dy),
        ((body_left, body_top), (body_right, body_top),
         (body_right, body_bottom), (body_left, body_bottom)),
        translate(((367,222),(417,171),(426,143),(424,110),(462,151),(435,193),(386,242)), front_dx, top_dy),
        translate(((424,110),(462,151),(502,166),(495,210),(436,193),(417,171)), front_dx, top_dy),
        translate(((424,110),(424,143),(435,153),(438,150)), front_dx, top_dy),
        translate(((495,166),(513,173),(508,185),(495,181)), front_dx, top_dy),
        (453 + front_dx, 159 + top_dy),
        (454 + front_dx, 159 + top_dy),
        translate(((501,171),(514,175),(511,185),(499,181)), front_dx, top_dy),
        translate(((472,190),(494,196),(492,201),(471,195)), front_dx, top_dy),
    )


def roll_world_horse_traits() -> dict:
    """Random measurements + colours for one horse, used by every scene."""
    if random.random() < C.LEG_DIFFERENCE_CHANCE:
        leg_difference = random.uniform(C.MIN_LEG_DIFFERENCE, C.MAX_LEG_DIFFERENCE)
    else:
        leg_difference = 0

    max_possible   = C.MAX_LEG_LENGTH - C.MIN_LEG_LENGTH
    leg_difference = max(-max_possible, min(max_possible, leg_difference))

    back_low  = max(C.MIN_LEG_LENGTH, C.MIN_LEG_LENGTH - leg_difference)
    back_high = min(C.MAX_LEG_LENGTH, C.MAX_LEG_LENGTH - leg_difference)
    back_length  = random.uniform(back_low, back_high)
    front_length = back_length + leg_difference

    if random.random() < C.LEG_OFFSET_CHANCE:
        magnitude  = random.uniform(C.MIN_LEG_OFFSET, C.MAX_LEG_OFFSET)
        shift_ratio = magnitude / C.MAX_LEG_OFFSET
        leg_shift  = magnitude * shift_ratio / C.SCALE
    else:
        leg_shift = 0

    start_angle = random.uniform(C.MIN_START_ANGLE, C.MAX_START_ANGLE)
    hoof_length, hoof_shape = get_random_hoof()
    torso_length = random.uniform(C.TORSO_LENGTH_MIN, C.TORSO_LENGTH_MAX)
    torso_height = random.uniform(C.TORSO_HEIGHT_MIN, C.TORSO_HEIGHT_MAX)
    hip_limit = torso_length / 2 - C.TORSO_HIP_INSET
    hip_min = C.MODEL_CENTRE_X - hip_limit
    hip_max = C.MODEL_CENTRE_X + hip_limit
    back_hip_x = max(hip_min, min(hip_max, hip_min + leg_shift))
    front_hip_x = max(hip_min, min(hip_max, hip_max - leg_shift))

    return {
        "color":        random.choice(C.HORSE_COLORS),
        "back_length":  back_length,
        "front_length": front_length,
        "back_hip_x":   back_hip_x,
        "front_hip_x":  front_hip_x,
        "start_angle":  start_angle,
        "hoof_length":  hoof_length,
        "hoof_shape":   hoof_shape,
        "torso_length": torso_length,
        "torso_height": torso_height,
        "tail_length":  random.uniform(C.TAIL_LENGTH_MIN, C.TAIL_LENGTH_MAX),
        "tail_width":   random.uniform(C.TAIL_WIDTH_MIN, C.TAIL_WIDTH_MAX),
    }