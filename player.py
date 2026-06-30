from parties import Party
from display_objects import display_person, display_state

class Player:
    def __init__(self, party):
        self.party = party

    def edit_senate_elections(self, elections):
        return
    
    def choose_presidential_ticket(self, nation):
        return [nation.presidential_hopefuls[self.party][3], nation.presidential_hopefuls[self.party][0]]

class HumanPlayer(Player):
    def __init__(self, party):
        super().__init__(party)

    def edit_senate_elections(self, senate_election):
        """Menu for the player to choose their candidates in senate elections"""
        if not senate_election.no_elections():
            while True:
                state_input = input("Type in the abbreviation of a state to view election details or Q to quit ")
                if state_input.upper() == "Q":
                    return
                if state_input.upper() in senate_election.elections.keys():
                    for election in senate_election.elections[state_input]:
                        self.choose_senate_candidates(election)

    def choose_senate_candidates(self, election):
        print(election)
        print()
        display_state(election.state, election.nation.issues)
        for candidate in election.general_candidates:
            display_person(candidate, election.nation.issues)
        for i in range (len(election.primary_candidates[self.party])):
            print(i+1)
            display_person(election.primary_candidates[self.party][i], election.nation.issues)
        candidate_number = int(input("Enter the number of the candidate you would like to nominate "))
        election.nominate_candidate(election.primary_candidates[self.party][candidate_number - 1])

    def choose_presidential_ticket(self, nation):
        for i in range(len(nation.presidential_hopefuls[self.party])):
            print(i + 1)
            display_person(nation.presidential_hopefuls[self.party][i], nation.issues)
        nominee_index = -1
        running_mate_index = -1
        while nominee_index == running_mate_index:
            nominee_index = int(input("Enter the number of the candidate you would like to nominate for president "))
            running_mate_index = int(input("Enter the number of the candidate you would like to nominate for vice president "))
        nation.presidential_hopefuls[self.party][nominee_index-1].set_stat("fame", 100)
        return [nation.presidential_hopefuls[self.party][nominee_index-1], nation.presidential_hopefuls[self.party][running_mate_index-1]]

    def set_platform(self, issues):
        """Prompt the player to choose their party's stance on each issue"""
        platform = dict()
        for issue in issues:
            print("Issue: " + str(issue))
            stances = list(issue.stances.values())
            for i in range(len(stances)):
                print(str(i + 1) + ". " + str(stances[i]))
            choice = 0
            while choice < 1 or choice > len(stances):
                choice = int(input("Enter the number of your party's position on this issue "))
            platform[issue] = stances[choice - 1]
        self.party.set_platform(platform)


class CPUPlayer(Player):
    def __init__(self, party):
        super().__init__(party)

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