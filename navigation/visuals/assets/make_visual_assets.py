#!/usr/bin/env python3
"""Create the hand-authored teaching diagrams and deterministic GIF previews.

Requires Python 3 and Pillow.  Always use a new, explicit output directory:
    python make_visual_assets.py --output-dir C:/Temp/navigation-visuals-new

The SVGs are conceptual drawings, not robot photographs.  The A* preview uses
four-connected unit-cost search with a Manhattan heuristic.  The motion preview
uses an ideal yaw=90 degree body-to-world transform, without real dynamics.
"""

from __future__ import annotations

import argparse
import heapq
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from html import escape

from PIL import Image, ImageDraw, ImageFont


W, H = 800, 420
BG = "#f5f8fc"
WHITE = "#ffffff"
INK = "#233348"
MUTED = "#63758b"
BLUE = "#246bd6"
LIGHT_BLUE = "#dceaff"
ORANGE = "#ed8c24"
LIGHT_ORANGE = "#ffe2bd"
LINE = "#d9e2ed"
GREEN = "#268260"
RED = "#cb4d4d"
FONT = "'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif"


def text(x, y, value, size=22, fill=INK, weight=500, anchor="start"):
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')


def rect(x, y, width, height, fill=WHITE, stroke=LINE, radius=16, sw=2):
    return (f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
            f'rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def path(d, color=BLUE, width=4, dash=None, marker=True):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    if marker:
        extra += f' marker-end="url(#{"orange" if color == ORANGE else "green" if color == GREEN else "red" if color == RED else "blue"})"'
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round"{extra}/>')


def robot(x, y, heading=0, scale=1):
    # Local +x points to the right; SVG screen y is downward.
    return f'''<g transform="translate({x} {y}) rotate({-heading}) scale({scale})">
      <rect x="-24" y="-21" width="48" height="10" rx="4" fill="{INK}"/>
      <rect x="-24" y="11" width="48" height="10" rx="4" fill="{INK}"/>
      <rect x="-23" y="-15" width="46" height="30" rx="9" fill="{BLUE}" stroke="{WHITE}" stroke-width="2"/>
      <circle cx="0" cy="0" r="9" fill="{LIGHT_BLUE}"/>
      <path d="M0 0 H33" stroke="{BLUE}" stroke-width="7" stroke-linecap="round"/>
      <path d="M15 -7 L25 0 L15 7" fill="none" stroke="{WHITE}" stroke-width="3"/>
    </g>'''


def flag(x, y):
    return f'''<path d="M{x} {y + 35} V{y}" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>
      <path d="M{x + 2} {y} L{x + 30} {y + 9} L{x + 2} {y + 18} Z" fill="{ORANGE}"/>'''


def svg(title, description, body):
    markers = "".join(
        f'<marker id="{name}" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0 L10 5 L0 10 Z" fill="{color}"/></marker>'
        for name, color in [("blue", BLUE), ("orange", ORANGE), ("green", GREEN), ("red", RED)]
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="420" viewBox="0 0 800 420" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
  <defs>{markers}</defs>
  <rect width="800" height="420" rx="20" fill="{BG}"/>
  <g font-family="{FONT}">
  {text(28, 44, title, 27, weight=700)}
  {text(772, 72, '合成教学示意', 14, MUTED, anchor='end')}
  {body}
  </g>
</svg>'''


def overview():
    body = rect(28, 88, 406, 272)
    body += '<path d="M225 125 V300" stroke="#233348" stroke-width="26" stroke-linecap="round"/>'
    body += text(245, 220, "墙", 22, MUTED)
    body += path("M85 280 H145 Q163 280 163 300 V321 Q163 335 180 335 H285 Q305 335 305 315 V205 Q305 185 327 185 H362", ORANGE, 5, "8 7")
    body += robot(85, 280, 0, 0.9) + text(60, 328, "起点", 20, BLUE)
    body += flag(365, 147) + text(345, 224, "目标", 20)
    for number, y, label, sub in [
        (1, 96, "我在哪？", "定位"),
        (2, 181, "从哪走？", "规划"),
        (3, 266, "怎么动？", "控制"),
    ]:
        body += rect(493, y, 265, 68)
        body += f'<circle cx="522" cy="{y + 34}" r="17" fill="{LIGHT_BLUE}"/>'
        body += text(522, y + 41, number, 20, BLUE, 700, "middle")
        body += text(550, y + 42, label, 25, weight=700)
        body += text(737, y + 42, sub, 17, MUTED, anchor="end")
    body += path("M625 166 V177", BLUE, 3)
    body += path("M625 251 V262", BLUE, 3)
    body += path("M489 299 H472 Q458 299 458 282 V145 Q458 130 485 130", BLUE, 3)
    body += text(490, 385, "边观察，边调整，再继续走", 20, MUTED)
    return svg("导航：看清自己，再绕开障碍", "左侧是哨兵从起点绕过墙到达旗子的合成示意；右侧定位、规划、控制构成持续反馈的闭环。", body)


def messages():
    body = rect(45, 103, 180, 98) + text(135, 145, "发布者", 25, weight=700, anchor="middle")
    body += text(135, 178, "发送数据", 18, MUTED, anchor="middle")
    body += rect(310, 103, 180, 98, LIGHT_BLUE, LIGHT_BLUE)
    body += text(400, 166, "7", 51, BLUE, 700, "middle")
    body += text(400, 230, "一条消息", 19, MUTED, anchor="middle")
    body += rect(575, 103, 180, 98) + text(665, 145, "订阅者", 25, weight=700, anchor="middle")
    body += text(665, 178, "接收数据", 18, MUTED, anchor="middle")
    body += path("M236 153 H294") + path("M503 153 H561")
    body += rect(45, 259, 710, 55, WHITE, LINE, 12)
    body += text(63, 294, "同名", 21, GREEN, 700)
    body += text(177, 294, "/demo/value", 22)
    body += path("M345 287 H427", GREEN, 4)
    body += text(451, 294, "/demo/value", 22)
    body += text(716, 294, "接通", 21, GREEN, 700, "end")
    body += rect(45, 328, 710, 55, WHITE, LINE, 12)
    body += text(63, 363, "不同名", 21, RED, 700)
    body += text(177, 363, "/demo/value", 22)
    body += path("M345 356 H375 M404 356 H427", RED, 4, marker=False)
    body += '<path d="M381 348 L397 364 M397 348 L381 364" stroke="#cb4d4d" stroke-width="4" stroke-linecap="round"/>'
    body += text(451, 363, "/demo/other", 22)
    body += text(716, 363, "断开", 21, RED, 700, "end")
    return svg("消息：话题同名，数据才能接上", "发布者通过话题发送数值为7的消息，订阅者接收；下方对照话题名一致时接通、不一致时断开。", body)


def frames():
    body = rect(25, 92, 359, 258) + rect(416, 92, 359, 258)
    body += text(45, 126, "车头朝右 · 0°", 22, weight=700)
    body += text(436, 126, "车头朝上 · 90°", 22, weight=700)
    # World axes stay fixed in both views, while the orange body axes rotate.
    for x in (65, 456):
        body += path(f"M{x} 312 H{x + 280}", BLUE, 3)
        body += path(f"M{x} 312 V155", BLUE, 3)
        body += text(x + 254, 337, "+x", 18, BLUE)
        body += text(x + 9, 165, "+y", 18, BLUE)
    body += robot(160, 244, 0, 1.0)
    body += path("M166 244 H309", ORANGE, 5)
    body += path("M160 237 V174", ORANGE, 3)
    body += text(231, 229, "前 +x", 20, ORANGE, 700)
    body += text(171, 182, "+y", 17, ORANGE)
    body += robot(621, 255, 90, 1.0)
    body += path("M621 248 V155", ORANGE, 5)
    body += path("M614 255 H530", ORANGE, 3)
    body += text(643, 174, "前 +x", 20, ORANGE, 700)
    body += text(525, 243, "+y", 17, ORANGE)
    body += text(621, 294, "前进 → 世界 +y", 21, BLUE, 700, "middle")
    body += text(44, 391, "蓝：世界坐标，固定", 21, BLUE)
    body += text(415, 391, "橙：身体坐标，随车转", 21, ORANGE)
    return svg("坐标：车头转了，“前方”也会转", "两幅俯视图中的蓝色世界坐标保持不动；车体偏航从0度转为90度，橙色身体正x方向由世界正x变为世界正y。", body)


def lidar():
    body = rect(28, 94, 412, 260) + rect(509, 94, 263, 260)
    body += '<path d="M272 124 H403 M272 124 V310" fill="none" stroke="#233348" stroke-width="16" stroke-linecap="round"/>'
    body += text(309, 153, "墙", 21, INK)
    for py in (145, 173, 201, 229, 257, 285):
        body += f'<path d="M139 291 L264 {py}" stroke="{BLUE}" stroke-width="2" opacity=".6"/>'
        body += f'<circle cx="264" cy="{py}" r="5" fill="{ORANGE}"/>'
    body += robot(139, 291, 30, 0.9)
    body += text(48, 132, "射线碰到墙", 22, weight=700)
    body += text(48, 335, "橙点 = 测到的位置", 20, ORANGE, 700)
    body += path("M451 221 H496", BLUE, 4)
    body += text(640, 131, "测量点", 23, weight=700, anchor="middle")
    for i, y in enumerate((168, 173, 167, 172, 169, 165, 172, 167)):
        body += f'<circle cx="{548 + i * 27}" cy="{y}" r="5" fill="{ORANGE}"/>'
    body += path("M641 196 V234", BLUE, 3)
    body += '<path d="M549 279 H733" stroke="#233348" stroke-width="12" stroke-linecap="round"/>'
    body += text(641, 322, "平面墙（简化）", 22, weight=700, anchor="middle")
    body += text(29, 387, "机器人位姿 + 地图 → 把测量点对齐", 21, BLUE)
    body += text(770, 407, "俯视简化 · 不代表真实 MID360 采样", 14, MUTED, anchor="end")
    return svg("雷达：先测到点，再和地图对齐", "合成俯视示意：机器人向墙发射射线，橙点是测量结果；测量点可简化为平面墙，结合机器人位姿与地图进行对齐。", body)


def costmap():
    body = rect(28, 92, 438, 280)
    # Center-based collision region (orange) and traversable outer costs (blue).
    body += rect(124, 124, 242, 238, "#eef4ff", "#eef4ff", 70, 0)
    body += rect(144, 145, 202, 196, "#dceaff", "#dceaff", 55, 0)
    body += rect(166, 166, 158, 154, "#bad3f7", "#bad3f7", 40, 0)
    body += rect(187, 186, 116, 114, LIGHT_ORANGE, ORANGE, 25, 2)
    body += rect(210, 208, 70, 70, INK, INK, 7, 0)
    body += text(245, 251, "障碍", 19, WHITE, 700, "middle")
    body += path("M70 319 V158 Q70 145 86 145 H409 Q425 145 425 161 V308", ORANGE, 5)
    body += robot(70, 319, 90, .72) + flag(425, 302)
    body += text(492, 132, "实心：真实障碍", 23, INK, 700)
    body += path("M491 142 H461 L284 226", INK, 2, marker=False)
    body += text(492, 206, "内圈：不能进", 23, ORANGE, 700)
    body += text(492, 235, "车体会碰到障碍", 18, MUTED)
    body += path("M490 216 H465 L304 255", ORANGE, 2, marker=False)
    body += text(492, 296, "外圈：越近越贵", 23, BLUE, 700)
    body += text(492, 326, "仍可走，通常优先绕开", 18, MUTED)
    body += path("M490 305 H463 L347 325", BLUE, 2, marker=False)
    body += text(29, 400, "以机器人中心判断；内圈大小取决于车体尺寸", 19, MUTED)
    return svg("代价地图：不能撞，也别贴墙走", "深灰色实心为障碍；橙色内圈表示机器人中心进入后车体会碰撞；蓝色外围是可行但代价增大的区域，橙色路线绕开碰撞区。", body)


def debug():
    body = text(29, 109, "沿着数据走，找最早断开的地方", 22, MUTED)
    stations = [(28, "① 消息", "Topic 名字"), (222, "② 时间 / TF", "是否对得上"),
                (416, "③ 地图 / 状态", "是否合理"), (610, "④ 速度", "是否发出")]
    for i, (x, label, sub) in enumerate(stations):
        body += rect(x, 142, 164, 110, WHITE, RED if i == 0 else LINE, 15, 3 if i == 0 else 2)
        body += text(x + 82, 184, label, 21, INK, 700, "middle")
        body += text(x + 82, 221, sub, 19, RED if i == 0 else MUTED, anchor="middle")
        if i < 3:
            body += path(f"M{x + 172} 196 H{x + 187}", BLUE, 3)
    body += rect(28, 278, 354, 87, "#fff0ed", "#f1cdca", 14)
    body += text(49, 311, "发现断点", 22, RED, 700)
    body += text(49, 344, "/scan ≠ /lidar", 24, RED, 700)
    body += path("M396 322 H431", BLUE, 4)
    body += rect(445, 278, 329, 87, "#edf8f2", "#c9e5d7", 14)
    body += text(466, 311, "修复后 ✓", 22, GREEN, 700)
    body += text(466, 344, "统一 Topic 名字，接通", 22, GREEN, 700)
    body += text(29, 401, "先留证据，再改动；一次只解决一个断点", 20, MUTED)
    return svg("排障：用四站证据缩小范围", "四个证据站依次为消息、时间与TF、地图与状态、速度。示例在消息站发现scan和lidar话题名不一致，统一名称后恢复接通。", body)


def first_run():
    body = ""
    steps = [(35, 276, 181, 78, BLUE, "浏览器先看", "今天"),
             (216, 218, 181, 136, "#e5eefb", "动手点演示", "下一步"),
             (397, 160, 181, 194, "#dbe7f7", "Python 小练习", "再下一步"),
             (578, 102, 187, 252, "#cfdef2", "ROS 节点", "最后")]
    for x, y, width, height, fill, label, small in steps:
        body += rect(x, y, width, height, fill, fill, 9, 0)
        body += text(x + width / 2, y + 34, label, 23, WHITE if x == 35 else INK, 700, "middle")
        body += text(x + width / 2, y + 62, small, 18, WHITE if x == 35 else MUTED, 500, "middle")
    body += rect(53, 224, 143, 39, LIGHT_ORANGE, LIGHT_ORANGE, 19, 0)
    body += text(124, 251, "今天只走这里", 19, "#95500d", 700, "middle")
    body += path("M226 195 H369", BLUE, 3, "5 6")
    body += path("M409 137 H552", BLUE, 3, "5 6")
    body += text(29, 399, "先看懂图和动画，再逐步动手", 23, BLUE, 700)
    return svg("入门路线：今天只迈第一步", "四阶台阶从浏览器先看、动手点演示、Python小练习到ROS节点，第一阶以蓝色和今天标签突出。", body)


def load_font(size):
    candidates = [Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/msyhbd.ttc"),
                  Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    raise RuntimeError("需要中文字体：Microsoft YaHei 或 Noto Sans CJK SC")


FONTS = {}


def ptext(draw, xy, value, size=22, color=INK, anchor=None):
    if size not in FONTS:
        FONTS[size] = load_font(size)
    draw.text(xy, str(value), font=FONTS[size], fill=color, anchor=anchor)


def parrow(draw, start, end, color=BLUE, width=4, head=11):
    draw.line([start, end], fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    points = [end, (end[0] - head * math.cos(angle - .5), end[1] - head * math.sin(angle - .5)),
              (end[0] - head * math.cos(angle + .5), end[1] - head * math.sin(angle + .5))]
    draw.polygon(points, fill=color)


def gif_canvas(title):
    im = Image.new("RGB", (800, 440), BG)
    draw = ImageDraw.Draw(im)
    ptext(draw, (28, 19), title, 27)
    ptext(draw, (772, 67), "合成教学动画", 14, MUTED, "ra")
    return im, draw


def astar_trace():
    """Return every expansion and the optimal path; no randomly lit cells."""
    start, goal = (1, 6), (13, 2)
    wall = {(7, y) for y in range(1, 8)}
    counter = 0
    heuristic = lambda cell: abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])
    queue = [(heuristic(start), heuristic(start), counter, start)]
    costs, previous, expanded, trace = {start: 0}, {}, set(), []
    while queue:
        _, _, _, current = heapq.heappop(queue)
        if current in expanded:
            continue
        expanded.add(current)
        if current != goal:
            for dx, dy in ((1, 0), (0, -1), (0, 1), (-1, 0)):
                nxt = current[0] + dx, current[1] + dy
                if not (0 <= nxt[0] < 15 and 0 <= nxt[1] < 9) or nxt in wall:
                    continue
                new_cost = costs[current] + 1
                if new_cost < costs.get(nxt, math.inf):
                    costs[nxt], previous[nxt] = new_cost, current
                    counter += 1
                    h = heuristic(nxt)
                    heapq.heappush(queue, (new_cost + h, h, counter, nxt))
        frontier = {entry[3] for entry in queue} - expanded
        trace.append((set(expanded), frontier, current))
        if current == goal:
            result = [goal]
            while result[-1] != start:
                result.append(previous[result[-1]])
            return start, goal, wall, trace, result[::-1]
    raise AssertionError("搜索没有找到目标")


def make_astar(output):
    start, goal, wall, trace, route = astar_trace()
    assert route[0] == start and route[-1] == goal
    assert all(cell not in wall for cell in route)
    assert all(abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1 for a, b in zip(route, route[1:]))
    # This wall has symmetric upper/lower bypasses; either has unit cost 20.
    assert len(route) - 1 == 20
    frames, durations = [], []
    # At most 24 search snapshots, followed by eight path-reveal snapshots.
    sample_count = min(24, len(trace))
    indices = sorted({round(i * (len(trace)-1) / (sample_count-1)) for i in range(sample_count)})
    states = [(trace[idx], [], idx + 1) for idx in indices]
    states += [(trace[-1], route[:max(2, math.ceil(i * len(route) / 8))], len(trace)) for i in range(1, 9)]
    for state_idx, ((expanded, frontier, current), visible_route, count) in enumerate(states):
        im, draw = gif_canvas("A*：先搜索，再连出绕墙路线")
        ox, oy, cell = 30, 96, 32
        for y in range(9):
            for x in range(15):
                pos = (x, y)
                fill = INK if pos in wall else LIGHT_BLUE if pos in expanded else LIGHT_ORANGE if pos in frontier else WHITE
                draw.rectangle((ox+x*cell, oy+y*cell, ox+(x+1)*cell-1, oy+(y+1)*cell-1), fill=fill, outline=LINE)
        if not visible_route:
            x, y = current
            draw.rectangle((ox+x*cell+3, oy+y*cell+3, ox+(x+1)*cell-4, oy+(y+1)*cell-4), fill=ORANGE)
        if len(visible_route) > 1:
            pts = [(ox+(x+.5)*cell, oy+(y+.5)*cell) for x, y in visible_route]
            draw.line(pts, fill=BLUE, width=8, joint="curve")
        for pos, label, fill in [(start, "起", BLUE), (goal, "终", ORANGE)]:
            x, y = ox+(pos[0]+.5)*cell, oy+(pos[1]+.5)*cell
            draw.ellipse((x-13, y-13, x+13, y+13), fill=fill)
            ptext(draw, (x, y-1), label, 19, WHITE, "mm")
        draw.rounded_rectangle((539, 96, 772, 385), radius=16, fill=WHITE, outline=LINE, width=2)
        ptext(draw, (558, 112), "找到路线" if visible_route else "搜索中…", 25, BLUE)
        ptext(draw, (558, 153), f"已展开 {count} 格", 21)
        for yy, color, label in [(207, LIGHT_BLUE, "已检查"), (246, LIGHT_ORANGE, "待检查")]:
            draw.rounded_rectangle((558, yy, 580, yy+22), radius=5, fill=color, outline=LINE)
            ptext(draw, (593, yy-2), label, 20)
        ptext(draw, (558, 291), "只走上下左右", 20, MUTED)
        ptext(draw, (558, 323), "每格成本 = 1", 20, MUTED)
        if visible_route:
            ptext(draw, (558, 356), "最短路线：20 步", 20, BLUE)
        ptext(draw, (30, 407), "曼哈顿启发式 · 蓝线是最终路径 · 可在正文交互版暂停", 18, MUTED)
        frames.append(im)
        durations.append(850 if state_idx == 0 else 1700 if state_idx == len(states)-1 else 180)
    save_gif(frames, output / "astar.gif", durations)
    return {"expanded": len(trace), "path_cost": len(route)-1, "frames_requested": len(frames)}


def draw_robot(draw, cx, cy):
    # The robot heading is 90 degrees in world coordinates: its local +x is up.
    draw.rounded_rectangle((cx-23, cy-23, cx-12, cy+23), radius=4, fill=INK)
    draw.rounded_rectangle((cx+12, cy-23, cx+23, cy+23), radius=4, fill=INK)
    draw.rounded_rectangle((cx-17, cy-24, cx+17, cy+24), radius=8, fill=BLUE, outline=WHITE, width=2)
    draw.ellipse((cx-9, cy-9, cx+9, cy+9), fill=LIGHT_BLUE)
    draw.line((cx, cy, cx, cy-35), fill=BLUE, width=7)
    draw.line([(cx-7, cy-13), (cx, cy-23), (cx+7, cy-13)], fill=WHITE, width=3)


def make_motion(output):
    frames, durations = [], []
    for i in range(28):
        t = i / 27
        yaw = math.pi / 2
        body_forward = 136 * t
        # A body-frame (dx, 0) becomes (dx*cos(yaw), dx*sin(yaw)) in world.
        world_x, world_y = body_forward * math.cos(yaw), body_forward * math.sin(yaw)
        assert abs(world_x) < 1e-10 and world_y >= 0
        cx, cy = 315 + world_x, 330 - world_y
        im, draw = gif_canvas("身体前进：车头朝上，就向世界 +y 走")
        draw.rounded_rectangle((28, 96, 466, 386), radius=16, fill=WHITE, outline=LINE, width=2)
        parrow(draw, (92, 353), (433, 353), BLUE, 3)
        parrow(draw, (92, 353), (92, 125), BLUE, 3)
        ptext(draw, (399, 360), "+x", 20, BLUE)
        ptext(draw, (104, 117), "+y", 20, BLUE)
        ptext(draw, (47, 359), "世界坐标（固定）", 18, BLUE)
        for yy in range(194, 331, 16):
            draw.line((315, yy, 315, yy+5), fill="#c2d5f0", width=5)
        if i:
            draw.line((315, 330, cx, cy), fill=BLUE, width=5)
        draw.ellipse((308, 323, 322, 337), fill=WHITE, outline=BLUE, width=2)
        draw_robot(draw, cx, cy)
        parrow(draw, (cx, cy-39), (cx, cy-88), ORANGE, 5)
        parrow(draw, (cx-30, cy), (cx-97, cy), ORANGE, 3)
        ptext(draw, (cx+22, cy-84), "前 +x", 21, ORANGE)
        ptext(draw, (cx-99, cy+8), "+y", 18, ORANGE)
        draw.rounded_rectangle((496, 96, 772, 386), radius=16, fill=WHITE, outline=LINE, width=2)
        ptext(draw, (519, 117), "车头朝上", 26)
        ptext(draw, (519, 159), "偏航角 = 90°", 23, MUTED)
        ptext(draw, (519, 222), "身体前进", 28, ORANGE)
        parrow(draw, (535, 271), (571, 271), BLUE, 3)
        ptext(draw, (583, 250), "世界 +y", 27, BLUE)
        ptext(draw, (519, 332), "轨迹沿蓝色竖线", 20, MUTED)
        ptext(draw, (30, 407), "理想运动教学示意 · 不含噪声、打滑或真实动力学", 18, MUTED)
        frames.append(im)
        durations.append(850 if i == 0 else 1700 if i == 27 else 140)
    save_gif(frames, output / "motion.gif", durations)


def save_gif(frames, destination, durations):
    # A shared palette prevents the background and text from flickering.
    frames[-1].save(destination.with_name(destination.stem + "-poster.png"))
    palette = frames[len(frames)//2].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    converted = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    converted[0].save(destination, save_all=True, append_images=converted[1:],
                      duration=durations, loop=0, optimize=True, disposal=1)


def validate(output):
    report = []
    for name in ("overview", "messages", "frames", "lidar", "costmap", "debug", "first-run"):
        file = output / f"{name}.svg"
        root = ET.parse(file).getroot()
        assert root.tag == "{http://www.w3.org/2000/svg}svg"
        assert root.attrib["viewBox"] == "0 0 800 420"
        assert root.find("{http://www.w3.org/2000/svg}desc") is not None
        report.append(f"{file.name}: SVG 可解析，800×420，{file.stat().st_size:,} 字节")
    for name in ("astar", "motion"):
        file = output / f"{name}.gif"
        with Image.open(file) as animation:
            assert animation.size == (800, 440)
            assert 20 <= animation.n_frames <= 35
            assert animation.info.get("loop") == 0
            assert file.stat().st_size < 700 * 1024
            durations = []
            for i in range(animation.n_frames):
                animation.seek(i)
                durations.append(animation.info.get("duration", 0))
            assert durations[0] >= 800 and durations[-1] >= 1500
            report.append(f"{file.name}: {animation.n_frames} 帧，{sum(durations)/1000:.2f} 秒/循环，{file.stat().st_size:,} 字节")
        poster = output / f"{name}-poster.png"
        with Image.open(poster) as still:
            assert still.size == (800, 440)
            assert still.format == "PNG"
        report.append(f"{poster.name}: 清晰终态静帧，{poster.stat().st_size:,} 字节")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="新建输出目录；目录已存在时拒绝覆盖")
    args = parser.parse_args()
    output = args.output_dir.expanduser().resolve()
    if output.exists():
        parser.error(f"输出目录已存在，拒绝覆盖：{output}")
    output.mkdir(parents=True, exist_ok=False)
    creators = {"overview": overview, "messages": messages, "frames": frames, "lidar": lidar,
                "costmap": costmap, "debug": debug, "first-run": first_run}
    for name, creator in creators.items():
        (output / f"{name}.svg").write_text(creator(), encoding="utf-8")
    result = make_astar(output)
    make_motion(output)
    print(f"A* 真实搜索：展开 {result['expanded']} 格，四邻接单位成本最短路 {result['path_cost']} 步")
    for line in validate(output):
        print(line)
    print(f"输出目录：{output}")


if __name__ == "__main__":
    main()
