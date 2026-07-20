import sqlite3
import math
import pandas as pd

DB_PATH = "data/nba.db"
K = 10            # how much a single game can move a rating
HOME_ADV = 50     # bonus points for home court advantage
START_RATING = 1500


def expected_score(rating_a, rating_b):
    """Returns Team A's probability of winning, given both ratings."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def margin_multiplier(point_diff, elo_diff):
    """
    Scales the rating change based on how big the win was.
    Bigger blowouts move ratings more, with diminishing returns.
    elo_diff is winner's rating minus loser's rating BEFORE the game,
    which dampens the multiplier when a favorite blows out an underdog
    (that's expected, so it shouldn't count as extra proof of strength).
    """
    return math.log(abs(point_diff) + 1) * (2.2 / ((elo_diff * 0.001) + 2.2))


def update_ratings(rating_winner, rating_loser, point_diff):
    """Returns the new ratings after a game result, scaled by margin of victory."""
    expected_win = expected_score(rating_winner, rating_loser)
    elo_diff = rating_winner - rating_loser
    multiplier = margin_multiplier(point_diff, elo_diff)

    new_winner = rating_winner + K * multiplier * (1 - expected_win)
    new_loser = rating_loser + K * multiplier * (0 - (1 - expected_win))
    return new_winner, new_loser


def load_games():
    conn = sqlite3.connect(DB_PATH)
    games = pd.read_sql("SELECT * FROM games", conn)
    conn.close()
    return games


def build_elo_ratings(games):
    games = games.sort_values("GAME_DATE")
    ratings = {}

    for game_id, group in games.groupby("GAME_ID"):
        if len(group) != 2:
            continue  # skip incomplete game pairs

        row_a, row_b = group.iloc[0], group.iloc[1]

        for team in (row_a.TEAM_ABBREVIATION, row_b.TEAM_ABBREVIATION):
            if team not in ratings:
                ratings[team] = START_RATING

        if row_a.WL == "W":
            winner, loser = row_a, row_b
        else:
            winner, loser = row_b, row_a

        point_diff = abs(row_a.PTS - row_b.PTS)

        new_winner, new_loser = update_ratings(
            ratings[winner.TEAM_ABBREVIATION],
            ratings[loser.TEAM_ABBREVIATION],
            point_diff
        )
        ratings[winner.TEAM_ABBREVIATION] = new_winner
        ratings[loser.TEAM_ABBREVIATION] = new_loser

    return ratings


def backtest_accuracy(games, verbose=True):
    games = games.sort_values("GAME_DATE")
    ratings = {}
    correct = 0
    total = 0

    for game_id, group in games.groupby("GAME_ID"):
        if len(group) != 2:
            continue

        row_a, row_b = group.iloc[0], group.iloc[1]

        for team in (row_a.TEAM_ABBREVIATION, row_b.TEAM_ABBREVIATION):
            if team not in ratings:
                ratings[team] = START_RATING

        # Predict winner BEFORE updating ratings with this game's result
        prob_a_wins = expected_score(ratings[row_a.TEAM_ABBREVIATION], ratings[row_b.TEAM_ABBREVIATION])
        predicted_winner = row_a.TEAM_ABBREVIATION if prob_a_wins > 0.5 else row_b.TEAM_ABBREVIATION
        actual_winner = row_a.TEAM_ABBREVIATION if row_a.WL == "W" else row_b.TEAM_ABBREVIATION

        if predicted_winner == actual_winner:
            correct += 1
        total += 1

        # Now update ratings with the actual result
        if row_a.WL == "W":
            winner, loser = row_a, row_b
        else:
            winner, loser = row_b, row_a

        point_diff = abs(row_a.PTS - row_b.PTS)

        new_winner, new_loser = update_ratings(
            ratings[winner.TEAM_ABBREVIATION],
            ratings[loser.TEAM_ABBREVIATION],
            point_diff
        )
        ratings[winner.TEAM_ABBREVIATION] = new_winner
        ratings[loser.TEAM_ABBREVIATION] = new_loser

    accuracy = correct / total * 100
    if verbose:
        print(f"\nBacktest: {correct}/{total} correct ({accuracy:.1f}% accuracy)")
    return accuracy


def tune_parameters(games):
    global K, HOME_ADV
    best_accuracy = 0
    best_k = None
    best_home_adv = None

    for test_k in [10, 15, 20, 25, 30]:
        for test_home_adv in [50, 75, 100, 125, 150]:
            K = test_k
            HOME_ADV = test_home_adv
            accuracy = backtest_accuracy(games, verbose=False)
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_k = test_k
                best_home_adv = test_home_adv

    print(f"\nBest params: K={best_k}, HOME_ADV={best_home_adv} -> {best_accuracy:.1f}% accuracy")
    return best_k, best_home_adv


if __name__ == "__main__":
    games = load_games()
    ratings = build_elo_ratings(games)

    ranked = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
    print("Current team Elo ratings:")
    for team, rating in ranked:
        print(f"{team}: {rating:.1f}")

    backtest_accuracy(games)
    tune_parameters(games)