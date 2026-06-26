import random
import math
from .constants import (
    PLANE_LENGTH, PLANE_HEIGHT,
    NUM_CIRCLES_MEAN, NUM_CIRCLES_STD,
    CIRCLE_MEAN_RADIUS, CIRCLE_STD_RADIUS,
    EXPLOSION_RADIUS, SOLDIER_RADIUS,
)


class Terrain:
    def __init__(self, width=PLANE_LENGTH, height=PLANE_HEIGHT):
        self.width = width
        self.height = height
        self.solid = [[False] * height for _ in range(width)]
        self.circles = []

    def generate(self):
        for x in range(self.width):
            for y in range(self.height):
                self.solid[x][y] = False
        self.circles.clear()

        n = max(1, int(random.gauss(NUM_CIRCLES_MEAN, NUM_CIRCLES_STD)))
        for _ in range(n):
            cx = random.randint(0, self.width - 1)
            cy = random.randint(0, self.height - 1)
            r = max(5, int(random.gauss(CIRCLE_MEAN_RADIUS, CIRCLE_STD_RADIUS)))
            self._fill_circle(cx, cy, r, True)
            self.circles.append((cx, cy, r))

    def _fill_circle(self, cx, cy, radius, value):
        r2 = radius * radius
        x0 = max(0, cx - radius)
        x1 = min(self.width - 1, cx + radius)
        y0 = max(0, cy - radius)
        y1 = min(self.height - 1, cy + radius)
        for x in range(x0, x1 + 1):
            dx = x - cx
            for y in range(y0, y1 + 1):
                dy = y - cy
                if dx * dx + dy * dy <= r2:
                    self.solid[x][y] = value

    def collide_point(self, px, py):
        if px < 0 or px >= self.width or py < 0 or py >= self.height:
            return True
        return self.solid[px][py]

    def explode(self, px, py, radius=EXPLOSION_RADIUS):
        self._fill_circle(int(px), int(py), radius, False)

    def is_valid_spawn(self, px, py, existing_spawns, min_dist=20):
        for ex, ey in existing_spawns:
            dx = px - ex
            dy = py - ey
            if dx * dx + dy * dy < min_dist * min_dist:
                return False

        check_r = SOLDIER_RADIUS + 2
        x0 = max(0, int(px) - check_r)
        x1 = min(self.width - 1, int(px) + check_r)
        y0 = max(0, int(py) - check_r)
        y1 = min(self.height - 1, int(py) + check_r)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                if self.solid[x][y]:
                    dx = x - px
                    dy = y - py
                    if dx * dx + dy * dy < check_r * check_r:
                        return False
        return True

    def find_spawn(self, existing_spawns, left_half=False, max_tries=200):
        x_min = 10 if left_half else self.width // 2 + 10
        x_max = self.width // 2 - 10 if left_half else self.width - 10

        if x_min >= x_max:
            x_min, x_max = 10, self.width - 10

        for _ in range(max_tries):
            px = random.randint(x_min, x_max)
            py = random.randint(20, self.height - 20)
            if self.is_valid_spawn(px, py, existing_spawns):
                return px, py
        return None

    def find_random_spawn(self, existing_spawns, max_tries=300):
        for _ in range(max_tries):
            px = random.randint(20, self.width - 20)
            py = random.randint(20, self.height - 20)
            if self.is_valid_spawn(px, py, existing_spawns):
                return px, py

        for _ in range(max_tries):
            px = random.randint(20, self.width - 20)
            py = random.randint(20, self.height - 20)
            ok = True
            for ex, ey in existing_spawns:
                if (px - ex) ** 2 + (py - ey) ** 2 < 15 * 15:
                    ok = False
                    break
            if ok:
                return px, py
        return None
