import pytest

from src.simulation import ed_scoring_value


@pytest.mark.parametrize(
    "guess, outcome, expected",
    [
        ("1 - 0", "2 - 0", 4),  # correct home win, wrong score, one team correct
        ("1 - 0", "2 - 1", 4),  # correct home win, wrong score, correct margin
        ("1 - 0", "3 - 1", 3),  # correct home win, wrong score, one team correct
        ("1 - 0", "1 - 0", 7),  # exact score
        ("1 - 1", "1 - 0", 1),  # wrong result, one team correct
        ("1 - 1", "1 - 1", 8),  # exact score, draw
        ("1 - 1", "0 - 0", 5),  # right result, draw
        ("1 - 0", "0 - 1", 0),  # completely wrong
    ],
)
def test_ed_scoring_value(guess, outcome, expected):
    assert ed_scoring_value(guess, outcome) == expected
