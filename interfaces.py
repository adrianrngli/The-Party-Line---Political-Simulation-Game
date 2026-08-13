from display_objects import display_person, display_state


class GameInterface:
    """Abstract boundary between game logic and the player.

    All player interaction (prompts, selections, pauses, and display) goes
    through an instance of this class. The game logic and the players never
    call input()/print() directly, so swapping the console frontend for a GUI
    only requires implementing these methods against the new toolkit.
    """

    def main_menu(self, title="The Party Line", options=None):
        """Show the title screen before the game starts and return the action
        the player chose.

        `options` is a list of (label, action) pairs, so later additions (load
        game, settings, quit) only need a longer list here rather than changes
        in each frontend. Default: announce the title and pick from the labels
        via select(); a graphical frontend draws a real title screen.
        """
        options = list(options or [("New Game", "new")])
        self.announce(title)
        self.announce()
        return self.select("Choose an option:", options,
                           labeler=lambda entry: entry[0])[1]

    def end_screen(self, title, lines=(), action_label="Return to Main Menu"):
        """Show the closing screen once a run is over and block until the player
        acknowledges it. Default: announce the title and lines, then pause; a
        graphical frontend gives it a screen of its own."""
        self.announce(title)
        for line in lines:
            self.announce(line)
        self.pause(action_label + " (press enter) ")

    def select(self, prompt, options, labeler=str, *, details=None, allow_quit=False,
               reference=None, focus_state=None):
        """Present `options` and return the one the player chooses.

        labeler(option) -> str produces the short label shown in the list.
        details(interface, option), if given, renders richer per-option detail.
        reference(interface), if given, renders fixed context shown alongside the
        options (e.g. the opponent's candidate) -- it is not selectable.
        focus_state, if given, is a state abbreviation whose info a map frontend
        surfaces automatically (e.g. the state a senate race is in).
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

    def show_vote(self, title, summary, details=None):
        """Show a chamber vote. `title` names the vote, `summary` is the list of
        result lines (party tallies, totals, outcome), and `details` is an
        optional list of individual member-vote lines. Default: announce the
        title, the summary, then the details. A graphical frontend hides the
        details behind a button so only the final result shows up front."""
        self.announce(title)
        for line in summary:
            self.announce(line)
        for line in (details or []):
            self.announce(line)

    def event(self, title, lines=()):
        """Show a breaking-news event or annual report: `title` is the banner
        and `lines` the body lines. Default: emit them as narration. A graphical
        frontend shows a dismissible popup the player must acknowledge before
        continuing."""
        self.announce(title)
        for line in lines:
            self.announce(line)

    def show_decision(self, title, summary):
        """Show the president's sign/veto decision on a bill that passed both
        chambers, as its own screen. Default: announce the title and each line.
        A graphical frontend shows it as a dismissible screen."""
        self.announce(title)
        for line in summary:
            self.announce(line)

    def show_result(self, title, rows):
        """Show a headline result summary that stays on screen while the player
        reviews it -- e.g. an election's national totals -- as a clearly titled,
        labeled block. This is reserved for important outcomes that aren't
        available in any standing panel, so a graphical frontend can give it a
        dedicated, well-formatted area instead of a scrolling feed. `title` names
        the result; `rows` is a list of already-formatted lines. Default: print a
        titled block."""
        self.announce("")
        self.announce(str(title))
        for row in rows:
            self.announce("  " + str(row))

    def pick_state(self, prompt, state_abbrevs, allow_quit=True, info=None,
                   locked=None):
        """Choose one of the given states (by abbreviation), or None if the
        player quits. `info` optionally maps each abbreviation to a line of
        detail (e.g. race polling) a map frontend can surface on hover.
        `locked` is an optional set of abbreviations the player may still
        inspect but no longer edit (e.g. a race whose candidate is already
        chosen); a frontend should show them as locked and not offer them for
        selection. Default: a plain list of the still-editable states via
        select(); a map frontend can override this."""
        locked = set(locked or ())
        selectable = [ab for ab in state_abbrevs if ab not in locked]
        return self.select(prompt, selectable, allow_quit=allow_quit)

    def set_context(self, **fields):
        """Receive current game context (year, president, party, nation, ...)
        for persistent status/panel displays. No-op by default; a GUI uses it."""
        pass

    def set_map_colors(self, party_by_state=None):
        """Color the map by election result: a dict of {state abbreviation ->
        party letter}. Pass None to reset to the neutral default. No-op by
        default; a map frontend uses it while showing results."""
        pass

    def set_state_results(self, results_by_state=None):
        """Attach per-state election result text: a dict of {state abbreviation
        -> list of lines}. Shown in a state's info panel while results are up.
        Pass None to clear. No-op by default; a map frontend uses it."""
        pass

    @staticmethod
    def _clamp_percent(value):
        return max(0.0, min(100.0, value))


class ConsoleInterface(GameInterface):
    """Text frontend: reproduces the game's original console behavior."""

    def select(self, prompt, options, labeler=str, *, details=None, allow_quit=False,
               reference=None, focus_state=None):
        options = list(options)
        while True:
            if reference is not None:
                reference(self)
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
