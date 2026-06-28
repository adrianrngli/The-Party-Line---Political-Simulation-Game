def display_state(state, issues=[]):
    """Display all the information for a state to the console"""
    print(state.name)
    print(str(state.rep_number) + " representatives")
    print("Wealth: " + state.wealth_classification())
    print("Density: " + state.density_classification())
    print("Positions:")
    for issue in issues:
        print(str(issue) + ": " + str(state.get_stance(issue)))
    print()

def display_person(person, issues=[]):
    """Display all the information for a politician to the console"""
    print(person)
    print("Age: " + str(person.age))
    print("Years of experience: " + str(person.years_of_experience))
    print("Fame: " + person.fame_classification())
    print("Popularity: " + person.popularity_classification())
    print("Charisma: " + person.charisma_classification())
    print("Corruptness: " + person.corruptness_classification())
    print("Positions:")
    for issue in issues:
        print(str(issue) + ": " + str(person.get_stance(issue)))
    print()