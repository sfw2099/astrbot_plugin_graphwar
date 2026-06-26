import json
import os
import threading


class StatsManager:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.stats_file = os.path.join(data_dir, "graphwar_stats.json")
        self._lock = threading.Lock()
        self._stats = {}
        self._load()

    def _load(self):
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    self._stats = json.load(f)
            except Exception:
                self._stats = {}
        if "players" not in self._stats:
            self._stats["players"] = {}

    def _save(self):
        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(self._stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[graphwar] stats save error: {e}")

    def _get_player(self, user_id):
        if user_id not in self._stats["players"]:
            self._stats["players"][user_id] = {
                "name": "",
                "max_kill_streak": 0,
                "total_kills": 0,
                "total_deaths": 0,
                "games_played": 0,
            }
        return self._stats["players"][user_id]

    def record_kill(self, user_id, user_name, current_streak):
        with self._lock:
            p = self._get_player(user_id)
            p["name"] = user_name
            p["total_kills"] += 1
            if current_streak > p["max_kill_streak"]:
                p["max_kill_streak"] = current_streak
            self._save()

    def record_death(self, user_id, user_name):
        with self._lock:
            p = self._get_player(user_id)
            p["name"] = user_name
            p["total_deaths"] += 1
            self._save()

    def record_game_join(self, user_id, user_name):
        with self._lock:
            p = self._get_player(user_id)
            p["name"] = user_name
            p["games_played"] += 1
            self._save()

    def get_leaderboard(self, limit=10):
        with self._lock:
            players = list(self._stats["players"].values())
            players.sort(key=lambda x: x.get("max_kill_streak", 0), reverse=True)
            return players[:limit]

    def get_player_stats(self, user_id):
        with self._lock:
            return self._get_player(user_id).copy()
