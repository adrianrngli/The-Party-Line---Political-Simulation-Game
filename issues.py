from statholder import StatHolder
from pollstats import PollStat

class Stance(PollStat):
    """Represents a stance on an issue. Each stance has a value for its associated type."""
    def __init__(self, name: str, type: str, value, isModerate: bool):
        self.value = value
        self.name = name
        self.type= type
        self.moderate = isModerate

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
    
    # def value(self):
    #    return self.stats["value"].value

class Issue():
    """Represents a political issue. Issues have a list of stance objects for politicians and states to take on the issue."""
    def __init__(self, name, type, stances, min_value, max_value):
        self.name = name
        self.type = type
        self.stances = stances
        self.min_value = min_value
        self.max_value = max_value

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

class AllIssues:

    def __init__(self):
        self.issues = []
        with open("input_files/issues.txt") as file:
            file.readline()
            for line in file:
                l = line.split(", ")
                stances = dict()
                for i in range(4, len(l), 3):
                    stances[l[i]] = Stance(l[i], l[1], float(l[i+1]), bool(int(l[i+2])))
                self.issues.append(Issue(l[0], l[1], stances, l[2], l[3]))

    def new_issue(self):
        return self.issues[0]
    
    def generate_issues(self, num):
        return self.issues[:num]