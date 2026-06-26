# Graphwar 函数战争

![Version](https://img.shields.io/badge/version-v0.2.9-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-GPL-orange)

AstrBot 插件：数学函数炮弹对战游戏。输入函数控制弹道轨迹，击杀对手。

改编自 [Graphwar](https://github.com/catabriga/graphwar)

---

## 游戏规则

- **自由混战 (FFA)**：所有人互相攻击
- **每人 N 条命**（可配）：被击中后随机刷新，用完离开
- **随时加入**：游戏进行中可随时 `/gw join`
- **地形刷新**：每 N 回合重新生成地形并重定位玩家
- **人机模式**：`/gw botstart` 开启，AI 球自动刷新
- **击杀排行榜**：`/gw stats` 查看战绩

---

## 指令

| 指令 | 说明 |
|------|------|
| `/gw start` | 开始游戏（自动加入） |
| `/gw botstart` | 开始人机对战（AI 球自动刷新） |
| `/gw stop` | 停止游戏（仅开局者） |
| `/gw join` | 加入游戏 |
| `/gw quit` | 离开游戏 |
| `/gw fire <函数>` | 发射炮弹 |
| `/gw status` / `/gw s` | 查看当前局面 |
| `/gw stats` | 击杀排行榜 |
| `/gw mode <normal\|ode1\|ode2>` | 切换函数模式 |
| `/gw angle <角度>` | 设置发射角度（ode2 模式） |
| `/gw help` | 查看帮助 |

---

## 游戏模式

### 普通函数 (normal)
输入 `y = f(x)`，函数图像就是弹道轨迹。弹道从起点向左右双向延伸。
```
sin(x)*5
(x-3)^2/20
(x-3)^-2
12x
```

### 一阶微分方程 (ode1)
输入 `y' = f(x,y)`，RK4 积分求解。
```
y'=-y/3
y'=sin(x)+2
```

### 二阶微分方程 (ode2)
输入 `y'' = f(x,y,y')`，需先设置发射角度。
```
/gw angle 30
/gw fire y''=-y+y'
```

---

## 函数语法

### 运算符
`+ - * / ^`

### 函数
`sqrt() log() ln() abs() sin() cos() tan() exp()`

### 常量
`e pi`

### 示例
```
sin(x)*5
(x^2)/50
ln(abs(x))
1/(x+2)
(x-3)^(-2)
```

---

## 配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `turn_time` | int | 120 | 回合限时（秒） |
| `max_lives` | int | 3 | 每人生命次数 |
| `terrain_refresh_turns` | int | 10 | 地形刷新回合数 |
| `default_mode` | string | normal | 默认游戏模式 |
| `bot_count` | int | 3 | 人机模式 AI 球数量 |
| `explosion_radius` | int | 18 | 爆炸破坏半径（像素） |
| `show_coords` | bool | false | 显示坐标数轴和网格 |
| `image_width` | int | 770 | 渲染图片宽度 |
| `image_height` | int | 450 | 渲染图片高度 |

---

## License

GPL-3.0
