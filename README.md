# ed-football-prediction-simulator

### About Ed's football prediction league
Approximately every week, a batch of 10 Premier League football fixtures is announced, but also occasionally the fixtures are from the Champions League, Europa League, Championship, Scottish PL etc. I need to provide predictions each week, and often I'm too lazy to research it, so this code was built to take Betfair odds and generate the best guess possible.

Scoring system:
* 8pts = Spot on (draw)
* 7pts = Spot on
* 5pts = Right result (draw)
* 4pts = Right result with one team goal total correct
* 3pts = Right result with no team goal total correct
* 1pt = One team’s goal total correct (without getting the result right)

### What this repo does
Script to:
1. Parse the fixtures and pull the match info using Betfair API, including Betfair exchange betting odds (which is the closest thing to a true probability available)
2. Simulate how much expected value I have from each potential guess, according to Ed's scoring system (see above) based on Monte Carlo simulation (50,000 simulations - configurable)
3. Format the fixtures list with the best possible prediction suggestions as my guesses, and save the file for copying+pasting back to Ed.
