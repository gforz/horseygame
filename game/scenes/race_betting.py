"""race_betting.py — The pre-race betting screen.

Shows the four horses with their names, a WIN? button per lane and a sidebar
for the stake. Returns (lane, bet), or None if the player backs out.
"""

import math

import pygame

from game import constants as C
from game import state
from game.constants import s
from game.gfx.fonts import get_font
from game.gfx.horse_draw import draw_horses
from game.gfx.track_art import draw_track, lane_rect
from game.ui import hud


def betting_screen(screen, clock, horses, note="", iris_expand=False):
    """Interactive pre-race betting UI with right-side sidebar and clickable WIN lane buttons. Returns (lane, bet) or None."""

    title_font = get_font(s(32), bold=True)
    font       = get_font(s(22))
    small_font = get_font(s(18))
    name_font = get_font(s(32), bold=True)
    money_font = get_font(s(28), bold=True)

    selected = None
    bet      = max(C.MIN_BET, min(C.BET_STEP * 5, max(C.MIN_BET, state.player_money)))

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
                    bet = min(state.player_money, bet + C.BET_STEP)
                if event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_a):
                    bet = max(C.MIN_BET, bet - C.BET_STEP)
                if event.key == pygame.K_m:
                    bet = state.player_money

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                for lane, btn_rect in win_buttons:
                    if btn_rect.collidepoint(pos):
                        selected = lane

                if buy_btn_rect.collidepoint(pos) and selected is not None and state.player_money >= bet:
                    return selected, bet

        bet = max(C.MIN_BET, min(bet, max(C.MIN_BET, state.player_money)))

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

        can_buy = selected is not None and state.player_money >= bet
        buy_col = (200, 170, 30) if can_buy else (100, 100, 100)
        pygame.draw.rect(screen, buy_col, buy_btn_rect, border_radius=s(10))
        pygame.draw.rect(screen, C.WHITE, buy_btn_rect, max(1, s(2)), border_radius=s(10))

        b_surf = font.render("BUY TICKET", True, (20, 20, 20) if can_buy else (180, 180, 180))
        screen.blit(b_surf, b_surf.get_rect(center=buy_btn_rect.center))

        hud.draw_hud(screen, money_font, show_lasso=False)

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