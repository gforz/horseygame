"""world_entities.py — The things that live in the overworld.

WorldHorse   a horse wandering the map, catchable with the lasso
Lasso        throw-and-reel rope
Van          the player's horse trailer: caught-horse inventory UI
Player       the player-controlled van/car
"""

import math
import random

import pygame

from game import constants as C
from game.constants import s
from game.gfx.fonts import get_font
from game.gfx.world_art import build_vehicle_sprite


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

    last_instance = None

    def __init__(self):
        Van.last_instance   = self
        self.inventory      = []          # list[WorldHorse]
        self.open           = False
        self.dragging_horse = None        # WorldHorse | None
        self.drag_offset_x  = 0
        self.drag_offset_y  = 0
        self.drag_start_pos = (0, 0)
        self.hay_items      = []          # list[dict]: [{"rel_x": float, "rel_y": float}]

    # ------------------------------------------------------------------
    def toggle(self) -> None:
        self.open           = not self.open
        self.dragging_horse = None

    def container_rect(self) -> pygame.Rect:
        """The inventory panel, in screen space."""
        return pygame.Rect(
            C.WIDTH // 2 - 350, C.HEIGHT // 2 - 250, 700, 500
        )

    def slot_rect(self, index: int) -> pygame.Rect:
        """Screen rectangle of one inventory slot."""
        container = self.container_rect()
        return pygame.Rect(
            container.x + 30 + (index % 4) * 160,
            container.y + 80 + (index // 4) * 160,
            140, 140,
        )

    def handle_click(self, mouse_pos: tuple) -> None:
        """Check if a horse slot was clicked; start dragging if so."""
        if not self.container_rect().collidepoint(mouse_pos):
            return

        for idx, h in enumerate(self.inventory):
            item_rect = self.slot_rect(idx)
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

        if not self.container_rect().collidepoint(mouse_pos):
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

        container_rect = self.container_rect()
        pygame.draw.rect(screen, C.DARK_BROWN, container_rect, border_radius=12)
        pygame.draw.rect(screen, C.WOOD, container_rect, 4, border_radius=12)

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

        for idx, h in enumerate(self.inventory):
            if h is self.dragging_horse:
                continue

            item_rect = self.slot_rect(idx)
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

        self._sprite_right = build_vehicle_sprite(flip=False)
        self._sprite_left  = build_vehicle_sprite(flip=True)
        self._headlight_beam_right = self._build_headlight_beam()
        self._headlight_beam_left = pygame.transform.flip(
            self._headlight_beam_right, True, False
        )

    # ------------------------------------------------------------------
    def update(self, keys, dt: float = 1.0 / C.FPS_WORLD) -> None:
        movement = C.MOVE_SPEED * dt * C.FPS_WORLD
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x        += movement
            self.direction = 1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x        -= movement
            self.direction = -1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= movement
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += movement

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

    @staticmethod
    def _build_headlight_beam() -> pygame.Surface:
        beam = pygame.Surface((500, 260), pygame.SRCALPHA)
        for source_y in (125, 145):
            pygame.draw.polygon(
                beam,
                (255, 215, 145, 22),
                [
                    (0, source_y - 4),
                    (500, source_y - 105),
                    (500, source_y + 105),
                    (0, source_y + 4),
                ],
            )
            pygame.draw.polygon(
                beam,
                (255, 238, 190, 38),
                [
                    (0, source_y - 3),
                    (340, source_y - 48),
                    (340, source_y + 48),
                    (0, source_y + 3),
                ],
            )
        return beam

    def draw_headlights(
        self,
        screen: pygame.Surface,
        camera_x: float,
        camera_y: float,
    ) -> None:
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        sprite = self._sprite_right if self.direction == 1 else self._sprite_left
        sprite_rect = sprite.get_rect(center=(sx, sy))
        beam = (
            self._headlight_beam_right
            if self.direction == 1
            else self._headlight_beam_left
        )

        if self.direction == 1:
            front_x = sprite_rect.right - 6
            beam_x = front_x
        else:
            front_x = sprite_rect.left
            beam_x = front_x - beam.get_width()

        beam_y = sy - beam.get_height() // 2 + 10
        screen.blit(beam, (beam_x, beam_y))
        for lamp_y in (sy + 3, sy + 13):
            pygame.draw.rect(screen, (255, 247, 190), (front_x, lamp_y, 6, 6))

    @property
    def feet_y(self) -> float:
        """Y-coordinate of the bottom of the vehicle sprite (for depth sorting)."""
        return self.y + C.SPRITE_ROWS * C.CELL / 2