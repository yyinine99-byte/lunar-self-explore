"""农历日期转换器 — 基于 lunardate 库准确转换。

使用 lunardate 包提供 1900-2100 年的准确农历日期。
比之前的春节查表 + 大小月交替法准确得多。
"""

import datetime
import lunardate


def solar_to_lunar(solar_date: datetime.date) -> dict:
    """公历转农历（使用 lunardate 库）。

    Returns:
        {"year": int, "month": int, "day": int, "is_leap": bool}
    """
    lunar = lunardate.LunarDate.fromSolarDate(
        solar_date.year, solar_date.month, solar_date.day
    )
    return {
        "year": lunar.year,
        "month": lunar.month,
        "day": lunar.day,
        "is_leap": getattr(lunar, 'isLeapMonth', False),
    }
