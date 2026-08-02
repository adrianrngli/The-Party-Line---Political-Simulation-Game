from display_objects import display_person, display_state


class GameInterface:
    """Abstract boundary between game logic and the player.

    All player interaction (prompts, selections, pauses, and display) goes
    through an instance of this class. The game logic and the players never
    call input()/print() directly, so swapping the console frontend for a GUI
    only requires implementing these methods against the new toolkit.
    """

    def select(self, prompt, options, labeler=str, *, details=None, allow_quit=False):
        """Present `options` and return the one the player chooses.

        labeler(option) -> str produces the short label shown in the list.
        details(interface, option), if given, renders richer per-option detail.
        If allow_quit is True the player may back out, in which case return None.
        """
        raise NotImplementedError

    def confirm(self, prompt):
        """Ask a yes/no question. Return True for yes."""
        raise NotImplementedError

    def pause(self, message=""):
        """Block until the player is ready to continue (a 'press enter' beat)."""
        raise NotImplementedError

    def announce(self, text=""):
        """Emit a line of narration/output to the player."""
        raise NotImplementedError

    def show_person(self, person, issues=[]):
        """Render a politician's full profile."""
        raise NotImplementedError

    def show_state(self, state, issues=[]):
        """Render a state's full profile."""
        raise NotImplementedError

    def show_poll(self, title, results):
        """Render poll results, a sequence of (label, percentage) pairs.

        Default: an ASCII bar per option, built on announce(). Graphical
        frontends may override with real bars.
        """
        self.announce(title)
        for label, percent in results:
            filled = int(round(self._clamp_percent(percent) / 100.0 * 20))
            bar = "#" * filled + "-" * (20 - filled)
            self.announce("  " + str(label) + "  " + bar + " " + str(round(percent, 1)) + "%")

    def set_context(self, **fields):
        """Receive current game context (year, president, party, ...) for a
        persistent status display. No-op by default; a GUI can render it."""
        pass

    @staticmethod
    def _clamp_percent(value):
        return max(0.0, min(100.0, value))


class ConsoleInterface(GameInterface):
    """Text frontend: reproduces the game's original console behavior."""

    def select(self, prompt, options, labeler=str, *, details=None, allow_quit=False):
        options = list(options)
        while True:
            for i, option in enumerate(options):
                print(str(i + 1) + ". " + labeler(option))
                if details is not None:
                    details(self, option)
            if allow_quit:
                print("Q. Quit")
            raw = input(prompt + " ")
            if allow_quit and raw.strip().upper() == "Q":
                return None
            try:
                index = int(raw)
            except ValueError:
                continue
            if 1 <= index <= len(options):
                return options[index - 1]

    def confirm(self, prompt):
        answer = input(prompt + " ")
        return len(answer) > 0 and answer[0].upper() == "Y"

    def pause(self, message=""):
        input(message)

    def announce(self, text=""):
        print(text)

    def show_person(self, person, issues=[]):
        display_person(person, issues)

    def show_state(self, state, issues=[]):
        display_state(state, issues)
