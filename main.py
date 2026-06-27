from src.betfair import BetfairClient, get_matches, get_odds
from src.logger import get_logger
from src.parsing import compile_suggested_predictions, parse_fixtures
from src.simulation import get_expected_values

logger = get_logger()

if __name__ == "__main__":
    # Parse latest date, unless a separate date is supplied
    fixtures, parsed_fixtures = parse_fixtures()
    logger.info(parsed_fixtures)

    client = BetfairClient()
    matches = get_matches(client, fixtures_list=parsed_fixtures)
    df = get_odds(client, matches)

    # Simulate outcomes
    suggested_predictions, match_values = get_expected_values(df)

    # Compile predictions and save
    compile_suggested_predictions(fixtures, suggested_predictions, match_values)
