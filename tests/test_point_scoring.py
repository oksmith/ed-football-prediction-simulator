from src.simulation import ed_scoring_value


def test_ed_scoring_value():
    guess = "1 - 0"
    outcome = "2 - 0"
    assert ed_scoring_value(guess, outcome) == 4

    guess = "1 - 0"
    outcome = "1 - 0"
    assert ed_scoring_value(guess, outcome) == 7
