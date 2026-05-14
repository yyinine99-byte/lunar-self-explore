"""星盘计算核心 - 使用 skyfield 计算行星位置、星座、宫位和相位。"""

import datetime
from typing import Dict, List, Optional, Tuple
from skyfield.api import load, Loader
from skyfield.framelib import ecliptic_frame
from skyfield.toposlib import wgs84
import os
import math

ZODIAC_SIGNS = [
    "白羊座", "金牛座", "双子座", "巨蟹座",
    "狮子座", "处女座", "天秤座", "天蝎座",
    "射手座", "摩羯座", "水瓶座", "双鱼座"
]

ZODIAC_SYMBOLS = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]

SIGN_RULERS = {
    "白羊座": "火星", "金牛座": "金星", "双子座": "水星", "巨蟹座": "月球",
    "狮子座": "太阳", "处女座": "水星", "天秤座": "金星", "天蝎座": "冥王星",
    "射手座": "木星", "摩羯座": "土星", "水瓶座": "天王星", "双鱼座": "海王星"
}

SIGN_ELEMENTS = {
    "白羊座": "火", "狮子座": "火", "射手座": "火",
    "金牛座": "土", "处女座": "土", "摩羯座": "土",
    "双子座": "风", "天秤座": "风", "水瓶座": "风",
    "巨蟹座": "水", "天蝎座": "水", "双鱼座": "水"
}

SIGN_MODALITIES = {
    "白羊座": "开创", "巨蟹座": "开创", "天秤座": "开创", "摩羯座": "开创",
    "金牛座": "固定", "狮子座": "固定", "天蝎座": "固定", "水瓶座": "固定",
    "双子座": "变动", "处女座": "变动", "射手座": "变动", "双鱼座": "变动"
}

PLANET_NAMES = {
    "Sun": "太阳", "Moon": "月球", "Mercury": "水星", "Venus": "金星",
    "Mars": "火星", "Jupiter": "木星", "Saturn": "土星",
    "Uranus": "天王星", "Neptune": "海王星", "Pluto": "冥王星"
}

PLANET_SYMBOLS = {
    "Sun": "☉", "Moon": "☾", "Mercury": "☿", "Venus": "♀",
    "Mars": "♂", "Jupiter": "♃", "Saturn": "♄",
    "Uranus": "♅", "Neptune": "♆", "Pluto": "♇"
}

_ts = None
_eph = None
_bodies = {}


def _load_ephemeris():
    global _ts, _eph, _bodies
    if _ts is not None:
        return
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".skyfield_cache")
    os.makedirs(cache_dir, exist_ok=True)
    loader = Loader(cache_dir)
    _ts = loader.timescale()
    _eph = loader("de421.bsp")
    _bodies = {
        "Sun": _eph["sun"],
        "Moon": _eph["moon"],
        "Mercury": _eph["mercury"],
        "Venus": _eph["venus"],
        "Mars": _eph["mars"],
        "Jupiter": _eph["jupiter barycenter"],
        "Saturn": _eph["saturn barycenter"],
        "Uranus": _eph["uranus barycenter"],
        "Neptune": _eph["neptune barycenter"],
        "Pluto": _eph["pluto barycenter"],
    }


def _get_sign(longitude: float) -> Tuple[int, str, str, float]:
    sign_idx = int(longitude // 30)
    degree_in_sign = float(longitude % 30)
    return sign_idx, ZODIAC_SIGNS[sign_idx], ZODIAC_SYMBOLS[sign_idx], round(degree_in_sign, 2)


def _compute_obliquity(tt_jd: float) -> float:
    """计算黄赤交角 (IAU 2000 模型, 精度角秒级)。"""
    T = (tt_jd - 2451545.0) / 36525.0
    eps = (23 + 26/60 + 21.448/3600
           - 46.8150/3600 * T
           - 0.00059/3600 * T**2
           + 0.001813/3600 * T**3)
    return eps


def _compute_ascendant(lst_deg: float, lat: float, obliquity: float) -> float:
    """用球面天文学精确计算上升点 (ASC)。

    ASC = atan2(cos(LST), -(sin(LST)*cos(ε) + tan(φ)*sin(ε)))
    """
    lst_rad = math.radians(lst_deg)
    eps_rad = math.radians(obliquity)
    lat_rad = math.radians(lat)

    y = math.cos(lst_rad)
    x = -(math.sin(lst_rad) * math.cos(eps_rad) + math.tan(lat_rad) * math.sin(eps_rad))

    asc_rad = math.atan2(y, x)
    asc_deg = math.degrees(asc_rad) % 360
    return asc_deg


def _compute_mc(lst_deg: float, obliquity: float) -> float:
    """计算天顶 (MC / Medium Coeli)。

    MC = atan2(sin(LST), cos(LST)*cos(ε))
    """
    lst_rad = math.radians(lst_deg)
    eps_rad = math.radians(obliquity)

    y = math.sin(lst_rad)
    x = math.cos(lst_rad) * math.cos(eps_rad)

    mc_rad = math.atan2(y, x)
    mc_deg = math.degrees(mc_rad) % 360
    return mc_deg


def _is_retrograde(location, t, body_obj, today_lon: float) -> bool:
    """判断行星是否逆行：比较前后两天的黄经变化。"""
    t2 = t.ts.utc(int(t.utc[0]), int(t.utc[1]), int(t.utc[2]),
                   int(t.utc[3]), int(t.utc[4]), int(t.utc[5]) + 86400)
    astrometric2 = location.at(t2).observe(body_obj)
    _, lon2_deg, _ = astrometric2.frame_latlon(ecliptic_frame)
    tomorrow_lon = float(lon2_deg.degrees % 360)

    diff = tomorrow_lon - today_lon
    if diff > 180:
        diff -= 360
    elif diff < -180:
        diff += 360
    return bool(diff < 0)


def _generate_portrait_tagline(sun_sign: str, moon_sign: str, asc_sign: str,
                                dominant_element: str, day_master: str = "", star_name: str = "") -> str:
    """根据核心配置生成画像标签。"""
    tags = []

    # 太阳星座特质
    sun_traits = {
        "白羊座": "冲锋者", "金牛座": "守成者", "双子座": "漫游者", "巨蟹座": "守护者",
        "狮子座": "发光体", "处女座": "精修师", "天秤座": "平衡者", "天蝎座": "深潜者",
        "射手座": "探索者", "摩羯座": "攀登者", "水瓶座": "破局者", "双鱼座": "造梦者"
    }
    # 月亮星座情绪底色
    moon_traits = {
        "白羊座": "火爆但忘得快", "金牛座": "稳如老狗", "双子座": "脑子停不下来",
        "巨蟹座": "情绪像潮水", "狮子座": "需要被看见", "处女座": "焦虑是燃料",
        "天秤座": "纠结癌晚期", "天蝎座": "爱恨都浓烈", "射手座": "不开心就跑",
        "摩羯座": "情绪压缩包", "水瓶座": "抽离式冷静", "双鱼座": "万物皆有灵"
    }
    # 上升星座对外面具
    asc_traits = {
        "白羊座": "看起来不好惹", "金牛座": "看起来慢悠悠", "双子座": "看起来什么都懂",
        "巨蟹座": "看起来好相处", "狮子座": "看起来很有范", "处女座": "看起来很专业",
        "天秤座": "看起来很好说话", "天蝎座": "看起来不好接近", "射手座": "看起来很洒脱",
        "摩羯座": "看起来很靠谱", "水瓶座": "看起来不太一样", "双鱼座": "看起来很好骗"
    }

    sun_tag = sun_traits.get(sun_sign, sun_sign)
    moon_tag = moon_traits.get(moon_sign, "")
    asc_tag = asc_traits.get(asc_sign, "")

    # 元素底色
    element_tags = {"火": "一团野火", "土": "一座山", "风": "一阵风", "水": "一汪深潭"}

    inner = f"{sun_tag}"
    if moon_tag:
        inner += f"，{moon_tag}"
    outer = asc_tag if asc_tag else ""

    element_str = element_tags.get(dominant_element, "")

    parts = []
    if outer:
        parts.append(outer)
    parts.append(f"骨子里是{inner}")

    if element_str:
        parts.append(f"底色是{element_str}")

    return "，".join(parts[:3])


def compute_chart(birth_dt: datetime.datetime, lat: float, lon: float) -> Dict:
    """计算完整星盘。"""
    _load_ephemeris()

    t = _ts.utc(
        birth_dt.year, birth_dt.month, birth_dt.day,
        birth_dt.hour, birth_dt.minute, birth_dt.second
    )

    earth = _eph["earth"]
    location = earth + wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon)

    planets_data = []
    for body_name, body_obj in _bodies.items():
        astrometric = location.at(t).observe(body_obj)
        lat_deg, lon_deg, distance = astrometric.frame_latlon(ecliptic_frame)
        ecliptic_lon = float(lon_deg.degrees % 360)

        sign_idx, sign_name, sign_symbol, sign_deg = _get_sign(ecliptic_lon)
        retrograde = _is_retrograde(location, t, body_obj, ecliptic_lon)

        planets_data.append({
            "name_en": body_name,
            "name_cn": PLANET_NAMES.get(body_name, body_name),
            "symbol": PLANET_SYMBOLS.get(body_name, ""),
            "sign": sign_name,
            "sign_symbol": sign_symbol,
            "degree_in_sign": sign_deg,
            "ecliptic_longitude": round(ecliptic_lon, 4),
            "retrograde": retrograde,
            "element": SIGN_ELEMENTS.get(sign_name, ""),
            "modality": SIGN_MODALITIES.get(sign_name, ""),
            "ruler_of": [s for s, r in SIGN_RULERS.items()
                         if r == PLANET_NAMES.get(body_name, body_name)],
        })

    # ── 精确上升点 (ASC) 和天顶 (MC) ──
    gast = t.gast  # Greenwich Apparent Sidereal Time (小时)
    lst = (gast + lon / 15.0) % 24.0
    lst_deg = lst * 15.0
    obliquity = _compute_obliquity(t.tt)

    asc_lon = _compute_ascendant(lst_deg, lat, obliquity)
    mc_lon = _compute_mc(lst_deg, obliquity)

    asc_idx, asc_name, asc_symbol, asc_deg = _get_sign(asc_lon)
    _, mc_name, mc_symbol, mc_deg = _get_sign(mc_lon)

    # ── 等宫制计算12宫位 ──
    houses = []
    for i in range(12):
        house_cusp = (asc_lon + i * 30) % 360
        _, h_sign, h_symbol, h_deg = _get_sign(house_cusp)
        houses.append({
            "house_number": i + 1,
            "cusp_longitude": round(house_cusp, 4),
            "sign": h_sign,
            "sign_symbol": h_symbol,
            "degree_in_sign": h_deg,
        })

    # ── 相位 ──
    aspects = _compute_aspects(planets_data)

    ascendant = {
        "sign": asc_name, "sign_symbol": asc_symbol,
        "degree": asc_deg, "longitude": round(asc_lon, 4),
    }
    midheaven = {
        "sign": mc_name, "sign_symbol": mc_symbol,
        "degree": mc_deg, "longitude": round(mc_lon, 4),
    }

    # ── 元素分布 ──
    element_counts = {"火": 0, "土": 0, "风": 0, "水": 0}
    for p in planets_data:
        if p["element"] in element_counts:
            element_counts[p["element"]] += 1
    dominant_element = max(element_counts, key=element_counts.get)

    sun_data = next(p for p in planets_data if p["name_en"] == "Sun")
    moon_data = next(p for p in planets_data if p["name_en"] == "Moon")

    portrait_tagline = _generate_portrait_tagline(
        sun_data["sign"], moon_data["sign"], asc_name, dominant_element
    )

    return {
        "planets": planets_data,
        "houses": houses,
        "ascendant": ascendant,
        "midheaven": midheaven,
        "aspects": aspects,
        "element_distribution": element_counts,
        "dominant_element": dominant_element,
        "portrait_tagline": portrait_tagline,
        "summary": _generate_chart_summary(planets_data, ascendant, dominant_element, element_counts),
    }


def _compute_aspects(planets: List[Dict]) -> List[Dict]:
    ASPECT_TYPES = [
        ("合相", 0, 8), ("六分相", 60, 6), ("四分相", 90, 6),
        ("三分相", 120, 6), ("对分相", 180, 6),
    ]
    aspects = []
    for i, p1 in enumerate(planets):
        for j, p2 in enumerate(planets):
            if i >= j:
                continue
            lon1 = p1["ecliptic_longitude"]
            lon2 = p2["ecliptic_longitude"]
            diff = abs(lon1 - lon2) % 360
            if diff > 180:
                diff = 360 - diff
            for aspect_name, aspect_angle, orb in ASPECT_TYPES:
                if abs(diff - aspect_angle) <= orb:
                    aspects.append({
                        "planet1": p1["name_cn"], "planet2": p2["name_cn"],
                        "aspect": aspect_name, "angle": round(diff, 1),
                        "orb": round(abs(diff - aspect_angle), 1),
                    })
                    break
    return aspects


def _generate_chart_summary(planets: List[Dict], ascendant: Dict,
                            dominant_element: str, element_counts: Dict) -> str:
    sun = next(p for p in planets if p["name_en"] == "Sun")
    moon = next(p for p in planets if p["name_en"] == "Moon")
    parts = [
        f"太阳{sun['sign']}{sun['degree_in_sign']}°",
        f"月亮{moon['sign']}{moon['degree_in_sign']}°",
        f"上升{ascendant['sign']}{ascendant['degree']}°",
        f"主导元素：{dominant_element}（火{element_counts['火']}土{element_counts['土']}风{element_counts['风']}水{element_counts['水']}）",
    ]
    return "，".join(parts)
