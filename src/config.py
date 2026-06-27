"""
Constant values used in the prediction simulator.
"""

from pathlib import Path

import yaml

ADJUSTMENT = {0: 0.432, 1: 0.243, 2: 0.216, 3: 0.108}
"""
Given the result was 4-x, what's the probability that x is 0, 1, 2, 3?
P(losing_goals_correct) in an 'Any Other Home Win' or 'Any Other Away Win' situation.

Quick tally for an early approximation (using all fixtures since 2019):
0 - 16
1 - 9
2 - 8
3 - 4
"""

OUTCOMES: list[str] = [
    "0 - 0",
    "0 - 1",
    "0 - 2",
    "0 - 3",
    "1 - 0",
    "1 - 1",
    "1 - 2",
    "1 - 3",
    "2 - 0",
    "2 - 1",
    "2 - 2",
    "2 - 3",
    "3 - 0",
    "3 - 1",
    "3 - 2",
    "3 - 3",
    "Any Other Home Win",
    "Any Other Away Win",
    "Any Other Draw",
]


SCORECASTS_LOC = "scorecasts"
OUTPUT_LOC = "outputs"


def load_yaml(path: Path, key: str) -> dict[str, str]:
    with path.open() as f:
        data = yaml.safe_load(f)[key]
    return data


TEAMS_MAP = load_yaml(path=Path("config.yml"), key="teams")

COMPETITIONS = load_yaml(path=Path("config.yml"), key="competitions")
