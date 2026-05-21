"""DeepSeek API 代理服务。

通过服务端代理调用 DeepSeek API，用户无需提供自己的 API Key。
使用 httpx 异步客户端，支持流式输出 (SSE)。

成本参考：
- DeepSeek: 输入 ¥1/百万 token, 输出 ¥2/百万 token
- 单次对话 (5-8k token) ≈ ¥0.01-0.02
"""

import os
import httpx
from typing import Optional, AsyncGenerator
from system_prompts import SYSTEM_PROMPT_EXPLORE, SYSTEM_PROMPT_ANSWER
from star_database import get_relationship_map

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"  # 成本最优，中文能力强

# 备用：如果有其他兼容 API 的 key
# 也可以使用 OpenAI 兼容的第三方 API


def build_messages(chart_data: dict, user_message: str, history: Optional[list] = None, mode: str = "explore") -> list:
    """构建发送给 AI 的完整消息列表。

    将用户的出生信息计算结果嵌入到 system prompt 中，
    确保 AI 始终能参考这些数据。

    Args:
        chart_data: 完整的计算结果（星盘+五行能量+星宿）
        user_message: 用户当前消息
        history: 之前的对话历史
        mode: "explore" (探索模式) 或 "answer" (答案模式)

    Returns:
        messages 列表
    """
    # 提取关键信息嵌入系统提示词
    chart_info = chart_data.get("chart", {})
    bazi_info = chart_data.get("bazi", {})
    star_info = chart_data.get("star_mansion", {})

    # 构建画像上下文
    context_blocks = []

    # ── 天干人格化映射（仅做术语桥接，不替代 AI 分析）──
    STEM_TRAITS = {
        "甲": "参天大树·正直刚健·向上生长·不喜被压制",
        "乙": "藤萝花草·柔韧灵活·心思细腻·善于借力",
        "丙": "太阳之火·热情奔放·感染力强·需要观众",
        "丁": "灯烛之火·内敛专注·洞察人心·持久温暖",
        "戊": "城墙之土·稳重敦厚·承载力强·有时固执",
        "己": "田园之土·温和包容·务实细致·不争不抢",
        "庚": "刀剑之金·果断刚毅·不惧冲突·追求公正",
        "辛": "珠宝之金·精致敏感·追求完美·自带贵气",
        "壬": "江河之水·豁达流动·智慧深远·不拘小节",
        "癸": "雨露之水·细腻渗透·直觉敏锐·润物无声",
    }
    GOD_HINTS = {
        "比肩": "独立好强·不喜依附", "劫财": "行动敢闯·哥们义气",
        "食神": "创造表达·温和输出", "伤官": "锋锐不拘·挑战权威",
        "正财": "务实积累·对价值敏感", "偏财": "商业嗅觉·敢于冒险",
        "正官": "规则自律·追求认可", "七杀": "魄力决断·手段强硬",
        "正印": "包容学习·安全感需求", "偏印": "独特视角·不走寻常路",
    }
    STRENGTH_IMPL = {
        "极旺": "能量过剩→需克制与引导，易刚愎",
        "身强": "能量自足→抗压不轻易动摇，风险是固执",
        "中和": "能量均衡→适应性好，可进可退",
        "身弱": "能量偏弱→善借力合作，需避免过度消耗",
        "极弱": "能量不足→敏感善察，需从旁支找支撑",
    }

    # 星盘关键信息 — 三层分级 + 相位
    if chart_info:
        asc = chart_info.get("ascendant", {})
        planets = chart_info.get("planets", [])
        aspects = chart_info.get("aspects", [])

        # ── 行星分组 ──
        def _pl(p):
            """格式化单颗行星：名+星座+度数"""
            return f"{p.get('name_cn','')}{p.get('sign','')}{p.get('degree_in_sign','')}°"

        # 核心（日月升）
        sun = next((p for p in planets if p.get("name_en") == "Sun"), {})
        moon = next((p for p in planets if p.get("name_en") == "Moon"), {})
        core_strs = [
            f"日{sun.get('sign','?')}{sun.get('degree_in_sign','')}°",
            f"月{moon.get('sign','?')}{moon.get('degree_in_sign','')}°",
            f"升{asc.get('sign','?')}{asc.get('degree','')}°",
        ]

        # 个性行星（水金火）
        personal_names = {"Mercury": "水星", "Venus": "金星", "Mars": "火星"}
        personal = [p for p in planets if p.get("name_en") in personal_names]
        personal_strs = [_pl(p) for p in personal]

        # 外行星（木土天海冥）
        outer_names = {"Jupiter": "木星", "Saturn": "土星", "Uranus": "天王星", "Neptune": "海王星", "Pluto": "冥王星"}
        outer = [p for p in planets if p.get("name_en") in outer_names]
        outer_strs = [_pl(p) for p in outer]

        # ── 相位（硬/软分级） ──
        # 硬相位：合/刑/冲 → 重点解读，尤其 orb≤5°；软相位：六合/拱 → 次要
        aspect_abbr = {"合相": "合", "四分相": "刑", "对分相": "冲",
                       "六分相": "六合", "三分相": "拱"}
        hard_aspects = []  # 合/刑/冲
        soft_aspects = []  # 六合/拱
        if aspects:
            for a in aspects:
                raw_type = a.get("aspect", "")
                abbr = aspect_abbr.get(raw_type, raw_type)
                entry = f"{a['planet1']}{abbr}{a['planet2']}(orb{a['orb']}°)"
                if raw_type in ("合相", "四分相", "对分相"):
                    hard_aspects.append(entry)
                else:
                    soft_aspects.append(entry)

        def _build_aspect_block():
            lines = []
            if hard_aspects:
                hard_line = "  ".join(hard_aspects)
                lines.append(f"硬相位（合/刑/冲，≤5°为重点）：{hard_line}")
            else:
                lines.append("硬相位：无")
            if soft_aspects:
                soft_line = "  ".join(soft_aspects)
                lines.append(f"软相位（六合/拱，次要）：{soft_line}")
            else:
                lines.append("软相位：无")
            return "\n".join(lines)

        aspect_block = _build_aspect_block()

        context_blocks.append(f"""【星盘数据】
核心：{' / '.join(core_strs)}
个性：{' / '.join(personal_strs)}
外行：{' / '.join(outer_strs)}
元素：{chart_info.get('dominant_element', '?')}主导 火{chart_info.get('element_distribution', {}).get('火', 0)}土{chart_info.get('element_distribution', {}).get('土', 0)}风{chart_info.get('element_distribution', {}).get('风', 0)}水{chart_info.get('element_distribution', {}).get('水', 0)}
相位：
{aspect_block}""")

    # 五行能量关键信息（重写：干净格式 + 人格化桥接）
    if bazi_info:
        dm = bazi_info.get('day_master', '')
        dm_stem = dm[0] if dm else ''
        dm_trait = STEM_TRAITS.get(dm_stem, '')
        strength = bazi_info.get('day_master_strength_detail', {})
        sl = bazi_info.get('day_master_strength', '')
        si = STRENGTH_IMPL.get(sl, '')

        # 四柱 — 每柱一行
        pillar_lines = []
        abbr_map = {"年柱": "年", "月柱": "月", "日柱": "日", "时柱": "时"}
        for p in bazi_info.get("pillars", []):
            nm = p.get("name", "")
            ab = abbr_map.get(nm, nm)
            sg = bazi_info.get("ten_gods", {}).get(f"{ab}干", "")
            bg = bazi_info.get("branch_ten_gods", {}).get(f"{ab}支", "")
            hs = ",".join(p.get("hidden_stems_full", [])[:2])
            pillar_lines.append(
                f"  {nm} {p.get('stem','')}{p.get('branch','')}（{p.get('element','')}）天干{sg}·地支{bg} | 藏干：{hs}"
            )

        # 十神汇总（只列出现过的，附速查提示）
        all_gods = set()
        for d in [bazi_info.get("ten_gods", {}), bazi_info.get("branch_ten_gods", {})]:
            for v in d.values():
                if v:
                    all_gods.add(v)
        god_note = " | ".join(
            [f"{g}→{GOD_HINTS.get(g, '')}" for g in sorted(all_gods) if g in GOD_HINTS]
        )

        context_blocks.append(f"""【五行能量数据】
日主{dm}（{bazi_info.get('day_master_yin_yang', '')}）→ {dm_trait}
{sl}（评分{strength.get('score', 'N/A')}）→ {si}
{'; '.join(strength.get('details', []))}

四柱：
{chr(10).join(pillar_lines)}

十神速查：{god_note}""")

    # 星宿信息（含关系系统）
    if star_info:
        mansion_name = star_info.get('name', 'N/A')
        mansion_idx = star_info.get('index', 0)

        # 星宿关系地图：按类型归组，每类型一行，列出近/中/远代表星宿
        rel_lines = []
        if mansion_idx:
            try:
                from collections import OrderedDict
                relations = get_relationship_map(mansion_idx)
                type_groups = OrderedDict()
                for r in relations:
                    t = r['type']
                    if t not in type_groups:
                        type_groups[t] = {'grades': [], 'tag': r['tag'], 'dynamic': r['dynamic'],
                                           'strength': r['strength'], 'risk': r['risk'], 'best_for': r['best_for']}
                    g = r['grade']
                    type_groups[t]['grades'].append(f"{g}({r['mansion']})" if g else r['mansion'])
                for t, info in type_groups.items():
                    grades_str = '、'.join(info['grades'])
                    first_sentence = info['dynamic'].split('。')[0] if info['dynamic'] else ''
                    rel_lines.append(f"  {info['tag']}型——{first_sentence}\n    代表星宿：{grades_str}\n    优势：{info['strength']}\n    风险：{info['risk']}")
            except Exception:
                pass

        context_blocks.append(f"""【星宿数据】
{mansion_name}（{star_info.get('element', '')}·{star_info.get('direction', '')}方·{star_info.get('animal', '')}）
性格关键词：{star_info.get('personality', 'N/A')}

星宿关系地图 — {mansion_name}与其他星宿的六种适配关系：
{chr(10).join(rel_lines) if rel_lines else '（关系数据暂不可用）'}""")

    # 构建完整消息 — 按模式选择独立 prompt
    base_prompt = SYSTEM_PROMPT_ANSWER if mode == "answer" else SYSTEM_PROMPT_EXPLORE
    system_content = base_prompt + "\n\n==== 用户个人信息（供参考）====\n" + "\n\n".join(context_blocks) + "\n\n==== 以上是用户的计算结果 ====\n请用这些信息辅助分析，但不要全部罗列出来。在用户问到时自然地引用相关数据。"

    messages = [{"role": "system", "content": system_content}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_message})

    return messages


async def chat_stream(chart_data: dict, user_message: str, history: Optional[list] = None, mode: str = "explore") -> AsyncGenerator[str, None]:
    """流式对话接口。

    Args:
        chart_data: 画像数据
        user_message: 用户消息
        history: 历史消息
        mode: "explore" | "answer"

    Yields:
        SSE 格式的流式响应片段
    """
    if not DEEPSEEK_API_KEY:
        yield "data: {\"error\": \"API Key 未配置，请联系管理员。\"}\n\n"
        return

    messages = build_messages(chart_data, user_message, history, mode)

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": messages,
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        ) as response:
            if response.status_code != 200:
                text = await response.aread()
                yield f"data: {{\"error\": \"API 调用失败: {response.status_code}\"}}\n\n"
                return

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield "data: [DONE]\n\n"
                        break
                    yield f"data: {data}\n\n"


async def chat_non_stream(chart_data: dict, user_message: str, history: Optional[list] = None, mode: str = "explore") -> dict:
    """非流式对话接口（备用）。

    Returns:
        {"reply": str, "error": str | None}
    """
    if not DEEPSEEK_API_KEY:
        return {"reply": "", "error": "API Key 未配置，请联系管理员。"}

    messages = build_messages(chart_data, user_message, history, mode)

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": messages,
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        )

        if response.status_code != 200:
            return {"reply": "", "error": f"API 调用失败: {response.status_code} - {response.text}"}

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"reply": content, "error": None}
