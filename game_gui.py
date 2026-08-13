"""Launch Party Chair Sim with the pygame GUI frontend.

The console version still lives in game_loop.py; this simply swaps in the
pygame implementation of GameInterface. Requires: pip install pygame
"""

from pygame_interface import PygameInterface
from game import Game


def main():
    interface = PygameInterface()
    if interface.main_menu() != "new":
        return
    game = Game(interface)
    game.run()


if __name__ == "__main__":
    main()
