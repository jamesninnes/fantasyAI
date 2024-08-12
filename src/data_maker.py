from .helpers import save_data, load_data, get_next_gameweek_id
import numpy as np
import json
import os
from . import variables
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# global variables
all_seasons = variables.ALL_SEASONS
next_event = get_next_gameweek_id()
positions = variables.positions()


def safe_divide(a, b):
    return a / b if b != 0 else 0


def initialize_league_data():
    league_data = {}
    for season in all_seasons:
        league_data[season] = {
            "all_players_effective_total_points": 0,
            "all_players_minutes": 0
        }
    return league_data


def load_data_files():
    logging.info("Loading data files...")
    teams = load_data("filtered_teams.json", "data")
    fixtures = load_data("filtered_fixtures.json", "data")
    players = load_data("filtered_players.json", "data")
    return teams, fixtures, players


def calculate_fixture_easiness(teams, fixtures):
    logging.info("Calculating fixture easiness ratings...")
    max_fer_points = 0
    avg_fer_points = 0

    for team in teams:
        fer = []
        for fixture in fixtures:
            if fixture["team_a"] == team["id"]:
                fer.append(1 - 0.1 * fixture["team_a_difficulty"])
            elif fixture["team_h"] == team["id"]:
                fer.append(1 - 0.1 * fixture["team_h_difficulty"])
            if len(fer) == 5:
                break

        team["fer"] = fer
        team["fer_points"] = np.mean(fer) * (1 - np.var(fer))
        avg_fer_points += team["fer_points"]

    if len(teams) > 0:
        avg_fer_points /= len(teams)
    else:
        avg_fer_points = 0

    for team in teams:
        if avg_fer_points != 0:
            team["fer_points"] = round(team["fer_points"] / avg_fer_points, 3)
        else:
            team["fer_points"] = 0
        max_fer_points = max(max_fer_points, team["fer_points"])

    teams = sorted(teams, key=lambda k: k["fer_points"], reverse=True)
    save_data(teams, "teams_cleaned.json", "data")
    return teams, max_fer_points


def process_player_data(players, teams, league_data):
    logging.info("Processing player data...")
    max_consistency = {season: 0 for season in all_seasons}

    for player in players:
        player["position"] = positions[player["element_type"]]
        player["value_points"] = 0

        for team in teams:
            if team["id"] == player["team"]:
                player["team_name"] = team["name"]
                player["fer"] = team["fer_points"]
                player["value_points"] += 10 if team["fer_points"] >= 1 else 8
                break

        total_career_games = 0
        for season in player["seasons"]:
            process_season_data(season, max_consistency)
            total_career_games += season["total_games"]

        assign_season_factors(player, total_career_games)

    return players, max_consistency


def process_season_data(season, max_consistency):
    if len(season["gw_history"]) > 0:
        season["effective_total_points"] = np.sum(season["gw_history"]).item()
        season["gw_avg_points"] = np.mean(season["gw_history"]).item()
        season["variance"] = np.var(season["gw_history"]).item() if len(
            season["gw_history"]) > 1 else 0
        season["consistency_factor"] = season["gw_avg_points"] * \
            (100 - season["variance"])
    else:
        season["effective_total_points"] = season["gw_avg_points"] = season["variance"] = season["consistency_factor"] = 0

    max_consistency[season["season"]] = max(
        max_consistency[season["season"]], season["consistency_factor"])
    del season["gw_history"]

    season["total_games"] = round(safe_divide(
        season["total_points"], season["points_per_game"]))
    season["now_cost"] /= 10


def assign_season_factors(player, total_career_games):
    for season in player["seasons"]:
        if season["season"] == variables.CURRENT_SEASON:
            season["season_factor"] = safe_divide(
                (season["total_games"] / total_career_games) + 1, 2)
        else:
            season["season_factor"] = safe_divide(
                season["total_games"] / total_career_games, 2)


def normalize_consistency_and_calculate_value_points(players, max_consistency):
    logging.info("Normalizing consistency and calculating value points...")
    logging.info(f"Max consistency values: {max_consistency}")
    for player in players:
        player["consistency_overall"] = 0
        for season in player["seasons"]:
            if max_consistency[season["season"]] > 0:
                season["consistency_factor"] /= max_consistency[season["season"]]
            else:
                season["consistency_factor"] = 0  # or some default value

            player["consistency_overall"] += season["consistency_factor"] * \
                season["season_factor"]
            player["value_points"] += calculate_value_points(
                season["consistency_factor"]) * season["season_factor"]


def calculate_value_points(consistency_factor):
    if consistency_factor >= 0.8:
        return 8
    elif consistency_factor >= 0.6:
        return 7
    elif consistency_factor >= 0.4:
        return 6
    elif consistency_factor >= 0.2:
        return 5
    elif consistency_factor > 0:
        return 4
    return 0


def calculate_league_stats(players, league_data):
    logging.info("Calculating league stats...")
    for season in all_seasons:
        league_data[season]["total_players"] = len(
            load_data("filtered_players.json", "data"))

    for player in players:
        for season in player["seasons"]:
            league_data[season["season"]
                        ]["all_players_effective_total_points"] += season["effective_total_points"]
            league_data[season["season"]
                        ]["all_players_minutes"] += season["minutes"]

    for season in all_seasons:
        if league_data[season]["total_players"] > 0:
            league_data[season]["avg_effective_total_points_per_player"] = league_data[season][
                "all_players_effective_total_points"] / league_data[season]["total_players"]
            league_data[season]["avg_minutes_per_player"] = league_data[season]["all_players_minutes"] / \
                league_data[season]["total_players"]
        else:
            league_data[season]["avg_effective_total_points_per_player"] = 0
            league_data[season]["avg_minutes_per_player"] = 0

        if season == variables.CURRENT_SEASON:
            if next_event > 1:
                league_data[season]["avg_minutes_per_player"] /= (
                    next_event - 1)
            else:
                league_data[season]["avg_minutes_per_player"] = 0
        else:
            league_data[season]["avg_minutes_per_player"] /= 38

    logging.info(f"League stats: {league_data}")
    return league_data


def calculate_player_values(players, league_data, max_fer_points):
    logging.info("Calculating player values...")
    max_value_points = 0
    for player in players:
        player["value_points"] = 0  # Initialize value_points for each player
        for season in player["seasons"]:
            minutes_per_game = safe_divide(
                season["minutes"], season["total_games"])
            if minutes_per_game >= 60:
                player["value_points"] += 4 * season["season_factor"]
            elif minutes_per_game >= league_data[season["season"]]["avg_minutes_per_player"]:
                player["value_points"] += 3 * season["season_factor"]
            elif minutes_per_game > 0:
                player["value_points"] += 2 * season["season_factor"]
        max_value_points = max(max_value_points, player["value_points"])

    logging.info(f"Max FER points: {max_fer_points}")
    logging.info(f"Max value points: {max_value_points}")

    for player in players:
        if max_fer_points > 0:
            player["fer"] /= max_fer_points
        else:
            player["fer"] = 0

        if max_value_points > 0:
            player["value_points"] /= max_value_points
        else:
            player["value_points"] = 0

        value = sum(season.get("value", 0) * season.get("season_factor", 0)
                    for season in player["seasons"])
        player["final_value"] = 53 * value + 27 * player["fer"] + 13.5 * \
            player.get("consistency_overall", 0) + 9.5 * player["value_points"]
        current_season_cost = player["seasons"][0]["now_cost"] if player["seasons"] else 0
        player["final_value_per_cost"] = safe_divide(
            player["final_value"], current_season_cost)

    return players


def save_final_data(players, league_data):
    logging.info("Saving final data...")
    final_players_sorted = sorted(players, key=lambda k: (-k["final_value"]))
    save_data(final_players_sorted, "final_players_sorted.json", "data")
    save_data(league_data, "league_stats.json", "data")


def main():
    logging.info("Starting data processing...")

    if next_event <= 1:
        logging.warning(
            "The season hasn't started yet. Some calculations may not be meaningful.")

    league_data = initialize_league_data()
    teams, fixtures, players = load_data_files()
    teams, max_fer_points = calculate_fixture_easiness(teams, fixtures)
    players, max_consistency = process_player_data(players, teams, league_data)
    normalize_consistency_and_calculate_value_points(players, max_consistency)
    league_data = calculate_league_stats(players, league_data)
    players = calculate_player_values(players, league_data, max_fer_points)
    save_final_data(players, league_data)
    logging.info("Data processing completed successfully.")


if __name__ == "__main__":
    main()
