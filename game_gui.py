"""Launch The Party Line with the pygame GUI frontend.

The console version still lives in game_loop.py; this simply swaps in the
pygame implementation of GameInterface. Requires: pip install pygame
"""

from pygame_interface import PygameInterface
from game import Game


def main():
    # A finished run returns to the main menu, so the player can start another
    # without relaunching. The window closing exits the process from wherever
    # the player is, so the loop only ever ends on a non-"new" menu choice.
    interface = PygameInterface()
    while interface.main_menu() == "new":
        game = Game(interface)
        game.run()


if __name__ == "__main__":
    main()
