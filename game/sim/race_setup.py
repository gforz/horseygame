"""race_setup.py — Builds the physics world for one race: four horses in lanes.

Every horse gets randomly rolled proportions, a head, a tail, two motorised
legs and hooves, so no two races look or run the same.
"""

import random

from game import constants as C
from game.constants import get_random_horse_color
from game.gfx.horse_model import (
    get_back_leg_swing,
    get_random_hoof,
    hoof_vertices,
    torso_mass_for_size,
)
from game.physics import PhysicsSpace, torque_to_box2d
from game.sim.horse_parts import (
    Leg,
    create_horse_head,
    create_horse_tail,
)
from game.sim.names import draw_race_names
from game.sim.race_horse import RaceHorse


def create_race() -> tuple:
    """Return a fresh Box2D world and four RaceHorse objects."""

    space = PhysicsSpace(C.GRAVITY)
    race_names = draw_race_names()

    # Ground segment for each lane
    for lane in range(C.LANE_COUNT):
        lane_top    = C.TRACK_TOP + lane * C.LANE_HEIGHT
        lane_bottom = lane_top + C.LANE_HEIGHT - C.LANE_PAD
        lane_category = 1 << (lane + 1)

        space.add_edge(
            (C.TRACK_LEFT,  lane_bottom),
            (C.TRACK_RIGHT, lane_bottom),
            friction=C.HOOF_FRICTION,
            collision_category=lane_category,
            collision_mask=lane_category,
        )
        # Collision boundary at bottom of the screen so horses cannot fall out
        space.add_edge(
            (-1000, C.HEIGHT - 4),
            (C.WIDTH + 1000, C.HEIGHT - 4),
            friction=2.5,
            collision_category=lane_category,
            collision_mask=lane_category,
        )

    horses = []

    race_collision_group = 1

    for i in range(C.LANE_COUNT):
        lane_top    = C.TRACK_TOP + i * C.LANE_HEIGHT
        lane_bottom = lane_top + C.LANE_HEIGHT - C.LANE_PAD
        lane_category = 1 << (i + 1)

        # Random leg lengths
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
        leg_lengths  = [back_length * C.SCALE, front_length * C.SCALE]

        # Randomize how far each hip sits inward from the torso edge.
        hip_shift = 0.0
        if random.random() < C.LEG_OFFSET_CHANCE:
            magnitude  = random.uniform(C.MIN_LEG_OFFSET, C.MAX_LEG_OFFSET)
            shift_ratio = magnitude / C.MAX_LEG_OFFSET
            hip_shift = magnitude * shift_ratio

        # Torso
        torso_length = random.uniform(C.TORSO_LENGTH_MIN, C.TORSO_LENGTH_MAX)
        torso_height = random.uniform(C.TORSO_HEIGHT_MIN, C.TORSO_HEIGHT_MAX)
        hip_limit = (torso_length / 2 - C.TORSO_HIP_INSET) * C.SCALE
        HIP_POSITIONS = [-hip_limit + hip_shift, hip_limit - hip_shift]
        torso_x = C.HORSE_START_OFFSET + C.MODEL_CENTRE_X * C.SCALE
        torso_y = lane_bottom - torso_height / 2 * C.SCALE - max(leg_lengths)

        torso = space.create_box_body(
            mass=torso_mass_for_size(torso_length, torso_height),
            position=(torso_x, torso_y),
            size=(torso_length * C.SCALE, torso_height * C.SCALE),
            angle=0,
            friction=0.8,
            group_index=race_collision_group,
            collision_category=lane_category,
            collision_mask=lane_category,
        )
        head = create_horse_head(
            space,
            torso,
            torso_length,
            torso_height,
            group_index=race_collision_group,
            collision_category=lane_category,
            collision_mask=lane_category,
        )
        tail = create_horse_tail(
            space,
            torso,
            torso_length,
            torso_height,
            group_index=race_collision_group,
            collision_category=lane_category,
            collision_mask=lane_category,
        )

        horse_start_angle = random.uniform(C.MIN_START_ANGLE, C.MAX_START_ANGLE)
        back_leg_swing = get_back_leg_swing(back_length)
        hoof_length, hoof_shape = get_random_hoof()
        back_hip_min_angle = max(
            -C.HIP_MAX_ANGLE,
            -(back_leg_swing + random.uniform(
                C.BACK_HIP_LIMIT_MARGIN_MIN,
                C.BACK_HIP_LIMIT_MARGIN_MAX,
            )),
        )

        # Build legs
        legs = []
        for leg_index, hip_x in enumerate(HIP_POSITIONS):
            leg_length = leg_lengths[leg_index]
            hip_y      = torso_height / 2 * C.SCALE
            hip_world  = torso.local_to_world((hip_x, hip_y))

            original_angle = -horse_start_angle if leg_index == 0 else horse_start_angle
            leg_body = space.create_box_body(
                mass=C.LEG_MASS,
                position=(0, 0),
                size=(C.LEG_WIDTH, leg_length),
                angle=torso.angle + original_angle,
                friction=2.8,
                group_index=race_collision_group,
                collision_category=lane_category,
                collision_mask=lane_category,
            )
            hoof_center_y = leg_length / 2 - 2 * C.U
            space.add_hoof_fixture(
                leg_body,
                vertices=tuple(
                    (x * C.SCALE, hoof_center_y + y * C.SCALE)
                    for x, y in hoof_vertices(hoof_length, hoof_shape)
                ),
                friction=C.HOOF_FRICTION,
                group_index=race_collision_group,
                collision_category=lane_category,
                collision_mask=lane_category,
            )

            anchor_offset  = leg_body.local_to_world((0, -leg_length / 2))
            leg_body.position = (
                hip_world.x - anchor_offset.x,
                hip_world.y - anchor_offset.y,
            )

            max_motor_torque = C.BACK_LEG_MAX_TORQUE
            if leg_index == 1:
                front_leg_force    = random.uniform(C.MIN_FRONT_LEG_FORCE, C.MAX_FRONT_LEG_FORCE)
                max_motor_torque = (
                    torque_to_box2d(front_leg_force) * C.LEG_MOTOR_TORQUE_SCALE
                )
            else:
                front_leg_force    = None
            hip_joint = space.create_revolute_joint(
                torso,
                leg_body,
                hip_world,
                back_hip_min_angle if leg_index == 0 else C.HIP_MIN_ANGLE,
                C.HIP_MAX_ANGLE,
                max_motor_torque,
            )

            legs.append(Leg(
                body=leg_body,
                motor=hip_joint,
                hip_x=hip_x,
                motor_force=front_leg_force,
                original_angle=original_angle,
                swing_angle=back_leg_swing if leg_index == 0 else C.LEG_SWING_ANGLE,
                wait_time=random.uniform(C.MIN_LEG_WAIT, C.MAX_LEG_WAIT),
                move_duration=random.uniform(C.MIN_MOVE_TIME, C.MAX_MOVE_TIME),
            ))

        horse_obj = RaceHorse(
            lane=i,
            torso=torso,
            color=get_random_horse_color(),  # Generates a brand-new random color each round!
            legs=legs,
            leg_lengths=leg_lengths,
            start_angle=horse_start_angle,
            head=head,
            tail=tail,
            torso_length=torso_length,
            torso_height=torso_height,
            hoof_length=hoof_length,
            hoof_shape=hoof_shape,
            name=race_names[i],
        )
        horse_obj.finished = False
        horses.append(horse_obj)

    return space, horses