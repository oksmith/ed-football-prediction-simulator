from src.betfair import BetfairClient
from src.get_odds import get_matches, get_odds
from src.logger import get_logger
from src.parsing import compile_suggested_predictions, parse_fixtures
from src.simulation import get_expected_values

logger = get_logger()

# TODO list:
# - don't use pandas DataFrames anywhere. Use raw dicts or numpy arrays when simulating
# - better credential handling
# - more unit tests
# - clearer documentation (for myself in the future) -- especially `betfair.py`

if __name__ == "__main__":
    fixtures, parsed_fixtures = parse_fixtures()

    # Fetch Betfair information
    client = BetfairClient()
    matches = get_matches(client, fixtures_list=parsed_fixtures)
    df = get_odds(client, matches)

    # Simulate outcomes
    suggested_predictions, match_values = get_expected_values(df)

    # Compile predictions and save
    compile_suggested_predictions(fixtures, suggested_predictions, match_values)
