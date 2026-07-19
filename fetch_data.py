from nba_api.stats.static import teams

team_list = teams.get_teams()
print(f"Found {len(team_list)} teams")
for team in team_list:
    if 'b' in team['full_name'].lower():
        print(team['full_name']) 