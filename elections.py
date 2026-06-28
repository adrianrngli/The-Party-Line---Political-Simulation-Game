from people import Politician, Senator, convert_to_senator, convert_to_president, convert_to_vice_president
from pollstats import PollStat
from issues import Issue, Stance
from nation import Nation
from locations import State
import random
from math import sqrt

class Election:
    """Base class representing an election of some sort between multiple opposing entities"""
    def __init__(self, nation):
        self.nation = nation
        self.points = dict()

class StateElection(Election):
    """Represents an election at the state level"""
    def __init__(self, state, nation, candidates = []):
        super().__init__(nation)
        self.general_candidates = candidates
        self.winner = None
        self.state = state
        for candidate in self.general_candidates:
            self.points[candidate] = 0

    
    def issues_contest(self):
        for candidate in self.general_candidates:
            for issue in self.nation.issues:
                self.points[candidate] += -20.0 * sqrt(100.0 - self.state.stats[issue.type].distance_to(candidate.get_stance(issue))) + 200.0


    def fame_contest(self):
        for candidate in self.general_candidates:
            self.points[candidate] += candidate.stats["fame"].value/2
    
    def popularity_contest(self):
        for candidate in self.general_candidates:
            if candidate.party.letter == 'D' or candidate.party.letter == 'R':
                self.points[candidate] += candidate.stats["popularity"].value/2
    
    def charisma_contest(self):
        for candidate in self.general_candidates:
            if candidate.party.letter == 'D' or candidate.party.letter == 'R':
                self.points[candidate] += candidate.stats["charisma"].value/2

    def random_contest(self):
        partitions = [0, 50]
        for i in range(len(self.general_candidates) - 1):
            partitions.append(random.randint(0, 50))
        partitions.sort()
        for i in range(len(self.general_candidates)):
            self.points[self.general_candidates[i]] += partitions[i+1] - partitions[i]

class StateSenateElection(StateElection):
    """Represents an election for a senator"""
    def __init__(self, state, outgoing, nation):
        general_candidates = []
        self.primary_candidates = dict()
        
        for i in range(2):
            self.primary_candidates[nation.parties[i]] = []
            if (not outgoing.set_to_retire) and outgoing.party == nation.parties[i]:
                general_candidates.append(outgoing)
                self.primary_candidates[nation.parties[i]].append(outgoing)
            else:
                general_candidates.append(Politician(nation.parties[i], state))
                self.primary_candidates[nation.parties[i]].append(general_candidates[i])
            for j in range(2):
                self.primary_candidates[nation.parties[i]].append(Politician(nation.parties[i], state))
        super().__init__(state, nation, general_candidates)
        self.outgoing = outgoing

   
    def incumbency_contest(self):
        for candidate in self.general_candidates:
            if candidate in self.state.senators:
                self.points[candidate] += 50
                return
            
    def headwinds_contest(self):
        if self.nation.year % 4 != 0:
            for i in range(2):
                if self.general_candidates[i].party != self.nation.president.party:
                    self.points[self.general_candidates[i]] += 35

    def run_election(self):
        """runs the election. Elections are made up of contests giving each candidate points. 
        Based on the result of these contests, the winner is made into the new senator.
        returns the results as a string"""
        self.fame_contest()
        self.popularity_contest()
        self.charisma_contest()
        self.issues_contest()
        self.incumbency_contest()
        self.headwinds_contest()
        self.random_contest()
        election_results = self.get_results()
        self.implement_results()
        return election_results

    def get_polling(self):
        """runs a mock election and returns the results as a string"""
        self.fame_contest()
        self.popularity_contest()
        self.charisma_contest()
        self.issues_contest()
        self.incumbency_contest()
        self.headwinds_contest()
        poll_results = self.get_results()
        poll_results += " " + self.race_classification()
        for candidate in self.general_candidates:
            self.points[candidate] = 0
        return poll_results
    
    def get_results(self):
        total_points = 0
        for candidate in self.general_candidates:
            total_points += self.points[candidate]
        results_string = ""
        for i in range(2):
            results_string += str(self.general_candidates[i])
            results_string += " "
            results_string += str(round(100.0*self.points[self.general_candidates[i]]/total_points, 1))
            results_string += "%"
            if i != 1:
                results_string += " "
        
        return results_string
    
    def implement_results(self):
        if self.points[self.general_candidates[0]] > self.points[self.general_candidates[1]]:
            self.winner = self.general_candidates[0]
        elif self.points[self.general_candidates[0]] < self.points[self.general_candidates[1]]:
            self.winner = self.general_candidates[1]
        else:
            raise NotImplementedError
        
        if self.winner not in self.state.senators:
            self.winner.retired = True
            self.winner = convert_to_senator(self.winner, self.nation.year)
            self.state.replace_senator(self.outgoing, self.winner)

    def race_classification(self):
        """Returns a string classifying how the election is projected to go, in the form tossup/tilt/lean/likely/solid (party)"""
        percentages = [0, 0]
        total_points = 0
        if self.points[self.general_candidates[0]] > self.points[self.general_candidates[1]]:
            leader = self.general_candidates[0]
        else:
            leader = self.general_candidates[1]
        for i in range(2):
            percentages[i] += self.points[self.general_candidates[i]] * 100
            total_points += self.points[self.general_candidates[i]]
        for i in range(2):
            percentages[i] /= total_points
        if abs(percentages[0] - percentages[1]) < 1.0:
            return "tossup"
        elif abs(percentages[0] - percentages[1]) < 2.0:
            return "tilt " + leader.party.letter
        elif abs(percentages[0] - percentages[1]) < 5.0:
            return "lean " + leader.party.letter
        elif abs(percentages[0] - percentages[1]) < 15.0:
            return "likely " + leader.party.letter
        else:
            return "solid " + leader.party.letter
        
    def nominate_candidate(self, nominee):
        """Puts a primary candidate as the general candidate nominee for their party"""
        for i in range(2):
            if self.general_candidates[i].party == nominee.party:
                self.points.pop(self.general_candidates[i])
                self.general_candidates[i] = nominee
                self.points[nominee] = 0

    def __str__(self):
        election_header = ""
        for i in range(2):
            election_header += str(self.general_candidates[i])
            if i != 1:
                election_header += " vs. "
        return election_header
    
class StatePresidentialElection(StateElection):
    def __init__(self, state, nation, candidates, running_mates):
        super().__init__(state, nation, candidates)
        self.running_mates = running_mates
        self.popular_vote = dict()
        if self.general_candidates[0].party == self.nation.president.party:
            self.defender = self.general_candidates[0]
            self.challenger = self.general_candidates[1]
        else:
            self.challenger = self.general_candidates[0]
            self.defender = self.general_candidates[1]

    def locality_contest(self):
        for candidate in self.general_candidates:
            if candidate.state.region == self.state.region:
                self.points[candidate] += 10
                if candidate.state == self.state:
                    self.points[candidate] += 25
            if self.running_mates[candidate].state.region == self.state.region:
                self.points[candidate] += 5
                if self.running_mates[candidate].state == self.state:
                    self.points[candidate] += 10

    def unified_party_contest(self):
        for primary_opponent in self.nation.presidential_hopefuls[self.defender.party]:
            if (primary_opponent != self.defender and 
                (primary_opponent == self.nation.president or 
                 primary_opponent.stats["fame"].value > self.defender.stats["fame"].value and primary_opponent.distance_between_stats(self.defender, ["economic_stance", "foreign_stance", "social_stance"]) >= 15.0)):
                self.points[self.challenger] += 15
                return
        self.points[self.defender] += 15
    
    def incumbency_contest(self):
        if self.defender == self.nation.president:
            self.points[self.defender] += 15
        else:
            self.points[self.challenger] += 15

    def no_third_party_contest(self):
        if len(self.general_candidates) > 2:
            self.points[self.challenger] += 15
        else:
            self.points[self.defender] += 15

    def no_recession_contest(self):
        self.points[self.defender] += 15

    def elite_charisma_contest(self):
        if self.defender.stats["charisma"].value > 92.0:
            self.points[self.defender] += 15
        else:
            self.points[self.challenger] += 15
        if self.challenger.stats["charisma"].value > 92.0:
            self.points[self.challenger] += 15
        else:
            self.points[self.defender] += 15

    def run_election(self):
        self.charisma_contest()
        self.popularity_contest()
        self.issues_contest()
        self.locality_contest()
        self.unified_party_contest()
        self.incumbency_contest()
        self.no_third_party_contest()
        self.no_recession_contest()
        self.elite_charisma_contest()
        self.random_contest()
        total_points = 0
        for candidate in self.general_candidates:
            total_points += self.points[candidate]
        for i in range(len(self.general_candidates)):
            self.popular_vote[self.general_candidates[i]] = round(100.0*self.points[self.general_candidates[i]]/total_points, 1)
        return self.popular_vote
    
    def get_results(self):
        result_string = ""
        for i in range(len(self.general_candidates)):
            result_string += str(self.general_candidates[i]) + " " + str(self.popular_vote[self.general_candidates[i]]) + "%"
            if i != len(self.general_candidates) - 1:
                result_string += " "
        return result_string

class NationalSenateElection(Election):
    """Represents the senate elections at the national level. Holds all of the state senate elections for the year"""
    def __init__(self, nation):
        super().__init__(nation)
        self.elections = dict()
        for state in nation.states:
            self.elections[state.abbreviation] = []
        self.initial_seats = nation.get_senate_composition()
        for i in range(2):
            self.points[nation.parties[i]] = 0
        self.initial_leader = None
        if self.initial_seats[self.nation.parties[0]] > self.initial_seats[self.nation.parties[1]]:
            self.initial_leader = self.nation.parties[0]
        elif self.initial_seats[self.nation.parties[1]] > self.initial_seats[self.nation.parties[0]]:
            self.initial_leader = self.nation.parties[1]
        for state in nation.states:
            for sen in state.senators:
                if sen.election_year == nation.year % 6:
                    self.elections[state.abbreviation].append(StateSenateElection(state, sen, nation))

    def display_polling(self):
        """Displays the polling for every election"""
        for state in self.nation.states:
            for election in self.elections[state.abbreviation]:
                print(election.get_polling())
                
    def run_elections(self):
        """Runs every senate election in the current year, implements the results, and then prints the outcome"""
        for state in self.nation.states:
            for election in self.elections[state.abbreviation]:
                print(election.run_election())
        new_leader = None
        outcome_string = ""
        self.points = self.nation.get_senate_composition()
        if self.points[self.nation.parties[0]] > self.points[self.nation.parties[1]]:
            new_leader = self.nation.parties[0]
        elif self.points[self.nation.parties[1]] > self.points[self.nation.parties[0]]:
            new_leader = self.nation.parties[1]
        if new_leader != None and new_leader == self.initial_leader:
            outcome_string = self.initial_leader.name + " hold"
        elif new_leader != None and self.initial_leader != None:
            outcome_string = new_leader.name + " gain"
        change_string = "no net change"
        for i in range(2):
            if self.points[self.nation.parties[i]] > self.initial_seats[self.nation.parties[i]]:
                change_string = self.nation.parties[i].letter + "+" + str(self.points[self.nation.parties[i]] 
                                                                          - self.initial_seats[self.nation.parties[i]])
        print(outcome_string + " (" + change_string + ")")

    def no_elections(self):
        for state in self.nation.states:
            if len(self.elections[state.abbreviation]) > 0:
                return False
        return True
    
class NationalPresidentialElection(Election):
    def __init__(self, nation, candidates, running_mates):
        super().__init__(nation)
        self.elections = dict()
        if candidates[0].party.letter == "R":
            candidates.insert(2, candidates[0])
            candidates.pop(0)
        self.candidates = candidates
        self.electoral_vote = dict()
        self.proportional_vote = dict()
        for candidate in candidates:
            self.electoral_vote[candidate] = 0
            self.proportional_vote[candidate] = 0.0
        for state in nation.states:
            self.elections[state.abbreviation] = StatePresidentialElection(state, nation, candidates, running_mates)
        self.running_mates = running_mates

    def run_election(self):
        total_vote_count = 0.0
        for state in self.nation.states:
            state_results = self.elections[state.abbreviation].run_election()
            state_winner = self.candidates[0]
            for candidate in self.candidates:
                self.proportional_vote[candidate] += state_results[candidate] * state.rep_number
                total_vote_count += state_results[candidate] * state.rep_number
                if state_results[candidate] > state_results[state_winner]:
                    state_winner = candidate
            self.electoral_vote[state_winner] += state.rep_number + 2
            print(state.abbreviation + " (" + str(state.rep_number + 2) + " votes)")
            print(self.elections[state.abbreviation].get_results())
        electoral_vote_string = ""
        popular_vote_string = ""
        
        for i in range(len(self.candidates)):
            electoral_vote_string += str(self.candidates[i]) + " " + str(self.electoral_vote[self.candidates[i]])
            popular_vote_string += str(self.candidates[i]) + " " + str(round(100*self.proportional_vote[self.candidates[i]]/total_vote_count, 2)) + "%"
            if i != len(self.candidates) - 1:
                electoral_vote_string += " "
                popular_vote_string += " "
        print("Electoral vote:")
        print(electoral_vote_string)
        print("Popular Vote:")
        print(popular_vote_string)
        self.implement_results()

    def implement_results(self):
        for candidate in self.candidates:
            if self.electoral_vote[candidate] >= 270:
                self.winner = candidate
        if self.winner == None:
            raise Exception()
        if self.winner != self.nation.president:
            self.winner.retired = True
            self.nation.president = convert_to_president(self.winner)
        if self.running_mates[self.winner] != self.nation.vice_president:
            self.running_mates[self.winner].retired = True
            self.nation.vice_president = convert_to_vice_president(self.running_mates[self.winner])