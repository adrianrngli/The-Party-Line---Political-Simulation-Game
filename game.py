from parties import Party
from nation import Nation
from elections import NationalSenateElection, NationalPresidentialElection, NationalHouseElection
from player import HumanPlayer, CPUPlayer
from issues import AllIssues


class Game:
    """Owns the overall game state and drives it one turn phase at a time.

    The class contains no console I/O of its own: every player decision is
    delegated to a player (which uses the interface), and every "press enter"
    beat or line of narration goes through `self.interface`. A console frontend
    and a GUI frontend can both drive the same phases by supplying different
    GameInterface implementations.
    """

    def __init__(self, interface):
        self.interface = interface
        self.democrats = Party("Democrat", 'D')
        self.democrats.set_political_stances(35, 65, 65)
        self.republicans = Party("Republican", 'R')
        self.republicans.set_political_stances(45, 65, 70)
        self.all_issues = AllIssues()
        initial_centers = {"economic_stance": 40, "foreign_stance": 65, "social_stance": 67.5}
        initial_issues = []
        initial_issues.extend(self.all_issues.generate_issues(1, initial_centers, initial_issues, "economic_stance"))
        initial_issues.extend(self.all_issues.generate_issues(1, initial_centers, initial_issues, "foreign_stance"))
        initial_issues.extend(self.all_issues.generate_issues(1, initial_centers, initial_issues, "social_stance"))
        initial_issues.extend(self.all_issues.generate_issues(1, initial_centers, initial_issues))

        self.players = self._create_players()
        for player in self.players:
            player.set_platform(initial_issues)

        self.nation = Nation([self.democrats, self.republicans], self.players[0].party,
                             self.all_issues, initial_issues, self.interface)

        # Per-year election state, rebuilt each turn.
        self.senate_elections = None
        self.house_elections = None
        self.presidential_election = None

    def _create_players(self):
        """Ask which party the human leads; the CPU takes the other. Human is index 0."""
        choice = self.interface.select(
            "What party will you align yourself with?",
            ['Democratic', 'Republican'],
        )
        if choice == 'Democratic':
            return [HumanPlayer(self.democrats, self.interface),
                    CPUPlayer(self.republicans, self.interface)]
        return [HumanPlayer(self.republicans, self.interface),
                CPUPlayer(self.democrats, self.interface)]

    # --- top-level driver -------------------------------------------------

    def run(self, years=61):
        """Play the game to completion. A GUI can instead call the phase
        methods below directly, interleaving its own rendering."""
        self.report_state_of_the_nation()
        for _ in range(years):
            self.play_year()
        self.retirement(years)

    def retirement(self, years):
        """Close out a finished run: a full career as chair ends in retirement."""
        self.interface.end_screen(
            "Retirement",
            ["After " + str(years) + " years in politics, you retire as chair of the "
             + str(self.players[0].party) + ".",
             "The year is " + str(self.nation.year) + ". The party passes to your successor."],
        )

    def play_year(self):
        self.interface.announce("Polling on issues: ")
        self.nation.display_polling_on_issues()

        self.senate_elections = NationalSenateElection(self.nation)
        self.house_elections = None
        self.presidential_election = None

        if not self.senate_elections.no_elections():
            self.election_setup_phase()
        if self.nation.year != 1960:
            self.legislative_phase()

        self.interface.announce()
        self.nation.mid_year_update()

        self.election_results_phase()

        self.interface.pause("Press enter to advance year ")
        self.interface.announce()
        self.nation.increment_year()
        for player in self.players:
            if type(player) == CPUPlayer:
                player.update_party(self.nation.president)
        if self.nation.year % 4 == 3:
            for player in self.players:
                player.set_platform(self.nation.issues)

    # --- individual turn phases -------------------------------------------

    def election_setup_phase(self):
        """Player nominations for the senate races (and presidential ticket in
        election years). Only reached when there are senate races this year."""
        if self.nation.year % 2 == 0:
            self.house_elections = NationalHouseElection(self.nation)
        self.senate_elections.display_polling()
        self.interface.announce(self.nation.get_senate_totals())
        for player in self.players:
            if type(player) == CPUPlayer:
                player.edit_senate_elections(self.senate_elections)
        for player in self.players:
            if type(player) == HumanPlayer:
                player.edit_senate_elections(self.senate_elections)
        if self.nation.year % 4 == 0:
            self.presidential_setup_phase()

    def presidential_setup_phase(self):
        # The CPU nominates first so the human can see the opposing ticket while
        # choosing their own. Tickets are recombined in player order afterward.
        tickets = {}
        for player in self.players:
            if type(player) == CPUPlayer:
                tickets[player] = player.choose_presidential_ticket(self.nation)
        opponent_ticket = next(iter(tickets.values()), None)
        for player in self.players:
            if type(player) == HumanPlayer:
                tickets[player] = player.choose_presidential_ticket(self.nation, opponent_ticket)
        ordered_tickets = [tickets[player] for player in self.players]
        presidential_candidates = [ticket[0] for ticket in ordered_tickets]
        running_mates = {ticket[0]: ticket[1] for ticket in ordered_tickets}
        self.presidential_election = NationalPresidentialElection(
            self.nation, presidential_candidates, running_mates)

    def legislative_phase(self):
        """The House majority party proposes a bill; the other party sets its
        stance; the bill is put to a vote."""
        proposing_party = self.nation.get_house_majority_party()
        if proposing_party is None:
            return
        proposed_bill = None
        for player in self.players:
            if player.party == proposing_party:
                proposed_bill = player.propose_law(self.nation)
        if proposed_bill is None:
            return  # nothing left on the slate to legislate on until it refreshes
        for player in self.players:
            if player.party != proposing_party:
                player.choose_bill_stance(proposed_bill)
        outcome = proposed_bill.try_to_pass()
        self.interface.show_result(str(proposed_bill), ["Outcome: " + outcome])
        if outcome == "Passed":
            self.nation.record_law(proposed_bill)

    def election_results_phase(self):
        """Run whichever elections were set up this year, in the original order:
        president first, then senate, then house. After each, the map is colored
        by the result for a viewing pause, then reset to neutral."""
        ui = self.interface
        if self.nation.year % 4 == 0:
            ui.pause("Press enter to run the presidential election. ")
            self.presidential_election.run_election()
            ui.set_map_colors(self.presidential_election.result_colors)
            ui.set_state_results(self.presidential_election.state_results)
            ui.pause("Presidential results: click a state to see its result. ")
            ui.set_map_colors(None)
            ui.set_state_results(None)
            ui.announce()
        if not self.senate_elections.no_elections():
            ui.pause("Press enter to run senate elections. ")
            self.senate_elections.run_elections()  # posts the result summary
            ui.set_map_colors(self.senate_elections.result_colors)
            ui.set_state_results(self.senate_elections.state_results)
            ui.pause("Senate results: click a state with a race to see its result. ")
            ui.set_map_colors(None)
            ui.set_state_results(None)
            ui.announce()
            if self.nation.year % 2 == 0:
                ui.pause("Press enter to run house elections. ")
                self.house_elections.run_elections()  # posts the result summary
                ui.set_map_colors(self.house_elections.result_colors)
                ui.set_state_results(self.house_elections.state_results)
                ui.pause("House results: states colored where a party gained seats; click one for details. ")
                ui.set_map_colors(None)
                ui.set_state_results(None)
                ui.announce()

    # --- reporting --------------------------------------------------------

    def report_state_of_the_nation(self):
        ui = self.interface
        ui.announce(str(self.nation.year))
        ui.announce("President:")
        ui.announce(str(self.nation.president))
        ui.announce("Presidential approval rating: "
                    + str(round(self.nation.president.stats["popularity"].value, 1)) + "% approve")
        ui.announce("Senate composition:")
        ui.announce(self.nation.get_senate_totals())
        ui.announce("House composition:")
        ui.announce(self.nation.get_house_totals())
        for party in self.nation.parties:
            ui.announce(str(party) + " approval rating: "
                        + str(round(party.stats["popularity"].value, 1)) + "% approve")
