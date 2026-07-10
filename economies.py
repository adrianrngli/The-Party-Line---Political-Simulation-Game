import random

class IndustryGrowthTracker:
    def __init__(self, industry, year):
        self.industry = industry
        self.year = year
        self.baseline = 2.0
        self.increment = 0.75
        self.std = 0.5
        self.cycle = [2, 2, 1, 0, -1, -2, -1, 0, 1]
        self.growth = random.gauss(self.baseline + self.cycle[year % 9] * self.increment, self.std)

    def add_effect(self, quantity):
        self.modifier -= quantity

    def increment_year(self):
        self.year += 1
        self.growth = random.gauss(self.baseline + self.cycle[self.year % 9] * self.increment, self.std)

    def get_growth(self):
        return self.growth
    
class MultipleIndustryTracker:
    def __init__(self, industries, year):
        self.year = year
        self.trackers = {}
        for industry in industries:
            self.trackers[industry] = IndustryGrowthTracker(industry, year)

    def get_growth(self, industry):
        return self.trackers[industry].get_growth()
    
    def increment_year(self):
        self.year += 1
        for industry in self.trackers.keys():
            self.trackers[industry].increment_year()
    
class EconRecord:
    def __init__(self):
        self.record = {1949: 2.0, 1950: 2.0, 1951: 2.0, 1952: 2.0, 1953: 2.0, 1954: 2.0, 1955: 2.0, 1956: 2.0, 1957: 1.0, 1958: 1.0, 1959: 1.0}

    def years(self):
        return self.record.keys()

    def write_entry(self, year, quantity):
        self.record[year] = quantity

    def get_growth(self, year):
        return self.record[year]
    
def economic_forecast(growth):
    if growth < -0.5:
        return "The US economy is forecasted to shrink this year."
    elif growth < 0.5:
        return "US economic growth stagnates this year."
    elif growth < 1.5:
        return "The US economy is forecasted to grow slightly this year."
    elif growth < 2.5:
        return "US economic growth is moderate this year."
    elif growth < 3.5:
        return "The US economy is forecasted to grow significantly this year."
    else:
        return "The US economy undergrows record growth!"