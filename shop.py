"""shop.py — Lasso-Mart shop interior scene."""

import pygame

import constants as C
import track
from methods import get_font


def run_shop() -> None:
    """Run the Lasso-Mart shop interior loop."""
    screen = pygame.display.get_surface()
    if screen is None:
        raise RuntimeError("The display must be initialized before entering the shop.")

    pygame.display.set_caption("Lasso-Mart")
    clock = pygame.time.Clock()

    # Colors
    WOOD_BG = (130, 80, 35)
    PANEL_BG = (40, 100, 50)
    TEXT_WHITE = (255, 255, 255)
    GOLD = (255, 215, 0)

    # Map button rect (top right)
    map_btn_rect = pygame.Rect(screen.get_width() - 110, 20, 90, 40)

    # Purchase feedback message
    message = ""
    message_until = 0

    while True:
        dt = min(clock.tick(C.FPS_WORLD) / 1000.0, 0.033)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check MAP button click
                if map_btn_rect.collidepoint(event.pos):
                    return

                # Check item purchases
                if hay_rect.collidepoint(event.pos):
                    if track.player_money >= 5:
                        track.player_money -= 5
                        message = "Purchased Hay!"
                        message_until = pygame.time.get_ticks() + 2000
                    else:
                        message = "Not enough money!"
                        message_until = pygame.time.get_ticks() + 2000
                elif lasso_item_rect.collidepoint(event.pos):
                    if track.player_money >= 60:
                        track.player_money -= 60
                        message = "Purchased Lasso!"
                        message_until = pygame.time.get_ticks() + 2000
                    else:
                        message = "Not enough money!"
                        message_until = pygame.time.get_ticks() + 2000

        screen.fill(WOOD_BG)

        # Title: Lasso-Mart at top center
        title_font = get_font(C.s(40), bold=True)
        title_surf = title_font.render("Lasso-Mart", True, (200, 60, 200))
        title_rect = title_surf.get_rect(center=(screen.get_width() // 2, C.s(50)))
        screen.blit(title_surf, title_rect)

        # Money display (top left)
        track.draw_player_money(screen, get_font(C.s(28), bold=True))

        # MAP button (top right)
        pygame.draw.rect(screen, (220, 60, 60), map_btn_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), map_btn_rect, 2, border_radius=8)
        map_font = get_font(C.s(20), bold=True)
        map_text = map_font.render("MAP", True, TEXT_WHITE)
        screen.blit(map_text, map_text.get_rect(center=map_btn_rect.center))

        # Price list board on the right (Hay $5 and Lasso $60)
        board_w, board_h = 320, 150
        board_x = screen.get_width() - board_w - 60
        board_y = 120
        board_rect = pygame.Rect(board_x, board_y, board_w, board_h)
        pygame.draw.rect(screen, PANEL_BG, board_rect, border_radius=10)
        pygame.draw.rect(screen, (20, 60, 30), board_rect, 3, border_radius=10)

        item_font = get_font(C.s(24), bold=True)
        hay_text = item_font.render("Hay $5", True, TEXT_WHITE)
        lasso_text = item_font.render("Lasso $60", True, TEXT_WHITE)

        hay_rect = pygame.Rect(board_x + 30, board_y + 25, board_w - 60, 45)
        lasso_item_rect = pygame.Rect(board_x + 30, board_y + 80, board_w - 60, 45)

        # Hover effects
        if hay_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (60, 140, 70), hay_rect, border_radius=6)
        if lasso_item_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (60, 140, 70), lasso_item_rect, border_radius=6)

        screen.blit(hay_text, hay_text.get_rect(center=hay_rect.center))
        screen.blit(lasso_text, lasso_text.get_rect(center=lasso_item_rect.center))

        # Counter desk at the bottom (clean, no boot)
        counter_rect = pygame.Rect(0, screen.get_height() - 220, screen.get_width(), 220)
        pygame.draw.rect(screen, (100, 55, 20), counter_rect)
        pygame.draw.line(screen, (150, 90, 35), counter_rect.topleft, counter_rect.topright, 8)

        # Purchase Popup Message
        if pygame.time.get_ticks() < message_until:
            msg_font = get_font(C.s(28), bold=True)
            msg_surf = msg_font.render(message, True, GOLD)
            msg_rect = msg_surf.get_rect(center=(screen.get_width() // 2, screen.get_height() - 120))
            pygame.draw.rect(screen, (40, 20, 10), msg_rect.inflate(30, 16), border_radius=8)
            pygame.draw.rect(screen, GOLD, msg_rect.inflate(30, 16), 2, border_radius=8)
            screen.blit(msg_surf, msg_rect)

        pygame.display.flip()