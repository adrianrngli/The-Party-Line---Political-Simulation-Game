from pollstats import PollStat
import random
from math import sqrt
    

class StatHolder:
    """A StatHolder represents any entity that has stats ranging from 1-100 that can be changed. These include both states and politicians"""

    def __init__(self, stat_names: list):
        self.stats = dict()
        for name in stat_names:
            self.stats[name] = (PollStat())

    def set_stat(self, stat_name: str, value: float):
        if stat_name in self.stats.keys():
            self.stats[stat_name].value = value

    def simple_noisify_all_stats(self, moe: float):
        """Changes all stats to be a random value within moe (margin of error) of the original stat.
        The random value is uniformly picked from the range"""
        for name in self.stats:
            self.stats[name].simple_noisify(moe)

    def gaussian_noisify_all_stats(self, std = 2.0):
        """Changes all stats to be a random value near the original stat, based on a normal distribution"""
        for name in self.stats:
            self.stats[name].gaussian_noisify(std)

    def difference_in_stat(self, other, stat):
        return self.stats[stat].value - other.stats[stat].value

    def distance_between_stats(self, holder2, stats):
        """Calculates the straight line distance from holder1 to holder2 in terms of the stats in the list stats.
        stats is a list of strings dictating which stats of the holders will be measured"""
        total = 0.0
        for stat in stats:
            total += (self.stats[stat].value-holder2.stats[stat].value)*(self.stats[stat].value-holder2.stats[stat].value)
        return sqrt(total)