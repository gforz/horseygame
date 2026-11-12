"""
classes.py — All game-object classes for the Horsey Game.

Race-side:  Leg, RaceHorse
World-side: WorldHorse, Lasso, Van, Player
"""

import math
import random
from typing import Optional

import pygame

import constants as C
from constants import s
from physics import PhysicsBody, PhysicsSpace


# ============================================================
# RACE-SIDE CLASSES
# ============================================================

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
        half_width = C.HEAD_BOX_LENGTH * C.SCALE * self.size_scale / 2
        half_height = C.HEAD_BOX_HEIGHT * C.SCALE * self.size_scale / 2
        points = [
            self.body.local_to_world((-half_width, -half_height)),
            self.body.local_to_world((half_width, -half_height)),
            self.body.local_to_world((half_width, half_height)),
            self.body.local_to_world((-half_width, half_height)),
        ]
        left = math.floor(min(point.x for point in points))
        top = math.floor(min(point.y for point in points))
        right = math.ceil(max(point.x for point in points))
        bottom = math.ceil(max(point.y for point in points))
        return pygame.Rect(left, top, right - left, bottom - top)


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
        half_width = self.width * C.SCALE * self.size_scale / 2
        half_length = self.length * C.SCALE * self.size_scale / 2
        points = [
            self.body.local_to_world((-half_width, -half_length)),
            self.body.local_to_world((half_width, -half_length)),
            self.body.local_to_world((half_width, half_length)),
            self.body.local_to_world((-half_width, half_length)),
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
    from methods import horse_body_geometry

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


class RaceHorse:
    """
    A horse competing on the race track.
    Owns a Box2D torso body and a list of two Leg objects.
    """

    def __init__(
        self,
        lane: int,
        torso: PhysicsBody,
        color: tuple,
        legs: list,        # list[Leg]
        leg_lengths: list,  # list[float]
        start_angle: float,
        head: HorseHead,
        tail: HorseTail,
        torso_length: float,
        torso_height: float,
        hoof_length: float,
        hoof_shape: str,
        size_scale: float = 1.0,
        name: str = "",
    ):
        self.lane        = lane
        self.torso       = torso
        self.color       = color
        self.legs        = legs
        self.leg_lengths = leg_lengths
        self.start_angle = start_angle
        self.head = head
        self.tail = tail
        self.torso_length = torso_length
        self.torso_height = torso_height
        self.hoof_length = hoof_length
        self.hoof_shape = hoof_shape
        self.size_scale = size_scale
        self.name = name

    # ------------------------------------------------------------------
    def rect(self) -> pygame.Rect:
        """Bounding rectangle used for collision / finish-line detection."""
        x = self.torso.position.x - C.MODEL_CENTRE_X * C.SCALE * self.size_scale
        y = self.torso.position.y - C.MODEL_CENTRE_Y * C.SCALE * self.size_scale
        body_left = C.MODEL_CENTRE_X - self.torso_length / 2
        body_right = C.MODEL_CENTRE_X + self.torso_length / 2
        body_top = C.MODEL_CENTRE_Y - self.torso_height / 2
        body_bottom = C.MODEL_CENTRE_Y + self.torso_height / 2
        horse_left = body_left - (126 - C.HORSE_LEFT)
        horse_right = body_right + (C.HORSE_RIGHT - 386)
        horse_top = body_top + (C.HORSE_TOP - 222)
        horse_bottom = body_bottom + (C.HORSE_BOTTOM - 355)
        extra_height = max(self.leg_lengths) - (
            C.DEFAULT_LEG_LENGTH * C.SCALE * self.size_scale
        )

        body_rect = pygame.Rect(
            int(x + horse_left * C.SCALE * self.size_scale),
            int(y + horse_top * C.SCALE * self.size_scale),
            int((horse_right - horse_left) * C.SCALE * self.size_scale),
            int((horse_bottom - horse_top) * C.SCALE * self.size_scale + extra_height),
        )
        return body_rect.union(self.head.rect()).union(self.tail.rect())

    def update(self, dt: float, is_dragged: bool) -> None:
        """Step the leg FSMs; skip if the horse is currently being dragged."""
        if is_dragged:
            self.head.stop()
            self.tail.stop()
            for leg in self.legs:
                leg.stop()
            return

        self.head.update()
        self.tail.update()
        for leg_index, leg in enumerate(self.legs):
            leg.update(dt, self.torso, leg_index)

    def draw(self, surface: pygame.Surface, camera_x: float = 0) -> None:
        """Draw legs, body and head onto *surface*."""
        from methods import draw_horse_body, draw_horse_head, draw_horse_tail, draw_leg

        # Back leg first (drawn behind body)
        draw_leg(
            surface, self.legs[0].body, self.color, self.leg_lengths[0],
            self.hoof_length, self.hoof_shape, camera_x, self.size_scale,
        )
        draw_horse_tail(surface, self, camera_x)
        draw_horse_body(surface, self, camera_x)
        draw_horse_head(surface, self, camera_x)
        # Front leg on top
        draw_leg(
            surface, self.legs[1].body, self.color, self.leg_lengths[1],
            self.hoof_length, self.hoof_shape, camera_x, self.size_scale,
        )


# ============================================================
# WORLD-SIDE CLASSES
# ============================================================

class WorldHorse:
    """A horse wandering in the overworld map."""

    def __init__(self, traits: dict, sprite_right: pygame.Surface,
                 sprite_left: pygame.Surface, x: float, y: float):
        self.traits         = traits
        self.sprite_right  = sprite_right
        self.sprite_left   = sprite_left
        self.x             = x
        self.y             = y
        self.w             = sprite_right.get_width()
        self.h             = sprite_right.get_height()
        self.direction     = random.choice([1, -1])
        self.state         = "idle"      # "idle" | "walk" | "caught"
        self.timer         = random.randint(C.FPS_WORLD, C.FPS_WORLD * 3)
        self.dx            = 0.0
        self.dy            = 0.0

    # ------------------------------------------------------------------
    def rect_at(self, x: float, y: float) -> pygame.Rect:
        return pygame.Rect(
            int(x - self.w / 2),
            int(y - self.h),
            self.w,
            self.h,
        )

    def can_stand(self, x: float, y: float, obstacles: list) -> bool:
        rect = self.rect_at(x, y)
        if rect.left < 20 or rect.right > C.WORLD_WIDTH - 20:
            return False
        if rect.top < 20 or y > C.WORLD_HEIGHT - 10:
            return False
        for obstacle in obstacles:
            if rect.colliderect(obstacle):
                return False
        return True

    def stop(self) -> None:
        self.state  = "idle"
        self.timer  = random.randint(C.FPS_WORLD * 1, C.FPS_WORLD * 3)
        self.dx     = 0.0
        self.dy     = 0.0

    def start_walking(self) -> None:
        dx, dy = random.choice(C.HORSE_DIRECTIONS)
        self.state  = "walk"
        self.timer  = random.randint(C.FPS_WORLD * 1, C.FPS_WORLD * 4)
        self.dx     = dx
        self.dy     = dy
        if dx > 0:
            self.direction = 1
        elif dx < 0:
            self.direction = -1

    def update(self, obstacles: list) -> None:
        if self.state == "caught":
            return

        self.timer -= 1

        if self.state == "idle":
            if self.timer <= 0:
                self.start_walking()
            return

        new_x = self.x + self.dx * C.HORSE_SPEED_WORLD
        new_y = self.y + self.dy * C.HORSE_SPEED_WORLD

        if self.can_stand(new_x, new_y, obstacles):
            self.x = new_x
            self.y = new_y
            if self.timer <= 0:
                self.stop()
        else:
            self.stop()

    def draw(self, screen: pygame.Surface,
             camera_x: float, camera_y: float,
             screen_w: int, screen_h: int) -> None:
        if self.state == "caught":
            return

        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)

        sprite = self.sprite_right if self.direction == 1 else self.sprite_left
        rect   = sprite.get_rect(midbottom=(sx, sy))

        if rect.right < 0 or rect.left > screen_w:
            return
        if rect.bottom < 0 or rect.top > screen_h:
            return

        screen.blit(sprite, rect)


class Lasso:
    """
    Throw-and-reel lasso mechanic with an authentic cowboy rope loop.
    Call throw() on click, update() every frame, draw() to render.
    """

    def __init__(self):
        self.active        = False
        self.pos           = [0.0, 0.0]
        self.target_pos    = [0.0, 0.0]
        self.progress      = 0.0        # 0.0 -> 1.0 traveling out, 1.0 -> 0.0 returning
        self.returning     = False      # True when reeling back (empty or with a horse)
        self.caught_horse    = None       # WorldHorse | None

    def throw(self, from_x: float, from_y: float,
              target_x: float, target_y: float) -> None:
        if self.active:
            return
        
        # Calculate angle and clamp to LASSO_MAX_RANGE
        dist = math.hypot(target_x - from_x, target_y - from_y)
        if dist > 0:
            angle = math.atan2(target_y - from_y, target_x - from_x)
            capped_dist = min(dist, C.LASSO_MAX_RANGE)
            clamped_target_x = from_x + math.cos(angle) * capped_dist
            clamped_target_y = from_y + math.sin(angle) * capped_dist
        else:
            clamped_target_x = from_x
            clamped_target_y = from_y

        self.active        = True
        self.returning     = False
        self.pos           = [from_x, from_y]
        self.target_pos    = [clamped_target_x, clamped_target_y]
        self.progress      = 0.0
        self.caught_horse    = None

    def update(self, horses: list, car_x: float, car_y: float):
        if not self.active:
            return None

        step = C.LASSO_SPEED / C.LASSO_MAX_RANGE

        if not self.returning:
            # Traveling outward from 0.0 to 1.0
            self.progress += step
            if self.progress >= 1.0:
                self.progress = 1.0
                self.returning = True  # Switch to return phase

                # Check hit at maximum extension point
                hit = None
                for h in horses:
                    if h.state != "caught":
                        dist = math.hypot(
                            h.x - self.target_pos[0],
                            h.y - self.target_pos[1],
                        )
                        if dist < 60:
                            hit = h
                            break
                if hit:
                    self.caught_horse = hit
                    self.caught_horse.state = "caught"
        else:
            # Reeling inward from 1.0 down to 0.0
            self.progress -= step

            # If we caught a horse, drag its world coordinates back towards the car
            if self.caught_horse is not None:
                self.caught_horse.x = (
                    car_x + (self.target_pos[0] - car_x) * max(0.0, self.progress)
                )
                self.caught_horse.y = (
                    car_y + (self.target_pos[1] - car_y) * max(0.0, self.progress)
                )

            # Finished reeling back to the car
            if self.progress <= 0.0:
                caught = self.caught_horse
                self.active = False
                self.caught_horse = None
                self.returning = False
                return caught  # Returns the caught horse to add to the van inventory!

        return None

    def draw(self, screen: pygame.Surface,
             car_x: float, car_y: float,
             camera_x: float, camera_y: float) -> None:
        if not self.active:
            return

        car_sx = int(car_x - camera_x)
        car_sy = int(car_y - camera_y)

        if self.caught_horse is None:
            curr_x = car_x + (self.target_pos[0] - car_x) * max(0.0, min(1.0, self.progress))
            curr_y = car_y + (self.target_pos[1] - car_y) * max(0.0, min(1.0, self.progress))
        else:
            curr_x = self.caught_horse.x
            curr_y = self.caught_horse.y

        curr_sx = int(curr_x - camera_x)
        curr_sy = int(curr_y - camera_y)

        rope_color = (210, 180, 140)  # Manila rope tan color

        # Draw main tracking line from player/car to active lasso tip
        pygame.draw.line(screen, rope_color, (car_sx, car_sy), (curr_sx, curr_sy), max(2, s(3)))

        # Draw a rotating cowboy loop / noose head at the tip
        angle = math.atan2(curr_sy - car_sy, curr_sx - car_sx)
        loop_radius = s(16)
        loop_center_x = curr_sx + int(math.cos(angle) * loop_radius)
        loop_center_y = curr_sy + int(math.sin(angle) * loop_radius)
        
        loop_rect = pygame.Rect(0, 0, s(28), s(16))
        loop_surf = pygame.Surface(loop_rect.size, pygame.SRCALPHA)
        pygame.draw.ellipse(loop_surf, rope_color, loop_surf.get_rect(), max(2, s(3)))
        
        degrees = math.degrees(-angle)
        rotated_loop = pygame.transform.rotate(loop_surf, degrees)
        screen.blit(rotated_loop, rotated_loop.get_rect(center=(loop_center_x, loop_center_y)))


class Van:
    """Player's horse trailer — inventory storage and UI overlay."""

    def __init__(self):
        self.inventory      = []          # list[WorldHorse]
        self.open           = False
        self.dragging_horse = None        # WorldHorse | None
        self.drag_offset_x  = 0
        self.drag_offset_y  = 0
        self.drag_start_pos = (0, 0)

    # ------------------------------------------------------------------
    def toggle(self) -> None:
        self.open           = not self.open
        self.dragging_horse = None

    def handle_click(self, mouse_pos: tuple) -> None:
        """Check if a horse slot was clicked; start dragging if so."""
        container_rect = pygame.Rect(
            C.WIDTH // 2 - 350, C.HEIGHT // 2 - 250, 700, 500
        )
        if not container_rect.collidepoint(mouse_pos):
            return

        slot_x = container_rect.x + 30
        slot_y = container_rect.y + 80

        for idx, h in enumerate(self.inventory):
            item_rect = pygame.Rect(
                slot_x + (idx % 4) * 160,
                slot_y + (idx // 4) * 160,
                140, 140,
            )
            if item_rect.collidepoint(mouse_pos):
                self.dragging_horse  = h
                self.drag_offset_x   = mouse_pos[0] - item_rect.x
                self.drag_offset_y   = mouse_pos[1] - item_rect.y
                self.drag_start_pos  = mouse_pos
                break

    def handle_release(self, mouse_pos: tuple,
                       car_x: float, car_y: float) -> None:
        """Drop a dragged horse; release to world if outside the container."""
        if self.dragging_horse is None:
            return

        container_rect = pygame.Rect(
            C.WIDTH // 2 - 350, C.HEIGHT // 2 - 250, 700, 500
        )
        if not container_rect.collidepoint(mouse_pos):
            # Release back into the world near the car
            self.dragging_horse.x     = car_x + random.randint(-60, 60)
            self.dragging_horse.y     = car_y + random.randint(40, 80)
            self.dragging_horse.state = "idle"
            self.inventory.remove(self.dragging_horse)

        self.dragging_horse = None

    def add(self, horse) -> None:
        if horse not in self.inventory:
            self.inventory.append(horse)

    def draw(self, screen: pygame.Surface, mouse_pos: tuple) -> None:
        """Draw the full inventory overlay."""
        if not self.open:
            return

        overlay = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        container_rect = pygame.Rect(
            C.WIDTH // 2 - 350, C.HEIGHT // 2 - 250, 700, 500
        )
        pygame.draw.rect(screen, C.DARK_BROWN, container_rect, border_radius=12)
        pygame.draw.rect(screen, C.WOOD, container_rect, 4, border_radius=12)

        from methods import get_font
        title_font = get_font(30, bold=True)
        small_font = get_font(17)

        title_surf = title_font.render(
            f"Van Inventory (Horses Caught: {len(self.inventory)})",
            True, C.GOLD,
        )
        screen.blit(
            title_surf,
            title_surf.get_rect(center=(container_rect.centerx, container_rect.y + 35)),
        )

        inst_surf = small_font.render(
            "Drag horses outside this container to release them back into the world!",
            True, C.WORLD_WHITE,
        )
        screen.blit(
            inst_surf,
            inst_surf.get_rect(center=(container_rect.centerx, container_rect.bottom - 25)),
        )

        slot_x = container_rect.x + 30
        slot_y = container_rect.y + 80

        for idx, h in enumerate(self.inventory):
            if h is self.dragging_horse:
                continue

            item_rect = pygame.Rect(
                slot_x + (idx % 4) * 160,
                slot_y + (idx // 4) * 160,
                140, 140,
            )
            pygame.draw.rect(screen, (50, 40, 30), item_rect, border_radius=8)
            pygame.draw.rect(screen, C.GOLD, item_rect, 2, border_radius=8)

            mini = pygame.transform.smoothscale(h.sprite_right, (100, 50))
            screen.blit(mini, mini.get_rect(center=item_rect.center))

        # Dragged horse follows cursor
        if self.dragging_horse is not None:
            dx = mouse_pos[0] - self.drag_offset_x
            dy = mouse_pos[1] - self.drag_offset_y
            drag_rect = pygame.Rect(dx, dy, 140, 140)
            pygame.draw.rect(screen, (70, 60, 40), drag_rect, border_radius=8)
            pygame.draw.rect(screen, C.WORLD_WHITE, drag_rect, 2, border_radius=8)
            mini = pygame.transform.smoothscale(self.dragging_horse.sprite_right, (100, 50))
            screen.blit(mini, mini.get_rect(center=drag_rect.center))


class Player:
    """The player-controlled van/car."""

    def __init__(self, x: float, y: float):
        self.x         = x
        self.y         = y
        self.direction = 1    # 1 = right, -1 = left

        from methods import build_vehicle_sprite
        self._sprite_right = build_vehicle_sprite(flip=False)
        self._sprite_left  = build_vehicle_sprite(flip=True)

    # ------------------------------------------------------------------
    def update(self, keys) -> None:
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x        += C.MOVE_SPEED
            self.direction = 1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x        -= C.MOVE_SPEED
            self.direction = -1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= C.MOVE_SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += C.MOVE_SPEED

        self.x = max(45, min(C.WORLD_WIDTH  - 45, self.x))
        self.y = max(45, min(C.WORLD_HEIGHT - 45, self.y))

    def near_track(self, track_rect: pygame.Rect) -> bool:
        player_rect      = pygame.Rect(int(self.x - 35), int(self.y - 35), 70, 70)
        interaction_area = track_rect.inflate(100, 100)
        return player_rect.colliderect(interaction_area)

    def draw(self, screen: pygame.Surface,
             camera_x: float, camera_y: float) -> None:
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        sprite = self._sprite_right if self.direction == 1 else self._sprite_left
        screen.blit(sprite, sprite.get_rect(center=(sx, sy)))

    @property
    def feet_y(self) -> float:
        """Y-coordinate of the bottom of the vehicle sprite (for depth sorting)."""
        return self.y + C.SPRITE_ROWS * C.CELL / 2