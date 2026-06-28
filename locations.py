from statholder import StatHolder
from economies import EconConstants
from pollstats import StatOperations
from math import sqrt

class State(StatHolder):
    """A State represents one of the 50 States in the US"""

    def __init__(self, name: str, abbreviation: str, region: str, rep_number, largest_city: str):
        super().__init__(["economic_stance", "foreign_stance", "social_stance", "agriculture", "manufacturing", "professional_services", "public_sector", "wealth", "density"])
        self.name = name
        self.abbreviation = abbreviation
        self.region = region
        self.rep_number = int(rep_number)
        self.largest_city = City(largest_city, self)
        self.senators = [None, None]
        self.governor = None
    
    def add_senator(self, senator):
        """Add a senator into a state's vacant senate seat"""
        for i in range(2):
            if self.senators[i] == None:
                self.senators[i] = senator
                return
            
    def remove_senator(self, senator):
        """Removes a senator from a state's senate seats"""
        for i in range(2):
            if self.senators[i] is senator:
                self.senators[i] = None
                return
            
    def replace_senator(self, toReplace, toAdd):
        """Replaces a senator in the state with a new one"""
        toReplace.retire()
        self.remove_senator(toReplace)
        self.add_senator(toAdd)

    def add_governor(self, governor):
        """Puts a new governor into the state"""
        self.governor = governor

    def remove_governor(self):
        """Removes the current governor from the state"""
        self.governor = None

    def set_political_stances(self, economic_stance, foreign_stance, social_stance):
        self.set_stat("economic_stance", economic_stance)
        self.set_stat("foreign_stance", foreign_stance)
        self.set_stat("social_stance", social_stance)

    def set_industries(self, agriculture, manufacturing, professional_services, public_sector):
        self.set_stat("agriculture", agriculture)
        self.set_stat("manufacturing", manufacturing)
        self.set_stat("professional_services", professional_services)
        self.set_stat("public_sector", public_sector)

    def simple_noisify_all_stats(self, moe: float):
        """Changes all stats to be a random value within moe (margin of error) of the original stat.
        The random value is uniformly picked from the range"""
        super().simple_noisify_all_stats(moe)
        StatOperations.normalize([self.stats["agriculture"], self.stats["manufacturing"], self.stats["professional_services"], self.stats["public_sector"]])

    def gaussian_noisify_all_stats(self, std=2.0):
        """Changes all stats to be a random value near the original stat, based on a normal distribution"""
        super().gaussian_noisify_all_stats(std)
        StatOperations.normalize([self.stats["agriculture"], self.stats["manufacturing"], self.stats["professional_services"], self.stats["public_sector"]])

    def wealth_classification(self):
        if self.stats["wealth"].value < 20.0:
            return "poor"
        elif self.stats["wealth"].value < 40.0:
            return "lower middle"
        elif self.stats["wealth"].value < 60.0:
            return "middle"
        elif self.stats["wealth"].value < 80.0:
            return "upper middle"
        else:
            return "rich"

    def density_classification(self):
        if self.stats["density"].value < 20.0:
            return "Sparse"
        elif self.stats["density"].value < 40.0:
            return "rural"
        elif self.stats["density"].value < 60.0:
            return "semi-urban"
        elif self.stats["density"].value < 80.0:
            return "urban"
        else:
            return "metropolitan"

    def get_stance(self, issue):
        """Takes in an issue and returns the stance that is most popular in the state"""
        closest_stance = issue.stances[next(iter(issue.stances))]
        least_distance = self.stats[issue.type].distance_to(closest_stance)
        for stance in issue.stances.keys():
            if self.stats[issue.type].distance_to(issue.stances[stance]) <= least_distance:
                closest_stance = issue.stances[stance]
                least_distance = self.stats[issue.type].distance_to(issue.stances[stance])
        return closest_stance
    
    def get_polling_on_issue(self, issue):
        polling = dict()
        total_vote = 0.0
        for stance in issue.stances.keys():
            polling[stance] = -10 * sqrt(self.stats[issue.type].distance_to(issue.stances[stance])) + 100
            total_vote += polling[stance]
        for opinion in polling.keys():
            polling[opinion] = polling[opinion]/total_vote * 100.0
        return polling

    def __str__(self):
        return self.name

class City:
    """Represents a City. Each State has one city, and cities have mayors who may become prominent politicians"""
    def __init__(self, name: str, state: State):
        self.name = name
        self.state = state
        self.mayor = None

    def add_mayor(self, mayor):
        """Adds a new mayor to the city"""
        self.mayor = mayor

    def remove_mayor(self):
        """Removes the current mayor from the city"""
        self.mayor = None
    
    