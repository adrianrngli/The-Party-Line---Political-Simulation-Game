from statholder import StatHolder
from pollstats import PollStat

class Party(StatHolder):
    """Represents a major political party. The game will always start with the Democrat and Republican parties, but third parties may emerge"""
    def __init__(self, name, letter):
        super().__init__(["economic_stance", "foreign_stance", "social_stance", "popularity"])
        assert letter == name[0]
        self.name = name
        self.letter = letter
        self.platform = None
        self.set_stat("popularity", 53.0)
    
    def set_political_stances(self, economic_stance, foreign_stance, social_stance):
        """Sets the political stances of the party"""
        self.set_stat("economic_stance", economic_stance)
        self.set_stat("foreign_stance", foreign_stance)
        self.set_stat("social_stance", social_stance)

    def set_platform(self, platform):
        """Adopt a platform and re-derive each axis from the stances it contains.
        An axis the platform says nothing about keeps its current value: the
        issues of the day cover the axes unevenly, and a silent platform means
        the party hasn't moved on that axis, not that it has swung to zero."""
        self.platform = platform
        for axis in ["economic_stance", "foreign_stance", "social_stance"]:
            issue_count = 0
            average_position = 0.0
            for issue in platform.keys():
                if platform[issue].type == axis:
                    issue_count += 1
                    average_position += platform[issue].value
            if issue_count != 0:
                self.set_stat(axis, average_position / issue_count)

    def get_stance(self, issue):
        return self.platform[issue]

    def __str__(self):
        return self.name + " Party"