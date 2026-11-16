"""race.py — The race track scene.

Runs race after race until ESC is pressed. Every second finished race passes
one stage of the day; when it becomes night the track is empty, so you are sent
back to the world.
"""

import math
from collections.abc import Callable

import pygame

from game import constants as C
from game import daytime
from game import state
from game.constants import s
from game.display import get_screen
from game.gfx.fonts import get_font
from game.gfx.horse_draw import draw_horses
from game.gfx.track_art import draw_track
from game.scenes.race_betting import betting_screen
from game.sim import horse_care
from game.sim.race_setup import create_race
from game.ui import hud


def run_track(
    owned_horses: list | None = None,
    on_day_passed: Callable[[], None] | None = None,
) -> None:
    """Run continuous races within the track scene until ESC is pressed."""

    pygame.display.set_caption("Four Horse Racing")
    screen = get_screen()
    clock  = pygame.time.Clock()
    owned_horses = list(dict.fromkeys(owned_horses or []))

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
        state.player_money -= bet

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
                                    state.player_money += bet + winnings
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
                    if not horse.finished and horse.nose_x() >= C.FINISH_X:
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

            hud.draw_time_lighting(screen)
            hud.draw_hud(screen, money_font, show_lasso=False)

            if iris_state is not None:
                max_dim = int(math.hypot(C.WIDTH, C.HEIGHT))
                if iris_state == "shrinking":
                    iris_radius -= int(max_dim * dt * 2.5)
                    if iris_radius <= 0:
                        iris_radius = 0
                        running = False

                overlay = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 255))
                pygame.draw.circle(overlay, (0, 0, 0, 0), (C.WIDTH // 2, C.HEIGHT // 2), iris_radius)
                screen.blit(overlay, (0, 0))

            pygame.display.flip()

        if payout_done:
            state.bets_won += 1
        else:
            state.bets_lost += 1

        days_passed = daytime.advance_after_race()
        for _ in range(days_passed):
            for horse in owned_horses:
                if not horse.traits.get("dead", False):
                    horse_care.advance_horse_day(horse)
            if on_day_passed is not None:
                on_day_passed()

        if track_running:
            if daytime.is_night():
                track_running = False
            else:
                space, horses = create_race()
                should_expand_iris = True