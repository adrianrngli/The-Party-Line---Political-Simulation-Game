from parties import Party
from laws import Bill
import random
from math import sqrt

class Player:
    def __init__(self, party, interface=None):
        self.party = party
        self.interface = interface

    def edit_senate_elections(self, elections):
        return

    def choose_presidential_ticket(self, nation, opponent_ticket=None):
        presidential_hopefuls = nation.presidential_hopefuls[self.party].copy()
        if nation.president in presidential_hopefuls:
            return [nation.president, nation.vice_president]
        presidential_hopefuls.sort(key=lambda p: p.distance_between_stats(self.party, ["economic_stance", "foreign_stance", "social_stance"]))
        if nation.vice_president in presidential_hopefuls:
            for i in range(len(presidential_hopefuls)):
                if presidential_hopefuls[i] != nation.vice_president:
                    return [nation.vice_president, presidential_hopefuls[i]]
        else:
            if presidential_hopefuls[0].stats["charisma"].value >= presidential_hopefuls[1].stats["charisma"].value:
                return [presidential_hopefuls[0], presidential_hopefuls[1]]
            else:
                return [presidential_hopefuls[0], presidential_hopefuls[1]]

    def propose_law(self, nation):
        unresolved_issues = []
        for issue in nation.issues:
            if not issue.resolved:
                unresolved_issues.append(issue)
        bill_index = random.randint(0, len(unresolved_issues) - 1)
        return Bill(unresolved_issues[bill_index], self.party.get_stance(unresolved_issues[bill_index]), self.party, nation.year, nation)

    def choose_bill_stance(self, bill):
        if bill.stance == self.party.get_stance(bill.issue):
            bill.set_party_vote(self.party, "Yea")
        else:
            bill.set_party_vote(self.party, "Nay")

class HumanPlayer(Player):
    """A player driven by a human, via the supplied GameInterface.

    Each method decides *which* options are available (applying the game's
    rules and constraints) and hands them to the interface to present and
    resolve. No console I/O happens here, so any frontend that implements
    GameInterface can drive a human player.
    """

    def __init__(self, party, interface):
        super().__init__(party, interface)

    def edit_senate_elections(self, senate_election):
        """Let the player browse states with senate races and nominate candidates."""
        if senate_election.no_elections():
            return
        while True:
            states_with_races = [abbreviation
                                 for abbreviation, elections in senate_election.elections.items()
                                 if elections]
            locked_states = {abbreviation
                             for abbreviation in states_with_races
                             if all(election.is_party_locked(self.party)
                                    for election in senate_election.elections[abbreviation])}
            state_polling = senate_election.get_polling_by_state()
            state_choice = self.interface.pick_state(
                "Senate elections: click a highlighted state to nominate your candidate — locked states are already decided. Quit when you're done.",
                states_with_races,
                allow_quit=True,
                info=state_polling,
                locked=locked_states,
            )
            if state_choice is None:
                return
            for election in senate_election.elections[state_choice]:
                if not election.is_party_locked(self.party):
                    self.choose_senate_candidates(election)

    def choose_senate_candidates(self, election):
        issues = election.nation.issues
        self.interface.announce(str(election))
        self.interface.announce()
        self.interface.show_state(election.state, issues)
        opponent = next((candidate for candidate in election.general_candidates
                         if candidate.party != self.party), None)

        def show_opponent(ui):
            ui.announce("Opponent's candidate")
            if opponent is not None:
                ui.show_person(opponent, issues)
            else:
                ui.announce("(none yet)")

        nominee = self.interface.select(
            "Nominate your Senate candidate for " + election.state.name,
            election.primary_candidates[self.party],
            details=lambda ui, candidate: ui.show_person(candidate, issues),
            reference=show_opponent,
            focus_state=election.state.abbreviation,
        )
        election.nominate_candidate(nominee)

    def choose_presidential_ticket(self, nation, opponent_ticket=None):
        hopefuls = nation.presidential_hopefuls[self.party]

        def show_opponent_ticket(ui):
            ui.announce("Opponent's ticket")
            if opponent_ticket:
                ui.announce("For President:")
                ui.show_person(opponent_ticket[0], nation.issues)
                ui.announce("For Vice President:")
                ui.show_person(opponent_ticket[1], nation.issues)
            else:
                ui.announce("(not yet chosen)")

        reference = show_opponent_ticket if opponent_ticket else None
        nominee = self.interface.select(
            "Enter the number of the candidate you would like to nominate for president",
            hopefuls,
            details=lambda ui, candidate: ui.show_person(candidate, nation.issues),
            reference=reference,
        )
        nominee.set_stat("fame", 100)
        running_mate = self.interface.select(
            "Enter the number of the candidate you would like to nominate for vice president",
            [hopeful for hopeful in hopefuls if hopeful != nominee],
            details=lambda ui, candidate: ui.show_person(candidate, nation.issues),
            reference=reference,
        )
        return [nominee, running_mate]

    def set_platform(self, issues):
        """Prompt the player to choose their party's stance on each issue"""
        platform = dict()
        for issue in issues:
            stances = list(issue.stances.values())
            platform[issue] = self.interface.select(
                "Choose your party's position on " + str(issue),
                stances,
            )
        self.party.set_platform(platform)

    def propose_law(self, nation):
        """Prompt the player to choose an issue and a stance, then attempt to pass a bill on it"""
        unresolved_issues = [issue for issue in nation.issues if not issue.resolved]
        issue = self.interface.select(
            "Choose the issue you would like to legislate on",
            unresolved_issues,
        )

        stances = list(issue.stances.values())
        bills = [Bill(issue, stance, self.party, nation.year, nation) for stance in stances]

        def bill_label(bill):
            label = str(bill.stance)
            label += ": " + str(bill.get_house_party_votes(self.party)) + " House " + self.party.name + " votes, "
            label += str(bill.get_senate_party_votes(self.party)) + " Senate " + self.party.name + " votes, "
            if bill.get_presidential_approval() == "Pass":
                label += " President approves"
            else:
                label += " President disapproves"
            return label

        return self.interface.select(
            "Choose your law's stance on " + str(issue),
            bills,
            labeler=bill_label,
        )

    def choose_bill_stance(self, bill):
        prompt = "The " + str(bill.proposer) + " is proposing " + str(bill) + ". Will you instruct your party to vote Yea or Nay?"
        if self.interface.confirm(prompt):
            bill.set_party_vote(self.party, "Yea")
        else:
            bill.set_party_vote(self.party, "Nay")

class CPUPlayer(Player):
    def __init__(self, party, interface=None):
        super().__init__(party, interface)

    def set_platform(self, issues):
        platform = dict()
        for issue in issues:
            closest_stance = issue.stances[next(iter(issue.stances))]
            least_distance = self.party.stats[issue.type].distance_to(closest_stance)
            for stance in issue.stances.keys():
                if self.party.stats[issue.type].distance_to(issue.stances[stance]) < least_distance:
                    closest_stance = issue.stances[stance]
                    least_distance = self.party.stats[issue.type].distance_to(issue.stances[stance])
            platform[issue] = closest_stance
        self.party.set_platform(platform)

    def update_party(self, president):
        for axis in ["economic_stance", "foreign_stance", "social_stance"]:
            if president.stats["popularity"].value >= 50.0:
                self.party.stats[axis].push_toward(president.stats[axis], sqrt(president.stats["popularity"].value - 50.0)/75)
            else:
                self.stats[axis].push_away_from(president.stats[axis], sqrt(50.0 - president.stats["popularity"].value)/75)