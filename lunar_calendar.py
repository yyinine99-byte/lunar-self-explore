"""农历日期转换器 — 基于春节日期查表。

使用预存的农历新年（春节）日期表，从公历日期推算农历月日。
MVP 级别精度，星宿查询够用。
"""

import datetime


# 农历新年（春节）公历日期表
# 格式: (公历年, 公历月, 公历日, 农历年)
CNY_DATES = {
    1990: (1, 27),
    1991: (2, 15),
    1992: (2, 4),
    1993: (1, 23),
    1994: (2, 10),
    1995: (1, 31),
    1996: (2, 19),
    1997: (2, 7),
    1998: (1, 28),
    1999: (2, 16),
    2000: (2, 5),
    2001: (1, 24),
    2002: (2, 12),
    2003: (2, 1),
    2004: (1, 22),
    2005: (2, 9),
    2006: (1, 29),
    2007: (2, 18),
    2008: (2, 7),
    2009: (1, 26),
    2010: (2, 14),
    2011: (2, 3),
    2012: (1, 23),
    2013: (2, 10),
    2014: (1, 31),
    2015: (2, 19),
    2016: (2, 8),
    2017: (1, 28),
    2018: (2, 16),
    2019: (2, 5),
    2020: (1, 25),
    2021: (2, 12),
    2022: (2, 1),
    2023: (1, 22),
    2024: (2, 10),
    2025: (1, 29),
    2026: (2, 17),
    2030: (2, 3),
}

# 农历每月天数 (简化：大月30天，小月29天，交替)
# 实际历法更复杂（由定气法确定），此处用近似
_LUNAR_MONTH_DAYS = [30, 29, 30, 29, 30, 29, 30, 29, 30, 29, 30, 29]


def solar_to_lunar(solar_date: datetime.date) -> dict:
    """公历转农历（春节查表法）。

    Returns:
        {"year": int, "month": int, "day": int, "is_leap": bool}
    """
    y = solar_date.year

    # 确保年份在查表范围内
    if y not in CNY_DATES:
        # 使用最近年份的春节 + 近似推算
        cny_y = max(k for k in CNY_DATES if k <= y)
        cny_m, cny_d = CNY_DATES[cny_y]
        cny = datetime.date(cny_y, cny_m, cny_d)

        # 计算距离该年春节多少天
        if solar_date >= cny:
            diff = (solar_date - cny).days
            lunar_year = cny_y
        else:
            # 在该年春节之前，属于上一个农历年
            prev_cny_y = max(k for k in CNY_DATES if k < cny_y)
            prev_cny_m, prev_cny_d = CNY_DATES[prev_cny_y]
            prev_cny = datetime.date(prev_cny_y, prev_cny_m, prev_cny_d)
            diff = (solar_date - prev_cny).days
            lunar_year = prev_cny_y
    else:
        cny_m, cny_d = CNY_DATES[y]
        cny = datetime.date(y, cny_m, cny_d)

        if solar_date >= cny:
            diff = (solar_date - cny).days
            lunar_year = y
        else:
            # 在春节之前，属于上一个农历年
            prev_y = y - 1
            if prev_y in CNY_DATES:
                prev_cny_m, prev_cny_d = CNY_DATES[prev_y]
            else:
                # 近似
                prev_cny_m, prev_cny_d = (1, 31)
            prev_cny = datetime.date(prev_y, prev_cny_m, prev_cny_d)
            diff = (solar_date - prev_cny).days
            lunar_year = prev_y

    # 从春节开始累加月份
    lunar_month = 1
    lunar_day = diff + 1
    remaining = diff

    # 大月小月交替，从正月(大)开始
    for m in range(12):
        month_days = 30 if m % 2 == 0 else 29
        if remaining < month_days:
            lunar_month = m + 1
            lunar_day = remaining + 1
            break
        remaining -= month_days
    else:
        # 超出12个月（理论上不会发生）
        lunar_month = 12
        lunar_day = min(remaining + 1, 30)

    return {
        "year": lunar_year,
        "month": lunar_month,
        "day": lunar_day,
        "is_leap": False,
    }
