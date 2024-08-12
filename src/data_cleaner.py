from .helpers import save_data, load_data, get_next_gameweek_id
from . import variables


# global variables
next_event = get_next_gameweek_id()
all_seasons = variables.ALL_SEASONS


def clean_players_data():
    # load the players data
    all_players = load_data("players.json", "data/original")

    # define headers that we need to keep
    headers = ["first_name", "second_name", "minutes", "total_points", "points_per_game",
               "team", "element_type", "now_cost", "status", "id", "history"]

    # list to store the filtered information
    filtered_players = []

    # only keep the required headers and remove the unwanted information
    for player in all_players:
        # remove unwanted keys from the player's data
        player = {header: player[header] for header in headers}

        # add player's full name
        player_name = f"{player['first_name']} {player['second_name']}"
        player["full_name"] = player_name.lower()

        # convert floats casted into a string to floats
        player["points_per_game"] = float(player["points_per_game"])

        # create a single season entry for the current season
        player_season_stats = {
            # Assuming the first season in all_seasons is the current one
            "season": all_seasons[0],
            "minutes": player["minutes"],
            "total_points": player["total_points"],
            "points_per_game": player["points_per_game"],
            "now_cost": player["now_cost"],
            "history": player["history"]
        }

        # calculate the net points only if history is available
        if player_season_stats["history"]:
            player_gw_history = []
            for count, gw in enumerate(player_season_stats["history"][::-1]):
                if count < 5:
                    if gw["minutes"] >= 60:
                        net_points = gw["total_points"] - 2
                    elif 0 < gw["minutes"] < 60:
                        net_points = gw["total_points"] - 1
                    else:
                        net_points = gw["total_points"]
                    player_gw_history.append(net_points)
            player_season_stats["gw_history"] = player_gw_history
        else:
            player_season_stats["gw_history"] = []

        del player_season_stats["history"]

        player["seasons"] = [player_season_stats]

        # remove the stats that are now in the seasons list
        for key in ["minutes", "total_points", "points_per_game", "now_cost", "history"]:
            del player[key]

        filtered_players.append(player)

    # only retain the players who have played at least one minute in the season
    filtered_players = [player for player in filtered_players if (
        player["seasons"][0]["minutes"] > 0 and
        player["seasons"][0]["total_points"] > 0
    )]

    # save the data in a JSON file
    save_data(filtered_players, "filtered_players.json", "data")

    print(
        f"Filtered {len(filtered_players)} players out of {len(all_players)} total players.")


def clean_teams_data():
    """
    Cleans the data for the teams.
    """

    # load the teams data
    all_teams = load_data("teams.json", "data/original")

    # define headers that we need to keep
    headers = ["id", "name"]

    # list to store the filtered information
    filtered_teams = []

    # iterate over all the teams and remove unwanted information
    for team in all_teams:

        # remove unwanted keys from the team's data
        team = {header: team[header] for header in headers}
        filtered_teams.append(team)

    # save the data in a JSON file
    save_data(filtered_teams, "filtered_teams.json", "data")


def clean_fixtures_data():
    """
    Cleans the fixtures data and filters it.
    """

    # load the fixtures data
    all_fixtures = load_data("fixtures.json", "data/original")

    # define headers that we need to keep
    headers = headers = ["event", "finished", "team_a",
                         "team_a_difficulty", "team_h", "team_h_difficulty"]

    # list to store the filtered information
    filtered_fixtures = []

    # iterate over all the teams and remove unwanted information
    for fixture in all_fixtures:
        if fixture["event"] is not None:
            # remove unwanted keys from the fixture's data
            fixture = {header: fixture[header] for header in headers}
            filtered_fixtures.append(fixture)

    # only retain the fixtures that are yet to take place
    filtered_fixtures = [
        fixture for fixture in filtered_fixtures if fixture['event'] >= next_event]

    # save the data in a JSON file
    save_data(filtered_fixtures, "filtered_fixtures.json", "data")


def main():
    clean_players_data()
    print('Cleaned Players data.\n')
    clean_teams_data()
    print('Cleaned Teams data.\n')
    clean_fixtures_data()
    print('Cleaned Fixtures data.')


if __name__ == "__main__":
    main()
