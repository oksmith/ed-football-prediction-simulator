from typing import TypedDict

import numpy as np
import pandas as pd
from scipy import stats

from src.config import ADJUSTMENT, OUTCOMES
from src.logger import get_logger


class OutcomeEV(TypedDict):
    mean: float
    upper: float
    lower: float


# e.g. {"1 - 0": {"mean": 3.2, "upper": 3.5, "lower": 2.9}, ...}
MatchEV = dict[str, OutcomeEV]

# e.g. {"Arsenal v Chelsea": {"1 - 0": {...}, ...}, ...}
MatchValues = dict[str, MatchEV]

# e.g. {"Arsenal v Chelsea": "1 - 0", ...}
SuggestedPredictions = dict[str, str]


logger = get_logger()

N_SAMPLES = 50000


def ed_scoring_value(guess, outcome):
    team1, team2 = [int(x) for x in guess.split(" - ")]
    win = team1 > team2
    draw = team1 == team2
    lose = team1 < team2

    # First handle the more extreme outcomes that are outside of the Betfair expected values
    # i.e. scores higher than 4
    if outcome == "Any Other Home Win":
        # TODO: tweak this to adjust probability of opposition scoring? Eg. 4-1, 5-1, 4-3
        if win:
            return 3 + ADJUSTMENT[team2]
        else:
            return ADJUSTMENT[team2]
    elif outcome == "Any Other Away Win":
        if lose:
            return 3 + ADJUSTMENT[team1]
        else:
            return ADJUSTMENT[team1]
    elif outcome == "Any Other Draw":
        if draw:
            return 5
        else:
            return 0
    else:
        o_team1, o_team2 = [int(x) for x in outcome.split(" - ")]
        o_win = o_team1 > o_team2
        o_draw = o_team1 == o_team2
        o_lose = o_team1 < o_team2

    value = 0

    # Assign a "base" value, which is 3 for win and 5 for a draw
    if (win and o_win) or (lose and o_lose):
        value = 3
    elif draw and o_draw:
        value = 5

    # Override if the guess was exactly correct
    if (team1 == o_team1) and (team2 == o_team2):
        if o_win or o_lose:
            value = 7
        else:
            value = 8
    elif (win and o_win) or (lose and o_lose):
        # Right result (non-draw) bonus conditions
        if (team1 == o_team1) or (team2 == o_team2) or (o_team1 - o_team2 == team1 - team2):
            value = 4
    elif draw and o_draw:
        value = 5  # no bonus possible on draws short of exact score
    elif (team1 == o_team1) or (team2 == o_team2):
        value = 1  # one team correct, wrong result

    return value


def get_expected_values(data: pd.DataFrame, n_samples: int = N_SAMPLES):
    match_values = {}
    suggested_predictions = {}

    for event_id, row in data.iterrows():
        event_name = row["EventName"]
        if row[OUTCOMES].isnull().any():
            logger.warning(f"Skipping {event_name} — missing probabilities")
            continue
        logger.info(f"Simulating outcomes for {event_name}...")
        match_values[event_name] = get_expected_value_single_match(data, event_id, n_samples)
        suggested_predictions[event_name] = max(
            match_values[event_name], key=lambda k: match_values[event_name][k]["mean"]
        )

    return suggested_predictions, match_values


def get_expected_value_single_match(data: pd.DataFrame, event_id, n_samples: int = N_SAMPLES):
    """
    Apply Monte Carlo simulation and calculate expected value estimates from each of the potential
    guesses.
    """
    outcome_probabilities = dict(data.loc[event_id, OUTCOMES])
    simulated_outcomes = np.random.choice(
        OUTCOMES, n_samples, p=[outcome_probabilities[outcome] for outcome in OUTCOMES]
    )

    expected_value = {}

    # We don't score the "Any Other XXX" outcomes
    SCOREABLE_OUTCOMES = [o for o in OUTCOMES if not o.startswith("Any Other")]

    for guess in SCOREABLE_OUTCOMES:
        scores = np.array([ed_scoring_value(guess, outcome) for outcome in simulated_outcomes])
        _mean = np.float32(np.mean(scores))
        _sem = np.float32(stats.sem(scores))
        expected_value[guess] = {"mean": _mean, "upper": _mean + 2 * _sem, "lower": _mean - 2 * _sem}

    return expected_value


def calculate_expected_score(suggested_predictions: SuggestedPredictions, match_values: MatchValues):
    """
    Given a set of "suggestions", print out what the EV is from this set.
    """
    return sum([val[suggested_predictions[match]]["mean"] for match, val in match_values.items()])
