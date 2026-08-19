from economies import MultipleIndustryTracker

class Bill:
    def __init__(self, issue, stance, proposer, year, nation):
        self.issue = issue
        self.stance = stance
        self.proposer = proposer
        self.party_votes = dict()
        self.party_votes[proposer] = "Yea"
        self.year = year
        self.house_tally = dict()
        self.senate_votes = dict()
        self.nation = nation
        self.senate_composition = self.nation.get_senate_composition()

    def get_national_popularity(self):
        total_approval = 0.0
        for state in self.nation.states:
            total_approval += state.law_popularity(self.issue, self.stance) * state.rep_number
        return total_approval/435
    
    def set_party_vote(self, party, vote):
        self.party_votes[party] = vote
    
    def get_house_party_votes(self, party):
        if party in self.house_tally.keys():
            return self.house_tally[party]
        self.house_tally[party] = 0
        for state in self.nation.states:
            party_reps = state.rep_composition[party]
            if self.party_votes[party] == "Yea" and self.stance == state.get_stance(self.issue):
                self.house_tally[party] += party_reps
            elif self.party_votes[party] == "Yea":
                state_distance = state.stats[self.issue.type].distance_to(self.stance)
                if state.stats["presidential_approval"].value > 50.0 and self.nation.president.get_stance(self.issue) == self.stance:
                    if self.nation.president.party == party:
                        state_distance -= (state.stats["presidential_approval"].value - 50.0) / 4
                    else:
                        state_distance -= (state.stats["presidential_approval"].value - 50.0) / 8
                state_distance = min(100, max(0, state_distance))
                self.house_tally[party] += round(party_reps * (100 - state_distance) / 100.0)
            elif self.stance.moderate:
                state_approval = state.law_popularity(self.issue, self.stance)
                if state.stats["presidential_approval"].value > 50.0 and self.nation.president.get_stance(self.issue) == self.stance:
                    if self.nation.president.party == party:
                        state_approval += (state.stats["presidential_approval"].value - 50.0) / 2
                    else:
                        state_approval += (state.stats["presidential_approval"].value - 50.0) / 4
                self.house_tally[party] += round(party_reps * state_approval / 100.0)
        return self.house_tally[party]
    
    def get_senate_party_votes(self, party):
        yeas = 0
        for state in self.nation.states:
            for sen in state.senators:
                if sen.party == party:
                    if sen in self.senate_votes.keys():
                        if self.senate_votes[sen] == "Yea":
                            yeas += 1
                    elif sen.get_bill_vote(self.issue, self.stance, self.party_votes[sen.party], self.nation.president) == "Yea":
                        self.senate_votes[sen] = "Yea"
                        yeas += 1
                    else:
                        self.senate_votes[sen] = "Nay"
        return yeas
    
    def run_house_vote(self):
        house_composition = self.nation.get_house_composition()
        summary = []
        for i in range(2):
            party = self.nation.parties[i]
            yea = self.get_house_party_votes(party)
            summary.append(party.letter + " Yea: " + str(yea))
            summary.append(party.letter + " Nay: " + str(house_composition[party] - self.house_tally[party]))
        yeas = self.house_tally[self.nation.parties[0]] + self.house_tally[self.nation.parties[1]]
        summary.append(str(yeas) + " Yeas")
        summary.append(str(435 - yeas) + " Nays")
        passed = yeas > 217
        summary.append("Result: " + ("Passed" if passed else "Failed"))
        self.nation.interface.show_vote("House vote on " + str(self), summary)
        return passed
    
    def run_senate_vote(self):
        party_tallies = dict()
        for i in range(2):
            party_tallies[self.nation.parties[i]] = self.get_senate_party_votes(self.nation.parties[i])
        if party_tallies[self.nation.parties[0]] + party_tallies[self.nation.parties[1]] == 50:
            self.senate_composition[self.nation.president.party] += 1
            if self.party_votes[self.nation.president.party] == "Yea":
                party_tallies[self.nation.president.party] += 1
        yeas = party_tallies[self.nation.parties[0]] + party_tallies[self.nation.parties[1]]
        nays = self.senate_composition[self.nation.parties[0]] - party_tallies[self.nation.parties[0]] + self.senate_composition[self.nation.parties[1]] - party_tallies[self.nation.parties[1]]
        if not self.stance.moderate and yeas > 50 and yeas < 60:
            return False
        details = []
        for state in self.nation.states:
            for sen in state.senators:
                details.append(str(sen) + " " + self.senate_votes[sen])
        if self.senate_composition[self.nation.parties[0]] + self.senate_composition[self.nation.parties[1]] > 100:
            details.append(str(self.nation.vice_president) + " " + self.party_votes[self.nation.president.party])
        summary = []
        for i in range(2):
            party = self.nation.parties[i]
            summary.append(party.letter + " Yea: " + str(party_tallies[party]))
            summary.append(party.letter + " Nay: " + str(self.senate_composition[party] - party_tallies[party]))
        summary.append(str(yeas) + " yeas " + str(nays) + " nays")
        passed = yeas > 50
        summary.append("Result: " + ("Passed" if passed else "Failed"))
        self.nation.interface.show_vote("Senate vote on " + str(self), summary, details)
        return passed

    
    def get_senate_vote(self):
        party_tallies = dict()
        for i in range(2):
            party_tallies[self.nation.parties[i]] = self.get_senate_party_votes(self.nation.parties[i])
        if party_tallies[self.nation.parties[0]] + party_tallies[self.nation.parties[1]] == 50:
            self.senate_composition[self.nation.president.party] += 1
            if self.party_votes[self.nation.president.party] == "Yea":
                party_tallies[self.nation.president.party] += 1
        return party_tallies[self.nation.parties[0]] + party_tallies[self.nation.parties[1]]
    
    def get_presidential_approval(self):
        if self.nation.president.get_stance(self.issue) == self.stance:
            return "Pass"
        else:
            return "Veto"
    
    def try_to_pass(self):
        if self.run_house_vote():
            if self.run_senate_vote():
                return self.run_presidential_decision()
            else:
                if self.get_senate_vote() > 50:
                    self.nation.interface.event(
                        "Filibustered in the Senate",
                        [str(self) + " died in the Senate."])
                    return "Stopped by filibuster"
                else:
                    return "Failed Senate vote"
        else:
            return "Failed House vote"

    def run_presidential_decision(self):
        """Present the president's sign/veto choice on a bill that cleared both
        chambers, as its own screen, and return the resulting outcome string."""
        president = self.nation.president
        summary = []
        if self.get_presidential_approval() == "Pass":
            summary.append(str(president) + " signed " + str(self) + " into law!")
            outcome = "Passed"
        else:
            house_yeas = self.house_tally[self.nation.parties[0]] + self.house_tally[self.nation.parties[1]]
            senate_yeas = self.get_senate_vote()
            if house_yeas > 289 and senate_yeas > 66:
                summary.append(str(president) + " reluctantly signed " + str(self) + " into law!")
                outcome = "Passed"
            else:
                summary.append(str(president) + " vetoed " + str(self) + ".")
                outcome = "Vetoed"
        self.nation.interface.show_decision("Presidential decision on " + str(self), summary)
        return outcome
        
    def implement(self):
        for i in range(2):
            if self.party_votes[self.nation.parties[i]] == "Yea":
                self.nation.parties[i].stats["popularity"].add((self.get_national_popularity() - 50)/5)
            else:
                self.nation.parties[i].stats["popularity"].add((50 - self.get_national_popularity())/5)
        if self.issue.type == "economic_stance":
            self.nation.industry_tracker.apply_stance(self.stance)
        for state in self.nation.states:
            state.stats["presidential_approval"].add((state.law_popularity(self.issue, self.stance) - 50)/4)
            if self.issue.type == "economic_stance":
                if self.stance.value < 50 and state.stats["wealth"].value < 50:
                    state.stats["wealth"].add((50-self.stance.value)/20)
                elif self.stance.value > 50 and state.stats["wealth"].value > 50:
                    state.stats["wealth"].add((self.stance.value-50)/20)
            elif self.issue.type == "social_stance":
                state.stats["density"].add((state.stats["social_stance"].value-self.stance.value)/20)
        self.issue.resolved = True

    def __str__(self):
        return "The " + str(self.stance) + " Act of " + str(self.year)