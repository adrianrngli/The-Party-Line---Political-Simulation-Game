from statholder import StatHolder
from locations import State, City
from parties import Party
import random
import string
from faker import Faker
from issues import Issue, Stance
from math import sqrt
fake = Faker('en_US')

class Politician(StatHolder):
    """Represents a political figure. May or may not currently hold office."""

    def __init__(self, party: Party, state: State):
        super().__init__(["economic_stance", "foreign_stance", "social_stance", "fame", "popularity", "charisma", "corruptness"])
        self.first_name = fake.first_name()
        self.middle_initial = ''
        self.last_name = fake.last_name()
        middle_initial_seed = random.randint(1, 5)
        if (middle_initial_seed == 1):
            self.middle_initial = random.choice(string.ascii_letters).upper()+". "
        self.party = party
        self.state = state
        self.age = random.randint(25, 85)
        self.years_of_experience = random.randint(0, self.age-20)
        self.set_stat("fame", random.uniform(0, 80))
        self.set_stat("popularity", random.uniform(20, 65))
        self.set_stat("charisma", random.uniform(0, 100))
        self.set_stat("corruptness", random.uniform(0, 100))
        self.auto_set_stances()
        self.retired = False

    def increment_year(self):
        """Updates the age and years of experience to both increase by one after a year progresses"""
        self.age += 1
        self.years_of_experience += 1
        if self.age > 65:
            self.stats["charisma"].subtract(1)

    def auto_set_stances(self):
        """Automatically sets the stance on economic, foreign, and social policy to be a balance of the party and state's positions"""
        self.set_stat("economic_stance", (self.state.stats["economic_stance"].value+self.party.stats["economic_stance"].value)/2.0)
        self.set_stat("foreign_stance", (self.state.stats["foreign_stance"].value+self.party.stats["foreign_stance"].value)/2.0)
        self.set_stat("social_stance", (self.state.stats["social_stance"].value+self.party.stats["social_stance"].value)/2.0)
        self.stats["economic_stance"].simple_noisify(5.0)
        self.stats["foreign_stance"].simple_noisify(5.0)
        self.stats["social_stance"].simple_noisify(5.0)

    def full_name(self):
        full_name = ""
        full_name += self.first_name
        full_name += ' '
        full_name += self.middle_initial
        full_name += self.last_name
        return full_name
    
    def __str__(self):
        return self.full_name()+' ('+self.party.letter+'-'+self.state.abbreviation+')'

    def retire(self):
        self.retired = True

    def get_stance(self, issue):
        """Takes in an issue and returns the stance that the politician takes on the issue"""
        closest_stance = issue.stances[next(iter(issue.stances))]
        least_distance = self.stats[issue.type].distance_to(closest_stance)
        for stance in issue.stances.keys():
            if self.stats[issue.type].distance_to(issue.stances[stance]) <= least_distance:
                closest_stance = issue.stances[stance]
                least_distance = self.stats[issue.type].distance_to(issue.stances[stance])
        return closest_stance
    
    def fame_classification(self):
        if self.stats["fame"].value < 20.0:
            return "unknown"
        elif self.stats["fame"].value < 40.0:
            return "local name"
        elif self.stats["fame"].value < 60.0:
            return "statewide name"
        elif self.stats["fame"].value < 80.0:
            return "well known"
        else:
            return "household name"
    
    def popularity_classification(self):
        if self.stats["popularity"].value < 20.0:
            return "disgraced"
        elif self.stats["popularity"].value < 40.0:
            return "widely disliked"
        elif self.stats["popularity"].value < 60.0:
            return "average"
        elif self.stats["popularity"].value < 80.0:
            return "well-liked"
        else:
            return "beloved"
        
    def charisma_classification(self):
        if self.stats["charisma"].value < 20.0:
            return "sleep inducing"
        elif self.stats["charisma"].value < 40.0:
            return "awkward"
        elif self.stats["charisma"].value < 60.0:
            return "average"
        elif self.stats["charisma"].value < 80.0:
            return "eloquent"
        else:
            return "inspirational"
        
    def corruptness_classification(self):
        if self.stats["corruptness"].value < 20.0:
            return "squeaky clean"
        elif self.stats["corruptness"].value < 40.0:
            return "mostly clean"
        elif self.stats["corruptness"].value < 60.0:
            return "shady"
        elif self.stats["corruptness"].value < 80.0:
            return "criminal"
        else:
            return "pants on fire"
        
    def run_random_event(self, events):
        """Roll for a scandal or gaffe, apply its effect, and return a news
        headline string (or None). The caller gathers these into the year's
        news digest rather than surfacing each one on its own."""
        random_seed = random.random() * 500
        if random_seed < sqrt(self.stats["corruptness"].value/max(self.years_of_experience, 1)):
            scandal = events.random_scandal()
            scandal.apply(self)
            return scandal.generate_headline(self)
        random_seed = random.random() * 500
        if random_seed < sqrt(100 - self.stats["charisma"].value):
            gaffe = events.random_gaffe()
            gaffe.apply(self)
            return gaffe.generate_headline(self)
        return None
    
class Representative(Politician):
    """Represents a House Representative. Representatives vote on laws."""
    def retire(self):
        return
    
    def __str__(self):
        return "Rep "+super().__str__()
    
class Senator(Politician):
    """Represents a Senator, elected every six years, and votes on laws"""
    def __init__(self, party: Party, state: State, election_year: int):
        super().__init__(party, state)
        self.election_year = election_year
        self.set_to_retire = False
        if (self.age < 30):
            self.age = random.randint(30, 85)

    def consider_retirement(self, current_year: int):
        # when senators reach age 65 they get a 25% chance to not run for reelection. This chance increases by 4% for each year age increases
        # Returns a short announcement string when the senator decides to retire,
        # else None, so the caller can gather them into a start-of-year popup.
        if self.age >= 65 and current_year % 6 == self.election_year:
            retirement_chance = min(25+4*(self.age-65), 90)
            rand_num = random.randint(1, 100)
            if (rand_num <= retirement_chance):
                self.set_to_retire = True
                return str(self) + " (age " + str(self.age) + ") will not seek reelection when this term ends."
        return None

    def increment_year(self, year, president):
        """Updates age and stances for the senator. If they are 65+ and up for
        election they may decide not to seek reelection; returns that
        announcement string (or None) so the nation can collect them."""
        super().increment_year()
        for axis in ["economic_stance", "foreign_stance", "social_stance"]:
            if president.stats["popularity"].value >= 50.0:
                self.stats[axis].push_toward(president.stats[axis], sqrt(president.stats["popularity"].value - 50.0)/50)
            else:
                self.stats[axis].push_away_from(president.stats[axis], sqrt(50.0 - president.stats["popularity"].value)/50)
        if self.set_to_retire:
            self.retire()
            return None
        return self.consider_retirement(year)

    def retire(self):
        super().retire()
        self.state.remove_senator(self)

    def get_bill_vote(self, issue, stance, party_vote, president):
        if self.get_stance(issue) == stance:
            return "Yea"
        elif party_vote == "Yea" or stance.moderate:
            state_approval = self.state.law_popularity(issue, stance)
            if self.state.stats["presidential_approval"].value > 50.0 and president.get_stance(issue) == stance:
                if president.party == self.party:
                    state_approval += (self.state.stats["presidential_approval"].value - 50.0) / 2
                else:
                    state_approval += (self.state.stats["presidential_approval"].value - 50.0) / 4
            if state_approval > 50.0:
                return "Yea"
            else:
                return "Nay"
        else:
            return "Nay"
    
    def __str__(self):
        return "Senator "+super().__str__()
    
class Governor(Politician):
    """Represents a governor of a state; governors of states are major players that last for 4 or 8 years before retirement"""
    def __init__(self, party: Party, state: State):
        super().__init__(party, state)
        self.initial_exp = self.years_of_experience

    def increment_year(self):
        """Updates age and years of experience for the governor. Additionally, if the governor has been in office for four years they may retire. After 8 they will."""
        super().increment_year()
        if self.years_of_experience - self.initial_exp >= 8:
            self.retire()
        elif self.years_of_experience - self.initial_exp == 4:
            coin_flip = random.randint(0, 1)
            if coin_flip == 1:
                self.retire()

    def retire(self):
        super().retire()
        self.state.remove_governor()

    def __str__(self):
        return "Governor "+super().__str__()

class Mayor(Politician):
    """Represents a Mayor of a city. Stays around for 4 years before retirement"""
    def __init__(self, party: Party, state: State):
        super().__init__(party, state)
        self.city = self.state.largest_city
        self.city.add_mayor(self)
        self.initial_exp = self.years_of_experience

    def increment_year(self):
        """Updates age and years of experience for the mayor. Additionally, if the governor has been in office for four years they will retire."""
        super().increment_year()
        if self.years_of_experience - self.initial_exp >= 4:
            self.retire()

    def retire(self):
        super().retire()
        self.city.remove_mayor()

    def __str__(self):
        return "Mayor "+super().__str__()
    
class President(Politician):
    def __init__(self, party, state, years_in_office = 0):
        super().__init__(party, state)
        self.years_in_office = years_in_office
        self.age = max(self.age, 35)

    def increment_year(self):
        super().increment_year()
        self.years_in_office += 1

    def __str__(self):
        return "President " + super().__str__()[:-4] + ")" 
    
    def calculate_popularity(self, states):
        average_popularity = 0.0
        for state in states:
            average_popularity += state.stats["presidential_approval"].value * state.rep_number
        average_popularity /= 435
        self.set_stat("popularity", average_popularity)
        return self.stats["popularity"].value
    
    def run_random_event(self, events, states, interface):
        random_seed = random.random() * 100
        if random_seed < self.stats["corruptness"].value/max(self.years_of_experience, 1):
            scandal = events.random_scandal()
            scandal.apply_to_president(states)
            interface.event("Breaking news",
                            [scandal.generate_headline(self),
                             "Presidential approval falls across the country."])
            return scandal
        random_seed = random.random() * 100
        if random_seed < 100 - self.stats["charisma"].value:
            gaffe = events.random_gaffe()
            gaffe.apply_to_president(states)
            interface.event("Breaking news",
                            [gaffe.generate_headline(self),
                             "Presidential approval takes a hit nationwide."])
            return gaffe
    
class VicePresident(Politician):
    def __init__(self, party, state):
        super().__init__(party, state)

    def increment_year(self, president):
        super().increment_year()
        self.stats["popularity"].push_toward(president.stats["popularity"])

    def __str__(self):
        return "Vice President " + super().__str__()[:-4] + ")" 
    
def convert_to_senator(person, year):
    new_senator = Senator(person.party, person.state, year % 6)
    new_senator.first_name = person.first_name
    new_senator.middle_initial = person.middle_initial
    new_senator.last_name = person.last_name
    new_senator.age = person.age
    new_senator.years_of_experience = person.years_of_experience
    new_senator.stats = person.stats
    return new_senator

def convert_to_president(person, states, issues=[]):
    new_president = President(person.party, person.state)
    new_president.first_name = person.first_name
    new_president.middle_initial = person.middle_initial
    new_president.last_name = person.last_name
    new_president.age = person.age
    new_president.years_of_experience = person.years_of_experience
    new_president.stats = person.stats
    for state in states:
        state.set_initial_presidential_approval(person, issues)
    new_president.calculate_popularity(states)
    return new_president

def convert_to_vice_president(person):
    new_vp = VicePresident(person.party, person.state)
    new_vp.first_name = person.first_name
    new_vp.middle_initial = person.middle_initial
    new_vp.last_name = person.last_name
    new_vp.age = person.age
    new_vp.years_of_experience = person.years_of_experience
    new_vp.stats = person.stats
    new_vp.stats["popularity"].add(15)
    return new_vp
