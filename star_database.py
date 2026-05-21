"""二十八宿数据表 — 基于农历月日 + 月亮黄经双校验。

二十八宿按农历每月有固定起始宿，月内按日递推。
同时用月亮实际黄经做天文校验。

星宿关系系统：基于二十八宿圆周距离计算六种关系类型
（命之星/业胎/安坏/荣亲/危成/友衰），含互动模式描述。
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
# 五月: 参宿(20), 六月: 鬼宿(22), 七月: 张宿(25), 八月: 角宿(0)
# 九月: 氐宿(2), 十月: 心宿(4), 十一月: 斗宿(7), 十二月: 虚宿(10)
# 验证：1995年正月初十 → (12+10-1)%28=21 → 井宿 ✓
MONTH_START_MANSION = {
    1: 12, 2: 14, 3: 16, 4: 18,
    5: 20, 6: 22, 7: 25, 8: 0,
    9: 2, 10: 4, 11: 7, 12: 10,
}

# 二十八宿天文边界 — 基于月亮黄经等分法
# 角宿起始参考：Spica（角宿一）≈ 203.84° 黄经 (J2000)
# 使用等分法：每宿 360/28 ≈ 12.857°
_JIAO_REF = 203.84  # 角宿起始黄经
_MANSION_WIDTH = 360.0 / 28.0


def _norm_mansion_result(name: str, idx: int, method: str) -> dict:
    """将牛宿合并到女宿（现代二十七宿体系）。"""
    if idx == 9:  # 牛宿
        name = "女宿"
        idx = 10
    data = MANSION_DATA.get(name, {})
    return {
        "name": name,
        "index": idx,
        "element": data.get("element", ""),
        "animal": data.get("animal", ""),
        "direction": data.get("direction", ""),
        "personality": data.get("personality", ""),
        "method": method,
    }


def get_mansion_by_moon_longitude(moon_ecliptic_lon: float) -> dict:
    """根据月亮实际黄经（天文计算）确定二十八宿。

    使用等分法，以角宿一 (Spica) 黄经为参考起点。
    牛宿自动合并到女宿。

    Args:
        moon_ecliptic_lon: 月亮的黄道经度 (0-360)

    Returns:
        星宿信息字典
    """
    # 将月亮黄经映射到二十八宿索引
    offset = (moon_ecliptic_lon - _JIAO_REF) % 360
    mansion_idx = int(offset / _MANSION_WIDTH) % 28
    mansion_name = MANSION_NAMES[mansion_idx]
    return _norm_mansion_result(mansion_name, mansion_idx + 1, "moon_longitude")


def get_mansion_by_lunar_date(lunar_month: int, lunar_day: int, lunar_year: int = 2024, is_leap: bool = False) -> dict:
    """根据农历月日获取星宿信息（农历月固定起始宿法）。

    每个农历月有固定的起始星宿，月内按日递推。
    例如：正月起始为室宿，正月初十 = 井宿。
    闰月：太阳实际已进入下一中气区域，使用下一月的起始宿。
      例如：闰五月 → 使用六月的起始宿（井宿）计算。
    牛宿自动合并到女宿。

    Args:
        lunar_month: 农历月 (1-12)
        lunar_day: 农历日 (1-30)
        lunar_year: 农历年（保留，未来可用于年修正）
        is_leap: 是否为闰月

    Returns:
        包含星宿名和属性的字典
    """
    # 闰月处理：太阳已进入下一中气区域，使用下一月的起始宿
    effective_month = lunar_month
    if is_leap:
        effective_month = lunar_month + 1 if lunar_month < 12 else 1
    start_idx = MONTH_START_MANSION.get(effective_month, 0)
    mansion_idx = start_idx
    for _ in range(lunar_day - 1):
        mansion_idx = (mansion_idx + 1) % 28
        if mansion_idx == 8:  # 跳过牛宿（已合并到女宿）
            mansion_idx = (mansion_idx + 1) % 28
    mansion_name = MANSION_NAMES[mansion_idx]
    return _norm_mansion_result(mansion_name, mansion_idx + 1, "lunar_month")


# ═══════════════════════════════════════════
# 星宿关系系统 — 二十八宿圆周距离 → 六种关系类型
# ═══════════════════════════════════════════

# 六种关系类型的互动模式描述
RELATIONSHIP_MODES = {
    "命之星": {
        "tag": "灵魂镜像",
        "dynamic": "你们像在照镜子——相似到不可思议。彼此是最深的认同，无需多言的默契，但也可能因为太像而较劲。不是互补，是共振。",
        "strength": "理解力满分、灵魂深处的共振、天然信任感",
        "risk": "相似缺点互相放大、容易陷入'谁更对'的争夺",
        "best_for": "深度陪伴、共同成长、灵魂层面的对话",
    },
    "业胎": {
        "tag": "宿命纠缠",
        "dynamic": "业力最深的关系——业是被动承接方，胎是主动施与方。说不清为什么离不开，因为羁绊不只这一世。常伴有强烈的归属感和共同使命感，但也容易沉溺其中失去自我。",
        "strength": "无法替代的深度连接、强烈的归属感、共同使命感",
        "risk": "容易依赖甚至沉溺、分开后难以真正断开、边界模糊",
        "best_for": "深刻的情感体验、共同完成一件大事",
    },
    "安坏": {
        "tag": "相爱相杀",
        "dynamic": "安是安抚者，坏是破坏者——但破坏不是恶意的，是来打碎你的壳让你看见真实的自己。安坏关系里永远在上演追逐与拉扯：近安坏轰轰烈烈如火山喷发，占有欲强到窒息，恨海情天；远安坏若即若离，相隔万里却总被命运拉回；中安坏在激烈与温和间摇摆。这是最'上头'也最'疯'的关系类型。",
        "strength": "极致的激情和吸引力、促人快速成长和觉醒",
        "risk": "占有欲失控、情绪过山车、争吵激烈、相互消耗",
        "best_for": "脱胎换骨的恋爱经历（未必适合安稳婚姻）",
    },
    "荣亲": {
        "tag": "相敬如宾",
        "dynamic": "荣是荣耀方，亲是亲近方——像家人一样温暖稳定。荣亲关系缺乏轰轰烈烈的戏剧性，但有一粥一饭的踏实。近荣亲如兄妹般自然，远荣亲如远房亲戚般客气，中荣亲在亲密与距离间找到平衡。适合过日子，不适合'谈恋爱'。",
        "strength": "稳定、温暖、像家人一样的安全感、低冲突",
        "risk": "容易变淡、缺乏激情、可能沦为习惯和将就",
        "best_for": "稳定的婚姻和长期伴侣关系",
    },
    "危成": {
        "tag": "利益共生",
        "dynamic": "危是冒险方，成是成就方——一起做事比一起谈情更顺。危成关系的底色是'我可以从你身上得到什么'：近危成是事业上的黄金组合，远危成是远距离的利益联盟，中危成在功利和真情间拉锯。当利益一致时坚不可摧，利益冲突时瞬间瓦解。",
        "strength": "事业上最好的搭档、资源互补、目标驱动",
        "risk": "利益冲突时关系脆弱、容易物化对方、感情成为筹码",
        "best_for": "事业合作、资源互补、目标导向的关系",
    },
    "友衰": {
        "tag": "君子之交",
        "dynamic": "友是付出方，衰是受益方——像知己又像损友。友衰关系最轻松但也最'不靠谱'：近友衰是灵魂好友无话不谈，远友衰是点头之交淡如水，中友衰在朋友与暧昧间暧昧不清。可以聊一整夜，但未必能共度一生。",
        "strength": "轻松自在、精神层面高度共鸣、无压力",
        "risk": "难以落地、容易停在'聊得来'、可能只是精神寄托",
        "best_for": "精神交流、放松的陪伴、互相启发",
    },
}

# ═══════════════════════════════════════════
# 距离 → 关系类型 + 等级 映射
# 规律：近段(d1-4) 荣亲→友衰→安坏→危成
#       中段(d5-8) 逆序 危成→安坏→友衰→荣亲
#       业胎 d=9
#       远段(d10-14) 荣亲→友衰→安坏… d=13 按方向分流, d=14 危成(正对位)
# ═══════════════════════════════════════════

# 最短距离 → (关系类型, 等级)（d=13 需要在代码中按 CW 方向分流）
# 二十七宿（牛宿并入女宿）距离 → 关系类型映射
# 27 宿圆周上，d = 1-13，对应六种关系类型的近/中/远三个等级
_DISTANCE_MAP = {
    0:  ("命之星", ""),
    1:  ("荣亲", "近"),
    2:  ("友衰", "近"),
    3:  ("安坏", "近"),
    4:  ("危成", "近"),
    5:  ("危成", "中"),
    6:  ("安坏", "中"),
    7:  ("友衰", "中"),
    8:  ("荣亲", "中"),
    9:  ("业胎", ""),
    10: ("荣亲", "远"),
    11: ("友衰", "远"),
    12: ("安坏", "远"),
    13: ("危成", "远"),
}

# CW_eff ≤ 13 (SHORT 路径) 时的角色
_ROLES_CW_SHORT = {
    (1, "荣亲"): ("亲", "荣"),
    (2, "友衰"): ("友", "衰"),
    (3, "安坏"): ("坏", "安"),
    (4, "危成"): ("成", "危"),
    (5, "危成"): ("危", "成"),
    (6, "安坏"): ("安", "坏"),
    (7, "友衰"): ("衰", "友"),
    (8, "荣亲"): ("荣", "亲"),
    (9, "业胎"): ("胎", "业"),
    (10, "荣亲"): ("亲", "荣"),
    (11, "友衰"): ("友", "衰"),
    (12, "安坏"): ("坏", "安"),
    (13, "危成"): ("成", "危"),
}

# CW_eff ≥ 14 (LONG 路径) 时的角色
_ROLES_CW_LONG = {
    (1, "荣亲"): ("荣", "亲"),
    (2, "友衰"): ("衰", "友"),
    (3, "安坏"): ("安", "坏"),
    (4, "危成"): ("危", "成"),
    (5, "危成"): ("成", "危"),
    (6, "安坏"): ("坏", "安"),
    (7, "友衰"): ("友", "衰"),
    (8, "荣亲"): ("亲", "荣"),
    (9, "业胎"): ("业", "胎"),
    (10, "荣亲"): ("荣", "亲"),
    (11, "友衰"): ("衰", "友"),
    (12, "安坏"): ("安", "坏"),
    (13, "危成"): ("危", "成"),
}


def _get_roles(rel_type: str, cw_eff: int, d_eff: int) -> tuple:
    """返回 (role_a, role_b)，基于 27 宿有效圆周上的 CW 方向。"""
    key = (d_eff, rel_type)
    if cw_eff <= 13:
        return _ROLES_CW_SHORT.get(key, ("", ""))
    else:
        return _ROLES_CW_LONG.get(key, ("", ""))


# ═══════════════════════════════════════════
# 27×27 硬编码关系查找表（模块加载时一次性生成）
# 牛宿已并入女宿，使用 27 宿有效圆周计算
# ═══════════════════════════════════════════

_RELATIONSHIP_TABLE: dict = {}  # key: (raw_idx_a, raw_idx_b), value: dict

# 牛宿已并入女宿（现代二十七宿体系）
_NIUXU_INDEX = 9   # 牛宿
_NVXU_INDEX = 10   # 女宿（合并目标）

# 原始 28 位置索引 → 27 宿有效索引（牛宿 raw=9 被合并，不参与映射）
_RAW_TO_EFF: dict = {}
_EFF_TO_RAW: list = []  # 0-indexed, eff=1 → index 0


def _build_effective_mapping():
    """构建 28→27 索引映射（牛宿合并到女宿）。"""
    global _RAW_TO_EFF, _EFF_TO_RAW
    if _RAW_TO_EFF:
        return
    for raw in range(1, 29):
        if raw == _NIUXU_INDEX:
            _RAW_TO_EFF[raw] = None
        else:
            eff = len(_EFF_TO_RAW) + 1
            _RAW_TO_EFF[raw] = eff
            _EFF_TO_RAW.append(raw)


def _build_relationship_table():
    """构建完整的 27×27 星宿关系查找表（基于 27 宿有效圆周）。"""
    global _RELATIONSHIP_TABLE
    if _RELATIONSHIP_TABLE:
        return
    _build_effective_mapping()

    for a_raw in range(1, 29):
        a_eff = _RAW_TO_EFF.get(a_raw)
        if a_eff is None:
            continue  # 牛宿跳过
        for b_raw in range(1, 29):
            b_eff = _RAW_TO_EFF.get(b_raw)
            if b_eff is None:
                continue  # 牛宿跳过

            if a_raw == b_raw:
                rel_type, grade = "命之星", ""
            else:
                diff_eff = abs(a_eff - b_eff)
                d_eff = min(diff_eff, 27 - diff_eff)
                rel_type, grade = _DISTANCE_MAP[d_eff]

            cw_eff = (b_eff - a_eff) % 27
            role_a, role_b = _get_roles(rel_type, cw_eff, d_eff if a_raw != b_raw else 0)

            mode = RELATIONSHIP_MODES.get(rel_type, {})
            label = f"{grade}{rel_type}" if grade else rel_type
            _RELATIONSHIP_TABLE[(a_raw, b_raw)] = {
                "type": rel_type,
                "grade": grade,
                "label": label,
                "role_a": role_a,
                "role_b": role_b,
                "tag": mode.get("tag", ""),
                "dynamic": mode.get("dynamic", ""),
                "strength": mode.get("strength", ""),
                "risk": mode.get("risk", ""),
                "best_for": mode.get("best_for", ""),
            }


# 模块加载时构建
_build_relationship_table()

# 牛宿已并入女宿（现代二十七宿体系），查询/展示时自动重定向
# （_NIUXU_INDEX / _NVXU_INDEX 已定义在上方）

def _resolve_mansion(idx: int) -> int:
    """将牛宿重定向到女宿。"""
    return _NVXU_INDEX if idx == _NIUXU_INDEX else idx


def get_relationship(mansion_idx_a: int, mansion_idx_b: int) -> dict:
    """查询两个星宿之间的关系（从 28×28 硬编码表直接读取）。

    牛宿自动合并到女宿。

    Args:
        mansion_idx_a: 第一个星宿的索引 (1-28)
        mansion_idx_b: 第二个星宿的索引 (1-28)

    Returns:
        包含关系类型、等级、角色、互动模式描述的字典
    """
    a = _resolve_mansion(mansion_idx_a)
    b = _resolve_mansion(mansion_idx_b)
    if a == b and mansion_idx_a != mansion_idx_b:
        # 牛宿→女宿合并后，两者互为命之星
        return _RELATIONSHIP_TABLE.get((_NVXU_INDEX, _NVXU_INDEX), {}).copy()
    return _RELATIONSHIP_TABLE.get((a, b), {}).copy()


def get_relationship_map(mansion_idx: int) -> list:
    """获取某个星宿与全部 26 个其他星宿的关系列表。

    牛宿已并入女宿，不单独列出。
    """
    mansion_idx = _resolve_mansion(mansion_idx)
    relations = []
    for i in range(1, 29):
        if i == _NIUXU_INDEX:
            continue  # 牛宿已并入女宿
        resolved = _resolve_mansion(i)
        if resolved == mansion_idx:
            continue
        rel = get_relationship(mansion_idx, i)
        other_name = MANSION_NAMES[i - 1]
        other_data = MANSION_DATA.get(other_name, {})
        rel["mansion"] = other_name
        rel["mansion_element"] = other_data.get("element", "")
        rel["mansion_animal"] = other_data.get("animal", "")
        relations.append(rel)

    # 按关系类型分组排序：业胎 > 安坏 > 荣亲 > 危成 > 友衰 > 命之星
    type_order = {"业胎": 0, "安坏": 1, "荣亲": 2, "危成": 3, "友衰": 4, "命之星": 5}
    relations.sort(key=lambda r: (type_order.get(r.get("type", ""), 9), r.get("grade", "")))

    return relations
