import datetime
from typing import Literal

import numpy as np
import pandas as pd
from betfairlightweight import filters

from src.betfair import BetfairClient
from src.config import COMPETITIONS, OUTCOMES
from src.logger import get_logger

logger = get_logger()


MarketName = Literal["Match Odds", "Correct Score", "Over/Under 1.5 Goals", "Over/Under 2.5 Goals"]


MARKETS_OF_INTEREST = {"Match Odds", "Correct Score", "Over/Under 1.5 Goals", "Over/Under 2.5 Goals"}
"""
These are the betting markets we care about for the purposes of fetching odds from Betfair.
- Correct Score: Used to get the main odds of 0-0, 1-0, 0-1, etc. etc.
- Match Odds: TODO
- Over/Under 1.5 Goals: TODO
- Over/Under 2.5 Goals: TODO
"""

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

###########################################################################################

#                                    GET MATCHES                                          #

###########################################################################################


def _one_week_from_now() -> str:
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(weeks=1)).strftime("%Y-%m-%dT%TZ")


def get_competition_ids(client: BetfairClient, to_date: str) -> pd.DataFrame:
    # TODO: is there a way to pass in only cetain competitions?
    competitions = client.list_competitions(to_date)
    # TODO: no need to convert to dataframe. A TypedDict or Pydantic validated type is better.
    df = pd.DataFrame(
        {
            "Competition": [c.competition.name for c in competitions],
            "ID": [c.competition.id for c in competitions],
        }
    )
    return df.loc[df.Competition.isin(COMPETITIONS)]


# TODO: this is a CORE function used in `main.py`. Same as `get_odds`. Document them properly.
# TODO: when can `fixtures_list` ever be None? It is better to assert it's non-empty if we're
# gonna use it downstream.
# TODO: create a Pydantic data type called MatchesInfo and make it the return type
def get_matches(client: BetfairClient, fixtures_list: list | None = None) -> pd.DataFrame:
    """
    This function uses a fixture list from Ed, and matches the Betfair match details from
    the API.

    It assumes that matches will take place within the next week, and therefore fetches all
    match information during that time and filters for the games we're interested in.
    TODO: make sure we log missing fixtures here properly, via a logger.warning call.
    """
    to_date = _one_week_from_now()
    competition_ids = get_competition_ids(client, to_date)["ID"].tolist()

    events = client.list_events(competition_ids, to_date)
    # TODO: no need to convert to dataframe. A TypedDict or Pydantic validated type is better.
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


###########################################################################################

#                                     GET ODDS                                            #

###########################################################################################


# TODO: create an OddsInfo data type and make it part of the return type dict[str, OddsInfo]
# No need to convert to DataFrame. May require changes to BetfairClient.
def _fetch_all_books(
    client: BetfairClient,
    market_ids: list[str],
    batch_size: int = 40,
) -> dict[str, pd.DataFrame]:
    """
    Fetch market books for all market IDs in batches.
    Returns {market_id: odds_df}.

    Betfair limit: sum(weight) * n_markets <= 200 per request.
    EX_BEST_OFFERS at depth 1 = ~5 points per market → ~40 markets per call.
    """
    results = {}
    for i in range(0, len(market_ids), batch_size):
        batch = market_ids[i : i + batch_size]
        books = client.list_market_book(market_ids=batch)
        for book in books:
            # We store raw book here and parse later because we need the
            # runner names available
            results[book.market_id] = book
    return results


def _fetch_runner_names_bulk(
    client: BetfairClient,
    market_ids: list[str],
    batch_size: int = 40,  # TODO: how was this batch size chosen? document it better and experiment.
) -> dict[str, dict[int, str]]:
    """
    Fetch runner names for all markets in bulk catalogue calls.
    Returns {market_id: {selection_id: runner_name}}.
    """
    results = {}
    for i in range(0, len(market_ids), batch_size):
        batch = market_ids[i : i + batch_size]
        catalogues = client.list_market_catalogue(
            # TODO: what do these arguments do? document them through inline comments.
            filter=filters.market_filter(market_ids=batch),
            market_projection=["RUNNER_DESCRIPTION"],
            max_results=len(batch),
        )
        for cat in catalogues:
            results[cat.market_id] = {r.selection_id: r.runner_name for r in cat.runners}
    return results


def get_odds(client: BetfairClient, matches: pd.DataFrame) -> pd.DataFrame:
    # First, get all market IDs per-event. Note, we could be batch this by
    # passing all event IDs to a single catalogue call. There's a TODO later.
    event_market_ids = {event_id: get_market_ids(client, event_id) for event_id in matches.index}
    # {
    #   '35758406': {'Match Odds': '1.259456757', 'Over/Under 2.5 Goals': '1.259456696', 'Correct Score': '1.259456767', 'Over/Under 1.5 Goals': '1.259456700'},
    #   '35760639': ...
    #   ...
    # }
    print(event_market_ids)

    # Flatten to a list of all market IDs we care about
    all_market_ids = [mid for market_map in event_market_ids.values() for mid in market_map.values()]
    # This contains all of the market IDs that we care about (`MARKETS_OF_INTEREST`) for all events in the original match list.
    # ['1.259456757', '1.259456696', '1.259456767', '1.259456700', '1.259478006', '1.259478016', '1.259477949', '1.259477945']
    print(all_market_ids)

    # Now, let's bulk fetch "runner names" (i.e. the names of the exact score outcomes with listed odds) in batches
    logger.info(f"Fetching runner names for {len(all_market_ids)} markets")
    runner_names = _fetch_runner_names_bulk(client, all_market_ids)
    print(runner_names)
    # {'1.259456757': {33291: 'South Africa', 39112: 'Canada', 58805: 'The Draw'}, '1.259456696':
    # {47972: 'Under 2.5 Goals', 47973: 'Over 2.5 Goals'},
    # '1.259456767': {1: '0 - 0', 4: '0 - 1', 9: '0 - 2', 16: '0 - 3', 2: '1 - 0',
    # ...
    # }

    # Do the same with books (i.e. the listed odds).
    logger.info(f"Fetching market books for {len(all_market_ids)} markets")
    books = _fetch_all_books(client, all_market_ids)
    print(books)
    # {'1.259456696': <MarketBook>, '1.259456700': <MarketBook>, '1.259456757': <MarketBook>, '1.259456767': <MarketBook>,

    # Now assemble into a final results dictionary
    rows = {}
    for event_id, match in matches.iterrows():
        values = match.to_dict()
        for market, market_id in event_market_ids[event_id].items():
            book = books.get(market_id)
            if book is None:
                odds = None
            else:
                odds = _book_to_df(book, runner_names[market_id], market_id)

            print(market, market_id)
            print(odds)
            """
            Correct Score 1.259478016
                MarketID  SelectionID       SelectionName  BestBackPrice  BestLayPrice  Status
            0   1.259478016            1               0 - 0           13.0          14.0  ACTIVE
            1   1.259478016            4               0 - 1           15.5          17.0  ACTIVE
            2   1.259478016            9               0 - 2           40.0          44.0  ACTIVE
            3   1.259478016           16               0 - 3          130.0         160.0  ACTIVE
            4   1.259478016            2               1 - 0            7.2           7.6  ACTIVE
            5   1.259478016            3               1 - 1            8.4           8.8  ACTIVE
            6   1.259478016            8               1 - 2           20.0          22.0  ACTIVE
            7   1.259478016           15               1 - 3           70.0          80.0  ACTIVE
            8   1.259478016            5               2 - 0            9.2           9.6  ACTIVE
            9   1.259478016            6               2 - 1            9.8          10.0  ACTIVE
            10  1.259478016            7               2 - 2           20.0          22.0  ACTIVE
            11  1.259478016           14               2 - 3           65.0          85.0  ACTIVE
            12  1.259478016           10               3 - 0           16.5          17.5  ACTIVE
            13  1.259478016           11               3 - 1           17.0          18.0  ACTIVE
            14  1.259478016           12               3 - 2           36.0          38.0  ACTIVE
            15  1.259478016           13               3 - 3           90.0         120.0  ACTIVE
            16  1.259478016      9063254  Any Other Home Win           11.0          11.5  ACTIVE
            17  1.259478016      9063255  Any Other Away Win           75.0         100.0  ACTIVE
            18  1.259478016      9063256      Any Other Draw           80.0         900.0  ACTIVE
            """
            values.update(_extract_market_values(market, odds, match))

        rows[event_id] = values
        logger.info("Assembled odds for %s", match.EventName)

    # assert 1 == 2

    return pd.DataFrame(rows).T[FINAL_COLUMN_ORDER]


# TODO: don't use dataframes. Use properly typed objects like TypedDict or Pydantic validated types.
def _book_to_df(book, runner_name_map: dict[int, str], market_id: str) -> pd.DataFrame:
    """Convert a raw market book object to the odds DataFrame format."""
    runners = book.runners
    selection_ids = [r.selection_id for r in runners]
    return pd.DataFrame(
        {
            "MarketID": market_id,
            "SelectionID": selection_ids,
            "SelectionName": [runner_name_map[sid] for sid in selection_ids],
            "BestBackPrice": [_get_runner_price(r, "back") for r in runners],
            "BestLayPrice": [_get_runner_price(r, "lay") for r in runners],
            "Status": [r.status for r in runners],
        }
    )


# TODO: delete in favour of get_all_market_ides? This can come later...
def get_market_ids(client: BetfairClient, event_id: MarketName) -> dict[MarketName, str]:
    """
    Returns a dict of markets and odds, for a given `event_id`. Note that `event_id` in
    Betfair always has the following format: "1.259456757". I.e. it's not representing a
    float!

    For example:
    {
        'Match Odds': '1.259456757',
        'Over/Under 2.5 Goals': '1.259456696',
        'Correct Score': '1.259456767',
        ...
    }
    """
    catalogues = client.list_market_catalogue(
        # TODO: move Betfair functionality into BetfairClient....
        filter=filters.market_filter(event_ids=[event_id]),
        max_results=1000,
    )
    return {c.market_name: c.market_id for c in catalogues if c.market_name in MARKETS_OF_INTEREST}


# TODO: will fetching all at once speed things up?
def get_all_market_ids(
    client: BetfairClient,
    event_ids: list[MarketName],
) -> dict[str, dict[MarketName, str]]:
    catalogues = client.list_market_catalogue(
        filter=filters.market_filter(event_ids=event_ids),
        max_results=1000,
    )

    result: dict[str, dict[str, str]] = {}
    for cat in catalogues:
        if cat not in MARKETS_OF_INTEREST:
            continue
        # event_id = cat.event.id
        result[cat.market_name] = cat.market_id

    return result


def _get_runner_price(runner, kind: str) -> float:
    try:
        pool = runner.ex.available_to_back if kind == "back" else runner.ex.available_to_lay
        return pool[0].price
    except IndexError:
        # TODO: what does returning infinity mean here? Is it valid?
        return np.inf


def _to_probabilities(odds: pd.DataFrame) -> pd.DataFrame:
    odds = odds.copy()
    odds["Price"] = odds[["BestBackPrice", "BestLayPrice"]].mean(axis=1)
    odds["Prob"] = 1 / odds["Price"]
    odds["Prob"] /= odds["Prob"].sum()
    return odds


def _prob(odds: pd.DataFrame, name: str) -> float:
    return odds.loc[odds.SelectionName == name, "Prob"].values[0]


def _extract_market_values(market: str, odds: pd.DataFrame | None, match: pd.Series) -> dict[str, float]:
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


# def _batch_market_ids(
#     client: BetfairClient,
#     matches: pd.DataFrame,
# ) -> dict[str, dict[str, str]]:
#     """Fetch all market IDs for all events in one catalogue call per event,
#     then return {event_id: {market_name: market_id}}."""
#     all_market_ids: dict[str, dict[str, str]] = {}
#     for event_id in matches.index:
#         all_market_ids[event_id] = get_market_ids(client, event_id)
#     return all_market_ids

# def get_market_odds(client: BetfairClient, market_id: str) -> pd.DataFrame | None:
#     catalogue = client.list_market_catalogue(
#         filter=filters.market_filter(market_ids=[market_id]),
#         market_projection=["RUNNER_DESCRIPTION"],
#         max_results=100,
#     )
#     if not catalogue:
#         logger.error(f"Empty catalogue for market {market_id}")
#         return None

#     runner_names = {r.selection_id: r.runner_name for r in catalogue[0].runners}

#     books = client.list_market_book(market_ids=[market_id])
#     if len(books) != 1:
#         raise ValueError(f"Expected 1 market book for {market_id}, got {len(books)}")

#     book = books[0]
#     if book.number_of_winners != 1:
#         raise ValueError(f"Expected 1 winner for {market_id}, got {book.number_of_winners}")

#     runners = book.runners
#     selection_ids = [r.selection_id for r in runners]

#     return pd.DataFrame(
#         {
#             "MarketID": market_id,
#             "SelectionID": selection_ids,
#             "SelectionName": [runner_names[sid] for sid in selection_ids],
#             "BestBackPrice": [_get_runner_price(r, "back") for r in runners],
#             "BestLayPrice": [_get_runner_price(r, "lay") for r in runners],
#             "Status": [r.status for r in runners],
#         }
#     )

# # def get_odds(client: BetfairClient, matches: pd.DataFrame) -> pd.DataFrame:
# #     rows = {}
# #     for event_id, match in matches.iterrows():
# #         market_ids = get_market_ids(client, event_id)
# #         print(market_ids)
# #         # {'Match Odds': '1.259456757', 'Over/Under 2.5 Goals': '1.259456696', 'Correct Score': '1.259456767', 'Over/Under 1.5 Goals': '1.259456700'}
# #         values = match.to_dict()
# #         print(values)
# #         # {'EventName': 'South Africa v Canada', 'OpenDate': Timestamp('2026-06-28 19:00:00+0000', tz='UTC'), 'MarketCount': 65, 'Team1': 'South Africa', 'Team2': 'Canada'}

# #         for market, market_id in market_ids.items():
# #             odds = get_market_odds(client, market_id)
# #             print(odds)
# #             #       MarketID  SelectionID SelectionName  BestBackPrice  BestLayPrice  Status
# #             # 0  1.259456757        33291  South Africa           6.40          6.60  ACTIVE
# #             # 1  1.259456757        39112        Canada           1.69          1.70  ACTIVE
# #             # 2  1.259456757        58805      The Draw           3.90          3.95  ACTIVE
# #             values.update(_extract_market_values(market, odds, match))
# #             print(values)
# #             # {'EventName': 'South Africa v Canada', 'OpenDate': Timestamp('2026-06-28 19:00:00+0000', tz='UTC'), 'MarketCount': 65, 'Team1': 'South Africa', 'Team2': 'Canada', 'Team1WinProb': np.float64(0.1540628084628455), 'Team2WinProb': np.float64(0.5908013303884931), 'DrawProb': np.float64(0.2551358611486613)}

# #         rows[event_id] = values
# #         logger.info(f"Fetched odds for {match.EventName}")

# #     return pd.DataFrame(rows).T[FINAL_COLUMN_ORDER]
