import os
import re
from datetime import datetime
from pathlib import Path

import numpy as np

from src.config import OUTPUT_LOC, SCORECASTS_LOC, TEAMS_MAP
from src.logger import get_logger
from src.simulation import calculate_expected_score

logger = get_logger()

DATE_FORMAT = "%Y-%m-%d"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SKIP_KEYWORDS = {"FIXTURES", "SCORES", "EURO"}


def _validate_date_str(date: str) -> None:
    if not _DATE_RE.match(date):
        raise ValueError(f"date must be in YYYY-MM-DD format, got {date!r}")
    try:
        datetime.strptime(date, DATE_FORMAT)
    except ValueError:
        raise ValueError(f"date {date} is not a valid calendar date")


def _resolve_fixture_file(date: str | None, scorecasts_loc: str) -> Path:
    loc = Path(scorecasts_loc)
    if not loc.exists():
        raise FileNotFoundError(f"Scorecasts directory not found: {loc.resolve()}")

    if date is not None:
        _validate_date_str(date)
        path = loc / f"{date}.txt"
        if not path.exists():
            raise FileNotFoundError(f"No fixture file found for date {date!r} at {path.resolve()}")
        return path

    txt_files = [f.stem for f in loc.glob("*.txt")]
    if not txt_files:
        raise FileNotFoundError(f"No fixture files found in {loc.resolve()}")
    latest = max(txt_files)
    logger.warning("No date provided — using latest fixture file: %s.txt", latest)
    return loc / f"{latest}.txt"


def _parse_fixture_line(line: str, line_no: int) -> list[str]:
    parts = [x.strip() for x in line.split(" - ")]
    if len(parts) != 2:
        raise ValueError(f"Line {line_no} does not look like a fixture (expected 'TEAM - TEAM'): {line!r}")
    if any(p == "" for p in parts):
        raise ValueError(f"Line {line_no} has an empty team name: {line!r}")
    return parts


def parse_fixtures(
    date: str | None = None,
    scorecasts_loc: str = SCORECASTS_LOC,
    teams_map: dict[str, str] = TEAMS_MAP,
) -> tuple[list[list[str]], list[str]]:
    path = _resolve_fixture_file(date, scorecasts_loc)
    logger.info("Parsing fixtures from %s", path)

    raw_lines = path.read_text().strip().splitlines()

    fixtures = []
    for i, line in enumerate(raw_lines, start=1):
        if any(kw in line.upper() for kw in _SKIP_KEYWORDS):
            logger.debug("Skipping header line %d: %r", i, line)
            continue
        if not line.strip():
            continue
        fixtures.append(_parse_fixture_line(line, line_no=i))

    if not fixtures:
        raise ValueError(f"No fixtures found in {path} after filtering header lines")
    logger.info("Found %d fixtures", len(fixtures))

    missing = [abbr for fixture in fixtures for abbr in fixture if abbr not in teams_map]
    if missing:
        raise RuntimeError(
            f"Missing Betfair translations for {len(missing)} abbreviation(s): {sorted(set(missing))}\n"
            f"Add these to your teams.yaml before continuing."
        )

    parsed_fixtures = [" v ".join(teams_map[abbr] for abbr in fixture) for fixture in fixtures]
    logger.info("Parsed fixtures: %s", parsed_fixtures)

    return fixtures, parsed_fixtures


def compile_suggested_predictions(fixtures, suggested_predictions, match_values):
    parsed_fixtures = [" v ".join([TEAMS_MAP[f] for f in fixture]) for fixture in fixtures]
    for fixture in parsed_fixtures:
        if fixture not in suggested_predictions.keys():
            suggested_predictions[fixture] = "x - x"

    results = {fixture: suggested_predictions[fixture].replace(" ", "") for fixture in parsed_fixtures}
    predictions = [(" " + results[fixture] + " ").join(fixtures[i]) for i, fixture in enumerate(parsed_fixtures)]

    logger.info("PREDICTIONS:")
    _ = [print(line) for line in predictions]

    logger.info("EXPECTED SCORECAST SCORE: {}".format(calculate_expected_score(suggested_predictions, match_values)))

    save_predictions_and_values(predictions, match_values)


def save_predictions_and_values(predictions, values):
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    today = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(os.path.join(os.getcwd(), OUTPUT_LOC)):
        logger.info("Creating `{}` directory.".format(OUTPUT_LOC))
        os.makedirs(os.path.join(os.getcwd(), OUTPUT_LOC))

    predictions_path = os.path.join(os.getcwd(), OUTPUT_LOC, "{}_predictions_{}.txt".format(today, now))
    values_path = os.path.join(os.getcwd(), OUTPUT_LOC, "{}_values_{}.txt".format(today, now))

    values_lines = [
        [key]
        + [
            "{}: {} (lower: {}, upper: {})".format(
                outcome, str(np.round(ev["mean"], 4)), str(np.round(ev["lower"], 4)), str(np.round(ev["upper"], 4))
            )
            for outcome, ev in sorted(value.items(), key=lambda x: -x[1]["mean"])
        ]
        for key, value in values.items()
    ]
    values_lines = ["\n".join(match) for match in values_lines]

    with open(predictions_path, "w") as f:
        f.write("\n".join(predictions))

    with open(values_path, "w") as f:
        f.write("\n\n".join(values_lines))
