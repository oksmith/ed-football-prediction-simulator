# import getpass
import betfairlightweight
from betfairlightweight import filters

from src.logger import get_logger

logger = get_logger()

SECRETS = "betfair_creds.txt"

SOCCER_ID = 1
"""
This is ..... TODO
"""


# TODO: this is fragile, do it better e.g. dotenv secrets
def _get_credentials():
    with open(SECRETS, "r") as f:
        secrets = [str(line).strip("\n").strip() for line in f.readlines()]

    if len(secrets) < 4:
        raise ValueError(f"Expected 4 lines in {SECRETS} (username, password, app_key, certs), got {len(secrets)}")

    return {
        "username": secrets[0],
        "password": secrets[1],  # getpass.getpass('Betfair password: '),
        "app_key": secrets[2],
        "certs": secrets[3],
    }


class BetfairClient:
    def __init__(self):
        self.trading = betfairlightweight.APIClient(**_get_credentials())
        self.trading.login()

    def list_competitions(self, to_date: str):
        return self.trading.betting.list_competitions(
            filter=filters.market_filter(
                event_type_ids=[SOCCER_ID],
                market_start_time={"to": to_date},
            )
        )

    def list_events(self, competition_ids: list, to_date: str):
        return self.trading.betting.list_events(
            filter=filters.market_filter(
                competition_ids=competition_ids,
                market_start_time={"to": to_date},
            )
        )

    def list_market_catalogue(self, **kwargs):
        return self.trading.betting.list_market_catalogue(**kwargs)

    def list_market_book(self, market_ids: list):
        return self.trading.betting.list_market_book(
            market_ids=market_ids,
            price_projection=filters.price_projection(price_data=["EX_BEST_OFFERS"]),
        )
