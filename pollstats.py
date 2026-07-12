from math import sqrt
import random

class PollStat:
    """A PollStat represents a stat for a statholder. Each stat has a minimum of zero and maximum of one hundred"""
    def __init__(self, init_value=50.0):
        self.value = init_value

    def bound(self):
        """Makes sure the value of the stat is between 0 and 100"""
        self.value = min(100.0, max(self.value, 0.0))

    def distance_to(self, other):
        """Returns the distance in value between this pollstat and another pollstat"""
        return abs(self.value - other.value)

    def simple_noisify(self, moe: float):
        """Changes the value to a random value within moe (margin of error) of the original value.
        Value is picked uniformly at random from the interval"""
        self.value = random.uniform(self.value-moe, self.value+moe)
        self.bound()

    def gaussian_noisify(self, std = 2.0):
        """Changes the value to be a random value near the original value, based on a normal distribution"""
        self.value = random.gauss(self.value, std)
        self.bound()

    def add(self, quantity):
        self.value += random.gauss(quantity, quantity * 0.1)
        self.bound()

    def subtract(self, quantity):
        self.value -= random.gauss(quantity, quantity * 0.1)
        self.bound()

    def push_toward(self, other, factor = 0.2):
        self.add((other.value - self.value) * factor)

    def push_away_from(self, other, factor = 0.2):
        self.add((other.value - self.value) * factor)

    def add_percent(self, x):
        self.add(self.value * x/100.0)
    
class StatVector:
    """StatVectors represent a change in a stat. They can be applied to PollStats"""
    def __init__(self, stat_name: str, magnitude: float):
        self.name = stat_name
        self.magnitude = magnitude

    def simple_noisify(self, moe: float):
        """Changes the value to a random value within moe (margin of error) of the orginal value.
        Value is picked uniformally at random from the interval"""
        self.value = random.uniform(self.value-moe, self.value+moe)
        return self
    
    def gaussian_noisify(self, std=2.0):
        self.value = random.gauss(self.magnitude, std)
    
    def __add__(self, other):
        """addition of two StatVectors adds the values, but only if the name of both are the same"""
        if self.name == other.name:
            return StatVector(self.name, self.magnitude+other.magnitude)
        else:
            return self

class StatOperations:
    @staticmethod
    def normalize(stats, value=100.0):
        """takes in stats, a list of PollStats, and adjusts their values to add up to value, while keeping the ratio between them"""
        total = 0.0
        for stat in stats:
            total += stat.value
        for stat in stats:
            stat.value = (stat.value/total)*value

    @staticmethod
    def distance(holder1, holder2, stats):
        """Calculates the straight line distance from holder1 to holder2 in terms of the stats in the list stats.
        stats is a list of strings dictating which stats of the holders will be measured"""
        total = 0.0
        for stat in stats:
            total += (holder1.stats[stat].value-holder2.stats[stat].value)*(holder1.stats[stat].value-holder2.stats[stat].value)
        return sqrt(total)