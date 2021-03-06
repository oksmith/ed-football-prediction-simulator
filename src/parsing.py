import os

import numpy as np

from datetime import datetime

from src.config import SCORECASTS_LOC, OUTPUT_LOC, TEAMS_DICT
from src.simulation import calculate_expected_score


def parse_fixtures(date=None):
    if date:
        file_name = '{}.txt'.format(date)
    else:
        file_name = max([x[:-4] for x in os.listdir(SCORECASTS_LOC)]) + '.txt'
        
    with open('{}/{}'.format(SCORECASTS_LOC, file_name), 'r') as f:
        lines = f.read().strip().split('\n')
        fixtures = [[x.strip() for x in line.split(' - ')] for line in lines
                    if not (
                'FIXTURES' in line.upper() or 'SCORES' in line.upper()
                )]

    missing_translations = []
    for fixture in fixtures:
        for f in fixture:
            if f not in TEAMS_DICT.keys():
                missing_translations.append(f)

    if len(missing_translations) > 0:
        raise RuntimeError('Need the Betfair translation of the following keys: {}'.format(missing_translations))

    parsed_fixtures = [
        ' v '.join([TEAMS_DICT[f] for f in fixture]) for fixture in fixtures
    ]
    
    return fixtures, parsed_fixtures


def compile_suggested_predictions(fixtures, suggested_predictions, match_values):
    parsed_fixtures = [
        ' v '.join([TEAMS_DICT[f] for f in fixture]) for fixture in fixtures
    ]
    for fixture in parsed_fixtures:
        if fixture not in suggested_predictions.keys():
            suggested_predictions[fixture] = 'x - x'

    results = {
        fixture: suggested_predictions[fixture].replace(' ', '')
        for fixture in parsed_fixtures
    }
    predictions = [
        (' '+results[fixture]+' ').join(fixtures[i]) for i, fixture in enumerate(parsed_fixtures)
    ]
    
    print('PREDICTIONS:')
    _ = [print(line) for line in predictions]

    print('EXPECTED SCORECAST SCORE: {}'.format(calculate_expected_score(suggested_predictions, match_values)))

    save_predictions_and_values(predictions, match_values)
    
    
def save_predictions_and_values(predictions, values):
    now = datetime.now().strftime('%Y%m%d%H%M%S')
    today = datetime.now().strftime('%Y-%m-%d')

    if not os.path.exists(os.path.join(os.getcwd(), OUTPUT_LOC)):
        print('Creating `{}` directory.'.format(OUTPUT_LOC))
        os.makedirs(os.path.join(os.getcwd(), OUTPUT_LOC))

    predictions_path = os.path.join(os.getcwd(), OUTPUT_LOC, '{}_predictions_{}.txt'.format(today, now))
    values_path = os.path.join(os.getcwd(), OUTPUT_LOC, '{}_values_{}.txt'.format(today, now))

    values_lines = [
        [key]+['{}: {} (lower: {}, upper: {})'.format(
            outcome,
            str(np.round(ev['mean'], 4)),
            str(np.round(ev['lower'], 4)),
            str(np.round(ev['upper'], 4))
        ) for outcome, ev in sorted(value.items(), key=lambda x: -x[1]['mean'])]
        for key, value in values.items()
    ]
    values_lines = ['\n'.join(match) for match in values_lines]
    
    with open(predictions_path, 'w') as f:
        f.write('\n'.join(predictions))

    with open(values_path, 'w') as f:
        f.write('\n\n'.join(values_lines))

    print('Saved predictions.')