from parties import Party
from display_objects import display_person, display_state
from laws import Bill
import random

class Player:
    def __init__(self, party):
        self.party = party

    def edit_senate_elections(self, elections):
        return
    
    def choose_presidential_ticket(self, nation):
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

    def propose_law(self, nation):
        """Prompt the player to choose an issue and a stance, then attempt to pass a bill on it"""
        issues = nation.issues
        unresolved_issues = []
        for issue in issues:
            if not issue.resolved:
                unresolved_issues.append(issue)
        for i in range(len(unresolved_issues)):
            print(str(i + 1) + ". " + str(unresolved_issues[i]))
        issue_choice = 0
        while issue_choice < 1 or issue_choice > len(unresolved_issues):
            issue_choice = int(input("Enter the number of the issue you would like to legislate on "))
        issue = unresolved_issues[issue_choice - 1]

        stances = list(issue.stances.values())
        bills = [Bill(issue, stance, self.party, nation.year, nation) for stance in stances]
        for i in range(len(bills)):
            bill_string = str(i+1) + " " + str(bills[i].stance)
            bill_string += ": " + str(bills[i].get_house_party_votes(self.party)) + " House " + self.party.name + " votes, "
            bill_string += str(bills[i].get_senate_party_votes(self.party)) + " Senate " + self.party.name + " votes, "
            if bills[i].get_presidential_approval() == "Pass":
                bill_string += " President approves"
            else:
                bill_string += " President disapproves"
            print(bill_string)
        bill_choice = 0
        while bill_choice < 1 or bill_choice > len(bills):
            bill_choice = int(input("Enter the number of the stance your law will take "))
        bill = bills[bill_choice - 1]
        return bill

    def choose_bill_stance(self, bill):
        player_vote = input("The " + str(bill.proposer) + " is proposing " + str(bill) + ". Will you instruct your party to vote Yea or Nay? ")
        if player_vote[0].upper() == 'Y':
            bill.set_party_vote(self.party, "Yea")
        else:
            bill.set_party_vote(self.party, "Nay")

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