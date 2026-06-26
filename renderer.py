import os
import io
from PIL import Image, ImageDraw, ImageFont
from .constants import (
    PLANE_LENGTH, PLANE_HEIGHT, SOLDIER_RADIUS,
    EXPLOSION_RADIUS, PLAYER_COLORS, MODE_NAMES,
)


_FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "STZHONGS.TTF")

def _get_font(size=16):
    if os.path.exists(_FONT_PATH):
        try:
            return ImageFont.truetype(_FONT_PATH, size)
        except Exception:
            pass
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_game(terrain, players, current_player_id, trajectory=None,
                mode="normal", turn_info="", error_msg=None, func_str=""):
    """Render the game state to a PNG image.

    Args:
        terrain: Terrain object
        players: list of player dicts {id, name, px, py, alive, lives, color, kills}
        current_player_id: id of current turn player
        trajectory: list of (px, py) points or None
        mode: game mode string
        turn_info: info text for top bar
        error_msg: error message to display
        func_str: last fired function string to display

    Returns:
        PIL Image object
    """
    margin = 40
    img_w = PLANE_LENGTH + margin * 2
    img_h = PLANE_HEIGHT + margin * 2 + 60

    img = Image.new("RGB", (img_w, img_h), (30, 30, 35))
    draw = ImageDraw.Draw(img)

    play_x = margin
    play_y = margin + 30

    draw.rectangle(
        [play_x, play_y, play_x + PLANE_LENGTH, play_y + PLANE_HEIGHT],
        fill=(245, 245, 248),
    )

    for x in range(PLANE_LENGTH):
        for y in range(PLANE_HEIGHT):
            if terrain.solid[x][y]:
                img.putpixel((play_x + x, play_y + y), (50, 50, 55))

    cx = play_x + PLANE_LENGTH // 2
    cy = play_y + PLANE_HEIGHT // 2
    draw.line([(cx, play_y), (cx, play_y + PLANE_HEIGHT)], fill=(200, 200, 210), width=1)
    draw.line([(play_x, cy), (play_x + PLANE_LENGTH, cy)], fill=(200, 200, 210), width=1)

    font_small = _get_font(14)
    font_med = _get_font(18)
    font_large = _get_font(22)

    for label, lx, ly in [("-25", play_x + 5, cy + 3), ("25", play_x + PLANE_LENGTH - 20, cy + 3),
                          ("15", cx + 3, play_y + 3), ("-15", cx + 3, play_y + PLANE_HEIGHT - 18)]:
        draw.text((lx, ly), label, fill=(180, 180, 190), font=font_small)

    if trajectory and len(trajectory) > 1:
        traj_color = (255, 60, 60)
        for i in range(len(trajectory) - 1):
            x1, y1 = trajectory[i]
            x2, y2 = trajectory[i + 1]
            draw.line(
                [(play_x + x1, play_y + y1), (play_x + x2, play_y + y2)],
                fill=traj_color, width=4,
            )

    for p in players:
        if not p.get("alive", False) and not p.get("spectating", False):
            continue
        px = p["px"]
        py = p["py"]
        color = p.get("color", (100, 100, 100))
        is_current = p["id"] == current_player_id

        draw.ellipse(
            [play_x + px - SOLDIER_RADIUS, play_y + py - SOLDIER_RADIUS,
             play_x + px + SOLDIER_RADIUS, play_y + py + SOLDIER_RADIUS],
            fill=color, outline=(255, 255, 255) if is_current else (0, 0, 0),
            width=3 if is_current else 1,
        )

        name = p.get("name", "?")[:8]
        lives = p.get("lives", 0)
        kills = p.get("kills", 0)

        label_y = play_y + py - SOLDIER_RADIUS - 16
        if label_y < play_y + 2:
            label_y = play_y + py + SOLDIER_RADIUS + 2

        label = f"{name}[{lives}]k{kills}"
        draw.text((play_x + px - 20, label_y), label, fill=color, font=font_small)

        if is_current:
            draw.text((play_x + px - 5, label_y - 16), "▼", fill=(255, 200, 50), font=font_med)

    title = f"函数战争 | {MODE_NAMES.get(mode, mode)} | {turn_info}"
    draw.text((margin, 8), title, fill=(220, 220, 230), font=font_med)

    if func_str:
        draw.text((margin, 27), f"f(x) = {func_str}", fill=(180, 220, 255), font=font_small)

    if error_msg:
        draw.text((margin, img_h - 25), error_msg, fill=(255, 100, 100), font=font_small)

    return img


def render_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def render_to_file(img, path):
    img.save(path, format="PNG")
    return path
