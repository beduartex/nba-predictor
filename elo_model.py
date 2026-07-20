import sqlite3
import pandas as pd

DB_PATH = "data/nba.db"
K = 20            #how much a single game can move a rating
HOME_ADV = 100    #bonus points for home court advantage
START_RATING = 1500


def expected_score(rating_a, rating_b):
    """Returns Team A's probability of winning, given both ratings."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_ratings(rating_winner, rating_loser):
    """Returns the new ratings after a game result."""
    expected_win = expected_score(rating_winner, rating_loser)
    new_winner = rating_winner + K * (1 - expected_win)
    new_loser = rating_loser + K * (0 - (1 - expected_win))
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

        new_winner, new_loser = update_ratings(
            ratings[winner.TEAM_ABBREVIATION],
            ratings[loser.TEAM_ABBREVIATION]
        )
        ratings[winner.TEAM_ABBREVIATION] = new_winner
        ratings[loser.TEAM_ABBREVIATION] = new_loser

    return ratings

def backtest_accuracy(games):
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

        new_winner, new_loser = update_ratings(
            ratings[winner.TEAM_ABBREVIATION],
            ratings[loser.TEAM_ABBREVIATION]
        )
        ratings[winner.TEAM_ABBREVIATION] = new_winner
        ratings[loser.TEAM_ABBREVIATION] = new_loser

    accuracy = correct / total * 100
    print(f"\nBacktest: {correct}/{total} correct ({accuracy:.1f}% accuracy)")
    return accuracy

if __name__ == "__main__":
    games = load_games()
    ratings = build_elo_ratings(games)

    ranked = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
    print("Current team Elo ratings:")
    for team, rating in ranked:
        print(f"{team}: {rating:.1f}")

    backtest_accuracy(games)