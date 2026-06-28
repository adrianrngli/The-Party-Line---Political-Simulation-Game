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
        return [nation.presidential_hopefuls[self.party][nominee_index-1], nation.presidential_hopefuls[self.party][running_mate_index-1]]

class CPUPlayer(Player):
    def __init__(self, party):
        super().__init__(party)