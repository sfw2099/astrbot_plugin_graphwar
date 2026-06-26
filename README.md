# Graphwar 函数战争

![Version](https://img.shields.io/badge/version-v0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-GPL-orange)

AstrBot 插件：数学函数炮弹对战游戏。输入函数控制弹道轨迹，击杀对手。

改编自 [Graphwar](https://github.com/catabriga/graphwar)

## 安装

在 AstrBot WebUI 插件市场搜索 `astrbot_plugin_graphwar` 安装。

## 游戏规则

- **自由混战 (FFA)**：所有人互相攻击
- **每人 3 条命**：被击中后随机刷新，3 次后死亡离开
- **随时加入**：死亡后可以随时重新加入
- **永不结束**：持续竞技场模式，手动停止
- **击杀记录**：追踪单次存活的最高击杀次数

## 指令

| 指令 | 说明 |
|------|------|
| `/gw start` | 开始游戏（自动加入） |
| `/gw stop` | 停止游戏（仅开局者） |
| `/gw join` | 加入游戏 |
| `/gw quit` | 离开游戏 |
| `/gw fire <函数>` | 开火 |
| `/gw status` | 查看当前局面 |
| `/gw stats` | 击杀排行榜 |
| `/gw mode <normal\|ode1\|ode2>` | 切换模式 |
| `/gw angle <角度>` | 设置发射角度（ode2 模式） |
| `/gw help` | 查看帮助 |

## 游戏模式

### 普通函数 (normal)
输入 `y = f(x)`，函数图像就是弹道轨迹。
```
/gw fire sin(x)*5
/gw fire (x-3)^2/20
```

### 一阶微分方程 (ode1)
输入 `y' = f(x, y)`，RK4 积分求解弹道。
```
/gw fire y'=-y/3
/gw fire y'=sin(x)+2
```

### 二阶微分方程 (ode2)
输入 `y'' = f(x, y, y')`，需先设置发射角度。
```
/gw angle 30
/gw fire y''=-y+y'
```

## 函数语法

### 运算符
`+ - * / ^`

### 函数
`sqrt() log() ln() abs() sin() cos() tan() exp()`

### 示例
```
sin(x)*5
(x^2)/50
ln(abs(x))
1/(x+2)
2*sin(x/20)*5
```

## 配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| turn_time | 120 | 回合限时(秒) |
| max_lives | 3 | 每人生命次数 |
| terrain_refresh_turns | 10 | 地形刷新回合数 |
| default_mode | normal | 默认游戏模式 |
| image_width | 770 | 渲染图片宽度 |
| image_height | 450 | 渲染图片高度 |

## License

GPL-3.0
