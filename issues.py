import json
from statholder import StatHolder
from pollstats import PollStat

class Stance(PollStat):
    """Represents a stance on an issue. Each stance has a value for its associated type."""
    def __init__(self, name: str, type: str, value, is_moderate: bool, industry_effects = {}):
        self.value = value
        self.name = name
        self.type= type
        self.moderate = is_moderate
        self.industry_effects = industry_effects

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
        self.resolved = False

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

class AllIssues:

    def __init__(self):
        self.issues = []
        with open("input_files/issues.json", 'r') as file:
            parsed_list = json.load(file)
            for issue in parsed_list:
                stances = dict()
                for stance in issue["stances"]:
                    new_stance = Stance(stance["name"], issue["type"], stance["value"], stance["moderate"], stance["industry_effects"])
                    stances[stance["name"]] = new_stance
                self.issues.append(Issue(issue["name"], issue["type"], stances, issue["min_value"], issue["max_value"]))
                    
            """
            file.readline()
            for line in file:
                l = line.split(", ")
                stances = dict()
                for i in range(4, len(l), 3):
                    stances[l[i]] = Stance(l[i], l[1], float(l[i+1]), bool(int(l[i+2])))
                self.issues.append(Issue(l[0], l[1], stances, l[2], l[3]))"""

    def new_issue(self):
        return self.issues[0]
    
    def generate_issues(self, num, current_issues=[]):
        generated_issues = []
        for issue in self.issues:
            if len(generated_issues) >= num:
                break
            if issue not in current_issues:
                issue.resolved = False
                generated_issues.append(issue)
        return generated_issues