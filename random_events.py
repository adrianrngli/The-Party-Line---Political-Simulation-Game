import json
import random

class Gaffe:
    def __init__(self, magnitude, action):
        self.magnitude = magnitude
        self.text = action

    def generate_headline(self, person):
        return str(person) + self.text + " in embarassing gaffe."
    
    def apply(self, person):
        person.stats["popularity"].subtract(self.magnitude)

    def apply_to_president(self, states):
        for state in states:
            state.stats["presidential_approval"].subtract(self.magnitude)

class Scandal:
    def __init__(self, magnitude, type):
        self.magnitude = magnitude
        self.type = type

    def generate_headline(self, person):
        return str(person) + " exposed in major " + self.type + " scandal."

    def apply(self, person):
        person.stats["popularity"].subtract(self.magnitude)

    def apply_to_president(self, states):
        for state in states:
            state.stats["presidential_approval"].subtract(self.magnitude)

class AllGaffes:
    """Loads all gaffes from file and provides access to them, including a random gaffe."""
    def __init__(self):
        self.gaffes = []
        with open("input_files/gaffes.json", 'r') as file:
            parsed_list = json.load(file)
            for gaffe in parsed_list:
                self.gaffes.append(Gaffe(gaffe["magnitude"], gaffe["action"]))

    def random_gaffe(self):
        return random.choice(self.gaffes)

class AllScandals:
    """Loads all scandals from file and provides access to them, including a random scandal."""
    def __init__(self):
        self.scandals = []
        with open("input_files/scandals.json", 'r') as file:
            parsed_list = json.load(file)
            for scandal in parsed_list:
                self.scandals.append(Scandal(scandal["magnitude"], scandal["type"]))

    def random_scandal(self):
        return random.choice(self.scandals)
    
class AllPopularityEvents:
    def __init__(self):
        self.all_gaffes = AllGaffes()
        self.all_scandals = AllScandals()

    def random_gaffe(self):
        return self.all_gaffes.random_gaffe()

    def random_scandal(self):
        return self.all_scandals.random_scandal()