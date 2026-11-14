"""
track.py — Race track game loop.

Responsible for:
  - Building the physics world (create_race)
  - Running the betting screen (betting_screen)
  - Running the main race loop (run_track)

All constants, drawing helpers and classes are imported from their
dedicated modules.
"""

import random
import math
from pathlib import Path

import pygame

import constants as C
from constants import s, get_random_horse_color
from classes import Leg, RaceHorse, create_horse_head, create_horse_tail
from physics import PhysicsSpace, torque_to_box2d
from methods import (
    get_font,
    get_back_leg_swing,
    get_random_hoof,
    hoof_vertices,
    torso_mass_for_size,
    draw_track,
    draw_horses,
    lane_rect,
)


# ============================================================
# MUTABLE GAME STATE
# ============================================================

player_money = C.STARTING_MONEY
_unused_race_names: list[str] = []


def load_horse_names() -> list[str]:
    """Load the available race names from the adjacent text file."""
    names_path = Path(__file__).with_name("horse_names.txt")
    with names_path.open(encoding="utf-8") as names_file:
        names = [line.strip() for line in names_file if line.strip()]
    if len(names) != len(set(names)):
        raise ValueError(f"{names_path.name} must not contain duplicate horse names")
    if len(names) < C.LANE_COUNT:
        raise ValueError(
            f"{names_path.name} must contain at least {C.LANE_COUNT} horse names"
        )
    return names


def draw_race_names() -> list[str]:
    """Draw unique names, exhausting a shuffled name cycle before refilling."""
    global _unused_race_names

    names = []
    skipped = []
    while len(names) < C.LANE_COUNT:
        if not _unused_race_names:
            _unused_race_names = load_horse_names()
            random.shuffle(_unused_race_names)

        name = _unused_race_names.pop()
        if name in names:
            skipped.append(name)
        else:
            names.append(name)

    _unused_race_names.extend(skipped)
    return names


# ============================================================
# PHYSICS WORLD FACTORY
# ============================================================

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
            friction=2.5,
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

    BASE_HIP_POSITIONS = [-120 * C.SCALE, 120 * C.SCALE]
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

        # Hip offsets
        if random.random() < C.LEG_OFFSET_CHANCE:
            magnitude  = random.uniform(C.MIN_LEG_OFFSET, C.MAX_LEG_OFFSET)
            shift_ratio = magnitude / C.MAX_LEG_OFFSET
            back_hip_x  = BASE_HIP_POSITIONS[0] + (magnitude * shift_ratio)
            front_hip_x = BASE_HIP_POSITIONS[1] - (magnitude * shift_ratio)
        else:
            back_hip_x  = BASE_HIP_POSITIONS[0]
            front_hip_x = BASE_HIP_POSITIONS[1]

        HIP_POSITIONS = [back_hip_x, front_hip_x]

        # Torso
        torso_length = random.uniform(C.TORSO_LENGTH_MIN, C.TORSO_LENGTH_MAX)
        torso_height = random.uniform(C.TORSO_HEIGHT_MIN, C.TORSO_HEIGHT_MAX)
        hip_limit = (torso_length / 2 - C.TORSO_HIP_INSET) * C.SCALE
        HIP_POSITIONS = [
            max(-hip_limit, min(hip_limit, hip_x))
            for hip_x in HIP_POSITIONS
        ]
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


# ============================================================
# HELPER: DRAW MONEY DISPLAY
# ============================================================

def draw_player_money(screen, money_font):
    """Draws the current money amount flush against the top-left corner with only the bottom-right corner rounded."""
    money_text = f"${player_money}"
    
    m_surf = money_font.render(money_text, True, (30, 160, 50))
    padding_x, padding_y = s(18), s(12)
    
    box_w = m_surf.get_width() + padding_x * 2
    box_h = m_surf.get_height() + padding_y * 2
    
    box_rect = pygame.Rect(-s(4), -s(4), box_w + s(4), box_h + s(4))
    
    pygame.draw.rect(
        screen, 
        (255, 255, 255), 
        box_rect, 
        border_bottom_right_radius=s(14)
    )
    pygame.draw.rect(
        screen, 
        (60, 60, 60), 
        box_rect, 
        max(1, s(2)), 
        border_bottom_right_radius=s(14)
    )
    
    screen.blit(m_surf, (s(14), s(8)))


# ============================================================
# BETTING SCREEN
# ============================================================

def betting_screen(screen, clock, horses, note="", iris_expand=False):
    """Interactive pre-race betting UI with right-side sidebar and clickable WIN lane buttons. Returns (lane, bet) or None."""

    global player_money

    title_font = get_font(s(32), bold=True)
    font       = get_font(s(22))
    small_font = get_font(s(18))
    name_font = get_font(s(32), bold=True)
    money_font = get_font(s(28), bold=True)

    selected = None
    bet      = max(C.MIN_BET, min(C.BET_STEP * 5, max(C.MIN_BET, player_money)))

    sidebar_w = s(360)
    sidebar_rect = pygame.Rect(C.WIDTH - sidebar_w, 0, sidebar_w, C.HEIGHT)

    max_dim = int(math.hypot(C.WIDTH, C.HEIGHT))
    iris_radius = 0 if iris_expand else max_dim

    while True:
        dt = clock.tick(C.FPS_TRACK) / 1000.0

        win_buttons = []
        for lane in range(C.LANE_COUNT):
            l_rect = lane_rect(lane)
            btn_w, btn_h = s(110), s(55)
            btn_x = min(l_rect.right + s(20), sidebar_rect.left - btn_w - s(20))
            btn_rect = pygame.Rect(btn_x, l_rect.centery - btn_h // 2, btn_w, btn_h)
            win_buttons.append((lane, btn_rect))

        buy_btn_rect = pygame.Rect(sidebar_rect.x + s(30), sidebar_rect.bottom - s(100), sidebar_w - s(60), s(55))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); raise SystemExit

            if iris_expand and iris_radius < max_dim:
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_d):
                    bet = min(player_money, bet + C.BET_STEP)
                if event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_a):
                    bet = max(C.MIN_BET, bet - C.BET_STEP)
                if event.key == pygame.K_m:
                    bet = player_money

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                for lane, btn_rect in win_buttons:
                    if btn_rect.collidepoint(pos):
                        selected = lane

                if buy_btn_rect.collidepoint(pos) and selected is not None and player_money >= bet:
                    return selected, bet

        bet = max(C.MIN_BET, min(bet, max(C.MIN_BET, player_money)))

        draw_track(screen)
        draw_horses(screen, horses)
        for horse in horses:
            name_surf = name_font.render(horse.name, True, C.WHITE)
            name_rect = name_surf.get_rect(
                midleft=(horse.rect().right + s(12), horse.rect().centery)
            )
            screen.blit(name_surf, name_rect)

        for lane, btn_rect in win_buttons:
            is_selected = (selected == lane)
            bg_col = C.GOLD if is_selected else (45, 45, 45)
            text_col = (20, 20, 20) if is_selected else C.WHITE
            pygame.draw.rect(screen, bg_col, btn_rect, border_radius=s(8))
            pygame.draw.rect(screen, C.WHITE, btn_rect, max(1, s(2)), border_radius=s(8))
            
            w_surf = title_font.render("WIN?", True, text_col)
            screen.blit(w_surf, w_surf.get_rect(center=btn_rect.center))

        sidebar_surf = pygame.Surface(sidebar_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(sidebar_surf, (25, 22, 12, 240), sidebar_surf.get_rect())
        screen.blit(sidebar_surf, sidebar_rect.topleft)
        pygame.draw.line(screen, C.GOLD, sidebar_rect.topleft, sidebar_rect.bottomleft, max(2, s(3)))

        sy = sidebar_rect.top + s(30)
        sx = sidebar_rect.centerx

        def blit_sidebar(surf, dy=0):
            nonlocal sy
            screen.blit(surf, surf.get_rect(midtop=(sx, sy + dy)))
            sy += surf.get_height() + s(15)

        blit_sidebar(title_font.render("PLACE YOUR BET", True, C.GOLD))
        
        blit_sidebar(small_font.render("Payout: 2 to 1", True, C.GOLD))

        bet_box_rect = pygame.Rect(sidebar_rect.x + s(30), sy, sidebar_w - s(60), s(55))
        pygame.draw.rect(screen, (50, 45, 35), bet_box_rect, border_radius=s(10))
        pygame.draw.rect(screen, C.WHITE, bet_box_rect, max(1, s(2)), border_radius=s(10))
        bet_surf = font.render(f"Bet: ${bet}", True, C.WHITE)
        screen.blit(bet_surf, bet_surf.get_rect(center=bet_box_rect.center))
        sy += bet_box_rect.height + s(15)

        blit_sidebar(small_font.render("Use Up/Down keys to change bet", True, (200, 200, 190)))

        if note:
            sy += s(10)
            blit_sidebar(small_font.render(note, True, C.LOSE_RED))

        can_buy = selected is not None and player_money >= bet
        buy_col = (200, 170, 30) if can_buy else (100, 100, 100)
        pygame.draw.rect(screen, buy_col, buy_btn_rect, border_radius=s(10))
        pygame.draw.rect(screen, C.WHITE, buy_btn_rect, max(1, s(2)), border_radius=s(10))
        
        b_surf = font.render("BUY TICKET", True, (20, 20, 20) if can_buy else (180, 180, 180))
        screen.blit(b_surf, b_surf.get_rect(center=buy_btn_rect.center))

        draw_player_money(screen, money_font)

        if iris_expand:
            iris_radius += int(max_dim * dt * 2.5)
            if iris_radius >= max_dim:
                iris_radius = max_dim
                iris_expand = False

            overlay = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 255))
            pygame.draw.circle(overlay, (0, 0, 0, 0), (C.WIDTH // 2, C.HEIGHT // 2), iris_radius)
            screen.blit(overlay, (0, 0))

        pygame.display.flip()


# ============================================================
# MAIN RACE LOOP
# ============================================================

def run_track() -> None:
    """Run continuous races within the track scene until ESC is pressed."""

    global player_money

    pygame.display.set_caption("Four Horse Racing")
    screen = pygame.display.get_surface() or pygame.display.set_mode((C.WIDTH, C.HEIGHT), pygame.SCALED | pygame.RESIZABLE)
    clock  = pygame.time.Clock()

    track_running = True
    space, horses = create_race()
    should_expand_iris = False
    money_font = get_font(s(26), bold=True)

    while track_running:
        note = ""

        choice = betting_screen(screen, clock, horses, note, iris_expand=should_expand_iris)
        should_expand_iris = False

        if choice is None:
            break

        bet_horse, bet = choice
        player_money -= bet

        running             = True
        physics_accumulator = 0.0
        camera_x            = 0.0

        winner              = None
        race_start_time     = pygame.time.get_ticks()

        rip_progress        = 0.0
        payout_done         = False
        iris_state          = None
        iris_radius         = 0

        while running:
            dt = min(clock.tick(C.FPS_TRACK) / 1000, 0.1)
            mouse_x, mouse_y = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()[0]

            ticket_w, ticket_h = s(320), s(85)
            ticket_rect = pygame.Rect(C.WIDTH // 2 - ticket_w // 2, C.HEIGHT - ticket_h - s(20), ticket_w, ticket_h)

            is_hovering_ticket = ticket_rect.collidepoint((mouse_x, mouse_y))

            if winner is None:
                if is_hovering_ticket and mouse_pressed and iris_state is None:
                    rip_progress += dt * 1.8
                    if rip_progress >= 1.0:
                        rip_progress = 1.0
                        winner = -1
                        iris_state = "shrinking"
                        max_dim = int(math.hypot(C.WIDTH, C.HEIGHT))
                        iris_radius = max_dim
                else:
                    if not mouse_pressed and iris_state is None:
                        rip_progress = 0.0
            else:
                if winner == bet_horse:
                    for event in pygame.event.get():
                        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if is_hovering_ticket and iris_state is None:
                                if not payout_done:
                                    payout_done = True
                                    winnings = bet * C.PAYOUT_ODDS
                                    player_money += bet + winnings
                                iris_state = "shrinking"
                                max_dim = int(math.hypot(C.WIDTH, C.HEIGHT))
                                iris_radius = max_dim
                else:
                    if is_hovering_ticket and mouse_pressed and iris_state is None:
                        rip_progress += dt * 1.8
                        if rip_progress >= 1.0:
                            rip_progress = 1.0
                            iris_state = "shrinking"
                            max_dim = int(math.hypot(C.WIDTH, C.HEIGHT))
                            iris_radius = max_dim
                    else:
                        if not mouse_pressed and iris_state is None:
                            rip_progress = 0.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); raise SystemExit

                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    track_running = False
                    running = False

            # Update horses individually
            if iris_state is None:
                for horse in horses:
                    if not horse.finished:
                        horse.update(dt, is_dragged=False)
                    else:
                        horse.head.stop()
                        horse.head.body.velocity = (0, 0)
                        horse.head.body.angular_velocity = 0
                        horse.tail.stop()
                        horse.tail.body.velocity = (0, 0)
                        horse.tail.body.angular_velocity = 0
                        horse.torso.velocity = (0, 0)
                        horse.torso.angular_velocity = 0
                        for leg in horse.legs:
                            leg.body.velocity = (0, 0)
                            leg.body.angular_velocity = 0
                            leg.stop()

            # Physics step
            if iris_state is None:
                physics_accumulator += dt
                while physics_accumulator >= C.PHYSICS_STEP:
                    space.step(C.PHYSICS_STEP)
                    physics_accumulator -= C.PHYSICS_STEP

                for horse in horses:
                    if not horse.finished and horse.rect().right >= C.FINISH_X:
                        horse.finished = True
                        if winner is None:
                            winner = horse.lane

                if winner is not None and pygame.time.get_ticks() - race_start_time >= C.MAX_RACE_TIME + 3000:
                    if iris_state is None:
                        iris_state = "shrinking"
                        max_dim = int(math.hypot(C.WIDTH, C.HEIGHT))
                        iris_radius = max_dim

                elif winner is None and pygame.time.get_ticks() - race_start_time >= C.MAX_RACE_TIME:
                    best_x = -1
                    best_lane = 0
                    for horse in horses:
                        if horse.rect().right > best_x:
                            best_x = horse.rect().right
                            best_lane = horse.lane
                    winner = best_lane
                    iris_state = "shrinking"
                    max_dim = int(math.hypot(C.WIDTH, C.HEIGHT))
                    iris_radius = max_dim

            leader_x = max(horse.rect().centerx for horse in horses)
            camera_x = max(
                0,
                min(
                    C.TRACK_RIGHT - C.WIDTH,
                    leader_x - C.WIDTH // 3,
                ),
            )
            draw_track(screen, bet_info=None, camera_x=camera_x)
            draw_horses(screen, horses, camera_x)

            if choice is not None and iris_state is None:
                alpha_val = 255 if is_hovering_ticket else 40
                ticket_surf = pygame.Surface((ticket_w, ticket_h), pygame.SRCALPHA)
                
                if winner is None or winner != bet_horse:
                    pygame.draw.rect(ticket_surf, (245, 240, 220, alpha_val), ticket_surf.get_rect(), border_radius=s(8))
                    pygame.draw.rect(ticket_surf, (100, 90, 80, alpha_val), ticket_surf.get_rect(), max(1, s(2)), border_radius=s(8))
                    
                    t_font = get_font(s(20))
                    t_text1 = t_font.render(f"Horse {bet_horse + 1}", True, (20, 20, 20))
                    t_text2 = t_font.render(f"Bet {bet}", True, (50, 50, 50))
                    
                    t_text1.set_alpha(alpha_val)
                    t_text2.set_alpha(alpha_val)
                    
                    ticket_surf.blit(t_text1, t_text1.get_rect(center=(ticket_w // 2, s(28))))
                    ticket_surf.blit(t_text2, t_text2.get_rect(center=(ticket_w // 2, s(58))))

                    if rip_progress > 0.0:
                        fixed_seg_h = s(10)
                        max_segments = int(ticket_h / fixed_seg_h)
                        active_segments = int(max_segments * rip_progress)
                        
                        points = [(ticket_w // 2, 0)]
                        for i in range(1, active_segments + 1):
                            seg_y = int(i * fixed_seg_h)
                            if seg_y > ticket_h:
                                seg_y = ticket_h
                            offset = s(6) if i % 2 == 1 else -s(6)
                            if i == active_segments:
                                offset = 0
                            points.append((ticket_w // 2 + offset, seg_y))
                        
                        if len(points) >= 2:
                            pygame.draw.lines(ticket_surf, (0, 0, 0), False, points, max(2, s(3)))
                else:
                    pygame.draw.rect(ticket_surf, (40, 35, 25, 240), ticket_surf.get_rect(), border_radius=s(8))
                    pygame.draw.rect(ticket_surf, C.GOLD, ticket_surf.get_rect(), max(2, s(3)), border_radius=s(8))

                    win_font = get_font(s(22), bold=True)
                    payout_amt = bet * C.PAYOUT_ODDS
                    w_text1 = win_font.render("WINNER!", True, C.GOLD)
                    w_text2 = get_font(s(18)).render(f"Payout: ${payout_amt}", True, C.WHITE)

                    ticket_surf.blit(w_text1, w_text1.get_rect(center=(ticket_w // 2, s(28))))
                    ticket_surf.blit(w_text2, w_text2.get_rect(center=(ticket_w // 2, s(60))))

                screen.blit(ticket_surf, ticket_rect.topleft)

            draw_player_money(screen, money_font)

            if iris_state is not None:
                max_dim = int(math.hypot(C.WIDTH, C.HEIGHT))
                if iris_state == "shrinking":
                    iris_radius -= int(max_dim * dt * 2.5)
                    if iris_radius <= 0:
                        iris_radius = 0
                        space, horses = create_race()  # Generates fresh randomized colors for the new race!
                        should_expand_iris = True
                        running = False

                overlay = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 255))
                pygame.draw.circle(overlay, (0, 0, 0, 0), (C.WIDTH // 2, C.HEIGHT // 2), iris_radius)
                screen.blit(overlay, (0, 0))

            pygame.display.flip()