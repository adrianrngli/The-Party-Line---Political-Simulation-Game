# The Party Line

A political simulation game where you play the chair of one of the two major
American parties, starting in 1960. You don't run for office yourself, but you
control the people who do. Choose your party's platform, nominate Senate and presidential
candidates state by state, and decide what your party does with a majority in
Congress. The country reacts to your decisions: opinions shift, the economy moves, scandals break,
and the other party adapts to the changing political climate.

Written in Python with a pygame interface built around an interactive US map.

## Requirements

- Python 3.9 or newer
- [pygame](https://www.pygame.org/) (graphical interface)
- [Faker](https://faker.readthedocs.io/) (generates politician names)

```sh
pip install -r requirements.txt
```

## Running the game

Run from the repository root — the game loads its data from `input_files/`
using relative paths.

```sh
python game_gui.py
```

This opens the main menu; **New Game** starts a fresh run, and the first thing
you'll be asked is which party you want to lead. The other party is played by
the computer.

## How a year works

Play runs one year at a time, for 60 years by default (`Game.run(years=60)`).
Not every phase happens every year:

| Phase | When | What you do |
| --- | --- | --- |
| Platform | Every 4 years | Pick your party's stance on each of the current issues. Your stances determine the party's economic, foreign, and social positions. |
| Senate nominations | Election years | Click a state holding a race and nominate your candidate from the primary field. |
| Presidential nominations | Every 4 years | Nominate a president and a running mate to run in the general election.
| Legislation | Every year | The party holding the House majority proposes a bill on an issue; the other party whips its members for or against. |
| Elections | Election years | Presidential, then Senate, then House. The map colors by result and you can click any state for result details. |
| Year end | Every year | Economic growth, scandals and gaffes, and the annual State of the Nation report. |

**Passing Bills**

A bill has to clear the House, survive the Senate (some bills will needs 60
votes to break a filibuster), and then be signed by the president, who will
veto a bill they disagree with unless both chambers passed it by enough of a
margin to be worth reconsidering. A law passed affects the nation, changing approval rates for politicians and parties, and affecting the economy.

**Nominating Candidates**

Candidates are not interchangeable. Each has different values for age, experience, fame, charisma,
corruptness, and their own stances. States take all of these into account, weighing a candidates stances against their own, but also taking into account the current national environment. You'll rarely have both a perfect environment and perfect candidate who aligns with both your views and the state's views, so you may need to make tough decisions on who to nominate.

## The interface

The pygame version is a dashboard, not a scrolling log:

- **The map** is the center of the screen. Click any state to see its profile,
  its senators, and its results while an election is being reported.
- **The side buttons** open standing panels: **Nation** (chamber composition,
  the economy), **Polling** (national polling on each issue), **President**,
  and **Parties** (both platforms side by side).
- **The bottom strip** carries the current prompt, candidate and bill choices,
  and the latest headline result. **Continue** (or Enter) advances.
- Blocks of text that outgrow their box scroll with the mouse wheel.

## Project layout

| File | Contents |
| --- | --- |
| `game.py` | The turn structure — owns game state and drives each phase. |
| `game_gui.py` | Launcher for the game|
| `interfaces.py` | `GameInterface`, the boundary between game logic and the player.|
| `pygame_interface.py` | The pygame dashboard: map, panels, pickers, modals. |
| `us_map.py` | Draws and hit-tests the US map from GeoJSON. |
| `player.py` | Human and computer players — who decides what, and how the AI decides. |
| `nation.py` | The country: states, Congress, the president, the yearly update. |
| `elections.py` | Presidential, Senate, and House elections. |
| `laws.py` | Bills, whip counts, chamber votes, and vetoes. |
| `people.py`, `locations.py`, `parties.py`, `issues.py` | Politicians, states and cities, parties, and issues. |
| `economies.py`, `pollstats.py`, `statholder.py` | Industry and growth modeling, and the stat types everything else is built on. |
| `random_events.py` | Scandals and gaffes. |
| `input_files/` | Game data: state figures, issues, scandals, gaffes, and map GeoJSON. |

## Status and roadmap

Playable start to finish, and still in development. Known gaps:

- No save or load — a run lasts as long as the window stays open.
- The main menu has only **New Game**; more options are meant to go there.
- Only the two major parties exist. Third parties are planned but not implemented.
- The end screen only announces your retirement; there's no summary of the
  career you just played.
- Major rebalancing of passing laws and elections is needed.
- Presidents don't do much besides sign and veto laws. More interactions with foreign powers will be added.
- In presidential elections, before the election runs you have no way of knowing the margins of each state.
