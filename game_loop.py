from statholder import StatHolder
from pollstats import PollStat, StatVector, StatOperations
from parties import Party
from locations import State, City
from people import Politician, Representative, Senator, Governor, Mayor
import random
from nation import Nation
from elections import Election, NationalSenateElection, NationalPresidentialElection, NationalHouseElection
from player import HumanPlayer, CPUPlayer
from issues import AllIssues

def initialize_players():
    player_party_choice = input("What party will you align yourself with? (D or R) ").upper()
    if player_party_choice == 'D':
        players.append(HumanPlayer(democrats))
        players.append(CPUPlayer(republicans))
    elif player_party_choice == 'R':
        players.append(HumanPlayer(republicans))
        players.append(CPUPlayer(democrats))
    
democrats = Party("Democrat", 'D')
democrats.set_political_stances(35, 65, 65)
republicans = Party("Republican", 'R')
republicans.set_political_stances(45, 65, 70)
players = []
all_issues = AllIssues()
initial_issues = all_issues.generate_issues(4)
initialize_players()
for player in players:
    player.set_platform(initial_issues)
nation = Nation([democrats, republicans], players[0].party, all_issues, initial_issues)
"""
elections = dict()
for state in nation.states:
    elections[state.abbreviation] = []

def setup_congressional_elections():
    for state in nation.states:
        for sen in state.senators:
            if sen.election_year == nation.year % 6:
                elections[state.abbreviation].append(SenateElection(state, sen, nation))
    for state in elections:
        for election in elections[state]:
            print(election.get_polling())
    print(nation.get_senate_totals())

def run_congressional_elections():
    for state in elections:
        for election in elections[state]:
            print(election.run_election())
        elections[state].clear()
    print(nation.get_senate_totals())
"""
for state in nation.states:
    #print(s.senators[0], s.senators[1])
    #print(s.name, s.stats["economic_stance"].value, s.stats["foreign_stance"].value, s.stats["social_stance"].value, s.stats["agriculture"].value, s.stats["manufacturing"].value, s.stats["professional_services"].value, s.stats["public_sector"].value, s.stats["wealth"].value, s.stats["density"].value)
    #if (StatOperations.distance(s, parties[0], ["economic_stance", "foreign_stance", "social_stance"]) <= StatOperations.distance(s, parties[1], ["economic_stance", "foreign_stance", "social_stance"])):
    #    print(s.name, parties[0].name)
    #else:
    #    print(s.name, parties[1].name)
    for sen in state.senators:
        #print(sen)
        for issue in nation.issues:
            #print(sen.get_stance(issue))
            pass


print(nation.year)
    
print("President:")
print(nation.president)
print("Presidential approval rating: " + str(round(nation.president.stats["popularity"].value, 1)) + "% approve")
print("Senate composition:")
print(nation.get_senate_totals())
print("House composition:")
print(nation.get_house_totals())
for i in range(2):
    print(str(nation.parties[i]) + " approval rating: " + str(round(nation.parties[i].stats["popularity"].value, 1)) + "% approve")

for i in range(60):
    print("Polling on issues: ")
    nation.display_polling_on_issues()
    senate_elections = NationalSenateElection(nation)
    
    if not senate_elections.no_elections():
        if nation.year % 2 == 0:
            house_elections = NationalHouseElection(nation)
        senate_elections.display_polling()
        print(nation.get_senate_totals())
        for i in range(2):
            players[i].edit_senate_elections(senate_elections)
        if nation.year % 4 == 0:
            tickets = []
            for player in players:
                tickets.append(player.choose_presidential_ticket(nation))
            presidential_candidates = []
            running_mates = dict()
            for ticket in tickets:
                presidential_candidates.append(ticket[0])
                running_mates[ticket[0]] = ticket[1]
            presidential_election = NationalPresidentialElection(nation, presidential_candidates, running_mates)
    if nation.year != 1960:
        proposing_party = nation.get_house_majority_party()
        if proposing_party is not None:
            proposed_bill = None
            for player in players:
                if player.party == proposing_party:
                    proposed_bill = player.propose_law(nation)
            for player in players:
                if player.party != proposing_party:
                    player.choose_bill_stance(proposed_bill)
            outcome = proposed_bill.try_to_pass()
            print(outcome)
            if outcome == "Passed":
                nation.record_law(proposed_bill)
    print()
    nation.mid_year_update()
    if nation.year % 4 == 0:
        input("Press enter to run the presidential election. ")
        presidential_election.run_election()
        print()
    if not senate_elections.no_elections():
        input("Press enter to run senate elections. ")
        senate_elections.run_elections()
        print(nation.get_senate_totals())
        print()
        if nation.year % 2 == 0:
            input("Press enter to run house elections. ")
            house_elections.run_elections()
            print(nation.get_house_totals())
            print()

        
    input("Press enter to advance year ")
    print()
    nation.increment_year()
    if nation.year % 4 == 0:
        for player in players:
            player.set_platform(nation.issues)