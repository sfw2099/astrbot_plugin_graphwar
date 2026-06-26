import os
import io
import asyncio
import time

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger, AstrBotConfig

try:
    from astrbot.api.all import Plain, Image, MessageChain
except ImportError:
    from astrbot.api.message_components import Plain, Image
    from astrbot.api.event import MessageChain

from .game import Game
from .renderer import render_game, render_to_file
from .stats import StatsManager
from .constants import MODE_NORMAL, MODE_NAMES, DEFAULT_MAX_LIVES, DEFAULT_TURN_TIME, DEFAULT_BOT_COUNT


@register("astrbot_plugin_graphwar", "ALin", "函数战争 - 数学函数炮弹对战游戏", "0.1.0")
class GraphWarPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config
        self.data_dir = StarTools.get_data_dir("astrbot_plugin_graphwar")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.stats = StatsManager(str(self.data_dir))
        self.games: dict[str, Game] = {}
        self._timeout_tasks: dict[str, asyncio.Task] = {}
        cfg = config or {}
        self.max_lives = cfg.get("max_lives", DEFAULT_MAX_LIVES)
        self.turn_time = cfg.get("turn_time", DEFAULT_TURN_TIME)
        self.terrain_refresh = cfg.get("terrain_refresh_turns", 10)
        self.default_mode = cfg.get("default_mode", MODE_NORMAL)
        self.bot_count = cfg.get("bot_count", DEFAULT_BOT_COUNT)
        logger.info(f"[graphwar] plugin loaded, data_dir={self.data_dir}")

    def _get_game(self, group_id):
        return self.games.get(group_id)

    def _get_or_create_game(self, group_id):
        if group_id not in self.games:
            self.games[group_id] = Game(
                group_id=group_id, max_lives=self.max_lives,
                turn_time=self.turn_time, terrain_refresh_turns=self.terrain_refresh,
                mode=self.default_mode, stats_manager=self.stats,
                bot_count=self.bot_count,
            )
        return self.games[group_id]

    def _render_to_file(self, game):
        data = game.get_render_data()
        img = render_game(data["terrain"], data["players"], data["current_player_id"],
                          data["trajectory"], data["mode"], data["turn_info"],
                          func_str=data.get("func_str", ""))
        path = str(self.data_dir / f"board_{game.group_id}.png")
        render_to_file(img, path)
        return path

    async def _send_image(self, event, game, text=""):
        path = self._render_to_file(game)
        if text:
            yield event.chain_result([Image.fromFileSystem(path), Plain(text)])
        else:
            yield event.image_result(path)

    def _start_timeout_monitor(self, group_id):
        if group_id in self._timeout_tasks:
            self._timeout_tasks[group_id].cancel()

        async def _monitor():
            while True:
                await asyncio.sleep(5)
                game = self.games.get(group_id)
                if game is None or not game.running:
                    break
                if game.is_turn_expired():
                    cp = game.current_player()
                    if cp:
                        await self._send_group_msg(group_id, f"超时！{cp['name']} 被跳过")
                    game.advance_turn()
                    await self._notify_turn(group_id)
                elif game.turn_time_remaining() == 30:
                    cp = game.current_player()
                    if cp:
                        await self._send_group_msg(group_id, f"警告：{cp['name']} 还剩 30 秒")

        self._timeout_tasks[group_id] = asyncio.create_task(_monitor())

    async def _send_group_msg(self, group_id, text):
        try:
            from astrbot.api.event import MessageChain as MC
            from astrbot.api.message_components import Plain as P
            umo = f"aiocqhttp:{group_id}"
            await self.context.send_message(umo, MC([P(text)]))
        except Exception as e:
            logger.warning(f"[graphwar] send msg: {e}")

    async def _notify_turn(self, group_id):
        game = self.games.get(group_id)
        if not game or not game.running:
            return
        cp = game.current_player()
        if not cp:
            return
        path = self._render_to_file(game)
        try:
            from astrbot.api.event import MessageChain as MC
            from astrbot.api.message_components import Plain as P, Image as Img
            umo = f"aiocqhttp:{group_id}"
            msg = (f"轮到: {cp['name']} | 生命:{cp['lives']} 击杀:{cp['kills']}\n"
                   f"输入 /gw fire <函数> | 剩余:{game.turn_time_remaining()}秒")
            await self.context.send_message(umo, MC([Img.fromFileSystem(path), P(msg)]))
        except Exception as e:
            logger.warning(f"[graphwar] notify: {e}")

    # ==================== Command Router ====================

    @filter.command("gw", alias={"graphwar"})
    async def gw_command(self, event: AstrMessageEvent):
        raw = event.message_str.strip()
        parts = raw.split(None, 2)
        if len(parts) < 2:
            async for r in self._show_help(event):
                yield r
            return
        sub = parts[1].lower()
        rest = parts[2] if len(parts) > 2 else ""
        gid = str(event.get_group_id()) if event.get_group_id() else ""
        if not gid:
            yield event.plain_result("此功能仅在群聊中可用")
            return
        handlers = {
            "start": self._cmd_start, "stop": self._cmd_stop,
            "join": self._cmd_join, "quit": self._cmd_quit,
            "fire": self._cmd_fire, "f": self._cmd_fire,
            "status": self._cmd_status, "s": self._cmd_status,
            "stats": self._cmd_stats, "help": self._show_help,
            "mode": self._cmd_mode, "angle": self._cmd_angle,
            "botstart": self._cmd_botstart,
        }
        h = handlers.get(sub)
        if h:
            async for r in h(event, gid, rest):
                yield r
        else:
            yield event.plain_result(f"未知指令: {sub}，输入 /gw help 查看帮助")

    async def _cmd_start(self, event, gid, rest):
        game = self._get_game(gid)
        if game and game.running:
            yield event.plain_result("游戏进行中！输入 /gw join 加入")
            return
        game = self._get_or_create_game(gid)
        uid = str(event.get_sender_id())
        name = event.get_sender_name() or f"user({uid})"
        game.start(uid, name)
        if game.mode == "bot":
            game.enable_bots()
        self._start_timeout_monitor(gid)
        async for r in self._send_image(event, game):
            yield r
        yield event.plain_result(
            f"游戏开始！模式:{MODE_NAMES.get(game.mode)} 生命:{game.max_lives}\n"
            f"/gw join 加入 | /gw fire <函数> 发射"
        )

    async def _cmd_botstart(self, event, gid, rest):
        game = self._get_game(gid)
        if game and game.running:
            yield event.plain_result("游戏进行中！请等待当前游戏结束")
            return
        game = self._get_or_create_game(gid)
        game.mode = "bot"
        uid = str(event.get_sender_id())
        name = event.get_sender_name() or f"user({uid})"
        game.start(uid, name)
        game.enable_bots()
        self._start_timeout_monitor(gid)
        async for r in self._send_image(event, game):
            yield r
        yield event.plain_result(
            f"人机模式开始！AI球数量:{game.bot_count} 生命:{game.max_lives}\n"
            f"/gw join 加入 | /gw fire <函数> 发射"
        )

    async def _cmd_stop(self, event, gid, rest):
        game = self._get_game(gid)
        if not game or not game.running:
            yield event.plain_result("当前没有游戏进行")
            return
        uid = str(event.get_sender_id())
        if uid != game.started_by:
            yield event.plain_result("只有发起者可以结束游戏")
            return
        game.stop()
        if gid in self._timeout_tasks:
            self._timeout_tasks[gid].cancel()
            del self._timeout_tasks[gid]
        yield event.plain_result("游戏已结束！")

    async def _cmd_join(self, event, gid, rest):
        game = self._get_game(gid)
        if not game or not game.running:
            yield event.plain_result("当前没有游戏，输入 /gw start 开始")
            return
        uid = str(event.get_sender_id())
        name = event.get_sender_name() or f"user({uid})"
        ok, msg = game.join(uid, name)
        if not ok:
            yield event.plain_result(msg)
            return
        yield event.plain_result(f"{name} 加入了游戏！生命:{game.max_lives}")

    async def _cmd_quit(self, event, gid, rest):
        game = self._get_game(gid)
        if not game:
            yield event.plain_result("no game")
            return
        uid = str(event.get_sender_id())
        ok, msg = game.quit(uid)
        yield event.plain_result(f"{msg}，已退出游戏" if msg else "已退出游戏")

    async def _cmd_fire(self, event, gid, rest):
        game = self._get_game(gid)
        if not game or not game.running:
            yield event.plain_result("当前没有游戏进行")
            return
        if not rest.strip():
            yield event.plain_result("用法: /gw fire <函数>")
            return
        uid = str(event.get_sender_id())
        result, err = game.fire(uid, rest.strip())
        if err:
            yield event.plain_result(err)
            return
        hits = result.get("hit_names", [])
        hit_text = f" 命中: {', '.join(hits)}" if hits else " 未命中！"
        async for r in self._send_image(event, game, f"{result['shooter_name']} fired: {result['func_str']}{hit_text}"):
            yield r
        game.advance_turn()
        await self._notify_turn(gid)

    async def _cmd_status(self, event, gid, rest):
        game = self._get_game(gid)
        if not game or not game.running:
            yield event.plain_result("当前没有游戏进行")
            return
        async for r in self._send_image(event, game):
            yield r

    async def _cmd_stats(self, event, gid, rest):
        lb = self.stats.get_leaderboard(10)
        if not lb:
            yield event.plain_result("暂无统计数据")
            return
        lines = ["=== 击杀排行榜 ==="]
        for i, p in enumerate(lb, 1):
            lines.append(f"{i}. {p.get('name','?')} | 最高连杀:{p.get('max_kill_streak',0)} | 总击杀:{p.get('total_kills',0)}")
        uid = str(event.get_sender_id())
        ps = self.stats.get_player_stats(uid)
        lines.append(f"\n个人最佳: 连杀 {ps.get('max_kill_streak',0)} | 总击杀 {ps.get('total_kills',0)}")
        yield event.plain_result("\n".join(lines))

    async def _cmd_mode(self, event, gid, rest):
        game = self._get_game(gid)
        if not game or not game.running:
            yield event.plain_result("当前没有游戏进行")
            return
        mode = rest.strip().lower()
        if mode not in ("normal", "ode1", "ode2"):
            yield event.plain_result(f"当前模式: {game.mode} | 可选: normal, ode1, ode2")
            return
        game.set_mode(mode)
        yield event.plain_result(f"模式已切换: {MODE_NAMES.get(mode)}")

    async def _cmd_angle(self, event, gid, rest):
        game = self._get_game(gid)
        if not game or not game.running:
            yield event.plain_result("当前没有游戏进行")
            return
        try:
            angle = int(rest.strip())
        except ValueError:
            yield event.plain_result("用法: /gw angle <角度>")
            return
        uid = str(event.get_sender_id())
        game.set_angle(uid, angle)
        yield event.plain_result(f"角度已设为 {angle} 度")

    async def _show_help(self, event, gid="", rest=""):
        help_text = (
            "=== 函数战争 帮助 ===\n"
            "/gw start — 开始游戏（自动加入）\n"
            "/gw botstart — 开始人机对战（AI球自动刷新）\n"
            "/gw stop — 结束游戏（仅发起者）\n"
            "/gw join — 加入游戏\n"
            "/gw quit — 退出游戏\n"
            "/gw fire <函数> — 发射炮弹（写函数表达式）\n"
            "/gw status / /gw s — 查看当前棋盘\n"
            "/gw stats — 击杀排行榜\n"
            "/gw mode <normal|ode1|ode2> — 切换模式\n"
            "  normal: 普通模式，直接写函数\n"
            "  ode1: 一阶微分模式\n"
            "  ode2: 二阶微分模式（需先设角度）\n"
            "/gw angle <角度> — 设置发射角度（ode2 模式）\n"
            "\n函数示例：\n"
            "  普通: sin(x)*5 或 y=sin(x)*5\n"
            "  一阶: y'=-y/3\n"
            "  二阶: y''=-y+y'（先 /gw angle 45）\n"
            "\n运算符: + - * / ^\n"
            "函数: sqrt log ln abs sin cos tan exp\n"
        )
        yield event.plain_result(help_text)

    async def terminate(self):
        for task in tuple(self._timeout_tasks.values()):
            task.cancel()
        self._timeout_tasks.clear()
