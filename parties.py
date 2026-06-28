from statholder import StatHolder
from pollstats import PollStat

class Party(StatHolder):
    """Represents a major political party. The game will always start with the Democrat and Republican parties, but third parties may emerge"""
    def __init__(self, name, letter):
        super().__init__(["economic_stance", "foreign_stance", "social_stance", "popularity"])
        assert letter == name[0]
        self.name = name
        self.letter = letter
    
    def set_political_stances(self, economic_stance, foreign_stance, social_stance):
        """Sets the political stances of the party"""
        self.set_stat("economic_stance", economic_stance)
        self.set_stat("foreign_stance", foreign_stance)
        self.set_stat("social_stance", social_stance)