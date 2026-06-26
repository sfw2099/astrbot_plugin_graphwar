import random
import time
from .constants import (
    DEFAULT_MAX_LIVES, DEFAULT_TURN_TIME, DEFAULT_TERRAIN_REFRESH_TURNS,
    MODE_NORMAL, MODE_BOT, DEFAULT_BOT_COUNT,
    PLAYER_COLORS, BOT_COLORS, SOLDIER_RADIUS,
)
from .terrain import Terrain
from .function_parser import CompiledFunction
from .physics import simulate_trajectory, compute_start_angle


class Game:
    def __init__(self, group_id, max_lives=DEFAULT_MAX_LIVES,
                 turn_time=DEFAULT_TURN_TIME,
                 terrain_refresh_turns=DEFAULT_TERRAIN_REFRESH_TURNS,
                 mode=MODE_NORMAL, stats_manager=None,
                 bot_count=DEFAULT_BOT_COUNT):
        self.group_id = group_id
        self.max_lives = max_lives
        self.turn_time = turn_time
        self.terrain_refresh_turns = terrain_refresh_turns
        self.mode = mode
        self.stats = stats_manager
        self.bot_count = bot_count

        self.terrain = Terrain()
        self.terrain.generate()

        self.players = {}
        self.turn_order = []
        self.current_turn_idx = 0
        self.turn_count = 0
        self.turn_start_time = 0
        self.last_trajectory = None
        self.last_fire_result = None
        self.last_fire_player = None
        self.last_func_str = None
        self.running = False
        self.started_by = None
        self._color_idx = 0
        self._bot_idx = 0
        self.bots_enabled = False

    def _next_color(self):
        c = PLAYER_COLORS[self._color_idx % len(PLAYER_COLORS)]
        self._color_idx += 1
        return c

    def _next_bot_color(self):
        return BOT_COLORS[self._bot_idx % len(BOT_COLORS)]

    def _spawn_bot(self):
        spawns = [(p["px"], p["py"]) for p in self.players.values() if p.get("alive", False)]
        pos = self.terrain.find_random_spawn(spawns)
        if pos is None:
            return None
        bid = f"bot_{self._bot_idx}"
        self._bot_idx += 1
        self.players[bid] = {
            "id": bid, "name": f"AI-{self._bot_idx}",
            "px": pos[0], "py": pos[1],
            "alive": True, "lives": 1,
            "kills": 0, "color": self._next_bot_color(),
            "angle": 0, "total_kills_this_life": 0,
            "is_bot": True,
        }
        return bid

    def enable_bots(self, count=None):
        if count is not None:
            self.bot_count = count
        self.bots_enabled = True
        current_bots = [pid for pid, p in self.players.items() if p.get("is_bot")]
        needed = max(0, self.bot_count - len(current_bots))
        for _ in range(needed):
            self._spawn_bot()

    def disable_bots(self):
        self.bots_enabled = False
        for pid in list(self.players.keys()):
            if self.players[pid].get("is_bot"):
                self.remove_player(pid)

    def _maintain_bots(self):
        if not self.bots_enabled or self.mode != MODE_BOT:
            return
        current_bots = [pid for pid, p in self.players.items()
                        if p.get("is_bot") and p.get("alive", False)]
        needed = max(0, self.bot_count - len(current_bots))
        for _ in range(needed):
            self._spawn_bot()

    def start(self, starter_id, starter_name):
        self.running = True
        self.started_by = starter_id
        self.join(starter_id, starter_name)
        self._rebuild_turn_order()
        self.turn_start_time = time.time()

    def join(self, player_id, player_name):
        if player_id in self.players and self.players[player_id].get("alive", False):
            return False, "你已经在游戏中了"

        spawns = [(p["px"], p["py"]) for p in self.players.values() if p.get("alive", False)]
        pos = self.terrain.find_random_spawn(spawns)
        if pos is None:
            return False, "找不到合适的出生点"

        if player_id not in self.players:
            color = self._next_color()
            self.players[player_id] = {
                "id": player_id, "name": player_name,
                "px": pos[0], "py": pos[1],
                "alive": True, "lives": self.max_lives,
                "kills": 0, "color": color, "angle": 0,
                "total_kills_this_life": 0,
            }
        else:
            p = self.players[player_id]
            p["px"] = pos[0]
            p["py"] = pos[1]
            p["alive"] = True
            p["lives"] = self.max_lives
            p["kills"] = 0
            p["angle"] = 0
            p["total_kills_this_life"] = 0
            p["name"] = player_name

        if player_id not in self.turn_order:
            self.turn_order.append(player_id)

        if self.stats:
            self.stats.record_game_join(player_id, player_name)
        return True, None

    def remove_player(self, player_id):
        if player_id in self.players:
            self.players[player_id]["alive"] = False
        if player_id in self.turn_order:
            self.turn_order.remove(player_id)
            if self.current_turn_idx >= len(self.turn_order):
                self.current_turn_idx = 0

    def quit(self, player_id):
        if player_id not in self.players:
            return False, "你不在游戏中"
        self.remove_player(player_id)
        return True, None

    def stop(self):
        self.running = False
        self.disable_bots()
        self.players.clear()
        self.turn_order.clear()
        self.current_turn_idx = 0

    def current_player(self):
        if not self.turn_order or self.current_turn_idx >= len(self.turn_order):
            return None
        pid = self.turn_order[self.current_turn_idx]
        return self.players.get(pid)

    def _rebuild_turn_order(self):
        self.turn_order = [pid for pid, p in self.players.items()
                           if p.get("alive", False) and not p.get("is_bot")]
        if self.current_turn_idx >= len(self.turn_order):
            self.current_turn_idx = 0

    def advance_turn(self):
        self.turn_count += 1
        if self.turn_count % self.terrain_refresh_turns == 0:
            self.terrain.generate()
            for p in self.players.values():
                if p.get("alive", False):
                    spawns = [(pp["px"], pp["py"]) for pp in self.players.values()
                              if pp.get("alive", False) and pp["id"] != p["id"]]
                    pos = self.terrain.find_random_spawn(spawns)
                    if pos:
                        p["px"], p["py"] = pos

        self._rebuild_turn_order()
        if self.turn_order:
            self.current_turn_idx = (self.current_turn_idx + 1) % len(self.turn_order)
        else:
            self.current_turn_idx = 0
        self.turn_start_time = time.time()
        self.last_trajectory = None
        self.last_func_str = None

    def turn_time_remaining(self):
        elapsed = time.time() - self.turn_start_time
        return max(0, self.turn_time - int(elapsed))

    def is_turn_expired(self):
        return self.turn_time_remaining() <= 0

    def set_angle(self, player_id, angle):
        if player_id not in self.players:
            return False, "你不在游戏中"
        self.players[player_id]["angle"] = angle
        return True, None

    def fire(self, player_id, func_str):
        p = self.current_player()
        if p is None or p["id"] != player_id:
            return None, "现在不是你的回合"

        if not p.get("alive", False):
            return None, "你已经死亡"

        try:
            func = CompiledFunction(func_str)
        except Exception as e:
            return None, f"函数解析失败: {e}"

        soldiers = [
            {"id": pid, "px": pp["px"], "py": pp["py"], "alive": pp.get("alive", False)}
            for pid, pp in self.players.items()
        ]

        angle = p.get("angle", 0)
        phys_mode = self.mode if self.mode != "bot" else MODE_NORMAL
        trajectory, hit_ids, end_point = simulate_trajectory(
            func, p["px"], p["py"], phys_mode,
            self.terrain, soldiers, player_id, angle,
        )

        self.last_trajectory = trajectory
        self.last_fire_player = player_id

        if end_point:
            self.terrain.explode(end_point[0], end_point[1])

        killed_names = []
        for hid in hit_ids:
            victim = self.players.get(hid)
            if victim and victim.get("alive", False):
                victim["lives"] -= 1
                if victim["lives"] <= 0:
                    victim["alive"] = False
                    killed_names.append(victim["name"])
                    if self.stats:
                        self.stats.record_death(hid, victim["name"])
                    if hid in self.turn_order:
                        self.turn_order.remove(hid)
                        if self.current_turn_idx >= len(self.turn_order) and self.turn_order:
                            self.current_turn_idx = 0
                else:
                    spawns = [(pp["px"], pp["py"]) for pp in self.players.values()
                              if pp.get("alive", False) and pp["id"] != hid]
                    pos = self.terrain.find_random_spawn(spawns)
                    if pos:
                        victim["px"], victim["py"] = pos
                    killed_names.append(f"{victim['name']}(剩余{victim['lives']}命)")

                p["kills"] += 1
                p["total_kills_this_life"] += 1
                if self.stats:
                    self.stats.record_kill(player_id, p["name"], p["total_kills_this_life"])

        self._maintain_bots()

        result = {
            "trajectory": trajectory,
            "hit_ids": hit_ids,
            "hit_names": killed_names,
            "end_point": end_point,
            "func_str": func_str,
            "shooter_name": p["name"],
            "kills_this_shot": len(hit_ids),
            "shooter_kills": p["kills"],
        }
        self.last_fire_result = result
        self.last_func_str = func_str
        return result, None

    def get_render_data(self):
        players_list = []
        for pid, p in self.players.items():
            players_list.append({
                "id": pid, "name": p["name"],
                "px": p["px"], "py": p["py"],
                "alive": p.get("alive", False),
                "lives": p.get("lives", 0),
                "kills": p.get("kills", 0),
                "color": p.get("color", (100, 100, 100)),
            })

        cp = self.current_player()
        cp_id = cp["id"] if cp else None
        cp_name = cp["name"] if cp else "无"
        time_left = self.turn_time_remaining()

        turn_info = f"回合 {self.turn_count + 1} | {cp_name} 的回合 | 剩余 {time_left}s"

        return {
            "terrain": self.terrain,
            "players": players_list,
            "current_player_id": cp_id,
            "trajectory": self.last_trajectory,
            "mode": self.mode,
            "turn_info": turn_info,
            "func_str": self.last_func_str or "",
        }

    def alive_count(self):
        return sum(1 for p in self.players.values() if p.get("alive", False))

    def set_mode(self, mode):
        if mode not in ("normal", "ode1", "ode2", "bot"):
            return False
        if mode == MODE_BOT and self.mode != MODE_BOT:
            self.enable_bots()
        elif mode != MODE_BOT and self.mode == MODE_BOT:
            self.disable_bots()
        self.mode = mode
        return True
