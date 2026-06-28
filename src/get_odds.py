import datetime
from typing import Any, Literal

import numpy as np
from betfairlightweight import filters

from src.betfair import BetfairClient
from src.config import COMPETITIONS, MatchInfo
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

###########################################################################################

#                                    GET MATCHES                                          #

###########################################################################################


def _one_week_from_now() -> str:
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(weeks=1)).strftime("%Y-%m-%dT%TZ")


def get_competition_ids(client: BetfairClient, to_date: str) -> dict[str, str]:
    # TODO: is there a way to pass in only cetain competitions?
    competitions = client.list_competitions(to_date)
    return [c.competition.id for c in competitions if c.competition.name in COMPETITIONS]


# TODO: this is a CORE function used in `main.py`. Same as `get_odds`. Document them properly.
def get_matches(client: BetfairClient, fixtures_list: list) -> dict[str, MatchInfo]:
    """
    This function uses a fixture list from Ed, and matches the Betfair match details from
    the API.

    It assumes that matches will take place within the next week, and therefore fetches all
    match information during that time and filters for the games we're interested in.
    TODO: make sure we log missing fixtures here properly, via a logger.warning call.
    """
    to_date = _one_week_from_now()
    competition_ids = get_competition_ids(client, to_date)

    events = client.list_events(competition_ids, to_date)

    if len(fixtures_list) == 0:
        logger.warning("The fixtures list is empty!")

    match_info: dict[str, MatchInfo] = {
        e.event.id: {
            "EventName": e.event.name,
            "OpenDate": e.event.open_date,
            "MarketCount": e.market_count,
            "Team1": e.event.name.split(" v ")[0],
            "Team2": e.event.name.split(" v ")[1],
        }
        for e in events
        if " v " in e.event.name and e.event.name in fixtures_list
    }
    return match_info


###########################################################################################

#                                     GET ODDS                                            #

###########################################################################################


# TODO: create an OddsInfo data type and make it part of the return type dict[str, OddsInfo]
# No need to convert to DataFrame. May require changes to BetfairClient.
def _fetch_all_books(
    client: BetfairClient,
    market_ids: list[str],
    batch_size: int = 40,
) -> dict[str, list]:
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
            # We store the runners
            results[book.market_id] = [
                {
                    "selection_id": r.selection_id,
                    "status": r.status,
                    "best_back_price": _get_runner_price(r, "back"),
                    "best_lay_price": _get_runner_price(r, "lay"),
                }
                for r in book.runners
            ]
    return results


def _get_runner_price(runner, kind: str) -> float:
    try:
        pool = runner.ex.available_to_back if kind == "back" else runner.ex.available_to_lay
        return pool[0].price
    except IndexError:
        # TODO: what does returning infinity mean here? Is it valid?
        return np.inf


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


# TODO: tighten up the return type
def get_odds(client: BetfairClient, matches: dict[str, MatchInfo]) -> dict[str, Any]:
    # First, get all market IDs per-event. Note, we could be batch this by
    # passing all event IDs to a single catalogue call. There's a TODO later.
    event_market_ids = {event_id: get_market_ids(client, event_id) for event_id in matches.keys()}
    # {
    #   '35758406': {'Match Odds': '1.259456757', 'Over/Under 2.5 Goals': '1.259456696', 'Correct Score': '1.259456767', 'Over/Under 1.5 Goals': '1.259456700'},
    #   '35760639': ...
    #   ...
    # }

    # Flatten to a list of all market IDs we care about
    all_market_ids = [mid for market_map in event_market_ids.values() for mid in market_map.values()]

    # Now, let's bulk fetch "runner names" (i.e. the names of the exact score outcomes with listed odds) in batches
    logger.info(f"Fetching runner names for {len(all_market_ids)} markets")
    runner_names = _fetch_runner_names_bulk(client, all_market_ids)
    # {
    #   '1.259456757': {33291: 'South Africa', 39112: 'Canada', 58805: 'The Draw'},
    #   '1.259456696': {47972: 'Under 2.5 Goals', 47973: 'Over 2.5 Goals'},
    #   '1.259456767': {1: '0 - 0', 4: '0 - 1', 9: '0 - 2', 16: '0 - 3', 2: '1 - 0',
    #   ...
    # }

    # Do the same with books (i.e. the listed odds).
    logger.info(f"Fetching market books for {len(all_market_ids)} markets")
    books = _fetch_all_books(client, all_market_ids)
    # {
    #   '1.259477795': [
    #       {'selection_id': 47972, 'status': 'ACTIVE', 'best_back_price': 1.79, 'best_lay_price': 1.81},
    #       {'selection_id': 47973, 'status': 'ACTIVE', 'best_back_price': 2.22,'best_lay_price': 2.28}
    #   ],
    #   '1.259477799': [...],
    #   ...
    # }

    # Now assemble into a final dictionary
    final_odds = {}
    for event_id, match_info in matches.items():
        for market, market_id in event_market_ids[event_id].items():
            book = books.get(market_id)
            if book is None:
                odds = None
            else:
                odds = [
                    dict(
                        {"market_id": market_id, "selection_name": runner_names[market_id][selection["selection_id"]]},
                        **selection,
                    )
                    for selection in book
                ]
            match_info.update(_extract_market_values(market, odds, match_info))

        final_odds[event_id] = match_info
        logger.info(f"Assembled odds for {match_info['EventName']}")

    return final_odds  # pd.DataFrame(final_odds).T[FINAL_COLUMN_ORDER]


# TODO: delete in favour of get_all_market_ides? This can come later...
def get_market_ids(client: BetfairClient, event_id: str) -> dict[MarketName, str]:
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


def _to_probabilities(odds: list[dict]) -> list[dict]:
    odds = [o.copy() for o in odds]

    for o in odds:
        o["price"] = (o["best_back_price"] + o["best_lay_price"]) / 2
        o["prob"] = 1 / o["price"]

    total = sum(o["prob"] for o in odds)
    for o in odds:
        o["prob"] /= total

    return odds


def _prob(odds: list[dict], name: str) -> float:
    return next(o["prob"] for o in odds if o["selection_name"] == name)


def _extract_market_values(market: str, odds: dict, match: MatchInfo) -> dict[str, float]:
    odds = _to_probabilities(odds)

    if market == "Match Odds":
        return {
            "Team1WinProb": _prob(odds, match["Team1"]),
            "Team2WinProb": _prob(odds, match["Team2"]),
            "DrawProb": _prob(odds, "The Draw"),
        }
    elif market in ("Over/Under 1.5 Goals", "Over/Under 2.5 Goals", "Correct Score"):
        return {o["selection_name"]: _prob(odds, o["selection_name"]) for o in odds}
    else:
        raise ValueError(f"Unexpected market type: {market}")
