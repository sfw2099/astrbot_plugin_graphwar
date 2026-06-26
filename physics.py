import math
from .constants import (
    PLANE_LENGTH, PLANE_HEIGHT, PLANE_GAME_LENGTH,
    STEP_SIZE, FUNC_MAX_STEPS,
    FUNC_MAX_STEP_DISTANCE_SQUARED, FUNC_MIN_X_STEP_DISTANCE,
    SOLDIER_RADIUS, MODE_NORMAL, MODE_ODE1, MODE_ODE2,
)
from .function_parser import CompiledFunction


def plane_to_game(px, py):
    gx = PLANE_GAME_LENGTH * (px - PLANE_LENGTH / 2) / PLANE_LENGTH
    gy = -PLANE_GAME_LENGTH * (py - PLANE_HEIGHT / 2) / PLANE_LENGTH
    return gx, gy


def game_to_plane(gx, gy):
    px = PLANE_LENGTH * gx / PLANE_GAME_LENGTH + PLANE_LENGTH / 2
    py = -PLANE_LENGTH * gy / PLANE_GAME_LENGTH + PLANE_HEIGHT / 2
    return px, py


def _rk4_step(func, x, y, h):
    k1 = func(x, y)
    k2 = func(x + h / 2, y + h * k1 / 2)
    k3 = func(x + h / 2, y + h * k2 / 2)
    k4 = func(x + h, y + h * k3)
    return y + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6


def _rk4_system_step(f1, f2, x, y, yp, h):
    k1y = f1(x, y, yp)
    k1yp = f2(x, y, yp)
    k2y = f1(x + h / 2, y + h * k1y / 2, yp + h * k1yp / 2)
    k2yp = f2(x + h / 2, y + h * k1y / 2, yp + h * k1yp / 2)
    k3y = f1(x + h / 2, y + h * k2y / 2, yp + h * k2yp / 2)
    k3yp = f2(x + h / 2, y + h * k2y / 2, yp + h * k2yp / 2)
    k4y = f1(x + h, y + h * k3y, yp + h * k3yp)
    k4yp = f2(x + h, y + h * k3y, yp + h * k3yp)
    ny = y + h * (k1y + 2 * k2y + 2 * k3y + k4y) / 6
    nyp = yp + h * (k1yp + 2 * k2yp + 2 * k3yp + k4yp) / 6
    return ny, nyp


def simulate_trajectory(func, start_px, start_py, mode, terrain, soldiers, shooter_id, angle_deg=0):
    """Simulate a function shot and return (trajectory_points, hit_soldiers, end_point).

    Args:
        func: CompiledFunction
        start_px, start_py: shooter soldier pixel position
        mode: MODE_NORMAL / MODE_ODE1 / MODE_ODE2
        terrain: Terrain object with collide_point(px, py)
        soldiers: list of dicts: {id, px, py, alive, color}
        shooter_id: id of the shooting soldier (skip self)
        angle_deg: firing angle (only used in ODE2 mode)

    Returns:
        (points: list of (px,py), hits: list of soldier_ids, end: (px,py) or None)
    """
    gx0, gy0 = plane_to_game(start_px, start_py)

    if mode == MODE_NORMAL:
        offset = gy0 - func.evaluate(gx0, 0, 0)
        if math.isnan(offset) or math.isinf(offset):
            return [(start_px, start_py)], [], (start_px, start_py)

        def get_y(x):
            v = func.evaluate(x, 0, 0)
            if math.isnan(v) or math.isinf(v):
                return float("nan")
            return v + offset

        dx = STEP_SIZE
        x = gx0 + dx * 0.5
        y = get_y(x)

    elif mode == MODE_ODE1:
        def deriv(x, y):
            v = func.evaluate(x, y, 0)
            if math.isnan(v) or math.isinf(v):
                return 0.0
            return v

        x = gx0
        y = gy0
        dx = STEP_SIZE

    elif mode == MODE_ODE2:
        angle_rad = math.radians(angle_deg)
        yp0 = math.tan(angle_rad)

        def f_y(x, y, yp):
            return yp

        def f_yp(x, y, yp):
            v = func.evaluate(x, y, yp)
            if math.isnan(v) or math.isinf(v):
                return 0.0
            return v

        x = gx0
        y = gy0
        yp = yp0
        dx = STEP_SIZE
    else:
        return [(start_px, start_py)], [], (start_px, start_py)

    points = [(start_px, start_py)]
    hit_ids = set()
    step_count = 0
    last_end = None

    while step_count < FUNC_MAX_STEPS:
        step_count += 1

        if mode == MODE_NORMAL:
            nx = x + dx
            ny = get_y(nx)
            if math.isnan(ny) or math.isinf(ny):
                break
        elif mode == MODE_ODE1:
            nx = x + dx
            ny = _rk4_step(deriv, x, y, dx)
        elif mode == MODE_ODE2:
            nx = x + dx
            ny, nyp = _rk4_system_step(f_y, f_yp, x, y, yp, dx)
            yp = nyp

        if math.isnan(ny) or math.isinf(ny):
            break

        dy_sq = (ny - y) ** 2
        if dy_sq > FUNC_MAX_STEP_DISTANCE_SQUARED and abs(nx - x) < FUNC_MIN_X_STEP_DISTANCE:
            dx *= 0.5
            if dx < FUNC_MIN_X_STEP_DISTANCE:
                break
            continue

        x = nx
        y = ny

        if abs(x) > PLANE_GAME_LENGTH / 2 + 5:
            break
        if abs(y) > PLANE_GAME_LENGTH * 0.7:
            break

        px, py = game_to_plane(x, y)

        if px < 0 or px >= PLANE_LENGTH or py < 0 or py >= PLANE_HEIGHT:
            break

        if terrain.collide_point(int(px), int(py)):
            points.append((px, py))
            last_end = (px, py)
            break

        for s in soldiers:
            if not s.get("alive", False):
                continue
            if s["id"] == shooter_id:
                continue
            sdx = px - s["px"]
            sdy = py - s["py"]
            if sdx * sdx + sdy * sdy < SOLDIER_RADIUS * SOLDIER_RADIUS:
                if s["id"] not in hit_ids:
                    hit_ids.add(s["id"])

        points.append((px, py))
        last_end = (px, py)

    return points, list(hit_ids), last_end


def compute_start_angle(func, start_px, start_py, mode):
    """Compute the initial firing angle for normal/ode1 modes."""
    if mode == MODE_ODE2:
        return 0.0

    gx0, gy0 = plane_to_game(start_px, start_py)

    if mode == MODE_NORMAL:
        offset = gy0 - func.evaluate(gx0, 0, 0)
        if math.isnan(offset) or math.isinf(offset):
            return 0.0
        gx1 = gx0 + 0.01
        gy1 = func.evaluate(gx1, 0, 0) + offset
    elif mode == MODE_ODE1:
        d = func.evaluate(gx0, gy0, 0)
        if math.isnan(d) or math.isinf(d):
            return 0.0
        gx1 = gx0 + 0.01
        gy1 = gy0 + d * 0.01
    else:
        return 0.0

    if math.isnan(gy1) or math.isinf(gy1):
        return 0.0

    return math.degrees(math.atan2(gy1 - gy0, gx1 - gx0))
