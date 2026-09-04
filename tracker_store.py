import json
import os
from typing import Any, Iterator, Optional

CONFIG_PATH: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker_config.json")

PinEntry = dict[str, Any]
GameEntry = dict[str, Any]


class TrackerConfig:
    def __init__(self, data: Optional[dict[str, Any]] = None) -> None:
        self.data: dict[str, Any] = data if data is not None else {}
        self.data.setdefault("games", [])
        self.data.setdefault("pinned", [])
        self.data.setdefault("last_selected_app_id", None)

    @classmethod
    def load(cls) -> "TrackerConfig":
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as file:
                    return cls(json.load(file))
            except (json.JSONDecodeError, OSError):
                pass
        return cls()

    def save(self) -> None:
        with open(CONFIG_PATH, "w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=2)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self.data

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    @property
    def games(self) -> list[GameEntry]:
        return self.data["games"]

    @property
    def pinned(self) -> list[PinEntry]:
        return self.data["pinned"]

    def add_game(self, app_id: int, name: str) -> None:
        for game_entry in self.games:
            if game_entry["app_id"] == app_id:
                game_entry["name"] = name
                return
        self.games.append({"app_id": app_id, "name": name})

    def remove_game(self, app_id: int) -> None:
        self.data["games"] = [game_entry for game_entry in self.games if game_entry["app_id"] != app_id]
        self.data["pinned"] = [pin_entry for pin_entry in self.pinned if pin_entry["app_id"] != app_id]

    def is_achievement_pinned(self, app_id: int, api_name: str) -> bool:
        return any(
            pin_entry for pin_entry in self.pinned
            if pin_entry["type"] == "achievement" and pin_entry["app_id"] == app_id and pin_entry["api_name"] == api_name
        )

    def pin_achievement(
        self,
        app_id: int,
        game_name: str,
        api_name: str,
        display_name: str,
        description: str,
        stat_name: Optional[str] = None,
        target: Optional[int] = None,
    ) -> None:
        if self.is_achievement_pinned(app_id, api_name):
            return
        self.pinned.append({
            "type": "achievement",
            "app_id": app_id,
            "game_name": game_name,
            "api_name": api_name,
            "display_name": display_name,
            "description": description,
            "stat_name": stat_name,
            "target": target,
        })

    def get_pinned_achievement(self, app_id: int, api_name: str) -> Optional[PinEntry]:
        return next(
            (pin_entry for pin_entry in self.pinned
             if pin_entry["type"] == "achievement" and pin_entry["app_id"] == app_id and pin_entry["api_name"] == api_name),
            None,
        )

    def link_achievement_stat(self, app_id: int, api_name: str, stat_name: str, target: int) -> None:
        pin_entry = self.get_pinned_achievement(app_id, api_name)
        if pin_entry is not None:
            pin_entry["stat_name"] = stat_name
            pin_entry["target"] = target

    def unpin_achievement(self, app_id: int, api_name: str) -> None:
        self.data["pinned"] = [
            pin_entry for pin_entry in self.pinned
            if not (pin_entry["type"] == "achievement" and pin_entry["app_id"] == app_id and pin_entry["api_name"] == api_name)
        ]

    def is_stat_pinned(self, app_id: int, stat_name: str) -> bool:
        return any(
            pin_entry for pin_entry in self.pinned
            if pin_entry["type"] == "stat_goal" and pin_entry["app_id"] == app_id and pin_entry["stat_name"] == stat_name
        )

    def pin_stat_goal(self, app_id: int, game_name: str, stat_name: str, display_name: str, target: int) -> None:
        self.pinned.append({
            "type": "stat_goal",
            "app_id": app_id,
            "game_name": game_name,
            "stat_name": stat_name,
            "display_name": display_name,
            "target": target,
        })

    def unpin_stat_goal(self, app_id: int, stat_name: str) -> None:
        self.data["pinned"] = [
            pin_entry for pin_entry in self.pinned
            if not (pin_entry["type"] == "stat_goal" and pin_entry["app_id"] == app_id and pin_entry["stat_name"] == stat_name)
        ]
