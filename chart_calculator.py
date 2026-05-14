"""星盘计算核心 - 使用 skyfield 计算行星位置、星座、宫位和相位。"""

import datetime
from typing import Dict, List, Optional, Tuple
from skyfield.api import load, Loader
from skyfield.framelib import ecliptic_frame
from skyfield.toposlib import wgs84
import os
import math

# 十二星座
ZODIAC_SIGNS = [
    "白羊座", "金牛座", "双子座", "巨蟹座",
    "狮子座", "处女座", "天秤座", "天蝎座",
    "射手座", "摩羯座", "水瓶座", "双鱼座"
]

# 星座符号
ZODIAC_SYMBOLS = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]

# 星座守护星
SIGN_RULERS = {
    "白羊座": "火星", "金牛座": "金星", "双子座": "水星", "巨蟹座": "月球",
    "狮子座": "太阳", "处女座": "水星", "天秤座": "金星", "天蝎座": "冥王星",
    "射手座": "木星", "摩羯座": "土星", "水瓶座": "天王星", "双鱼座": "海王星"
}

# 星座元素
SIGN_ELEMENTS = {
    "白羊座": "火", "狮子座": "火", "射手座": "火",
    "金牛座": "土", "处女座": "土", "摩羯座": "土",
    "双子座": "风", "天秤座": "风", "水瓶座": "风",
    "巨蟹座": "水", "天蝎座": "水", "双鱼座": "水"
}

# 行星名称映射
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

# 北交点 (True Node / Mean Node)
# skyfield 不直接提供，但我们可以在后续扩展


_ts = None
_eph = None
_bodies = {}


def _load_ephemeris():
    """延迟加载星历文件（首次调用时下载约12MB）。"""
    global _ts, _eph, _bodies

    if _ts is not None:
        return

    # 使用缓存目录
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
    """根据黄经度数获取星座信息。

    Returns:
        (sign_index, sign_name, sign_symbol, degree_in_sign)
    """
    sign_idx = int(longitude // 30)
    degree_in_sign = longitude % 30
    return sign_idx, ZODIAC_SIGNS[sign_idx], ZODIAC_SYMBOLS[sign_idx], round(degree_in_sign, 2)


def compute_chart(birth_dt: datetime.datetime, lat: float, lon: float) -> Dict:
    """计算完整星盘。

    Args:
        birth_dt: 出生日期时间 (需含时区或为UTC)
        lat: 纬度
        lon: 经度

    Returns:
        包含行星、宫位、上升、相位的字典
    """
    _load_ephemeris()

    # 构建 skyfield 时间对象
    t = _ts.utc(
        birth_dt.year, birth_dt.month, birth_dt.day,
        birth_dt.hour, birth_dt.minute, birth_dt.second
    )

    earth = _eph["earth"]
    location = earth + wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon)

    planets_data = []
    for body_name, body_obj in _bodies.items():
        # 从观测者位置观测天体
        astrometric = location.at(t).observe(body_obj)
        # 黄道坐标
        lat_deg, lon_deg, distance = astrometric.frame_latlon(ecliptic_frame)
        ecliptic_lon = lon_deg.degrees % 360

        sign_idx, sign_name, sign_symbol, sign_deg = _get_sign(ecliptic_lon)

        # 判断是否逆行
        apparent = astrometric.apparent()
        # 简单逆行判断：比较前后两天的黄经
        t2 = _ts.utc(
            birth_dt.year, birth_dt.month, birth_dt.day,
            birth_dt.hour, birth_dt.minute, birth_dt.second + 86400
        )
        astrometric2 = location.at(t2).observe(body_obj)
        _, lon2_deg, _ = astrometric2.frame_latlon(ecliptic_frame)
        retrograde = bool((lon2_deg.degrees % 360) < ecliptic_lon if ecliptic_lon > 300 else False)

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
            "ruler_of": [s for s, r in SIGN_RULERS.items() if r == PLANET_NAMES.get(body_name, body_name)],
        })

    # 上升点计算 (ASC) - 简化：使用黄道上升点估计
    # 标准计算需要球面天文学，此处使用黄道上升点近似
    # 根据出生时间，上升点近似 = 太阳所在度数 + (出生时间距离正午的小时数 * 15)
    sun_data = next(p for p in planets_data if p["name_en"] == "Sun")
    sun_lon = sun_data["ecliptic_longitude"]
    # 正午12点，每小时偏离对应约15度的上升点偏移
    noon_offset = (birth_dt.hour + birth_dt.minute / 60.0) - 12
    asc_approx_lon = (sun_lon + noon_offset * 15) % 360
    asc_idx, asc_name, asc_symbol, asc_deg = _get_sign(asc_approx_lon)

    # 计算12个宫位（等宫制作为简化）
    houses = []
    for i in range(12):
        house_cusp = (asc_approx_lon + i * 30) % 360
        _, h_sign, h_symbol, h_deg = _get_sign(house_cusp)
        houses.append({
            "house_number": i + 1,
            "cusp_longitude": round(house_cusp, 4),
            "sign": h_sign,
            "sign_symbol": h_symbol,
            "degree_in_sign": h_deg,
        })

    # 计算主要相位
    aspects = _compute_aspects(planets_data)

    # 上升点
    ascendant = {
        "sign": asc_name,
        "sign_symbol": asc_symbol,
        "degree": asc_deg,
        "longitude": round(asc_approx_lon, 4),
    }

    # 汇总元素比例
    element_counts = {"火": 0, "土": 0, "风": 0, "水": 0}
    for p in planets_data:
        if p["element"] in element_counts:
            element_counts[p["element"]] += 1

    dominant_element = max(element_counts, key=element_counts.get)

    return {
        "planets": planets_data,
        "houses": houses,
        "ascendant": ascendant,
        "aspects": aspects,
        "element_distribution": element_counts,
        "dominant_element": dominant_element,
        "summary": _generate_chart_summary(planets_data, ascendant, dominant_element, element_counts),
    }


def _compute_aspects(planets: List[Dict]) -> List[Dict]:
    """计算行星之间的主要相位。"""
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
                        "planet1": p1["name_cn"],
                        "planet2": p2["name_cn"],
                        "aspect": aspect_name,
                        "angle": round(diff, 1),
                        "orb": round(abs(diff - aspect_angle), 1),
                    })
                    break

    return aspects


def _generate_chart_summary(planets: List[Dict], ascendant: Dict,
                            dominant_element: str, element_counts: Dict) -> str:
    """生成星盘摘要。"""
    sun = next(p for p in planets if p["name_en"] == "Sun")
    moon = next(p for p in planets if p["name_en"] == "Moon")

    parts = [
        f"太阳{sun['sign']}{sun['degree_in_sign']}°",
        f"月亮{moon['sign']}{moon['degree_in_sign']}°",
        f"上升{ascendant['sign']}{ascendant['degree']}°",
        f"主导元素：{dominant_element}（火{element_counts['火']}土{element_counts['土']}风{element_counts['风']}水{element_counts['水']}）",
    ]
    return "，".join(parts)
