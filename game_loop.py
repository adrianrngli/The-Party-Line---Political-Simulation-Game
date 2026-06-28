from statholder import StatHolder
from pollstats import PollStat, StatVector, StatOperations
from parties import Party
from locations import State, City
from people import Politician, Representative, Senator, Governor, Mayor
import random
from nation import Nation
from elections import Election, NationalSenateElection, NationalPresidentialElection
from player import HumanPlayer, CPUPlayer

def initialize_game():
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
initialize_game()
nation = Nation([democrats, republicans], players[0].party)
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

for i in range(60):
    print(nation.year)
    print(nation.president)
    nation.display_polling_on_issues()
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
    senate_elections = NationalSenateElection(nation)
    if not senate_elections.no_elections():
        senate_elections.display_polling()
        print(nation.get_senate_totals())
        for i in range(2):
            players[i].edit_senate_elections(senate_elections)
        input("Press enter to run elections ")
        senate_elections.run_elections()
        print(nation.get_senate_totals())
        print("\n")
        if nation.year % 4 == 0:
            presidential_election.run_election()
    input("Press enter to advance year ")
    print()
    nation.increment_year()