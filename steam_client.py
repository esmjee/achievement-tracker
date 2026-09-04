import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class SteamAPIError(Exception):
    pass


class SteamClient:
    def __init__(self, api_key: str, steam_id64: str) -> None:
        self.api_key: str = api_key
        self.steam_id64: str = steam_id64

    @staticmethod
    def _get(url: str) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 403:
                raise SteamAPIError("Access denied (bad API key, or game/profile stats set to private).")
            raise SteamAPIError(f"Steam API returned HTTP {error.code}.")
        except urllib.error.URLError as error:
            raise SteamAPIError(f"Couldn't reach Steam API: {error.reason}")
        except json.JSONDecodeError:
            raise SteamAPIError("Steam API returned an unreadable response.")

    def verify_credentials(self) -> None:
        parameters = urllib.parse.urlencode({"key": self.api_key, "steamids": self.steam_id64})
        url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?{parameters}"
        data = self._get(url)
        players = data.get("response", {}).get("players", [])
        if not players:
            raise SteamAPIError("No Steam profile found for that SteamID64.")

    def get_owned_games(self) -> list[dict[str, Any]]:
        parameters = urllib.parse.urlencode({
            "key": self.api_key,
            "steamid": self.steam_id64,
            "include_appinfo": 1,
            "include_played_free_games": 1,
        })
        url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?{parameters}"
        data = self._get(url)
        games = data.get("response", {}).get("games", [])
        if not games:
            raise SteamAPIError(
                "No games found. Make sure 'Game details' is set to Public in your Steam privacy settings."
            )
        return sorted(
            (
                {"app_id": game_entry.get("appid"), "name": game_entry.get("name") or f"App {game_entry.get('appid')}"}
                for game_entry in games
            ),
            key=lambda game_entry: game_entry["name"].lower(),
        )

    def get_schema(self, app_id: int) -> dict[str, Any]:
        parameters = urllib.parse.urlencode({"key": self.api_key, "appid": app_id})
        url = f"https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/?{parameters}"
        data = self._get(url)
        game = data.get("game", {})
        game_name = game.get("gameName", f"App {app_id}")
        available_game_stats = game.get("availableGameStats", {})

        achievements = [
            {
                "api_name": achievement_entry.get("name"),
                "display_name": achievement_entry.get("displayName") or achievement_entry.get("name"),
                "description": achievement_entry.get("description", ""),
                "hidden": bool(achievement_entry.get("hidden")),
            }
            for achievement_entry in available_game_stats.get("achievements", [])
        ]
        stats = [
            {
                "name": stat_entry.get("name"),
                "display_name": stat_entry.get("displayName") or stat_entry.get("name"),
            }
            for stat_entry in available_game_stats.get("stats", [])
        ]

        if not achievements and not stats:
            raise SteamAPIError("This app has no achievements or stats, or the appid is wrong.")

        return {"game_name": game_name, "achievements": achievements, "stats": stats}

    def get_player_achievements(self, app_id: int) -> dict[str, dict[str, Any]]:
        parameters = urllib.parse.urlencode(
            {"key": self.api_key, "steamid": self.steam_id64, "appid": app_id}
        )
        url = f"https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?{parameters}"
        data = self._get(url)
        player_stats = data.get("playerstats", {})
        if not player_stats.get("success", True):
            raise SteamAPIError(player_stats.get("error", "Steam couldn't return achievements for this profile."))

        result: dict[str, dict[str, Any]] = {}
        for achievement_entry in player_stats.get("achievements", []):
            result[achievement_entry.get("apiname")] = {
                "achieved": bool(achievement_entry.get("achieved")),
                "unlocktime": achievement_entry.get("unlocktime", 0),
            }
        return result

    def get_user_stats(self, app_id: int) -> dict[str, int]:
        parameters = urllib.parse.urlencode(
            {"appid": app_id, "key": self.api_key, "steamid": self.steam_id64}
        )
        url = f"https://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/?{parameters}"
        data = self._get(url)
        stats = data.get("playerstats", {}).get("stats", [])
        return {stat_entry.get("name"): stat_entry.get("value", 0) for stat_entry in stats}
