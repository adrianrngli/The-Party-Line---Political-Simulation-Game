from interfaces import ConsoleInterface
from game import Game


def main():
    interface = ConsoleInterface()
    if interface.main_menu() != "new":
        return
    game = Game(interface)
    game.run()


if __name__ == "__main__":
    main()
