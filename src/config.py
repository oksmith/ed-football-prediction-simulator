"""
Constant values used in the prediction simulator.
"""

from pathlib import Path
from typing import TypedDict

import yaml
from pydantic import BaseModel, field_validator

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


# --- Pydantic: API boundary types ---
# These will have validation after fetching from Betfair and fail early if anything
# does not look right.


class RunnerOdds(BaseModel):
    """Represents a single runner (i.e. selection) returned from the Betfair API."""

    selection_name: str
    best_back_price: float | None
    best_lay_price: float | None
    status: str

    # We maintain `null` values for the back/lay prices if they exist. Note that this
    # comes after we contert to inf in _get_runner_price. TODO: decide if this is definitely
    # appropriate.
    @field_validator("best_back_price", "best_lay_price", mode="before")
    @classmethod
    def coerce_inf_to_none(cls, v: float) -> float | None:
        """Betfair returns no price as an empty list, which we convert to
        np.inf in _get_runner_price. Treat inf as 'no price available'."""
        return None if v == float("inf") else v


class MarketOdds(BaseModel):
    market_id: str
    market_name: str
    runners: list[RunnerOdds]


# TypedDicts are internal types that are already validated, and make it easier
# to read the code and reason with what data it's using


class MatchInfo(TypedDict):
    EventName: str
    OpenDate: str
    MarketCount: int
    Team1: str
    Team2: str


FINAL_COLUMN_ORDER = [
    "EventName",
    "OpenDate",
    "MarketCount",
    "Team1",
    "Team2",
    "Team1WinProb",
    "Team2WinProb",
    "DrawProb",
    "Over 1.5 Goals",
    "Under 1.5 Goals",
    "Over 2.5 Goals",
    "Under 2.5 Goals",
    *OUTCOMES,
]
"""
The constructed pd.DataFrame object will contain these columns.
"""
