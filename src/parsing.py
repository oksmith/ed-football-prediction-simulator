import os

import numpy as np

from datetime import datetime

from src.config import SCORECASTS_LOC, OUTPUT_LOC, TEAMS_DICT


def parse_fixtures(date=None):
    if date:
        file_name = '{}.txt'.format(date)
    else:
        file_name = max([x[:-4] for x in os.listdir(SCORECASTS_LOC)]) + '.txt'
        
    with open('{}/{}'.format(SCORECASTS_LOC, file_name), 'r') as f:
        fixtures = [[x.strip() for x in line.split(' - ')] for line in f.read().strip().split('\n')[1:]]
        
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

    save_predictions_and_values(predictions, match_values)
    
    
def save_predictions_and_values(predictions, values):
    now = datetime.now().strftime('%Y%m%d%H%M%S')

    if not os.path.exists(os.path.join(os.getcwd(), OUTPUT_LOC)):
        print('Creating `{}` directory.'.format(OUTPUT_LOC))
        os.makedirs(os.path.join(os.getcwd(), OUTPUT_LOC))

    predictions_path = os.path.join(os.getcwd(), OUTPUT_LOC, 'predictions_{}.txt'.format(now))
    values_path = os.path.join(os.getcwd(), OUTPUT_LOC, 'values_{}.txt'.format(now))

    values_lines = [
        [key]+[outcome + ': ' + str(np.round(ev, 4)) for outcome, ev in value.items()]
        for key, value in values.items()
    ]
    values_lines = ['\n'.join(match) for match in values_lines]
    
    with open(predictions_path, 'w') as f:
        f.write('\n'.join(predictions))

    with open(values_path, 'w') as f:
        f.write('\n\n'.join(values_lines))

    print('Saved predictions.')