import datetime

# import getpass
import betfairlightweight
import numpy as np
import pandas as pd
from betfairlightweight import filters

from src.config import COMPETITIONS, OUTCOMES

pd.options.display.max_columns = 50

SECRETS = "betfair_creds.txt"

SOCCER_ID = 1

MARKETS_OF_INTEREST = {"Match Odds", "Correct Score", "Over/Under 1.5 Goals", "Over/Under 2.5 Goals"}

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


def _get_credentials():
    with open(SECRETS, "r") as f:
        secrets = [str(line).strip("\n").strip() for line in f.readlines()]

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


# class BetfairPriceFetcher:
#     def __init__(self):
#         self.trading = betfairlightweight.APIClient(**_get_credentials())
#         self.trading.login()

#         self.matches_df = None
#         self.data = None

#     def get_competition_ids(self, to_date):
#         competition_filter = filters.market_filter(
#             event_type_ids=[SOCCER_ID],
#             market_start_time={
#                 'to': to_date
#             })

#         # Get a list of competitions for soccer
#         competitions = self.trading.betting.list_competitions(
#             filter=competition_filter
#         )

#         # Iterate over the competitions and create a dataframe of competitions and competition ids
#         soccer_competitions = pd.DataFrame({
#             'Competition': [competition_object.competition.name for competition_object in competitions],
#             'ID': [competition_object.competition.id for competition_object in competitions]
#         })

#         return soccer_competitions.loc[soccer_competitions.Competition.isin(COMPETITIONS)]

#     def get_next_week_matches(self, fixtures_list=None):
#         # Get a datetime object in a week and convert to string
#         datetime_in_a_week = (datetime.datetime.utcnow() + datetime.timedelta(weeks=1)).strftime("%Y-%m-%dT%TZ")

#         competitions = self.get_competition_ids(datetime_in_a_week)

#         events = self.trading.betting.list_events(
#             filter=filters.market_filter(
#                 competition_ids=competitions.ID.tolist(),
#                 market_start_time={
#                     'to': (datetime.datetime.utcnow() + datetime.timedelta(weeks=1)).strftime("%Y-%m-%dT%TZ")
#                 }
#             )
#         )

#         # Create a DataFrame with all the events by iterating over each event object
#         football_events_next_week = pd.DataFrame({
#             'EventName': [event_object.event.name for event_object in events],
#             'EventID': [event_object.event.id for event_object in events],
#             'OpenDate': [event_object.event.open_date for event_object in events],
#             'MarketCount': [event_object.market_count for event_object in events],
#         })
#         print(f"football_events_next_week: {football_events_next_week}")

#         matches_df = football_events_next_week.loc[
#             football_events_next_week.EventName.str.split(' v ').str.len() > 1
#         ].sort_values('OpenDate')

#         matches_df['Team1'] = matches_df.EventName.str.split(' v ').str[0]
#         matches_df['Team2'] = matches_df.EventName.str.split(' v ').str[1]

#         if fixtures_list:
#             matches_df = matches_df.loc[matches_df.EventName.isin(fixtures_list)]
#         print(f"matches_df: {matches_df}")
#         self.matches_df = matches_df.set_index('EventID')

#     def fetch_single_event_market_ids(self, event_id):
#         market_catalogues = self.trading.betting.list_market_catalogue(
#             filter=filters.market_filter(event_ids=[event_id]),
#             max_results='1000',
#         )

#         return {
#             market_cat_object.market_name: market_cat_object.market_id
#             for market_cat_object in market_catalogues
#             if market_cat_object.market_name in [
#                 'Match Odds',
#                 'Correct Score',
#                 'Over/Under 1.5 Goals',
#                 'Over/Under 2.5 Goals'
#             ]
#         }

#     def fetch_market_id_dict(self):
#         self.market_id_dict = {
#             event_id: self.fetch_single_event_market_ids(event_id=event_id)
#             for event_id in self.matches_df.index.unique()
#         }

#     def get_price(self, runner, kind):
#         try:
#             if kind == 'back':
#                 return runner.ex.available_to_back[0].price
#             else:
#                 assert kind == 'lay', 'Need price kind either `back` or `lay`'
#                 return runner.ex.available_to_lay[0].price
#         except IndexError:
#             return np.inf

#     def get_match_odds(self, market_id):

#         # Get market catalogues
#         market_catalogue_filter = filters.market_filter(
#             market_ids=[market_id],
#             # market_countries=['GB' 'ES', 'IT', 'DE']
#         )
#         market_catalogue = self.trading.betting.list_market_catalogue(
#             filter=market_catalogue_filter,
#             market_projection=['RUNNER_DESCRIPTION'],
#             max_results='100'
#         )
#         if len(market_catalogue) == 0:
#             print('EMPTY! ', market_id, market_catalogue)
#             return None

#         market_catalogue = market_catalogue[0]
#         runner_names = {
#             r.selection_id: r.runner_name for r in market_catalogue.runners
#         }

#         # Request market books
#         market_books = self.trading.betting.list_market_book(
#             market_ids=[market_id],
#             price_projection=filters.price_projection(
#                 price_data=['EX_BEST_OFFERS']
#             )
#         )

#         assert len(market_books) == 1

#         book = market_books[0]
#         assert book.number_of_winners == 1

#         runners = book.runners

#         # Extract prices
#         best_back_prices = [self.get_price(runner, kind='back') for runner in runners]
#         best_lay_prices = [self.get_price(runner, kind='lay') for runner in runners]

#         selection_ids = [runner.selection_id for runner in runners]
#         statuses = [runner.status for runner in runners]

#         runner_names = [runner_names[selection_id] for selection_id in selection_ids]

#         return pd.DataFrame({
#             'MarketID': [market_id]*len(selection_ids),
#             'SelectionID': selection_ids,
#             'SelectionName': runner_names,
#             'BestBackPrice': best_back_prices,
#             'BestLayPrice': best_lay_prices,
#             'Status': statuses,
#         })


def _one_week_from_now() -> str:
    return (datetime.datetime.utcnow() + datetime.timedelta(weeks=1)).strftime("%Y-%m-%dT%TZ")


def get_competition_ids(client: BetfairClient, to_date: str) -> pd.DataFrame:
    competitions = client.list_competitions(to_date)
    df = pd.DataFrame(
        {
            "Competition": [c.competition.name for c in competitions],
            "ID": [c.competition.id for c in competitions],
        }
    )
    return df.loc[df.Competition.isin(COMPETITIONS)]


def get_matches(client: BetfairClient, fixtures_list: list | None = None) -> pd.DataFrame:
    to_date = _one_week_from_now()
    competition_ids = get_competition_ids(client, to_date).ID.tolist()

    events = client.list_events(competition_ids, to_date)
    df = pd.DataFrame(
        {
            "EventName": [e.event.name for e in events],
            "EventID": [e.event.id for e in events],
            "OpenDate": [e.event.open_date for e in events],
            "MarketCount": [e.market_count for e in events],
        }
    )

    # Keep only "Team1 v Team2" style events
    df = df.loc[df.EventName.str.contains(" v ")].sort_values("OpenDate")
    df["Team1"] = df.EventName.str.split(" v ").str[0]
    df["Team2"] = df.EventName.str.split(" v ").str[1]

    if fixtures_list:
        df = df.loc[df.EventName.isin(fixtures_list)]

    return df.set_index("EventID")


def get_market_ids(client: BetfairClient, event_id: str) -> dict[str, str]:
    catalogues = client.list_market_catalogue(
        filter=filters.market_filter(event_ids=[event_id]),
        max_results=1000,
    )
    return {c.market_name: c.market_id for c in catalogues if c.market_name in MARKETS_OF_INTEREST}


def _get_runner_price(runner, kind: str) -> float:
    try:
        pool = runner.ex.available_to_back if kind == "back" else runner.ex.available_to_lay
        return pool[0].price
    except IndexError:
        return np.inf


def get_market_odds(client: BetfairClient, market_id: str) -> pd.DataFrame | None:
    catalogue = client.list_market_catalogue(
        filter=filters.market_filter(market_ids=[market_id]),
        market_projection=["RUNNER_DESCRIPTION"],
        max_results=100,
    )
    if not catalogue:
        print(f"Empty catalogue for market {market_id}")
        return None

    runner_names = {r.selection_id: r.runner_name for r in catalogue[0].runners}

    books = client.list_market_book(market_ids=[market_id])
    assert len(books) == 1
    book = books[0]
    assert book.number_of_winners == 1

    runners = book.runners
    selection_ids = [r.selection_id for r in runners]

    return pd.DataFrame(
        {
            "MarketID": market_id,
            "SelectionID": selection_ids,
            "SelectionName": [runner_names[sid] for sid in selection_ids],
            "BestBackPrice": [_get_runner_price(r, "back") for r in runners],
            "BestLayPrice": [_get_runner_price(r, "lay") for r in runners],
            "Status": [r.status for r in runners],
        }
    )


def _to_probabilities(odds: pd.DataFrame) -> pd.DataFrame:
    odds = odds.copy()
    odds["Price"] = odds[["BestBackPrice", "BestLayPrice"]].mean(axis=1)
    odds["Prob"] = 1 / odds["Price"]
    odds["Prob"] /= odds["Prob"].sum()
    return odds


def _prob(odds: pd.DataFrame, name: str) -> float:
    return odds.loc[odds.SelectionName == name, "Prob"].values[0]


def _extract_market_values(market: str, odds: pd.DataFrame | None, match: pd.Series) -> dict:
    """Return a flat dict of column → value for one market."""
    if odds is None:
        null = {
            "Match Odds": {"Team1WinProb": np.nan, "Team2WinProb": np.nan, "DrawProb": np.nan},
            "Over/Under 1.5 Goals": {"Over 1.5 Goals": np.nan, "Under 1.5 Goals": np.nan},
            "Over/Under 2.5 Goals": {"Over 2.5 Goals": np.nan, "Under 2.5 Goals": np.nan},
            "Correct Score": {name: np.nan for name in OUTCOMES},
        }
        if market not in null:
            raise ValueError(f"Unexpected market type: {market}")
        return null[market]

    odds = _to_probabilities(odds)

    if market == "Match Odds":
        return {
            "Team1WinProb": _prob(odds, match.Team1),
            "Team2WinProb": _prob(odds, match.Team2),
            "DrawProb": _prob(odds, "The Draw"),
        }
    elif market in ("Over/Under 1.5 Goals", "Over/Under 2.5 Goals", "Correct Score"):
        return {name: _prob(odds, name) for name in odds.SelectionName}
    else:
        raise ValueError(f"Unexpected market type: {market}")


def get_odds(client: BetfairClient, matches: pd.DataFrame) -> pd.DataFrame:
    rows = {}
    for event_id, match in matches.iterrows():
        market_ids = get_market_ids(client, event_id)
        values = match.to_dict()

        for market, market_id in market_ids.items():
            odds = get_market_odds(client, market_id)
            values.update(_extract_market_values(market, odds, match))

        rows[event_id] = values
        print(f"Fetched odds for {match.EventName}")

    return pd.DataFrame(rows).T[FINAL_COLUMN_ORDER]
