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

class StateHouseElection(Election):
    def __init__(self, state, nation):
        super().__init__(nation)
        self.state = state
        for i in range(2):
            self.points[self.nation.parties[i]] = 0

    def first_year_contest(self):
        if self.nation.year == 1960:
            for i in range(2):
                if self.nation.parties[i] == self.nation.president.party:
                    self.points[self.nation.parties[i]] += 100

    def issues_contest(self):
        for i in range(2):
            for issue in self.nation.issues:
                party_stance = self.nation.parties[i].get_stance(issue)
                self.points[self.nation.parties[i]] += -10.0 * sqrt(self.state.stats[issue.type].distance_to(party_stance)) + 100.0
                for industry in party_stance.industry_effects.keys():
                    self.points[self.nation.parties[i]] += party_stance.industry_effects[industry] / 2


    def popularity_contest(self):
        for i in range(2):
            self.points[self.nation.parties[i]] += self.nation.parties[i].stats["popularity"].value

    def headwinds_contest(self):
        if self.nation.year % 4 != 0:
            for i in range(2):
                if self.nation.parties[i] != self.nation.president.party:
                    self.points[self.nation.parties[i]] += 50
    
    def random_contest(self):
        partitions = [0, 50]
        for i in range(2):
            partitions.append(random.randint(0, 50))
        partitions.sort()
        for i in range(2):
            self.points[self.nation.parties[i]] += partitions[i+1] - partitions[i]

    def run_election(self):
        self.first_year_contest()
        self.issues_contest()
        self.popularity_contest()
        self.headwinds_contest()
        self.random_contest()
        self.implement_results()

    def implement_results(self):
        total_vote = self.points[self.nation.parties[0]] + self.points[self.nation.parties[1]]
        self.state.rep_composition[self.nation.parties[0]] = round(self.state.rep_number * self.points[self.nation.parties[0]] / total_vote)
        self.state.rep_composition[self.nation.parties[1]] = round(self.state.rep_number - self.state.rep_composition[self.nation.parties[0]])

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
        for issue in self.nation.issues:
            candidate_dists = dict()
            for candidate in self.general_candidates:
                candidate_stance = candidate.get_stance(issue)
                candidate_dists[candidate] = self.state.stats[issue.type].distance_to(candidate_stance)
                self.points[candidate] += -20.0 * sqrt(candidate_dists[candidate]) + 200.0
                for industry in candidate_stance.industry_effects.keys():
                    self.points[candidate] += candidate_stance.industry_effects[industry]
            if candidate_dists[self.general_candidates[0]] < candidate_dists[self.general_candidates[1]]:
                self.points[self.general_candidates[0]] += 2 * (candidate_dists[self.general_candidates[1]] - candidate_dists[self.general_candidates[0]])
            else:
                self.points[self.general_candidates[1]] += 2 * (candidate_dists[self.general_candidates[0]] - candidate_dists[self.general_candidates[1]])

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

    def no_recession_contest(self):
        in_national_recession = self.nation.econ_record.get_growth(self.nation.year) < 0.0
        in_state_recession = self.state.econ_record.get_growth(self.nation.year) < 0.0
        if in_national_recession:
            for candidate in self.general_candidates:
                if (candidate.party.letter == 'D' or candidate.party.letter == 'R') and candidate.party != self.nation.president.party:
                    self.points[candidate] += 8
        if in_state_recession:
            for candidate in self.general_candidates:
                if (candidate.party.letter == 'D' or candidate.party.letter == 'R') and candidate.party != self.nation.president.party:
                    self.points[candidate] += 8
        if not (in_national_recession or in_state_recession):
            for candidate in self.general_candidates:
                if candidate.party == self.nation.president.party:
                    self.points[candidate] += 8

    def long_term_economy_contest(self):
        current_growth = self.state.econ_record.average_growth((self.nation.year - 4) - (self.nation.year % 4) + 1, self.nation.year)
        past_growth = self.state.econ_record.average_growth((self.nation.year - 12) - (self.nation.year % 4) + 1, (self.nation.year - 4) - (self.nation.year % 4))
        if current_growth >= past_growth:
            for candidate in self.general_candidates:
                if candidate.party == self.nation.president.party:
                    self.points[candidate] += 8
        else:
            for candidate in self.general_candidates:
                if (candidate.party.letter == 'D' or candidate.party.letter == 'R') and candidate.party != self.nation.president.party:
                    self.points[candidate] += 8

    def random_contest(self):
        partitions = [0, 20]
        for i in range(len(self.general_candidates) - 1):
            partitions.append(random.randint(0, 20))
        partitions.sort()
        for i in range(len(self.general_candidates)):
            self.points[self.general_candidates[i]] += partitions[i+1] - partitions[i]

class StateSenateElection(StateElection):
    """Represents an election for a senator"""
    def __init__(self, state, outgoing, nation):
        general_candidates = []
        self.primary_candidates = dict()
        self.locked = dict()
        for party in nation.parties:
            self.locked[party] = False
        for i in range(2):
            self.primary_candidates[nation.parties[i]] = []
            if (not outgoing.set_to_retire) and outgoing.party == nation.parties[i]:
                self.primary_candidates[nation.parties[i]].append(outgoing)
            else:
                self.primary_candidates[nation.parties[i]].append(Politician(nation.parties[i], state))
            for j in range(2):
                self.primary_candidates[nation.parties[i]].append(Politician(nation.parties[i], state))
        for i in range(2):
            self.primary_candidates[nation.parties[i]].sort(key=lambda x: -x.stats["fame"].value)
            for j in range(1, 3):
                if self.primary_candidates[nation.parties[i]][j] == outgoing:
                    self.primary_candidates[nation.parties[i]][j] = self.primary_candidates[nation.parties[i]][0]
                    self.primary_candidates[nation.parties[i]][0] = outgoing
                    break
            general_candidates.append(self.primary_candidates[nation.parties[i]][0])
        super().__init__(state, nation, general_candidates)
        self.outgoing = outgoing

    def first_year_contest(self):
        if self.nation.year == 1960:
            for candidate in self.general_candidates:
                if (candidate.party.letter == 'D' or candidate.party.letter == 'R') and candidate.party == self.nation.president.party:
                    self.points[candidate] += 100
   
    def incumbency_contest(self):
        for candidate in self.general_candidates:
            if candidate in self.state.senators:
                self.points[candidate] += 100
                return
                  
    def headwinds_contest(self):
        if self.nation.year % 4 != 0:
            for i in range(2):
                if self.general_candidates[i].party != self.nation.president.party:
                    self.points[self.general_candidates[i]] += 50

    def run_election(self):
        """runs the election. Elections are made up of contests giving each candidate points. 
        Based on the result of these contests, the winner is made into the new senator.
        returns the results as a string"""
        self.first_year_contest()
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
        self.locked[nominee.party] = True

    def is_party_locked(self, party):
        return self.locked[party]

    def __str__(self):
        election_header = ""
        for i in range(2):
            election_header += str(self.general_candidates[i])
            if i != 1:
                election_header += " vs. "
        return election_header
    
class StatePresidentialElection(StateElection):
    # Points the challenger gains per term the incumbent party has held the White
    # House beyond the first, once it has held it for at least two terms. Tune
    # this to make voter fatigue with a long-tenured party stronger or weaker.
    BACKLASH_POINTS_PER_TERM = 20

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

    def first_year_contest(self):
        if self.nation.year == 1960:
            for candidate in self.general_candidates:
                if (candidate.party.letter == 'D' or candidate.party.letter == 'R') and candidate.party != self.nation.president.party:
                    self.points[candidate] += 100

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

    def popularity_contest(self):
        for candidate in self.general_candidates:
            if candidate.party.letter == 'D' or candidate.party.letter == 'R':
                if candidate == self.nation.president:
                    self.points[candidate] += self.state.stats["presidential_approval"].value/2
                else:
                    self.points[candidate] += candidate.stats["popularity"].value/2

    def unified_party_contest(self):
        for primary_opponent in self.nation.presidential_hopefuls[self.defender.party]:
            if (primary_opponent != self.defender and 
                (primary_opponent == self.nation.president or 
                 primary_opponent.stats["fame"].value > self.defender.stats["fame"].value and primary_opponent.distance_between_stats(self.defender, ["economic_stance", "foreign_stance", "social_stance"]) >= 15.0)):
                self.points[self.challenger] += 8
                return
        self.points[self.defender] += 8

    def party_mandate_contest(self):
        house_vote_difference = 0
        for year in [self.nation.year - 4, self.nation.year - 2]:
            result_string = self.nation.house_election_results[year]
            if result_string[0] == self.defender.party.letter:
                house_vote_difference += int(result_string[2:])
            elif result_string[0] == self.challenger.party.letter:
                house_vote_difference -= int(result_string[2:])
        if house_vote_difference > 0:
            self.points[self.defender] += 8
        else:
            self.points[self.challenger] += 8
    
    def incumbency_contest(self):
        if self.defender == self.nation.president:
            self.points[self.defender] += 8
        else:
            self.points[self.challenger] += 8

    def out_of_power_contest(self):
        """"Time for a change": a party shut out of the White House for two or
        more terms benefits from voter fatigue with the incumbent party. The
        challenger's party has been out of power for exactly as many terms as the
        incumbent party has held it, so once that streak reaches two terms the
        challenger gets a point advantage that grows with each further term."""
        terms_held = self.nation.consecutive_white_house_terms
        if terms_held >= 2:
            self.points[self.challenger] += self.BACKLASH_POINTS_PER_TERM * int(pow(2, (terms_held - 2)))

    def no_third_party_contest(self):
        if len(self.general_candidates) > 2:
            self.points[self.challenger] += 8
        else:
            self.points[self.defender] += 8

    def no_recession_contest(self):
        in_national_recession = self.nation.econ_record.get_growth(self.nation.year) < 0.0
        in_state_recession = self.state.econ_record.get_growth(self.nation.year) < 0.0
        if in_national_recession:
            self.points[self.challenger] += 8   
        if in_state_recession:
            self.points[self.challenger] += 8
        if not (in_national_recession or in_state_recession):
            self.points[self.defender] += 8

    

    def scandal_contest(self):
        if self.nation.presidential_scandal:
            self.points[self.challenger] += 8
        else:
            self.points[self.defender] += 8

    def elite_charisma_contest(self):
        if self.defender.stats["charisma"].value > 92.0:
            self.points[self.defender] += 8
        else:
            self.points[self.challenger] += 8
        if self.challenger.stats["charisma"].value > 92.0:
            self.points[self.challenger] += 8
        else:
            self.points[self.defender] += 8
        
    def bills_contest(self):
        major_bill_passed = False
        for year in range(self.nation.year - 3, self.nation.year + 1):
            if self.nation.laws_passed[year] != None and not self.nation.laws_passed[year].stance.moderate:
                major_bill_passed = True
                law = self.nation.laws_passed[year]
                if self.state.law_popularity(law.issue, law.stance) > 50.0:
                    self.points[self.defender] += 2
        if not major_bill_passed:
            self.points[self.challenger] += 8

    def run_election(self):
        self.first_year_contest()
        self.charisma_contest()
        self.popularity_contest()
        self.issues_contest()
        self.locality_contest()
        self.party_mandate_contest()
        self.unified_party_contest()
        self.incumbency_contest()
        self.out_of_power_contest()
        self.no_third_party_contest()
        self.no_recession_contest()
        self.long_term_economy_contest()
        self.scandal_contest()
        self.bills_contest()
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
        self.result_colors = dict()  # abbrev -> winning party letter, for the map
        self.state_results = dict()  # abbrev -> [result lines], for the state panel
        for i in range(2):
            self.points[nation.parties[i]] = 0
        self.initial_leader = self.nation.get_senate_majority_party()
        for state in nation.states:
            for sen in state.senators:
                if sen.election_year == nation.year % 6:
                    self.elections[state.abbreviation].append(StateSenateElection(state, sen, nation))

    def display_polling(self):
        """Displays the polling for every election"""
        for state in self.nation.states:
            for election in self.elections[state.abbreviation]:
                self.nation.interface.announce(election.get_polling())

    def get_polling_by_state(self):
        """Return {state abbreviation -> polling string} for each race, for a
        frontend to surface while the player browses the map."""
        polling = dict()
        for state in self.nation.states:
            for election in self.elections[state.abbreviation]:
                polling[state.abbreviation] = election.get_polling()
        return polling

    def run_elections(self):
        """Runs every senate election in the current year, implements the results, and then prints the outcome"""
        for state in self.nation.states:
            for election in self.elections[state.abbreviation]:
                results = election.run_election()
                self.nation.interface.announce(results)
                self.result_colors[state.abbreviation] = election.winner.party.letter
                self.state_results.setdefault(state.abbreviation, []).append(results)
        new_leader = None
        outcome_string = ""
        self.points = self.nation.get_senate_composition()
        new_leader = self.nation.get_senate_majority_party()
        if new_leader != None and new_leader == self.initial_leader:
            outcome_string = self.initial_leader.name + " hold"
        elif new_leader != None and self.initial_leader != None:
            outcome_string = new_leader.name + " gain"
        change_string = "no net change"
        for i in range(2):
            if self.points[self.nation.parties[i]] > self.initial_seats[self.nation.parties[i]]:
                change_string = self.nation.parties[i].letter + "+" + str(self.points[self.nation.parties[i]]
                                                                          - self.initial_seats[self.nation.parties[i]])
        self.nation.interface.show_result(
            "Senate Election Results",
            [outcome_string + " (" + change_string + ")",
             "New Senate: " + self.nation.get_senate_totals() + " (51 needed for a majority)"])

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
        self.result_colors = dict()  # abbrev -> winning party letter, for the map
        self.state_results = dict()  # abbrev -> [result lines], for the state panel
        for candidate in candidates:
            self.electoral_vote[candidate] = 0
            self.proportional_vote[candidate] = 0.0
        for state in nation.presidential_states():
            self.elections[state.abbreviation] = StatePresidentialElection(state, nation, candidates, running_mates)
        self.running_mates = running_mates

    def run_election(self):
        total_vote_count = 0.0
        for state in self.nation.presidential_states():
            state_results = self.elections[state.abbreviation].run_election()
            state_winner = self.candidates[0]
            for candidate in self.candidates:
                self.proportional_vote[candidate] += state_results[candidate] * state.rep_number
                total_vote_count += state_results[candidate] * state.rep_number
                if state_results[candidate] > state_results[state_winner]:
                    state_winner = candidate
            self.result_colors[state.abbreviation] = state_winner.party.letter
            self.electoral_vote[state_winner] += state.rep_number + 2
            self.state_results[state.abbreviation] = [
                self.elections[state.abbreviation].get_results(),
                str(state.rep_number + 2) + " electoral votes -> " + state_winner.party.letter]
        winner = self.candidates[0]
        for candidate in self.candidates:
            if self.electoral_vote[candidate] > self.electoral_vote[winner]:
                winner = candidate
        rows = [str(winner) + " wins the presidency"]
        for candidate in self.candidates:
            rows.append(str(candidate) + ":  " + str(self.electoral_vote[candidate])
                        + " electoral votes,  "
                        + str(round(100 * self.proportional_vote[candidate] / total_vote_count, 1))
                        + "% of the popular vote")
        rows.append("270 electoral votes needed to win")
        self.nation.interface.show_result("Presidential Election Results", rows)
        self.implement_results()

    def implement_results(self):
        for candidate in self.candidates:
            if self.electoral_vote[candidate] >= 270:
                self.winner = candidate
        if self.winner == None:
            raise Exception()
        # Track how long one party keeps the White House: another consecutive
        # term if the incumbent party held on, otherwise the streak resets.
        if self.winner.party == self.nation.president.party:
            self.nation.consecutive_white_house_terms += 1
        else:
            self.nation.consecutive_white_house_terms = 1
        if self.winner != self.nation.president:
            self.winner.retired = True
            self.nation.president = convert_to_president(self.winner, self.nation.states, self.nation.issues)
        if self.running_mates[self.winner] != self.nation.vice_president:
            self.running_mates[self.winner].retired = True
            self.nation.vice_president = convert_to_vice_president(self.running_mates[self.winner])

class NationalHouseElection(Election):

    def __init__(self, nation):
        super().__init__(nation)
        self.initial_seats = nation.get_house_composition()
        self.initial_leader = nation.get_house_majority_party()
        self.result_colors = dict()  # abbrev -> party that gained seats, for the map
        self.state_results = dict()  # abbrev -> [result lines], for the state panel
        self.elections = dict()
        for state in nation.states:
            self.elections[state.abbreviation] = StateHouseElection(state, nation)

    def run_elections(self):
        p0, p1 = self.nation.parties
        for state in self.nation.states:
            before0, before1 = state.rep_composition[p0], state.rep_composition[p1]
            self.elections[state.abbreviation].run_election()
            after0, after1 = state.rep_composition[p0], state.rep_composition[p1]
            gain0, gain1 = after0 - before0, after1 - before1
            # Color the state by whichever party gained seats (a swing map);
            # states with no net change stay neutral. Report the change compactly,
            # with the resulting seat composition underneath.
            if gain0 > 0:
                self.result_colors[state.abbreviation] = p0.letter
                change = p0.letter + "+" + str(gain0)
            elif gain1 > 0:
                self.result_colors[state.abbreviation] = p1.letter
                change = p1.letter + "+" + str(gain1)
            else:
                change = "No change"
            composition = p0.letter + " " + str(after0) + ", " + p1.letter + " " + str(after1)
            self.state_results[state.abbreviation] = [change, composition]
        new_leader = None
        outcome_string = ""
        self.points = self.nation.get_house_composition()
        new_leader = self.nation.get_house_majority_party()
        if new_leader != None and new_leader == self.initial_leader:
            outcome_string = self.initial_leader.name + " hold"
        elif new_leader != None and self.initial_leader != None:
            outcome_string = new_leader.name + " gain"
        change_string = "no net change"
        for i in range(2):
            if self.points[self.nation.parties[i]] > self.initial_seats[self.nation.parties[i]]:
                change_string = self.nation.parties[i].letter + "+" + str(self.points[self.nation.parties[i]] 
                                                                          - self.initial_seats[self.nation.parties[i]])
        self.nation.house_election_results[self.nation.year] = change_string
        self.nation.interface.show_result(
            "House Election Results",
            [outcome_string + " (" + change_string + ")",
             "New House: " + self.nation.get_house_totals() + " (218 needed for a majority)"])