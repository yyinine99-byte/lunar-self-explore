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
from system_prompts import SYSTEM_PROMPT_FULL

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

    # 星盘关键信息
    if chart_info:
        asc = chart_info.get("ascendant", {})
        planets = chart_info.get("planets", [])
        sun = next((p for p in planets if p.get("name_en") == "Sun"), {})
        moon = next((p for p in planets if p.get("name_en") == "Moon"), {})

        context_blocks.append(f"""【星盘数据】
太阳：{sun.get('sign', 'N/A')} {sun.get('degree_in_sign', '')}°
月亮：{moon.get('sign', 'N/A')} {moon.get('degree_in_sign', '')}°
上升：{asc.get('sign', 'N/A')} {asc.get('degree', '')}°
主导元素：{chart_info.get('dominant_element', 'N/A')}
元素分布：火{chart_info.get('element_distribution', {}).get('火', 0)} 土{chart_info.get('element_distribution', {}).get('土', 0)} 风{chart_info.get('element_distribution', {}).get('风', 0)} 水{chart_info.get('element_distribution', {}).get('水', 0)}
行星位置：{', '.join([f"{p.get('name_cn','')}{p.get('sign','')}{p.get('degree_in_sign','')}°" for p in planets if p.get('name_cn')]) if planets else 'N/A'}""")

    # 五行能量关键信息
    if bazi_info:
        pillars_text = ""
        for p in bazi_info.get("pillars", []):
            pillars_text += f"{p.get('name', '')}: {p.get('stem', '')}{p.get('branch', '')} ({p.get('element', '')}) | "
        strength = bazi_info.get('day_master_strength_detail', {})
        context_blocks.append(f"""【五行能量数据】
日主：{bazi_info.get('day_master', 'N/A')}（{bazi_info.get('day_master_element', '')}·{bazi_info.get('day_master_yin_yang', '')}）
四柱：{pillars_text}
天干十神：{bazi_info.get('ten_gods', {})}
地支十神：{bazi_info.get('branch_ten_gods', {})}
日主强弱：{bazi_info.get('day_master_strength', 'N/A')}（评分{strength.get('score', 'N/A')}，{'; '.join(strength.get('details', []))}）
各柱藏干：{', '.join([f"{p.get('name','')}:{','.join(p.get('hidden_stems_full',[]))}" for p in bazi_info.get('pillars', [])])}""")

    # 星宿信息
    if star_info:
        context_blocks.append(f"""【星宿数据】
{star_info.get('name', 'N/A')}（{star_info.get('element', '')}·{star_info.get('direction', '')}方）
动物象征：{star_info.get('animal', 'N/A')}
性格关键词：{star_info.get('personality', 'N/A')}""")

    # 构建完整消息
    system_content = SYSTEM_PROMPT_FULL + "\n\n==== 用户个人信息（供参考）====\n" + "\n\n".join(context_blocks) + "\n\n==== 以上是用户的计算结果 ====\n请用这些信息辅助分析，但不要全部罗列出来。在用户问到时自然地引用相关数据。"

    # 模式指令
    if mode == "answer":
        system_content += """
\n## 当前模式：答案模式 ⚡
- 直接给结论，不要铺垫和推导过程，像朋友聊天一样直给
- 三维综合分析原则不变——三个体系的数据自己在内部交叉比对，但输出时只呈现结论，不展示比对过程
- 不提及星盘/八字/星宿术语（如"你的太阳星座""你的日主"），用生活化语言表达
- 如果用户追问原因，简单补充，保持直接
- 绝对优先级例外极少使用：仅当问题明确只涉及单一体系的概念解释时才可只用一维"""

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

    async with httpx.AsyncClient(timeout=60.0) as client:
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
                "max_tokens": 2048,
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

    async with httpx.AsyncClient(timeout=60.0) as client:
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
                "max_tokens": 2048,
            },
        )

        if response.status_code != 200:
            return {"reply": "", "error": f"API 调用失败: {response.status_code} - {response.text}"}

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"reply": content, "error": None}
