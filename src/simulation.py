import numpy as np

from scipy import stats

from src.config import OUTCOMES, ADJUSTMENT


N_SAMPLES = 50000


def ed_scoring_value(guess, outcome):
    team1, team2 = [int(x) for x in guess.split(' - ')]
    win = team1 > team2
    draw = team1 == team2
    lose = team1 < team2
    
    if outcome == 'Any Other Home Win':
        # TODO: tweak this to adjust probability of opposition scoring? Eg. 4-1, 5-1, 4-3
        if win:
            return 3 + ADJUSTMENT[team2]
        else:
            return ADJUSTMENT[team2]
    elif outcome == 'Any Other Away Win':
        if lose:
            return 3 + ADJUSTMENT[team1]
        else:
            return ADJUSTMENT[team1]
    elif outcome == 'Any Other Draw':
        if draw:
            return 5
        else:
            return 0
    else:
        o_team1, o_team2 = [int(x) for x in outcome.split(' - ')]
        o_win = o_team1 > o_team2
        o_draw = o_team1 == o_team2
        o_lose = o_team1 < o_team2
    
    value = 0
    if (win and o_win) or (lose and o_lose):
        value = 3
    elif draw and o_draw:
        value = 5
        
    if (team1 == o_team1) and (team2 == o_team2):
        if o_win or o_lose:
            value = 7
        else:
            value = 8
    elif (team1 == o_team1) or (team2 == o_team2):
        value += 1
        
    return value


def get_expected_values(bf, n_samples=N_SAMPLES):
    match_values = {}
    suggested_predictions = {}
    for event_id in bf.data.index:
        event_name = bf.data.loc[event_id, 'EventName']
        print('Simulating outcomes for {}...'.format(event_name))
        if bf.data.loc[event_id, OUTCOMES].isnull().any():
            pass
        match_values[event_name] = get_expected_value_single_match(bf, event_id, n_samples)
        suggested_predictions[event_name] = [
            key for key in match_values[event_name].keys()
            if match_values[event_name][key]['mean'] == max([val['mean'] for val in match_values[event_name].values()])
        ][0]
        
    return suggested_predictions, match_values
    
    
def get_expected_value_single_match(bf, event_id, n_samples=N_SAMPLES):
    outcome_probabilities = dict(bf.data.loc[event_id, OUTCOMES])
    simulated_outcomes = np.random.choice(
        OUTCOMES, 
        n_samples, 
        p=[outcome_probabilities[outcome] for outcome in OUTCOMES]
    )
    
    expected_value = {}

    for guess in OUTCOMES:
        if guess not in ['Any Other Home Win', 'Any Other Away Win', 'Any Other Draw']:
            mean_ev = np.mean(
                [ed_scoring_value(guess, outcome) for outcome in simulated_outcomes]
            )
            sem = stats.sem([ed_scoring_value(guess, outcome) for outcome in simulated_outcomes])

            expected_value[guess] = {
                'mean': mean_ev,
                'upper': mean_ev + 2*sem,
                'lower': mean_ev - 2*sem
            }
    
    return expected_value


def calculate_expected_score(suggested_predictions, match_values):
    return sum([val[suggested_predictions[match]]['mean'] for match, val in match_values.items()])
