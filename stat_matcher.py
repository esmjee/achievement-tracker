import re
from typing import Any, Optional

AchievementEntry = dict[str, Any]
StatEntry = dict[str, Any]


class StatMatcher:
    STOPWORDS: set[str] = {
        "the", "a", "an", "of", "in", "to", "for", "and", "your", "you", "kill", "kills",
        "killed", "day", "days", "get", "reach", "have", "has", "achievement", "player",
        "stat", "count", "build", "with", "all", "each", "every", "any", "over", "one",
    }

    @classmethod
    def split_into_words(cls, identifier: str) -> set[str]:
        spaced: str = re.sub(r"(?<!^)(?=[A-Z])", " ", identifier).replace("_", " ")
        raw_words: list[str] = re.split(r"[^a-zA-Z]+", spaced.lower())
        words: set[str] = set()
        for raw_word in raw_words:
            if len(raw_word) <= 2 or raw_word in cls.STOPWORDS:
                continue
            words.add(raw_word)
            if raw_word.endswith("s") and len(raw_word) > 3:
                words.add(raw_word[:-1])
        return words

    @staticmethod
    def extract_target_number(text: str) -> Optional[int]:
        match = re.search(r"\d[\d,]*", text)
        if not match:
            return None
        return int(match.group(0).replace(",", ""))

    @classmethod
    def guess_stat_for_achievement(cls, achievement_entry: AchievementEntry, stats: list[StatEntry]) -> Optional[StatEntry]:
        achievement_words: set[str] = (
            cls.split_into_words(achievement_entry["description"]) | cls.split_into_words(achievement_entry["display_name"])
        )
        if not achievement_words:
            return None

        best_stat: Optional[StatEntry] = None
        best_score: int = 0
        second_best_score: int = 0
        for stat_entry in stats:
            stat_words: set[str] = cls.split_into_words(stat_entry["name"]) | cls.split_into_words(stat_entry["display_name"])
            score: int = len(achievement_words & stat_words)
            if score > best_score:
                second_best_score = best_score
                best_score = score
                best_stat = stat_entry
            elif score > second_best_score:
                second_best_score = score

        if best_stat is not None and best_score > 0 and best_score > second_best_score:
            return best_stat
        return None
