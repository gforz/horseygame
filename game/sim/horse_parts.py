"""horse_parts.py — The articulated pieces of a physics horse.

A horse is a torso (RaceHorse) with a head, a tail and two legs. Each part owns
a Box2D body plus a motorised joint, and each knows how to hold itself up.
"""

import math
import random
from typing import Optional

import pygame

from game import constants as C
from game.gfx.horse_model import horse_body_geometry
from game.physics import PhysicsBody, PhysicsSpace


class Leg:
    """
    One physics leg attached to a RaceHorse torso.
    Wraps a Box2D body and revolute joint and owns
    the waiting / moving_back / moving_forward state machine.
    """

    def __init__(
        self,
        body: PhysicsBody,
        motor,
        hip_x: float,
        motor_force,            # float | None
        original_angle: float,
        swing_angle: float,
        wait_time: float,
        move_duration: float,
    ):
        self.body         = body
        self.motor        = motor

        self.hip_x        = hip_x
        self.motor_force  = motor_force

        self.original_angle = original_angle
        self.swing_angle = swing_angle
        self.start_angle    = original_angle
        self.target_angle   = original_angle

        self.wait_time    = wait_time
        self.wait_timer   = 0.0
        self.move_timer   = 0.0
        self.move_duration = move_duration

        self.state = "waiting"      # "waiting" | "moving_back" | "moving_forward"

    # ------------------------------------------------------------------
    # Internal helper: drive motor toward target_angle (relative to torso)
    # ------------------------------------------------------------------
    def _move_towards(self, torso: PhysicsBody, target_angle: float) -> bool:
        """
        Spin the motor so the leg approaches *target_angle* relative to the
        torso.  Returns True when the target is reached (within tolerance).
        """
        relative_angle = self.body.angle - torso.angle
        target_angle = max(
            self.motor.lowerLimit,
            min(self.motor.upperLimit, target_angle),
        )
        difference = target_angle - relative_angle

        if abs(difference) > C.ANGLE_TOLERANCE:
            self.motor.motorSpeed = max(
                -C.LEG_ANGLE_SPEED,
                min(
                    C.LEG_ANGLE_SPEED,
                    difference * C.LEG_POSITION_GAIN,
                ),
            ) * C.MOTOR_DIRECTION
            return False

        self.motor.motorSpeed = 0
        return True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def stop(self) -> None:
        """Hard-stop the motor (used while horse is being dragged)."""
        self.motor.motorSpeed = 0

    def update(self, dt: float, torso: PhysicsBody, leg_index: int) -> None:
        """Advance the leg FSM by *dt* seconds."""

        original = self.original_angle

        if self.state == "waiting":
            self.motor.motorSpeed = 0
            self.wait_timer += dt

            if self.wait_timer >= self.wait_time:
                self.state       = "moving_back"
                self.move_timer  = 0.0
                self.move_duration = random.uniform(C.MIN_MOVE_TIME, C.MAX_MOVE_TIME)
                self.start_angle   = self.body.angle - torso.angle

                if leg_index == 0:
                    self.target_angle = original + C.BACK_LEG_OUTWARD_SWING
                else:
                    self.target_angle = original + self.swing_angle * C.FRONT_LEG_DIRECTION

        elif self.state == "moving_back":
            self.move_timer += dt
            t = min(1.0, self.move_timer / self.move_duration)
            interp_target = (
                self.start_angle
                + (self.target_angle - self.start_angle) * t
            )
            reached = self._move_towards(torso, interp_target)

            if reached or t >= 1.0:
                self.state       = "moving_forward"
                self.move_timer  = 0.0
                self.start_angle = self.body.angle - torso.angle
                if leg_index == 0:
                    self.target_angle = original + self.swing_angle * C.BACK_LEG_DIRECTION
                else:
                    self.target_angle = original

        elif self.state == "moving_forward":
            self.move_timer += dt
            t = min(1.0, self.move_timer / self.move_duration)
            interp_target = (
                self.start_angle
                + (self.target_angle - self.start_angle) * t
            )
            reached = self._move_towards(torso, interp_target)

            if reached or t >= 1.0:
                self.state      = "waiting"
                self.wait_timer = 0.0
                self.wait_time  = random.uniform(C.MIN_LEG_WAIT, C.MAX_LEG_WAIT)


class HorseHead:
    def __init__(
        self,
        torso: PhysicsBody,
        body: PhysicsBody,
        joint,
        center_x: float,
        center_y: float,
        size_scale: float = 1.0,
    ) -> None:
        self.torso = torso
        self.body = body
        self.joint = joint
        self.center_x = center_x
        self.center_y = center_y
        self.size_scale = size_scale
        self.grounded = False

    def update(self) -> None:
        self.grounded = self.grounded or any(
            edge.contact.touching and edge.other.type == 0
            for edge in self.body.native.contacts
        )
        if self.grounded:
            self.joint.motorSpeed = 0
            self.joint.maxMotorTorque = 0
            return

        angle_error = self.joint.angle
        angular_velocity = self.body.angular_velocity - self.torso.angular_velocity
        desired_speed = -(
            C.HEAD_SPRING_STIFFNESS * angle_error
            + C.HEAD_SPRING_DAMPING * angular_velocity
        )
        self.joint.motorSpeed = max(
            -C.HEAD_SPRING_MAX_SPEED,
            min(C.HEAD_SPRING_MAX_SPEED, desired_speed),
        )
        torque_limit = min(
            C.HEAD_SPRING_MAX_TORQUE,
            C.HEAD_SPRING_STIFFNESS * abs(angle_error)
            + C.HEAD_SPRING_DAMPING * abs(angular_velocity),
        )
        self.joint.maxMotorTorque = torque_limit

    def stop(self) -> None:
        self.joint.motorSpeed = 0
        self.joint.maxMotorTorque = 0

    def rect(self) -> pygame.Rect:
        return body_rect(
            self.body,
            C.HEAD_BOX_LENGTH * C.SCALE * self.size_scale,
            C.HEAD_BOX_HEIGHT * C.SCALE * self.size_scale,
        )


class HorseTail:
    def __init__(
        self,
        torso: PhysicsBody,
        body: PhysicsBody,
        joint,
        length: float,
        width: float,
        size_scale: float = 1.0,
    ) -> None:
        self.torso = torso
        self.body = body
        self.joint = joint
        self.length = length
        self.width = width
        self.size_scale = size_scale

    def update(self) -> None:
        angle_error = self.joint.angle
        angular_velocity = self.body.angular_velocity - self.torso.angular_velocity
        desired_speed = -(
            C.TAIL_SPRING_STIFFNESS * angle_error
            + C.TAIL_SPRING_DAMPING * angular_velocity
        )
        self.joint.motorSpeed = max(
            -C.TAIL_SPRING_MAX_SPEED,
            min(C.TAIL_SPRING_MAX_SPEED, desired_speed),
        )
        self.joint.maxMotorTorque = min(
            C.TAIL_SPRING_MAX_TORQUE,
            C.TAIL_SPRING_STIFFNESS * abs(angle_error)
            + C.TAIL_SPRING_DAMPING * abs(angular_velocity),
        )

    def stop(self) -> None:
        self.joint.motorSpeed = 0
        self.joint.maxMotorTorque = 0

    def rect(self) -> pygame.Rect:
        return body_rect(
            self.body,
            self.width * C.SCALE * self.size_scale,
            self.length * C.SCALE * self.size_scale,
        )


def body_rect(body: PhysicsBody, width: float, height: float) -> pygame.Rect:
    """Axis-aligned bounding box of a rotated rectangle body."""
    half_width = width / 2
    half_height = height / 2
    points = [
        body.local_to_world((-half_width, -half_height)),
        body.local_to_world((half_width, -half_height)),
        body.local_to_world((half_width, half_height)),
        body.local_to_world((-half_width, half_height)),
    ]
    left = math.floor(min(point.x for point in points))
    top = math.floor(min(point.y for point in points))
    right = math.ceil(max(point.x for point in points))
    bottom = math.ceil(max(point.y for point in points))
    return pygame.Rect(left, top, right - left, bottom - top)


def create_horse_head(
    space: PhysicsSpace,
    torso: PhysicsBody,
    torso_length: float,
    torso_height: float,
    group_index: int,
    collision_category: int = 0x0001,
    collision_mask: int = 0xFFFF,
    size_scale: float = 1.0,
) -> HorseHead:
    torso_right = C.MODEL_CENTRE_X + torso_length / 2
    torso_top = C.MODEL_CENTRE_Y - torso_height / 2
    front_offset = torso_right - 386
    top_offset = torso_top - 222
    center_x = 440.5 + front_offset
    center_y = 176 + top_offset
    anchor_x = 367 + front_offset
    anchor_y = 222 + top_offset

    head_position = torso.local_to_world((
        (center_x - C.MODEL_CENTRE_X) * C.SCALE * size_scale,
        (center_y - C.MODEL_CENTRE_Y) * C.SCALE * size_scale,
    ))

    head_geometry = horse_body_geometry(torso_length, torso_height)
    collision_polygons = [
        tuple(
            ((x - center_x) * C.SCALE * size_scale,
             (y - center_y) * C.SCALE * size_scale)
            for x, y in polygon
        )
        for polygon in head_geometry[2:6]
    ]
    body = space.create_compound_polygon_body(
        mass=C.HEAD_MASS * size_scale * size_scale,
        position=head_position,
        polygons=collision_polygons,
        angle=torso.angle,
        friction=C.HEAD_FRICTION,
        group_index=group_index,
        collision_category=collision_category,
        collision_mask=collision_mask,
    )
    anchor = torso.local_to_world((
        (anchor_x - C.MODEL_CENTRE_X) * C.SCALE * size_scale,
        (anchor_y - C.MODEL_CENTRE_Y) * C.SCALE * size_scale,
    ))
    joint = space.create_revolute_joint(
        torso,
        body,
        anchor,
        C.HEAD_MIN_ANGLE,
        C.HEAD_MAX_ANGLE,
        C.HEAD_SPRING_MAX_TORQUE,
    )
    return HorseHead(torso, body, joint, center_x, center_y, size_scale)


def create_horse_tail(
    space: PhysicsSpace,
    torso: PhysicsBody,
    torso_length: float,
    torso_height: float,
    group_index: int,
    collision_category: int = 0x0001,
    collision_mask: int = 0xFFFF,
    length: Optional[float] = None,
    width: Optional[float] = None,
    size_scale: float = 1.0,
) -> HorseTail:
    length = random.uniform(C.TAIL_LENGTH_MIN, C.TAIL_LENGTH_MAX) if length is None else length
    width = random.uniform(C.TAIL_WIDTH_MIN, C.TAIL_WIDTH_MAX) if width is None else width
    tail_angle = C.TAIL_START_ANGLE
    anchor = torso.local_to_world((
        (-torso_length / 2 + C.TORSO_HIP_INSET) * C.SCALE * size_scale,
        -torso_height / 2 * C.SCALE * size_scale,
    ))
    center = torso.local_to_world((
        (-torso_length / 2 + C.TORSO_HIP_INSET) * C.SCALE * size_scale
        - math.sin(tail_angle) * length * C.SCALE * size_scale / 2,
        -torso_height / 2 * C.SCALE * size_scale
        + math.cos(tail_angle) * length * C.SCALE * size_scale / 2,
    ))
    joint_half_width = width * C.SCALE * size_scale * 0.175
    tip_half_width = width * C.SCALE * size_scale / 2
    half_length = length * C.SCALE * size_scale / 2
    body = space.create_polygon_body(
        mass=C.TAIL_MASS * size_scale * size_scale * (length * width) / (
            ((C.TAIL_LENGTH_MIN + C.TAIL_LENGTH_MAX) / 2)
            * ((C.TAIL_WIDTH_MIN + C.TAIL_WIDTH_MAX) / 2)
        ),
        position=center,
        vertices=(
            (-joint_half_width, -half_length),
            (joint_half_width, -half_length),
            (tip_half_width, half_length),
            (-tip_half_width, half_length),
        ),
        angle=torso.angle + tail_angle,
        friction=C.HEAD_FRICTION,
        group_index=group_index,
        collision_category=collision_category,
        collision_mask=collision_mask,
    )
    body.native.gravityScale = 0
    joint = space.create_revolute_joint(
        torso,
        body,
        anchor,
        -C.HEAD_LIMIT_ANGLE,
        C.HEAD_LIMIT_ANGLE,
        C.TAIL_SPRING_MAX_TORQUE,
    )
    return HorseTail(torso, body, joint, length, width, size_scale)