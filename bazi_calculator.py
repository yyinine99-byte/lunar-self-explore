"""五行能量四柱计算 - 纯 Python 实现。

计算逻辑：
- 年柱：以立春为界，基于60甲子循环
- 月柱：基于节气划分（Skyfield 精确计算节气日期）
- 日柱：基于1900-01-01甲戌日的天数推算
- 时柱：基于时辰和日干推算

参考时间点：1900-01-01 = 甲戌日 (60甲子序号: 10)
"""

import datetime
from typing import Dict, Tuple

import chart_calculator as _cc
from skyfield.framelib import ecliptic_frame

STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
STEM_ELEMENTS = ["木", "木", "火", "火", "土", "土", "金", "金", "水", "水"]
STEM_YANG = [True, False, True, False, True, False, True, False, True, False]
BRANCH_HIDDEN = ["癸", "己", "甲", "乙", "戊", "丙", "丁", "己", "庚", "辛", "戊", "壬"]
BRANCH_ELEMENTS = ["水", "土", "木", "木", "土", "火", "火", "土", "金", "金", "土", "水"]
ZODIAC = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

# 六十甲子纳音表 (60组完整，索引0=甲子, 1=乙丑, ..., 59=癸亥)
NAYIN_TABLE = [
    "海中金", "海中金", "炉中火", "炉中火", "大林木", "大林木",
    "路旁土", "路旁土", "剑锋金", "剑锋金", "山头火", "山头火",
    "涧下水", "涧下水", "城头土", "城头土", "白蜡金", "白蜡金",
    "杨柳木", "杨柳木", "泉中水", "泉中水", "屋上土", "屋上土",
    "霹雳火", "霹雳火", "松柏木", "松柏木", "长流水", "长流水",
    "砂中金", "砂中金", "山下火", "山下火", "平地木", "平地木",
    "壁上土", "壁上土", "金箔金", "金箔金", "覆灯火", "覆灯火",
    "天河水", "天河水", "大驿土", "大驿土", "钗钏金", "钗钏金",
    "桑柘木", "桑柘木", "大溪水", "大溪水", "沙中土", "沙中土",
    "天上火", "天上火", "石榴木", "石榴木", "大海水", "大海水",
]

# 节气的近似日期 (用于 Skyfield 精确搜索的起始点)
_TERM_APPROX = {
    "立春": (2, 4), "惊蛰": (3, 6), "清明": (4, 5), "立夏": (5, 6),
    "芒种": (6, 6), "小暑": (7, 7), "立秋": (8, 7), "白露": (9, 8),
    "寒露": (10, 8), "立冬": (11, 7), "大雪": (12, 7), "小寒": (1, 6),
}

# 12个节对应的太阳黄经
_TERM_LONGITUDES = {
    "立春": 315, "惊蛰": 345, "清明": 15, "立夏": 45,
    "芒种": 75, "小暑": 105, "立秋": 135, "白露": 165,
    "寒露": 195, "立冬": 225, "大雪": 255, "小寒": 285,
}

# 年份 → 节气日期缓存
_solar_term_cache: Dict[int, Dict[str, datetime.date]] = {}


def _compute_solar_terms_for_year(year: int) -> Dict[str, datetime.date]:
    """使用 Skyfield 精确计算指定年份的12个节日期。结果会被缓存。"""
    if year in _solar_term_cache:
        return _solar_term_cache[year]

    _cc._load_ephemeris()
    sun = _cc._eph["sun"]
    earth = _cc._eph["earth"]

    result = {}
    for name, target_lon in _TERM_LONGITUDES.items():
        approx_m, approx_d = _TERM_APPROX[name]
        # 小寒可能跨年：小寒在1月，如果是计算2024年的小寒，实际是2025年1月
        search_year = year if name != "小寒" else year + 1
        approx_date = datetime.date(search_year, approx_m, approx_d)

        best_day = None
        best_diff = float('inf')

        for offset in range(-3, 4):
            d = approx_date + datetime.timedelta(days=offset)
            t = _cc._ts.utc(d.year, d.month, d.day, 12, 0, 0)
            astrometric = earth.at(t).observe(sun)
            _, lon_deg, _ = astrometric.frame_latlon(ecliptic_frame)
            sun_lon = lon_deg.degrees % 360

            diff = abs(sun_lon - target_lon)
            if diff > 180:
                diff = 360 - diff

            if diff < best_diff:
                best_diff = diff
                best_day = d

        result[name] = best_day

    _solar_term_cache[year] = result
    return result


def compute_day_pillar(dt: datetime.date) -> Tuple[int, int]:
    """计算日柱干支索引。1900-01-01 = 甲戌日 (序号10)。"""
    ref = datetime.date(1900, 1, 1)
    days = (dt - ref).days
    cycle = (days + 10) % 60
    return cycle % 10, cycle % 12


def compute_year_pillar(year: int, dt: datetime.date) -> Tuple[int, int]:
    """计算年柱干支索引（以立春为界，使用Skyfield精确节气）。"""
    terms = _compute_solar_terms_for_year(year)
    spring = terms["立春"]
    lunar_year = year if dt >= spring else year - 1
    stem = (lunar_year - 4) % 10
    branch = (lunar_year - 4) % 12
    return stem, branch


def compute_month_pillar(dt: datetime.date, year_stem: int) -> Tuple[int, int]:
    """计算月柱干支索引（以节气为界，使用Skyfield精确节气）。"""
    year = dt.year
    terms = _compute_solar_terms_for_year(year)

    # 12个节按顺序，确定月份
    term_order = ["立春", "惊蛰", "清明", "立夏", "芒种",
                   "小暑", "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]

    month_branch = 2  # 默认寅月 (立春)
    for i, name in enumerate(term_order):
        term_date = terms[name]
        if dt >= term_date:
            month_branch = (2 + i) % 12
        else:
            break

    # 反向找到最后一个已过的节气
    # 处理小寒跨年：如果当前日期早于立春，小寒在去年
    if dt < terms["立春"]:
        prev_year_terms = _compute_solar_terms_for_year(year - 1)
        xiaohan = prev_year_terms["小寒"]
        if dt >= xiaohan:
            month_branch = 1  # 丑月

    # 月干 = (年干对应起始 + 月地支偏移) % 10
    month_stem_starts = [2, 4, 6, 8, 0]  # 丙=2, 戊=4, 庚=6, 壬=8, 甲=0
    group = year_stem % 5
    month_stem = (month_stem_starts[group] + (month_branch - 2)) % 10
    return month_stem, month_branch


def compute_hour_pillar(hour: int, day_stem: int) -> Tuple[int, int]:
    """计算时柱干支索引。23时为子时(0), 1-3丑时(1)..."""
    branch = ((hour + 1) // 2) % 12
    hour_stem_starts = [0, 2, 4, 6, 8]
    group = day_stem % 5
    stem = (hour_stem_starts[group] + branch) % 10
    return stem, branch


def get_ten_gods(day_stem: int, other_stem: int) -> str:
    """计算十神关系（other_stem 相对于 day_stem）。"""
    stem_elements = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]  # 0木1火2土3金4水
    de = stem_elements[day_stem]
    oe = stem_elements[other_stem]
    dy = STEM_YANG[day_stem]
    oy = STEM_YANG[other_stem]
    same_yin_yang = (dy == oy)

    generates = (de + 1) % 5 == oe
    generated_by = (oe + 1) % 5 == de
    controls = (de + 2) % 5 == oe
    controlled_by = (oe + 2) % 5 == de
    same = (de == oe)

    if same and same_yin_yang:
        return "比肩"
    if same and not same_yin_yang:
        return "劫财"
    if generates and same_yin_yang:
        return "食神"
    if generates and not same_yin_yang:
        return "伤官"
    if generated_by and not same_yin_yang:
        return "正印"
    if generated_by and same_yin_yang:
        return "偏印"
    if controls and not same_yin_yang:
        return "正财"
    if controls and same_yin_yang:
        return "偏财"
    if controlled_by and not same_yin_yang:
        return "正官"
    if controlled_by and same_yin_yang:
        return "七杀"
    return "未知"


def _get_nayin(cycle_index: int) -> str:
    """根据60甲子序号获取纳音。"""
    return NAYIN_TABLE[cycle_index % 60]


def _adjust_to_true_solar_time(birth_hour: float, longitude: float, timezone_offset: int) -> float:
    """真太阳时校正。

    北京时间 (UTC+8) 以 120°E 为基准。每偏西 1° 减 4 分钟。
    例如大理 (100.27°E): 校正 = (100.27 - 120) × 4 ≈ -79 分钟。
    18:00 北京时间 → 约 16:41 真太阳时 → 申时。

    Returns:
        校正后的小时数 (浮点, 用于确定时辰)
    """
    ref_meridian = timezone_offset * 15  # 时区基准经线
    correction_min = (longitude - ref_meridian) * 4  # 分钟
    return birth_hour + correction_min / 60.0


def compute_bazi(birth_date: datetime.date, birth_hour: int, gender: str = "",
                 longitude: float = 120.0, timezone_offset: int = 8) -> Dict:
    """计算完整五行能量四柱。

    Args:
        birth_date: 公历出生日期
        birth_hour: 出生小时 (0-23, 当地时间)
        gender: "male" / "female"
        longitude: 出生地经度 (用于真太阳时校正)
        timezone_offset: 时区偏移小时数 (用于真太阳时校正)

    Returns:
        八字信息字典
    """
    # 真太阳时校正
    true_solar_hour = _adjust_to_true_solar_time(
        float(birth_hour), longitude, timezone_offset
    )

    y_stem, y_branch = compute_year_pillar(birth_date.year, birth_date)
    d_stem, d_branch = compute_day_pillar(birth_date)
    m_stem, m_branch = compute_month_pillar(birth_date, y_stem)
    h_stem, h_branch = compute_hour_pillar(int(true_solar_hour), d_stem)

    pillars = [
        {"name": "年柱", "stem": STEMS[y_stem], "branch": BRANCHES[y_branch],
         "element": STEM_ELEMENTS[y_stem], "hidden_stem": BRANCH_HIDDEN[y_branch],
         "cycle_index": (6 * y_stem - 5 * y_branch) % 60},
        {"name": "月柱", "stem": STEMS[m_stem], "branch": BRANCHES[m_branch],
         "element": STEM_ELEMENTS[m_stem], "hidden_stem": BRANCH_HIDDEN[m_branch],
         "cycle_index": (6 * m_stem - 5 * m_branch) % 60},
        {"name": "日柱", "stem": STEMS[d_stem], "branch": BRANCHES[d_branch],
         "element": STEM_ELEMENTS[d_stem], "hidden_stem": BRANCH_HIDDEN[d_branch],
         "cycle_index": (6 * d_stem - 5 * d_branch) % 60},
        {"name": "时柱", "stem": STEMS[h_stem], "branch": BRANCHES[h_branch],
         "element": STEM_ELEMENTS[h_stem], "hidden_stem": BRANCH_HIDDEN[h_branch],
         "cycle_index": (6 * h_stem - 5 * h_branch) % 60},
    ]

    day_master = STEMS[d_stem]
    day_element = STEM_ELEMENTS[d_stem]

    ten_gods = {}
    stems_in_pillars = [y_stem, m_stem, d_stem, h_stem]
    pillar_names = ["年干", "月干", "日干", "时干"]
    for si, sn in zip(stems_in_pillars, pillar_names):
        ten_gods[sn] = get_ten_gods(d_stem, si)

    # 纳音 — 使用60甲子序号查表
    nayin = []
    for s, b in [(y_stem, y_branch), (m_stem, m_branch),
                  (d_stem, d_branch), (h_stem, h_branch)]:
        cycle_idx = (6 * s - 5 * b) % 60
        nayin.append(_get_nayin(cycle_idx))

    yang_year = STEM_YANG[y_stem]
    yin_year = not yang_year
    if (yang_year and gender == "male") or (yin_year and gender == "female"):
        luck_direction = "顺排"
    else:
        luck_direction = "逆排"

    month_supports = BRANCH_ELEMENTS[m_branch] in [day_element,
                     _element_generates(BRANCH_ELEMENTS[m_branch])]
    day_master_strength = "得令" if month_supports else "失令"

    # 真太阳时信息
    solar_correction_min = (longitude - timezone_offset * 15) * 4
    true_hour_int = int(true_solar_hour)
    true_branch_idx = ((true_hour_int + 1) // 2) % 12

    return {
        "pillars": pillars,
        "day_master": day_master,
        "day_master_element": day_element,
        "day_master_yin_yang": "阳" if STEM_YANG[d_stem] else "阴",
        "ten_gods": ten_gods,
        "nayin": nayin,
        "zodiac": ZODIAC[y_branch],
        "luck_direction": luck_direction,
        "day_master_strength": day_master_strength,
        "true_solar_time": {
            "original_hour": birth_hour,
            "corrected_hour": round(true_solar_hour, 2),
            "correction_minutes": round(solar_correction_min, 1),
            "true_branch": BRANCHES[true_branch_idx],
            "note": f"经度{longitude}°校正{solar_correction_min:+.0f}分钟" if abs(solar_correction_min) > 5 else "经度接近时区中线，几乎无需校正",
        },
        "summary": f"日主{day_master}（{day_element}），" + "、".join(
            [f"{p['name']}: {p['stem']}{p['branch']}" for p in pillars]
        ),
    }


def _element_generates(elem: str) -> str:
    cycle = {"木": "水", "火": "木", "土": "火", "金": "土", "水": "金"}
    return cycle.get(elem, "")
