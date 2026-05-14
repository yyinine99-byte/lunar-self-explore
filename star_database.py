"""二十八宿数据表 — 基于农历月日 + 月亮黄经双校验。

二十八宿按农历每月有固定起始宿，月内按日递推。
同时用月亮实际黄经做天文校验。
"""

# 二十八宿名称（按顺序）
MANSION_NAMES = [
    "角宿", "亢宿", "氐宿", "房宿", "心宿", "尾宿", "箕宿",  # 东方青龙
    "斗宿", "牛宿", "女宿", "虚宿", "危宿", "室宿", "壁宿",  # 北方玄武
    "奎宿", "娄宿", "胃宿", "昴宿", "毕宿", "觜宿", "参宿",  # 西方白虎
    "井宿", "鬼宿", "柳宿", "星宿", "张宿", "翼宿", "轸宿",  # 南方朱雀
]

# 二十八宿属性
MANSION_DATA = {
    "角宿": {"element": "木", "animal": "蛟", "direction": "东", "personality": "刚正不阿，有领导力，善于开启新局"},
    "亢宿": {"element": "金", "animal": "龙", "direction": "东", "personality": "坚定执着，重原则，有时略显固执"},
    "氐宿": {"element": "土", "animal": "貉", "direction": "东", "personality": "稳重踏实，善积累，重实际利益"},
    "房宿": {"element": "火", "animal": "兔", "direction": "东", "personality": "敏捷灵动，适应力强，善于应变"},
    "心宿": {"element": "火", "animal": "狐", "direction": "东", "personality": "热情敏锐，善交际，富有感染力"},
    "尾宿": {"element": "木", "animal": "虎", "direction": "东", "personality": "勇敢进取，行动力强，不畏挑战"},
    "箕宿": {"element": "水", "animal": "豹", "direction": "东", "personality": "洒脱自由，口才好，善于表达"},
    "斗宿": {"element": "金", "animal": "獬", "direction": "北", "personality": "正直严谨，原则性强，重视公平"},
    "牛宿": {"element": "土", "animal": "牛", "direction": "北", "personality": "勤恳踏实，耐力十足，做事有条理"},
    "女宿": {"element": "水", "animal": "蝠", "direction": "北", "personality": "细腻温柔，直觉敏锐，善解人意"},
    "虚宿": {"element": "火", "animal": "鼠", "direction": "北", "personality": "智慧机敏，多思多虑，善于谋划"},
    "危宿": {"element": "水", "animal": "燕", "direction": "北", "personality": "敏感多情，创造力强，情绪起伏大"},
    "室宿": {"element": "火", "animal": "猪", "direction": "北", "personality": "热情开朗，享受生活，大方慷慨"},
    "壁宿": {"element": "水", "animal": "貐", "direction": "北", "personality": "深沉内敛，洞察力强，善于隐藏"},
    "奎宿": {"element": "木", "animal": "狼", "direction": "西", "personality": "独立自主，有主见，不随波逐流"},
    "娄宿": {"element": "金", "animal": "狗", "direction": "西", "personality": "忠诚可靠，重情义，值得信赖"},
    "胃宿": {"element": "土", "animal": "雉", "direction": "西", "personality": "温和包容，适应环境，安定为本"},
    "昴宿": {"element": "金", "animal": "鸡", "direction": "西", "personality": "细致入微，追求完美，观察力强"},
    "毕宿": {"element": "火", "animal": "乌", "direction": "西", "personality": "热情奔放，行动迅速，有时冲动"},
    "觜宿": {"element": "火", "animal": "猴", "direction": "西", "personality": "聪明灵活，好奇心强，善于学习"},
    "参宿": {"element": "水", "animal": "猿", "direction": "西", "personality": "智慧深邃，善于思考，偶有孤独感"},
    "井宿": {"element": "木", "animal": "犴", "direction": "南", "personality": "善良仁慈，乐于助人，心胸宽广"},
    "鬼宿": {"element": "金", "animal": "羊", "direction": "南", "personality": "温顺谦和，不善争执，内在坚韧"},
    "柳宿": {"element": "土", "animal": "獐", "direction": "南", "personality": "务实稳重，注重细节，有条不紊"},
    "星宿": {"element": "火", "animal": "马", "direction": "南", "personality": "热情自由，追逐梦想，不愿被束缚"},
    "张宿": {"element": "木", "animal": "鹿", "direction": "南", "personality": "温和仁慈，有艺术天赋，追求美感"},
    "翼宿": {"element": "火", "animal": "蛇", "direction": "南", "personality": "智慧深沉，善于策略，城府较深"},
    "轸宿": {"element": "水", "animal": "蚓", "direction": "南", "personality": "灵活多变，适应性强，善于沟通"},
}

# 每个农历月的起始星宿索引（正月到十二月）
# 正月: 室宿(12), 二月: 奎宿(14), 三月: 胃宿(16), 四月: 毕宿(18)
# 五月: 参宿(20), 六月: 鬼宿(21), 七月: 张宿(24), 八月: 角宿(0)
# 九月: 氐宿(2), 十月: 心宿(4), 十一月: 斗宿(7), 十二月: 虚宿(10)
# 验证：1995年正月初十 → (12+10-1)%28=21 → 井宿 ✓
MONTH_START_MANSION = {
    1: 12, 2: 14, 3: 16, 4: 18,
    5: 20, 6: 21, 7: 24, 8: 0,
    9: 2, 10: 4, 11: 7, 12: 10,
}

# 二十八宿天文边界 — 基于月亮黄经等分法
# 角宿起始参考：Spica（角宿一）≈ 203.84° 黄经 (J2000)
# 使用等分法：每宿 360/28 ≈ 12.857°
_JIAO_REF = 203.84  # 角宿起始黄经
_MANSION_WIDTH = 360.0 / 28.0


def get_mansion_by_moon_longitude(moon_ecliptic_lon: float) -> dict:
    """根据月亮实际黄经（天文计算）确定二十八宿。

    使用等分法，以角宿一 (Spica) 黄经为参考起点。

    Args:
        moon_ecliptic_lon: 月亮的黄道经度 (0-360)

    Returns:
        星宿信息字典
    """
    # 将月亮黄经映射到二十八宿索引
    offset = (moon_ecliptic_lon - _JIAO_REF) % 360
    mansion_idx = int(offset / _MANSION_WIDTH) % 28
    mansion_name = MANSION_NAMES[mansion_idx]
    data = MANSION_DATA.get(mansion_name, {})

    return {
        "name": mansion_name,
        "index": mansion_idx + 1,
        "element": data.get("element", ""),
        "animal": data.get("animal", ""),
        "direction": data.get("direction", ""),
        "personality": data.get("personality", ""),
        "method": "moon_longitude",
    }


def get_mansion_by_lunar_date(lunar_month: int, lunar_day: int, lunar_year: int = 2024) -> dict:
    """根据农历月日获取星宿信息（农历月固定起始宿法）。

    每个农历月有固定的起始星宿，月内按日递推。
    例如：正月起始为室宿，正月初十 = 井宿。

    Args:
        lunar_month: 农历月 (1-12)
        lunar_day: 农历日 (1-30)
        lunar_year: 农历年（保留，未来可用于年修正）

    Returns:
        包含星宿名和属性的字典
    """
    start_idx = MONTH_START_MANSION.get(lunar_month, 0)
    mansion_idx = (start_idx + lunar_day - 1) % 28
    mansion_name = MANSION_NAMES[mansion_idx]
    data = MANSION_DATA.get(mansion_name, {})

    return {
        "name": mansion_name,
        "index": mansion_idx + 1,
        "element": data.get("element", ""),
        "animal": data.get("animal", ""),
        "direction": data.get("direction", ""),
        "personality": data.get("personality", ""),
        "method": "lunar_month",
    }
