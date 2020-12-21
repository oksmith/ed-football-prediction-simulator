from src.parsing import parse_fixtures, compile_suggested_predictions
from src.betfair import BetfairPriceFetcher
from src.simulation import get_expected_values


if __name__ == '__main__':
    # Parse latest date, unless a separate date is supplied
    fixtures, parsed_fixtures = parse_fixtures()

    # Fetch betting odds
    bf = BetfairPriceFetcher()
    bf.get_next_week_matches(fixtures_list=parsed_fixtures)
    bf.get_odds()

    # Simulate outcomes
    suggested_predictions, match_values = get_expected_values(bf)

    # Compile predictions and save
    compile_suggested_predictions(fixtures, suggested_predictions, match_values)
