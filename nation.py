from statholder import StatHolder
from pollstats import PollStat, StatVector, StatOperations
from parties import Party
from locations import State, City
from people import Representative, Senator, Governor, Mayor, President, VicePresident
from issues import Issue, AllIssues, Stance
from random_events import AllPopularityEvents, Scandal
from economies import MultipleIndustryTracker, EconRecord, economic_forecast
import random

class Nation:
    """Represents the entire nation, holding all of the states and national information"""
    def __init__(self, parties, player_party, issues = []):
        self.year = 1960
        self.states = []
        self.parties = parties
        self.issues = issues
        self.in_unrest = False
        self.presidential_hopefuls = dict()
        for i in range(2):
            self.presidential_hopefuls[parties[i]] = []
        self.president = None
        self.vice_president = None
        self.house_election_results = dict()
        self.laws_passed = {1957: None, 1958: None, 1959: None, 1960: None}
        self.presidential_scandal = True
        self.industry_tracker = MultipleIndustryTracker(["agriculture", "manufacturing", "professional_services", "public_sector"], self.year)
        self.econ_record = EconRecord()

        # initialize states
        with open("input_files/states_basic_info.txt") as file:
            file.readline()
            for line in file:
                self.states.append(State(*line.replace('\n', '').split(", ")))
        for i in range(2):
            while True:
                rand_index = random.randint(0, 49)
                if self.states[rand_index].rep_number > 1:
                    self.states[rand_index].rep_number -= 1
                    break
        with open("input_files/states_political_stances.txt") as file:
            file.readline()
            for i in range(50):
                self.states[i].set_political_stances(*[float(x) for x in file.readline().split()])
        with open("input_files/states_industries.txt") as file:
            file.readline()
            for i in range(50):
                self.states[i].set_industries(*[float(x) for x in file.readline().split()])
        with open("input_files/states_wealths.txt") as file:
            file.readline()
            for i in range(50):
                self.states[i].set_stat("wealth", float(file.readline()))
        with open("input_files/states_densities.txt") as file:
            file.readline()
            for i in range(50):
                self.states[i].set_stat("density", float(file.readline()))
        for state in self.states:
            state.gaussian_noisify_all_stats()

        #initialize senators
        with open("input_files/initial_senate_seats.txt") as file:
            file.readline()
            for i in range(50):
                line = file.readline().replace("\n", '').split(", ")
                if (line[1] == "D"):
                    party1 = self.parties[0]
                elif (line[1] == "R"):
                    party1 = self.parties[1]
                elif line[1] == "P":
                    party1 = player_party
                
                self.states[i].add_senator(Senator(party1, self.states[i], int(line[2])))
                if (line[3] == "D"):
                    party2 = self.parties[0]
                elif (line[3] == "R"):
                    party2 = self.parties[1]
                elif line[3] == "P":
                    party2 = player_party
                self.states[i].add_senator(Senator(party2, self.states[i], int(line[4])))

        for party in parties:
            if party != player_party:
                self.president = President(party, self.states[0], years_in_office=8)
                self.vice_president = VicePresident(party, self.states[random.randint(0, 49)])
                for state in self.states:
                    state.rep_composition[party] = round(state.rep_number * 0.6)
                    state.rep_composition[player_party] = round(state.rep_number - state.rep_composition[party])
                self.house_election_results[1956] = party.letter + "+1"
                self.house_election_results[1958] = player_party.letter + "+2"

        #initialize issues
        self.all_issues = AllIssues()
        self.popularity_events = AllPopularityEvents()

        self.update_presidential_hopefuls()

    def increment_year(self):
        """Updates all information in the nation when the year advances"""
        self.year += 1
        if self.year % 4 == 1:
            self.presidential_scandal = False
        for state in self.states:
            state.increment_year(self.president)
        self.president.calculate_popularity(self.states)
        self.president.party.stats["popularity"].push_toward(self.president.stats["popularity"])
        self.president.increment_year()
        self.vice_president.increment_year(self.president)
        for state in self.states:
            for sen in state.senators:
                if sen != None:
                    sen.increment_year(self.year, self.president)
                    if sen.retired:
                        state.replace_senator(sen, Senator(sen.party, state, sen.election_year))
            if state.governor != None:
                state.governor.increment_year()
        self.update_presidential_hopefuls()
        self.industry_tracker.increment_year()

        print(self.year)
        print("President:")
        print(self.president)
        print("Presidential approval rating: " + str(round(self.president.stats["popularity"].value, 1)) + "% approve")
        print("Senate composition:")
        print(self.get_senate_totals())
        print("House composition:")
        print(self.get_house_totals())
        print(f"The US economy grew by {round(self.econ_record.get_growth(self.year - 1), 1)}% last year.")
        for i in range(2):
            print(str(self.parties[i]) + " approval rating: " + str(round(self.parties[i].stats["popularity"].value, 1)) + "% approve")
        print("Polling on issues: ")
        self.display_polling_on_issues()

    def get_senate_composition(self):
        """Returns a dictionary mapping each party to the amount of senate seats they have"""
        senate_composition = dict()
        senate_composition[self.parties[0]] = 0
        senate_composition[self.parties[1]] = 0
        for state in self.states:
            for sen in state.senators:
                senate_composition[sen.party] += 1
        return senate_composition

    def get_senate_totals(self):
        """Returns a string showing how many senate seats each party has"""
        senate_totals = self.get_senate_composition()
        total_results = self.parties[0].letter + " " + str(senate_totals[self.parties[0]]) + " " + self.parties[1].letter + " " + str(senate_totals[self.parties[1]])
        return total_results
    
    def get_senate_majority_party(self):
        senate_totals = self.get_senate_composition()
        if senate_totals[self.parties[0]] > senate_totals[self.parties[1]]:
            return self.parties[0]
        elif senate_totals[self.parties[1]] > senate_totals[self.parties[0]]:
            return self.parties[1]
        else:
            return self.president.party
        
    def get_house_composition(self):
        house_composition = dict()
        house_composition[self.parties[0]] = 0
        house_composition[self.parties[1]] = 0
        for state in self.states:
            house_composition[self.parties[0]] += state.rep_composition[self.parties[0]]
            house_composition[self.parties[1]] += state.rep_composition[self.parties[1]]
        return house_composition
    
    def get_house_totals(self):
        house_totals = self.get_house_composition()
        total_results = self.parties[0].letter + " " + str(house_totals[self.parties[0]]) + " " + self.parties[1].letter + " " + str(house_totals[self.parties[1]])
        return total_results

    def get_house_majority_party(self):
        house_totals = self.get_house_composition()
        if house_totals[self.parties[0]] > house_totals[self.parties[1]]:
            return self.parties[0]
        elif house_totals[self.parties[1]] > house_totals[self.parties[0]]:
            return self.parties[1]
        else:
            return None
        
    def get_polling_on_issue(self, issue):
        polling = dict()
        total_vote = 0.0
        for stance in issue.stances.keys():
            polling[stance] = 0.0
        for state in self.states:
            state_polling = state.get_polling_on_issue(issue)
            for opinion in state_polling:
                polling[opinion] += state_polling[opinion] * state.rep_number
            total_vote += 100.0 * state.rep_number
        for opinion in polling.keys():
            polling[opinion] = polling[opinion]/total_vote * 100.0
        return polling

    def display_polling_on_issues(self):
        for issue in self.issues:
            poll = self.get_polling_on_issue(issue)
            print(issue)
            poll_string = ""
            for stance in issue.stances.keys():
                poll_string += str(stance) + " " + str(round(poll[stance], 1)) + "% "
            print(poll_string)

    def record_law(self, law):
        self.laws_passed[self.year] = law

    def mid_year_update(self):
        for state in self.states:
            state.stats["presidential_approval"].subtract(2.5)
            for sen in state.senators:
                sen.run_random_event(self.popularity_events)
            if state.governor != None:
                state.governor.run_random_event(self.popularity_events)
            if state.largest_city.mayor != None:
                state.largest_city.mayor.run_random_event(self.popularity_events)
        president_event = self.president.run_random_event(self.popularity_events, self.states)
        if president_event != None and type(president_event) == Scandal:
            self.presidential_scandal = True
        self.vice_president.run_random_event(self.popularity_events)
        if self.year not in self.laws_passed.keys() or self.laws_passed[self.year] == None:
            self.laws_passed[self.year] = None
            house_majority_party = self.get_house_majority_party()
            if house_majority_party is not None:
                house_majority_party.stats["popularity"].subtract(3)
            else:
                for party in self.parties:
                    party.stats["popularity"].subtract(1.5)
            self.get_senate_majority_party().stats["popularity"].subtract(3)
            for state in self.states:
                state.stats["presidential_approval"].subtract(3)
            self.president.calculate_popularity(self.states)
        else:
            self.laws_passed[self.year].implement()
        for state in self.states:
            state.update_economy(self.industry_tracker, self.year)
        self.calculate_economic_growth()
        self.president.calculate_popularity(self.states)
        print("Presidential approval rating: " + str(round(self.president.stats["popularity"].value, 1)) + "%")
        for i in range(2):
            print(str(self.parties[i]) + " approval rating: " + str(round(self.parties[i].stats["popularity"].value, 1)) + "% approve")
        if self.laws_passed[self.year] != None:
            print(str(self.laws_passed[self.year]) + " approval rating: " + str(round(self.laws_passed[self.year].get_national_popularity(), 1)) + "%")
        if self.econ_record.get_growth(self.year) < 0.0:
            print("The US has entered a recession!")
        print(economic_forecast(self.econ_record.get_growth(self.year)))

    def calculate_economic_growth(self):
        total_national_growth = 0.0
        for state in self.states:
            total_national_growth += state.get_growth(self.year) * state.rep_number
        total_national_growth /= 435
        self.econ_record.write_entry(self.year, total_national_growth)
        
    def update_presidential_hopefuls(self):
        new_presidential_hopefuls = dict()
        for i in range(2):
            new_presidential_hopefuls[self.parties[i]] = []
        senators_by_fame = []
        for state in self.states:
            for sen in state.senators:
                senators_by_fame.append(sen)
        senators_by_fame.sort(key=lambda x: -x.stats["fame"].value)
        for party in self.parties:
            for i in range(3):
                # put 3 non retiring senators into the presidential hopefuls. prioritize more famous senators
                if i < len(self.presidential_hopefuls[party]) and not (self.presidential_hopefuls[party][i].retired or self.presidential_hopefuls[party][i].set_to_retire):
                    new_presidential_hopefuls[party].append(self.presidential_hopefuls[party][i])
                else:
                    for sen in senators_by_fame:
                        if sen.party == party and not (sen in self.presidential_hopefuls[party] or sen in new_presidential_hopefuls[party]) and not (sen.retired or sen.set_to_retire):
                            new_presidential_hopefuls[party].append(sen)
                            break
            for i in range(3, 6):
                # put 3 non retiring governors into the presidential hopefuls
                if i < len(self.presidential_hopefuls[party]) and not self.presidential_hopefuls[party][i].retired:
                    new_presidential_hopefuls[party].append(self.presidential_hopefuls[party][i])
                else:
                    while True:
                        state_index = random.randint(0, 49)
                        if self.states[state_index].governor == None:
                            self.states[state_index].add_governor(Governor(party, self.states[state_index]))
                            new_presidential_hopefuls[party].append(self.states[state_index].governor)
                            break
                        elif self.states[state_index].governor.party == party and not (self.states[state_index].governor in self.presidential_hopefuls[party] or self.states[state_index].governor in new_presidential_hopefuls[party]):
                            new_presidential_hopefuls[party].append(self.states[state_index].governor)
                            break
            if self.president.party == party:
                new_presidential_hopefuls[party].append(self.vice_president)
                if self.president.years_in_office + 4 <= 10:
                    new_presidential_hopefuls[party].append(self.president)
                
        self.presidential_hopefuls = new_presidential_hopefuls