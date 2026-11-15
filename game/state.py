"""state.py — Mutable game state shared by every scene.

Money and lasso stock live here so scenes never have to import each other
just to read or write a shared value.
"""

from game import constants as C

# Wallet, in dollars. Changed by betting, the shop and by selling horses.
player_money: int = C.STARTING_MONEY

# How many lassos the player owns. The shop adds one per purchase, catching a
# horse uses one up.
STARTING_LASSOS = 0
lasso_count: int = STARTING_LASSOS