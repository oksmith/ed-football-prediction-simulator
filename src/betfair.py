import getpass
import datetime

import pandas as pd
import numpy as np

import betfairlightweight
from betfairlightweight import filters

from src.config import OUTCOMES


pd.options.display.max_columns = 50

SECRETS = 'betfair_creds.txt'

SOCCER_ID = 1

FINAL_COLUMN_ORDER = ['EventName', 'OpenDate', 'MarketCount', 'Team1', 'Team2', 'Team1WinProb', 'Team2WinProb',
       'DrawProb', 'Over 1.5 Goals', 'Under 1.5 Goals', 'Over 2.5 Goals', 'Under 2.5 Goals', '0 - 0',
       '0 - 1', '0 - 2', '0 - 3', '1 - 0', '1 - 1', '1 - 2', '1 - 3', '2 - 0',
       '2 - 1', '2 - 2', '2 - 3', '3 - 0', '3 - 1', '3 - 2', '3 - 3',
       'Any Other Home Win', 'Any Other Away Win', 'Any Other Draw']


def _get_credentials():
    with open(SECRETS, 'r') as f:
        secrets = [str(line).strip('\n').strip() for line in f.readlines()]
    
    return {
        'username': secrets[0], 
        'password': getpass.getpass('Betfair password: '), 
        'app_key': secrets[1],
        'certs': secrets[2]
    }


class BetfairPriceFetcher:
    def __init__(self):
        self.trading = betfairlightweight.APIClient(**_get_credentials())
        self.trading.login()

        self.matches_df = None
        self.data = None
        
    def get_competition_ids(self, to_date):
        competition_filter = filters.market_filter(
            event_type_ids=[SOCCER_ID], 
            market_start_time={
                'to': to_date
            })

        # Get a list of competitions for soccer
        competitions = self.trading.betting.list_competitions(
            filter=competition_filter
        )

        # Iterate over the competitions and create a dataframe of competitions and competition ids
        soccer_competitions = pd.DataFrame({
            'Competition': [competition_object.competition.name for competition_object in competitions],
            'ID': [competition_object.competition.id for competition_object in competitions]
        })

        return soccer_competitions.loc[soccer_competitions.Competition.isin([
            # English competitions 
            'English Premier League',
            'English Championship',
            'English FA Cup',
            'English Football League Cup',
            'EFL Trophy',
            'English League 1',
            'English League 2',

            # European competitions
            'UEFA Champions League',
            'UEFA Europa League',
            'UEFA Europa Conference League',
            'UEFA Super Cup',
            'UEFA Europa League Qualifiers',

            # International competitions
            'UEFA Nations League',
            # FIFA World Cup 2022,
            'FIFA World Cup Qualifiers',
            'FIFA World Cup Qualifiers - Europe',
            # International Friendlies,
            'UEFA Euro 2020',

            # Scottish
            'Scottish Premiership',

            # Italian
            'Italian Serie A',

            # Spanish
            'Spanish La Liga',
            'Spanish Copa del Rey',

        ])]

    def get_next_week_matches(self, fixtures_list=None):
        # Get a datetime object in a week and convert to string
        datetime_in_a_week = (datetime.datetime.utcnow() + datetime.timedelta(weeks=1)).strftime("%Y-%m-%dT%TZ")

        competitions = self.get_competition_ids(datetime_in_a_week)

        events = self.trading.betting.list_events(
            filter=filters.market_filter(
                competition_ids=competitions.ID.tolist(),
                market_start_time={
                    'to': (datetime.datetime.utcnow() + datetime.timedelta(weeks=1)).strftime("%Y-%m-%dT%TZ")
                }
            )
        )

        # Create a DataFrame with all the events by iterating over each event object
        football_events_next_week = pd.DataFrame({
            'EventName': [event_object.event.name for event_object in events],
            'EventID': [event_object.event.id for event_object in events],
            'OpenDate': [event_object.event.open_date for event_object in events],
            'MarketCount': [event_object.market_count for event_object in events],
        })

        matches_df = football_events_next_week.loc[
            football_events_next_week.EventName.str.split(' v ').str.len() > 1
        ].sort_values('OpenDate')

        matches_df['Team1'] = matches_df.EventName.str.split(' v ').str[0]
        matches_df['Team2'] = matches_df.EventName.str.split(' v ').str[1]
        
        if fixtures_list:
            matches_df = matches_df.loc[matches_df.EventName.isin(fixtures_list)]

        self.matches_df = matches_df.set_index('EventID')
        
    def fetch_single_event_market_ids(self, event_id):
        market_catalogues = self.trading.betting.list_market_catalogue(
            filter=filters.market_filter(event_ids=[event_id]),
            max_results='1000',
        )

        return {
            market_cat_object.market_name: market_cat_object.market_id
            for market_cat_object in market_catalogues
            if market_cat_object.market_name in [
                'Match Odds',
                'Correct Score',
                'Over/Under 1.5 Goals',
                'Over/Under 2.5 Goals'
            ]
        }
        
    def fetch_market_id_dict(self):
        self.market_id_dict = {
            event_id: self.fetch_single_event_market_ids(event_id=event_id) 
            for event_id in self.matches_df.index.unique()
        }
        
    def get_price(self, runner, kind):
        try:
            if kind == 'back':
                return runner.ex.available_to_back[0].price 
            else:
                assert kind == 'lay', 'Need price kind either `back` or `lay`'
                return runner.ex.available_to_lay[0].price 
        except IndexError:
            return np.inf

    def get_match_odds(self, market_id):

        # Get market catalogues
        market_catalogue_filter = filters.market_filter(
            market_ids=[market_id],
            # market_countries=['GB' 'ES', 'IT', 'DE']
        )
        market_catalogue = self.trading.betting.list_market_catalogue(
            filter=market_catalogue_filter,
            market_projection=['RUNNER_DESCRIPTION'],
            max_results='100'
        )
        if len(market_catalogue) == 0:
            print('EMPTY! ', market_id, market_catalogue)
            return None

        market_catalogue = market_catalogue[0]
        runner_names = {
            r.selection_id: r.runner_name for r in market_catalogue.runners
        }

        # Request market books
        market_books = self.trading.betting.list_market_book(
            market_ids=[market_id],
            price_projection=filters.price_projection(
                price_data=['EX_BEST_OFFERS']
            )
        )

        assert len(market_books) == 1

        book = market_books[0]
        assert book.number_of_winners == 1

        runners = book.runners

        # Extract prices
        best_back_prices = [self.get_price(runner, kind='back') for runner in runners]
        best_lay_prices = [self.get_price(runner, kind='lay') for runner in runners]

        selection_ids = [runner.selection_id for runner in runners]
        statuses = [runner.status for runner in runners]

        runner_names = [runner_names[selection_id] for selection_id in selection_ids]

        return pd.DataFrame({
            'MarketID': [market_id]*len(selection_ids),
            'SelectionID': selection_ids,
            'SelectionName': runner_names,
            'BestBackPrice': best_back_prices,
            'BestLayPrice': best_lay_prices,
            'Status': statuses,
        })
    
    def get_odds(self):
        if not hasattr(self, 'market_id_dict'):
            self.fetch_market_id_dict()
            
        matches_with_odds = {}
        for event_id, match in self.matches_df.iterrows():

            for market, market_id in self.market_id_dict[event_id].items():
                odds = self.get_match_odds(market_id)
                if odds is None:
                    if market == 'Match Odds':
                        match['Team1WinProb'] = np.nan
                        match['Team2WinProb'] = np.nan
                        match['DrawProb'] = np.nan
                    elif market == 'Over/Under 1.5 Goals':
                        match['Over 1.5 Goals'] = np.nan
                        match['Under 1.5 Goals'] = np.nan
                    elif market == 'Over/Under 2.5 Goals':
                        match['Over 2.5 Goals'] = np.nan
                        match['Under 2.5 Goals'] = np.nan
                    elif market == 'Correct Score':
                        for name in OUTCOMES:
                            match[name] = np.nan
                    else:
                        raise ValueError('Unexpected market type! {}'.format(market))
                else:
                    odds['Price'] = odds[['BestBackPrice', 'BestLayPrice']].mean(axis=1)
                    odds['Prob'] = 1 / odds['Price']
                    total_prob = odds['Prob'].sum()
                    odds['Prob'] = odds['Prob'] / total_prob

                    if market == 'Match Odds':
                        match['Team1WinProb'] = odds.loc[odds.SelectionName == match.Team1, 'Prob'].values[0]
                        match['Team2WinProb'] = odds.loc[odds.SelectionName == match.Team2, 'Prob'].values[0]
                        match['DrawProb'] = odds.loc[odds.SelectionName == 'The Draw', 'Prob'].values[0]

                    elif market == 'Over/Under 1.5 Goals':
                        for name in odds.SelectionName:
                            match[name] = odds.loc[odds.SelectionName == name, 'Prob'].values[0]

                    elif market == 'Over/Under 2.5 Goals':
                        for name in odds.SelectionName:
                            match[name] = odds.loc[odds.SelectionName == name, 'Prob'].values[0]

                    elif market == 'Correct Score':
                        for name in odds.SelectionName:
                            match[name] = odds.loc[odds.SelectionName == name, 'Prob'].values[0]

                    else:
                        raise ValueError('Unexpected market type! {}'.format(market))

            matches_with_odds[event_id] = match
            print('Fetched odds for {}.'.format(self.matches_df.loc[event_id, 'EventName']))

        self.data = pd.DataFrame(matches_with_odds).T[FINAL_COLUMN_ORDER]
