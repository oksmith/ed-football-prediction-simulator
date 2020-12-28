"""
Constant values used in the prediction simulator.
"""

ADJUSTMENT = {
    0: 0.432,
    1: 0.243,
    2: 0.216,
    3: 0.108
}
'''
Given the result was 4-x, what's the probability that x is 0, 1, 2, 3?
P(losing_goals_correct) in an 'Any Other Home Win' or 'Any Other Away Win' situation.

Quick tally for an early approximation (using all fixtures since 2019):
0 - 16
1 - 9
2 - 8
3 - 4
'''

OUTCOMES = [
    '0 - 0', '0 - 1', '0 - 2', '0 - 3', '1 - 0', '1 - 1', '1 - 2', '1 - 3', 
    '2 - 0', '2 - 1', '2 - 2', '2 - 3', '3 - 0', '3 - 1', '3 - 2', '3 - 3',
    'Any Other Home Win', 'Any Other Away Win', 'Any Other Draw'
]


SCORECASTS_LOC = 'scorecasts'

OUTPUT_LOC = 'outputs'


TEAMS_DICT = {
    'ARS': 'Arsenal',
    'VIL': 'Aston Villa',
    'BRI': 'Brighton',
    'BUR': 'Burnley',
    'CHE': 'Chelsea',
    'CRY': 'Crystal Palace',
    'EVE': 'Everton',
    'FUL': 'Fulham', 
    'LDS': 'Leeds',
    'LEIC': 'Leicester',
    'LIV': 'Liverpool',
    'MANC': 'Man City',
    'MANU': 'Man Utd',
    'NEW': 'Newcastle',
    'SHE': 'Sheff Utd',
    'SHFU': 'Sheff Utd',
    'SOTN': 'Southampton',
    'TOTT': 'Tottenham',
    'WBA': 'West Brom',
    'WHU': 'West Ham',
    'WLV': 'Wolves',
    'BRENT': 'Brentford',
    'STK': 'Stoke',
    'CELT': 'Celtic',
    'ROSS': 'Ross Co',
    'HIBS': 'Hibernian',
    'ST.MRN': 'St Mirren',
    'ST.J': 'St Johnstone',
    'RANG': 'Rangers',
    'MTHRWL': 'Motherwell',
    'ABRDN': 'Aberdeen',
    
}