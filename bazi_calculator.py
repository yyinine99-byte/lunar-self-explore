"""八字四柱计算 - 纯 Python 实现。

计算逻辑：
- 年柱：以立春为界，基于60甲子循环
- 月柱：基于节气划分，每月从节开始
- 日柱：基于1900-01-01甲戌日的天数推算
- 时柱：基于时辰（2小时一段）和日干推算

参考时间点：1900-01-01 = 甲戌日 (60甲子序号: 10)
"""

import datetime
from typing import Dict, Tuple

# 天干
STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
# 地支
BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
# 五行属性 (对应天干索引)
STEM_ELEMENTS = ["木", "木", "火", "火", "土", "土", "金", "金", "水", "水"]
# 阴阳 (True=阳)
STEM_YANG = [True, False, True, False, True, False, True, False, True, False]
# 地支藏干 (简化版，只取主气)
BRANCH_HIDDEN = ["癸", "己", "甲", "乙", "戊", "丙", "丁", "己", "庚", "辛", "戊", "壬"]
# 地支五行
BRANCH_ELEMENTS = ["水", "土", "木", "木", "土", "火", "火", "土", "金", "金", "土", "水"]
# 生肖
ZODIAC = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]


def _days_between(d1: datetime.date, d2: datetime.date) -> int:
    return (d2 - d1).days


def _approx_solar_term(year: int, term_index: int) -> datetime.date:
    """近似节气日期。term_index: 0=立春, 1=惊蛰, ..., 11=小寒。
    使用简化公式，对一般用途足够准确（+-1天）。
    """
    # 12个主要节气（节，非气）的近似日期
    # 立春, 惊蛰, 清明, 立夏, 芒种, 小暑, 立秋, 白露, 寒露, 立冬, 大雪, 小寒
    base_dates = [
        (2, 4), (3, 6), (4, 5), (5, 6), (6, 6),
        (7, 7), (8, 7), (9, 8), (10, 8), (11, 7), (12, 7), (1, 6)
    ]
    m, d = base_dates[term_index]
    # 年份调整（节气的年份可能跨年；小寒在次年1月）
    y = year if term_index < 11 else year + 1
    return datetime.date(y, m, d)


def compute_day_pillar(dt: datetime.date) -> Tuple[int, int]:
    """计算日柱干支索引。"""
    ref = datetime.date(1900, 1, 1)  # 甲戌日
    days = _days_between(ref, dt)
    # 甲戌 = 10 (60甲子序号)
    cycle = (days + 10) % 60
    return cycle % 10, cycle % 12


def compute_year_pillar(year: int, dt: datetime.date) -> Tuple[int, int]:
    """计算年柱干支索引（以立春为界）。"""
    spring = _approx_solar_term(year, 0)  # 立春
    lunar_year = year if dt >= spring else year - 1
    # 1984 = 甲子年 (序号0)
    stem = (lunar_year - 4) % 10
    branch = (lunar_year - 4) % 12
    return stem, branch


def compute_month_pillar(dt: datetime.date, year_stem: int) -> Tuple[int, int]:
    """计算月柱干支索引（以节气为界）。"""
    year = dt.year
    term_names = ["立春", "惊蛰", "清明", "立夏", "芒种", "小暑", "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]

    # 确定月份索引（寅=2为起始月，即立春月为寅月，索引2）
    month_branch = 2  # 默认寅月
    for i in range(11, -1, -1):
        st = _approx_solar_term(year if i < 11 else year - 1, i)
        if dt >= st:
            month_branch = (2 + i) % 12
            break

    # 月干根据年干推算
    # 年干 甲/己 → 正月(寅月)丙寅, 乙/庚→戊寅, 丙/辛→庚寅, 丁/壬→壬寅, 戊/癸→甲寅
    month_stem_starts = [2, 4, 6, 8, 0]  # 丙=2, 戊=4, 庚=6, 壬=8, 甲=0
    group = year_stem % 5
    month_stem = (month_stem_starts[group] + (month_branch - 2)) % 10
    return month_stem, month_branch


def compute_hour_pillar(hour: int, day_stem: int) -> Tuple[int, int]:
    """计算时柱干支索引。"""
    # 时辰地支
    branch = ((hour + 1) // 2) % 12  # 23时为子时(0), 1时为丑时(1)...
    # 时干根据日干推算
    # 日干 甲/己 → 子时甲子, 乙/庚→丙子, 丙/辛→戊子, 丁/壬→庚子, 戊/癸→壬子
    hour_stem_starts = [0, 2, 4, 6, 8]  # 甲=0, 丙=2, 戊=4, 庚=6, 壬=8
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

    # 生成关系: (day_elem -> other_elem)
    # 木生火, 火生土, 土生金, 金生水, 水生木
    generates = (de + 1) % 5 == oe  # day 生 other
    generated_by = (oe + 1) % 5 == de  # other 生 day
    # 克制: 木克土, 土克水, 水克火, 火克金, 金克木
    controls = (de + 2) % 5 == oe  # day 克 other
    controlled_by = (oe + 2) % 5 == de  # other 克 day
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


def compute_bazi(birth_date: datetime.date, birth_hour: int, gender: str = "") -> Dict:
    """计算完整八字。

    Args:
        birth_date: 公历出生日期
        birth_hour: 出生小时 (0-23)
        gender: "male" / "female"

    Returns:
        八字信息字典
    """
    # 年柱
    y_stem, y_branch = compute_year_pillar(birth_date.year, birth_date)
    # 日柱
    d_stem, d_branch = compute_day_pillar(birth_date)
    # 月柱
    m_stem, m_branch = compute_month_pillar(birth_date, y_stem)
    # 时柱
    h_stem, h_branch = compute_hour_pillar(birth_hour, d_stem)

    # 四柱八字
    pillars = [
        {"name": "年柱", "stem": STEMS[y_stem], "branch": BRANCHES[y_branch],
         "element": STEM_ELEMENTS[y_stem], "hidden_stem": BRANCH_HIDDEN[y_branch]},
        {"name": "月柱", "stem": STEMS[m_stem], "branch": BRANCHES[m_branch],
         "element": STEM_ELEMENTS[m_stem], "hidden_stem": BRANCH_HIDDEN[m_branch]},
        {"name": "日柱", "stem": STEMS[d_stem], "branch": BRANCHES[d_branch],
         "element": STEM_ELEMENTS[d_stem], "hidden_stem": BRANCH_HIDDEN[d_branch]},
        {"name": "时柱", "stem": STEMS[h_stem], "branch": BRANCHES[h_branch],
         "element": STEM_ELEMENTS[h_stem], "hidden_stem": BRANCH_HIDDEN[h_branch]},
    ]

    # 日主
    day_master = STEMS[d_stem]
    day_element = STEM_ELEMENTS[d_stem]

    # 十神 (以日干为中心)
    ten_gods = {}
    stems_in_pillars = [y_stem, m_stem, d_stem, h_stem]
    pillar_names = ["年干", "月干", "日干", "时干"]
    for si, sn in zip(stems_in_pillars, pillar_names):
        ten_gods[sn] = get_ten_gods(d_stem, si)

    # 纳音 (简化)
    nayin_map = {
        (0, 0): "海中金", (0, 1): "海中金", (1, 0): "炉中火", (1, 1): "炉中火",
        (2, 0): "大林木", (2, 1): "大林木", (3, 0): "路旁土", (3, 1): "路旁土",
        (4, 0): "剑锋金", (4, 1): "剑锋金", (5, 0): "山头火", (5, 1): "山头火",
        (6, 0): "涧下水", (6, 1): "涧下水", (7, 0): "城头土", (7, 1): "城头土",
        (8, 0): "白蜡金", (8, 1): "白蜡金", (9, 0): "杨柳木", (9, 1): "杨柳木",
    }
    nayin_pairs = [(y_stem, y_branch), (m_stem, m_branch), (d_stem, d_branch), (h_stem, h_branch)]

    # 计算四柱的纳音
    nayin = []
    for s, b in nayin_pairs:
        key = (s % 5, b % 2)
        nayin.append(nayin_map.get(key, "-"))

    # 大运的简化描述（此处只提供起运方向，不精确推算起运岁数）
    yang_year = STEM_YANG[y_stem]
    yin_year = not yang_year
    # 阳男阴女顺排，阴男阳女逆排
    if (yang_year and gender == "male") or (yin_year and gender == "female"):
        luck_direction = "顺排"
    else:
        luck_direction = "逆排"

    # 日主强弱提示
    # 统计月支对日主的生扶
    month_supports = BRANCH_ELEMENTS[m_branch] in [day_element, _element_generates(BRANCH_ELEMENTS[m_branch])]
    day_master_strength = "得令" if month_supports else "失令"

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
        "summary": f"日主{day_master}（{day_element}），" + "、".join(
            [f"{p['name']}: {p['stem']}{p['branch']}" for p in pillars]
        ),
    }


def _element_generates(elem: str) -> str:
    """返回生该元素的元素：木生火，火生土，土生金，金生水，水生木。"""
    cycle = {"木": "水", "火": "木", "土": "火", "金": "土", "水": "金"}
    return cycle.get(elem, "")
