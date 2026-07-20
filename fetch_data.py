import sqlite3
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.library.parameters import SeasonTypeNullable

DB_PATH = "data/nba.db"
SEASON = "2025-26"

def get_connection():
    return sqlite3.connect(DB_PATH)

def fetch_teams(conn):
    team_list = teams.get_teams()
    df = pd.DataFrame(team_list)
    df.to_sql("teams", conn, if_exists="replace", index=False)
    print(f"Saved {len(df)} teams")
    
def fetch_games(conn, season=SEASON):
    finder = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        season_type_nullable=SeasonTypeNullable.regular
    )
    games = finder.get_data_frames()[0]
    games.to_sql("games", conn, if_exists="replace", index=False)
    print(f"Saved {len(games)} game rows for {season}")

def main():
    conn = get_connection()
    fetch_teams(conn)
    fetch_games(conn)
    conn.close()
    print("Done. Data saved to", DB_PATH)

if __name__ == "__main__":
    main()