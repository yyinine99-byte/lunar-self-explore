"""PDF 报告生成 — 《你的性格使用说明书》

基于用户星盘+八字+星宿数据，生成个性化 PDF 报告。
报告作为引流工具，引导用户进入对话页面做深度探索。
"""

import io
import os
import logging
from fpdf import FPDF
from PIL import Image
import qrcode

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# 字体路径检测
# ═══════════════════════════════════════════

def _find_chinese_font() -> str:
    """查找可用的中文字体，返回字体文件路径。找不到时自动下载。"""
    # 项目本地字体目录
    local_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    local_path = os.path.join(local_dir, "wqy-microhei.ttc")

    candidates = [
        # 项目本地
        local_path,
        # macOS
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        # Linux (Railway / common distros)
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
        # 也搜一下 wqy 目录
        "/usr/share/fonts/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy-microhei.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            logger.info(f"Using Chinese font: {path}")
            return path

    # 自动下载字体
    try:
        os.makedirs(local_dir, exist_ok=True)
        import urllib.request
        # WQY Micro Hei — 开源中文字体 (~5MB)
        url = (
            "https://raw.githubusercontent.com/anthonyfok/fonts-wqy-microhei/"
            "master/wqy-microhei.ttc"
        )
        logger.info(f"Downloading Chinese font to {local_path} ...")
        urllib.request.urlretrieve(url, local_path)
        if os.path.exists(local_path) and os.path.getsize(local_path) > 100000:
            logger.info("Font downloaded successfully")
            return local_path
    except Exception as e:
        logger.error(f"Failed to download font: {e}")

    logger.warning("No Chinese font found, PDF will fall back to ASCII")
    return ""


CN_FONT_PATH = _find_chinese_font()


# ═══════════════════════════════════════════
# 色彩体系
# ═══════════════════════════════════════════

BG_DARK       = (13, 13, 19)     # #0d0d13
TEXT_LIGHT    = (236, 229, 213)  # #ece5d5
GOLD          = (212, 192, 160)  # #d4c0a0
GOLD_LIGHTER  = (230, 215, 185)  # gold 亮色变体
WHITE_SOFT    = (245, 240, 235)
BLACK_SOFT    = (30, 28, 32)
GRAY_MEDIUM   = (140, 135, 130)
RED_ACCENT    = (180, 120, 100)
CARD_BG       = (22, 20, 28)
TABLE_ALT     = (35, 33, 42)
DIVIDER_COLOR = (80, 75, 70)


# ═══════════════════════════════════════════
# 内容引擎 — 数据 → 个性化文本
# ═══════════════════════════════════════════

# ── 日主画像 ──
DAY_MASTER_PROFILES = {
    "甲": {
        "core_insight": "你像一棵参天大树，天生有向上生长的力量，正直刚健，不喜被压制。",
        "talent": ["目标感强，一旦认准方向就能持续发力",
                   "有天然的领导力，别人愿意跟随你的节奏",
                   "抗压能力好，能在困难中保持稳定输出"],
        "blind_spot": ["有时过于刚直，不擅长迂回和妥协",
                       "容易忽视细节，觉得「差不多就行」",
                       "不习惯求助，什么都想自己扛"],
        "work_style": "你需要明确的成长空间和上升通道。给你一个可以持续深耕的领域，你会比大多数人走得远。但重复性的、没有成长感的工作会让你感到窒息。",
        "relationship": "你在关系中倾向于「给予者」角色，喜欢照顾对方但也期待被认可。你需要一个能理解你责任感、不把你的付出视为理所当然的人。",
    },
    "乙": {
        "core_insight": "你像藤萝花草，柔韧灵活，心思细腻，最擅长在复杂环境中找到自己的生长路径。",
        "talent": ["适应力极强，在变化中反而能找到机会",
                   "感知细腻，能捕捉到别人忽略的情绪和细节",
                   "善于借力，不硬碰硬而是以柔克刚"],
        "blind_spot": ["容易过度迁就他人，压抑自己的真实需求",
                       "想法多变，有时候自己也不知道到底要什么",
                       "在强势的人面前容易失声"],
        "work_style": "你不适合一刀切的标准流程。你需要灵活度和自主安排的空间。在需要创意、沟通、协调的领域，你的柔软反而是最大的竞争力。",
        "relationship": "你在关系中温柔体贴，但有时会为了维持和谐而委屈自己。你需要一个能看懂你欲言又止的人，而不是需要你一直解释自己的人。",
    },
    "丙": {
        "core_insight": "你像太阳之火，热情奔放，天生有感染力，人群中很难忽视你的存在。",
        "talent": ["感染力强，能带动周围人的情绪和积极性",
                   "热情外放，容易打开局面和建立连接",
                   "直觉敏锐，看人看事常有精准的第一判断"],
        "blind_spot": ["热情来得快去得也快，容易三分钟热度",
                       "需要观众的反馈才能持续输出，独处时动力下降",
                       "有时过于自我中心，忽略了别人的节奏"],
        "work_style": "你需要一个能被看见的舞台。不是说一定要做主角，但你的工作需要给你展示和表达的空间。被认可和看见是你持续前进的核心燃料。",
        "relationship": "你在爱里热情而直接，喜欢就去表达，不喜欢也藏不住。你需要一个能接住你热度、同时也能给你安全感和稳定感的人。",
    },
    "丁": {
        "core_insight": "你像灯烛之火，内敛专注，不张扬但持久温暖，善于洞察人心。",
        "talent": ["专注力强，能在某个领域深耕出成果",
                   "洞察力好，能看到事物背后隐藏的逻辑和动机",
                   "持久稳定，不追求爆发力但耐力惊人"],
        "blind_spot": ["容易过度内耗，心里翻江倒海但表面不动声色",
                       "不擅长自我宣传，做了十分只被看到三分",
                       "有时候过于执着细节，丢了全局视野"],
        "work_style": "你适合需要深度思考和专业积累的领域。你不追求快速出成果，但你的积累会在中长期爆发。给你安静专注的环境，你会产出超预期的结果。",
        "relationship": "你的情感深沉而持久，不善于表达但用行动在爱。你需要一个不需要你时刻「表现」的人，一个能看懂你沉默里的温度的人。",
    },
    "戊": {
        "core_insight": "你像城墙之土，稳重敦厚，承载力强，是别人眼中的「靠谱」担当。",
        "talent": ["稳重可靠，答应了的事一定会做到",
                   "承载力和耐心都很强，能把复杂的事一步步落地",
                   "对价值有天然的判断力，不容易被花哨的东西迷惑"],
        "blind_spot": ["有时过于固执，认定的事很难被说服",
                       "容易揽太多责任，最后把自己压垮",
                       "对自己和别人都要求高，偶尔显得不近人情"],
        "work_style": "你是团队里的基石型人物。给你明确的目标和资源，你能把一件事从想法推到落地。你需要的是被信任的空间，而不是被 micromanage。",
        "relationship": "你在关系中稳重可靠，是对方可以依赖的港湾。但你也需要学习表达柔软的一面——不是所有人都能读懂你沉默背后的在乎。",
    },
    "己": {
        "core_insight": "你像田园之土，温和包容，务实细致，是那种「润物细无声」的存在。",
        "talent": ["包容力强，能和不同性格的人和谐共处",
                   "务实细致，做事务实不浮夸",
                   "对别人的需求敏感，是天然的照顾者"],
        "blind_spot": ["不太会说「不」，容易被人情绑架",
                       "低调到有时候自己的价值被忽视",
                       "追求稳妥但也可能因此错过好机会"],
        "work_style": "你适合需要耐心和细致的工作。你喜欢稳定的节奏，不喜欢被频繁打断。在需要协调、服务、护理的领域，你的天赋会被最大化发挥。",
        "relationship": "你在关系中温和、体贴、不争不抢，但有时也期待对方能主动看到你的付出。你需要的是一个懂得珍惜平淡温暖的人。",
    },
    "庚": {
        "core_insight": "你像刀剑之金，果断刚毅，不惧冲突，天生有追求公正和秩序的驱动力。",
        "talent": ["决断力强，在复杂局面中能快速做出选择",
                   "正义感强，不畏惧站出来说话",
                   "执行力好，说了就做，不拖泥带水"],
        "blind_spot": ["有时候过于锋利，无意中伤害了身边的人",
                       "对模糊和低效的容忍度很低，容易焦虑",
                       "不擅长处理需要柔软方式解决的问题"],
        "work_style": "你需要清晰的目标和规则。在模糊、混乱、权责不清的环境里你会非常痛苦。给你明确的权责边界，你会是最高效的执行者和决策者。",
        "relationship": "你在关系中直接而真诚，不玩套路但也期待对方同等的坦诚。你需要一个能和你平等对话、不怕冲突敢于沟通的人。",
    },
    "辛": {
        "core_insight": "你像珠宝之金，精致敏感，追求完美，自带一种不张扬的贵气。",
        "talent": ["品味和审美在线，对品质有天然的判断力",
                   "追求完美，做出来的东西往往超出预期",
                   "感知细腻，能看到别人看不到的微妙的点"],
        "blind_spot": ["容易自我苛责，对自己太狠了",
                       "因为标准高，所以对人对己都容易感到失望",
                       "反复打磨不肯交付，「还不够好」是心魔"],
        "work_style": "你适合需要品味和品质判断的工作。给你打磨的空间，你会产出精品。但如果被催着交「差不多就行」的东西，你会非常痛苦。",
        "relationship": "你在爱里渴望被珍视——像珠宝一样被认真对待。你不一定需要轰轰烈烈，但你需要感觉到自己是对方心中的「特别」。",
    },
    "壬": {
        "core_insight": "你像江河之水，豁达流动，智慧深远，不拘小节，天生适合在大场面中穿梭。",
        "talent": ["思维开阔，能连接不同领域的知识和人脉",
                   "适应力强，在变化和不确定性中反而游刃有余",
                   "沟通能力好，容易和不同背景的人建立连接"],
        "blind_spot": ["有时候过于随性，承诺了但未必落地",
                       "注意力容易分散，对单一事物的深度不够",
                       "不喜欢被约束，常规和规则让你感到束缚"],
        "work_style": "你需要自由和流动感。固定的工位、固定的时间表会让你枯萎。你适合需要跑动、连接、探索的工作。在变化中找到节奏，是你最舒服的状态。",
        "relationship": "你在关系中需要空间和自由，被管太紧会想逃。你需要一个能和你一起探索世界、同时给彼此呼吸感的人。",
    },
    "癸": {
        "core_insight": "你像雨露之水，细腻渗透，直觉敏锐，润物无声但影响深远。",
        "talent": ["直觉极强，很多判断不需要逻辑推理就自然浮现",
                   "共情能力好，能深入理解他人的内心世界",
                   "创造力好，内心世界丰富，灵感源源不断"],
        "blind_spot": ["容易吸收别人的情绪，分不清是自己的还是别人的",
                       "内心世界太丰富，有时候和外部现实脱节",
                       "敏感也意味着容易受伤，需要更长的恢复期"],
        "work_style": "你适合需要深度洞察和创意的工作。给你安静的环境和信任，你的直觉会带你找到意想不到的答案。但嘈杂和高压的环境会干扰你的感知力。",
        "relationship": "你的情感如细雨渗透，不猛烈但深入骨髓。你需要一个能理解你敏感和深度的伴侣——一个能在你不说话时也懂你心情的人。",
    },
}

# ── 星座核心特质 ──
SIGN_TRAITS = {
    "白羊座": {"keyword": "冲锋者", "drive": "竞争与开创", "emotion": "直接热烈，不藏事"},
    "金牛座": {"keyword": "守成者", "drive": "稳定与积累", "emotion": "慢热深沉，认定就不放"},
    "双子座": {"keyword": "漫游者", "drive": "好奇与连接", "emotion": "用脑子谈恋爱，情绪切换快"},
    "巨蟹座": {"keyword": "守护者", "drive": "安全与归属", "emotion": "情绪像潮水，需要被需要"},
    "狮子座": {"keyword": "发光体", "drive": "认可与创造", "emotion": "大方热烈，需要被看见"},
    "处女座": {"keyword": "精修师", "drive": "完善与服务", "emotion": "用行动而非语言表达爱"},
    "天秤座": {"keyword": "平衡者", "drive": "和谐与美感", "emotion": "追求优雅的关系，怕冲突"},
    "天蝎座": {"keyword": "深潜者", "drive": "真相与掌控", "emotion": "爱恨浓烈，非黑即白"},
    "射手座": {"keyword": "探索者", "drive": "自由与意义", "emotion": "热情但怕束缚，需要空间"},
    "摩羯座": {"keyword": "攀登者", "drive": "成就与秩序", "emotion": "爱得深沉但表达克制"},
    "水瓶座": {"keyword": "破局者", "drive": "创新与独立", "emotion": "抽离式冷静，需要精神共鸣"},
    "双鱼座": {"keyword": "造梦者", "drive": "融合与超越", "emotion": "万物皆有灵，爱里容易迷失边界"},
}

# ── 元素气质 ──
ELEMENT_STYLES = {
    "火": {
        "temperament": "你是一团火——热情、直接、需要燃烧。你的生命力在于表达和行动，压抑会让你暗淡。",
        "work_hint": "你适合节奏快、有挑战、需要主动出击的环境。给你一个能点燃你热情的使命，你会发光。",
    },
    "土": {
        "temperament": "你是一座山——稳重、实际、值得依靠。你的力量在于扎根和积累，速成不是你的风格。",
        "work_hint": "你适合需要耐心和积累的领域。给你稳定的环境和清晰的目标，你会建起一座城堡。",
    },
    "风": {
        "temperament": "你是一阵风——自由、流动、善于连接。你的优势在于思维和沟通，被困住会让你枯萎。",
        "work_hint": "你适合需要思考、交流、创新的工作。给你思想的自由和表达的空间，你是天生的连接者。",
    },
    "水": {
        "temperament": "你是一汪深潭——敏感、深邃、直觉敏锐。你的力量在于感受和理解，表面的热闹不是你的主场。",
        "work_hint": "你适合需要深度洞察和共情能力的工作。给你安静和信任，你的直觉比任何分析都精准。",
    },
}

# ── 星宿互动风格 ──
MANSION_RELATIONSHIP_STYLE = {
    "角宿": "你在关系中像团队的领头人，自然吸引追随者。你需要的是一个能和你并肩作战而非仰视你的人。",
    "亢宿": "你在关系中坚定而执着，认定的人就不轻易放手。你需要的是一个同样认真、不玩感情游戏的人。",
    "氐宿": "你在关系中务实而稳重，爱是日积月累的陪伴而非一时的激情。你需要的是一个懂得珍惜日常的人。",
    "房宿": "你在关系中灵动而善变，需要持续的趣味和新鲜感来保持热情。你需要的是一个能和你一起探索世界的人。",
    "心宿": "你在关系中热情而有磁力，容易吸引人但也容易让人有压迫感。你需要的是一个能跟上你节奏但不被吞没的人。",
    "尾宿": "你在关系中主动而勇敢，喜欢就去追，不犹豫不后悔。你需要的是一个能欣赏你直接、不拖泥带水的风格的人。",
    "箕宿": "你在关系中洒脱而自由，不喜欢被束缚和定义。你需要的是一个能给你空间、同时让你心甘情愿想回家的人。",
    "斗宿": "你在关系中正直而严谨，对感情有高标准不轻易开始。你需要的是一个能和你并肩成长、一起变得更好的人。",
    "牛宿": "你在关系中踏实而勤恳，爱是用行动而不是情话表达的。你需要的是一个能看懂你的付出、不把你的好视为理所当然的人。",
    "女宿": "你在关系中细腻而温柔，善于照顾对方的感受。你需要的是一个能回应你的细腻、不让你觉得在唱独角戏的人。",
    "虚宿": "你在关系中多思而敏感，会反复琢磨对方的一句话一个眼神。你需要的是一个能给你安全感、让你觉得不必猜的人。",
    "危宿": "你在关系中敏感而深情，情绪起伏大但也因此爱得深刻。你需要的是一个能理解你的情绪波动、不会说「你想太多了」的人。",
    "室宿": "你在关系中热情而大方，喜欢分享、喜欢让对方开心。你需要的是一个能接住你的热情、也愿意回馈同等温暖的人。",
    "壁宿": "你在关系中深沉而内敛，外面的人看不懂但走进去的人出不来。你需要的是一个愿意花时间了解你、不急于下定论的人。",
    "奎宿": "你在关系中独立而有主见，不会为了迎合对方而改变自己。你需要的是一个尊重你独立性、不试图改造你的人。",
    "娄宿": "你在关系中忠诚而重情义，一旦认定就全身心投入。你需要的是一个同样认真、不随意对待感情的人。",
    "胃宿": "你在关系中温和而包容，善于适应对方的节奏。你需要的是一个不会利用你的温柔、而是珍惜它的人。",
    "昴宿": "你在关系中追求完美，对伴侣和自己都有高要求。你需要的是一个能理解你的精益求精不是挑剔、而是用心的表达的人。",
    "毕宿": "你在关系中热情而冲动，有时爱得太快太猛让自己也措手不及。你需要的是一个能接住你的热情同时帮你踩下刹车的人。",
    "觜宿": "你在关系中聪明而好奇，喜欢和伴侣在智识上碰撞。你需要的是一个能和你「聊得来」、让你觉得有趣的灵魂。",
    "参宿": "你在关系中智慧而深邃，需要精神层面的连接而非表面的搭伙过日子。你需要的是一个能走进你内心世界的人。",
    "井宿": "你在关系中善良而仁慈，容易为对方考虑得太多而忽略自己。你需要的是一个会提醒你「也要照顾好自己」的人。",
    "鬼宿": "你在关系中温顺而坚韧，看起来好说话但内心有自己的底线。你需要的是一个不会因为你温和就随意对待你的人。",
    "柳宿": "你在关系中稳重而实际，注重生活的秩序和节奏。你需要的是一个能和你在日常中找到默契、一起构建生活的人。",
    "星宿": "你在关系中热情而自由，渴望一起冒险和追逐梦想。你需要的是一个能和你并肩奔跑而非站在原地等你的人。",
    "张宿": "你在关系中温柔而有艺术气质，喜欢用浪漫的方式表达爱。你需要的是一个能欣赏你的细腻、也愿意回馈温柔的人。",
    "翼宿": "你在关系中深沉而有策略，不会轻易亮出底牌。你需要的是一个能让你感到安全、愿意卸下防备的人。",
    "轸宿": "你在关系中灵活而善于沟通，能适应不同类型的人。你需要的是一个让你愿意「定下来」而不只是「适应」的人。",
}

# ── 上升星座对外形象 ──
ASCENDANT_STYLES = {
    "白羊座": "你给人的第一印象是直接、有冲劲、不绕弯子。别人会觉得你「不好惹」，但相处久了会发现你的真诚。",
    "金牛座": "你给人的第一印象是沉稳、从容、不急不躁。别人会觉得你「慢悠悠」，但你的每一步都在扎根。",
    "双子座": "你给人的第一印象是聪明、健谈、什么都懂一点。别人会觉得你「很有趣」，但真正了解你的人才知道你的深度。",
    "巨蟹座": "你给人的第一印象是温柔、好相处、让人放下防备。这层外壳保护着你敏感的内心世界。",
    "狮子座": "你给人的第一印象是有气场、有范儿、不容忽视。但这份光芒背后，你也需要被真心看见和认可。",
    "处女座": "你给人的第一印象是专业、靠谱、有标准。别人会来找你解决问题，但你需要被看见的不只是你的能力。",
    "天秤座": "你给人的第一印象是好说话、有品位、让人舒服。你在社交中如鱼得水，但独处时你才能找回自己。",
    "天蝎座": "你给人的第一印象是不好接近、有距离感、让人不敢随意冒犯。这是你的保护色，走近了才知道你的温度。",
    "射手座": "你给人的第一印象是洒脱、随性、好相处。你喜欢这种自由的感觉，但也希望有人能看到你认真的一面。",
    "摩羯座": "你给人的第一印象是靠谱、有规划、不浪费时间。别人依赖你的稳定，但你也需要有人懂你坚硬外壳下的柔软。",
    "水瓶座": "你给人的第一印象是独特、不太一样、有自己的想法。你享受与众不同，但也希望有人能真正理解你的世界。",
    "双鱼座": "你给人的第一印象是柔软、好说话、容易接近。但你内心的边界需要被尊重——不是所有人都值得走进你的世界。",
}

# ── 月亮星座情感需求 ──
MOON_NEEDS = {
    "白羊座": "你需要被热烈地回应。你的情绪来得快去得也快，一个能跟上你节奏、不把小事放大的人最适合你。",
    "金牛座": "你需要稳定和安全感。你的情绪像深井，不轻易波动但一旦动了就很久。你需要一个能给你踏实日常的人。",
    "双子座": "你需要交流和新鲜感。你的情绪通过说话来消化，一个能和你聊到凌晨三点的人就是你最好的情绪出口。",
    "巨蟹座": "你需要被需要的感觉。你的情绪像潮汐，涨落有规律但强度很大。一个能给你安全港湾的人是你情绪的定心丸。",
    "狮子座": "你需要被看见和被欣赏。你的情绪需要观众——一个能看到你光芒、真诚赞美你的人，就是你的充电站。",
    "处女座": "你需要秩序和掌控感。你的情绪通过对事情的整理来消化，一个能尊重你节奏、不给你添乱的人最让你安心。",
    "天秤座": "你需要和谐与陪伴。你的情绪在关系中波动，一个有品位的、能和你一起享受生活美感的人是你最好的慰藉。",
    "天蝎座": "你需要深度和真实。你的情绪浓烈而极致，一个不怕你的深渊、敢和你一起深潜的人才能走进你心里。",
    "射手座": "你需要自由和冒险。你的情绪在探索中释放，一个能陪你一起疯、不给你套上绳索的人是你最舒服的陪伴。",
    "摩羯座": "你需要成就和秩序。你的情绪容易压抑，一个能帮你说出你不敢说的感受、温柔拆解你盔甲的人是你最需要的人。",
    "水瓶座": "你需要空间和理解。你的情绪习惯抽离式处理，一个尊重你独立性、不把「黏人」当爱的人才适合你。",
    "双鱼座": "你需要被温柔对待。你的情绪像海绵吸收周围一切，一个能帮你分清「你的」和「别人的」情绪的人是你最重要的保护伞。",
}


# ═══════════════════════════════════════════
# 报告内容生成
# ═══════════════════════════════════════════

def generate_report_content(chart_data: dict, app_url: str = "") -> dict:
    """从 chart_data 生成报告各部分的个性化文本。

    Returns:
        {
            "title_tagline": str,       # 报告主标题
            "portrait": str,            # Part 1: 一句话画像
            "insights": [dict, dict],   # Part 2: 核心洞察列表
            "talents": [str],           # Part 3: 天赋列表
            "blind_spots": [str],       # Part 3: 盲区列表
            "work_style": str,          # Part 4: 工作场景
            "relationship_style": str,  # Part 4: 关系场景
            "letter_intro": str,        # Part 5: 信的开头
            "qr_text": str,             # 引流文案
        }
    """
    chart = chart_data.get("chart", {})
    bazi = chart_data.get("bazi", {})
    star = chart_data.get("star_mansion", {})

    # ── 提取关键字段 ──
    sun_data = next((p for p in chart.get("planets", []) if p.get("name_en") == "Sun"), {})
    moon_data = next((p for p in chart.get("planets", []) if p.get("name_en") == "Moon"), {})
    sun_sign = sun_data.get("sign", "")
    moon_sign = moon_data.get("sign", "")
    asc_sign = chart.get("ascendant", {}).get("sign", "")
    dominant_element = chart.get("dominant_element", "")

    day_master = bazi.get("day_master", "")
    dm_stem = day_master[0] if day_master else ""
    strength = bazi.get("day_master_strength", "")

    star_name = star.get("name", "")
    star_element = star.get("element", "")

    # ── 查表 ──
    sun_t = SIGN_TRAITS.get(sun_sign, {})
    dm_p = DAY_MASTER_PROFILES.get(dm_stem, {})
    elem_s = ELEMENT_STYLES.get(dominant_element, {})
    asc_s = ASCENDANT_STYLES.get(asc_sign, "")
    moon_n = MOON_NEEDS.get(moon_sign, "")
    star_r = MANSION_RELATIONSHIP_STYLE.get(star_name, "")

    sun_kw = sun_t.get("keyword", sun_sign)

    # ── Part 1: 一句话画像 ──
    portrait = _build_portrait(sun_sign, moon_sign, asc_sign, dm_stem, star_name)

    # ── 主标题 ──
    title_tagline = _build_title(portrait)

    # ── Part 2: 核心洞察 ──
    insights = _build_insights(dm_p, sun_t, star_r, asc_s, dm_stem, strength)

    # ── Part 3: 天赋与盲区 ──
    talents = dm_p.get("talent", ["善于思考", "共情力强", "有创造力"])
    blind_spots = dm_p.get("blind_spot", ["容易内耗", "不善于表达需求", "完美主义倾向"])

    # ── Part 4: 适配场景 ──
    work_style = dm_p.get("work_style", "") + "\n\n" + elem_s.get("work_hint", "")
    relationship_raw = dm_p.get("relationship", "")
    if star_r:
        relationship_style = relationship_raw + "\n\n" + star_r
    else:
        relationship_style = relationship_raw

    # ── Part 5: 一封信 ──
    letter = _build_letter(sun_kw, dm_stem, star_name)

    # ── 引流文案 ──
    qr_text = "想继续探索？扫码开始对话"

    return {
        "title_tagline": title_tagline,
        "portrait": portrait,
        "insights": insights,
        "talents": talents,
        "blind_spots": blind_spots,
        "work_style": work_style,
        "relationship_style": relationship_style,
        "letter": letter,
        "qr_text": qr_text,
        "sun_sign": sun_sign,
        "moon_sign": moon_sign,
        "asc_sign": asc_sign,
        "day_master": day_master,
        "star_name": star_name,
        "dominant_element": dominant_element,
        "strength": strength,
    }


def _build_title(portrait: str) -> str:
    """从画像文本提炼报告标题。"""
    # 取画像的前半段做标题
    short = portrait[:24].rstrip("，。！？；、")
    templates = [
        f"一个{short}的人——你的性格使用说明书",
        f"你比自己想象的更丰富——{short}的性格使用说明书",
        f"「{short}」——一份写给你的性格使用说明书",
    ]
    # 根据长度选模板
    if len(portrait) < 30:
        return templates[0]
    return templates[1]


def _build_portrait(sun_sign: str, moon_sign: str, asc_sign: str, dm_stem: str, star_name: str) -> str:
    """生成一句话画像。"""
    dm_p = DAY_MASTER_PROFILES.get(dm_stem, {})
    dm_core = dm_p.get("core_insight", "")
    # 从日主核心句中提取意象（取「你像…」后面的部分）
    if "你像" in dm_core:
        metaphor = dm_core.split("你像")[1].split("，")[0].split("。")[0]
    else:
        metaphor = "独特而复杂"

    asc_traits_map = {
        "白羊座": "看起来风风火火",
        "金牛座": "看起来不紧不慢",
        "双子座": "看起来什么都懂一点",
        "巨蟹座": "看起来温温柔柔",
        "狮子座": "看起来气场全开",
        "处女座": "看起来一丝不苟",
        "天秤座": "看起来游刃有余",
        "天蝎座": "看起来生人勿近",
        "射手座": "看起来自由洒脱",
        "摩羯座": "看起来沉稳靠谱",
        "水瓶座": "看起来和谁都不一样",
        "双鱼座": "看起来柔柔软软",
    }
    asc_desc = asc_traits_map.get(asc_sign, "看起来很有特点")

    moon_traits_map = {
        "白羊座": "心里住着一个急性子",
        "金牛座": "心里住着一个守财奴",
        "双子座": "心里住着一个好奇宝宝",
        "巨蟹座": "心里住着一个需要被哄的小孩",
        "狮子座": "心里住着一个需要掌声的演员",
        "处女座": "心里住着一个细节控",
        "天秤座": "心里住着一个选择困难症",
        "天蝎座": "心里住着一个深情侦探",
        "射手座": "心里住着一个流浪者",
        "摩羯座": "心里住着一个老干部",
        "水瓶座": "心里住着一个外星人",
        "双鱼座": "心里住着一个诗人",
    }
    moon_desc = moon_traits_map.get(moon_sign, "心里有自己的小世界")

    parts = [
        f"你{asc_desc}，但{moon_desc}。骨子里你是一棵{metaphor}——",
    ]
    return "".join(parts)


def _build_insights(dm_p: dict, sun_t: dict, star_r: str, asc_s: str, dm_stem: str, strength: str) -> list:
    """组装 2-3 个核心洞察。"""
    insights = []

    # 洞察 1：从日主出发
    core = dm_p.get("core_insight", "")
    if core:
        # 补充场景化描述
        blind_spot_1 = dm_p.get("blind_spot", [""])[0]
        insights.append({
            "title": f"洞察一：你的底层驱动力——{dm_stem}木" if dm_stem in "甲乙" else (
                f"洞察一：你的底层驱动力——{dm_stem}火" if dm_stem in "丙丁" else (
                f"洞察一：你的底层驱动力——{dm_stem}土" if dm_stem in "戊己" else (
                f"洞察一：你的底层驱动力——{dm_stem}金" if dm_stem in "庚辛" else (
                f"洞察一：你的底层驱动力——{dm_stem}水")))),
            "body": core,
            "scene": f"这解释了为什么你{blind_spot_1}——这不是你的错，这是你的出厂设置。",
            "question": "这个描述和你对自己的理解一致吗？如果不一致，是哪里不一样？",
        })

    # 洞察 2：从太阳星座 + 上升出发（内外矛盾）
    sun_kw = sun_t.get("keyword", "")
    sun_emotion = sun_t.get("emotion", "")
    if sun_kw and asc_s:
        insights.append({
            "title": "洞察二：你的内外矛盾——社会面具与真实自我",
            "body": f"你的太阳在{sun_t.get('keyword','')}座，内核是「{sun_kw}」。{asc_s}",
            "scene": f"你在外面表现得像一个「{sun_kw}」，{sun_emotion}——但回到家关上门，你其实更敏感、更需要独处或深度连接。这种内外切换有时让你自己也困惑：到底哪一面才是真实的我？答案可能是：两面都是。",
            "question": "你在不同场合切换「面具」的时候，感觉累吗？还是已经习以为常了？",
        })

    # 洞察 3：从星宿出发（关系模式）
    if star_r:
        first_sentence = star_r.split("。")[0] if "。" in star_r else star_r[:50]
        insights.append({
            "title": "洞察三：你的关系底色——为什么你总是被某一类人吸引",
            "body": first_sentence + "。",
            "scene": star_r,
            "question": "回顾你过去的重要关系——这个模式你看到了吗？",
        })

    return insights


def _build_letter(sun_kw: str, dm_stem: str, star_name: str) -> str:
    """生成结尾信。"""
    dm_p = DAY_MASTER_PROFILES.get(dm_stem, {})
    blind_spots = dm_p.get("blind_spot", ["容易内耗", "对自己太苛刻", "不善于表达需求"])

    intro = f"写到这里，我想对你说一句话：你比你想象中更值得被理解。"

    b1 = blind_spots[0] if len(blind_spots) > 0 else "你的纠结"
    b2 = blind_spots[1] if len(blind_spots) > 1 else "你的敏感"
    b3 = blind_spots[2] if len(blind_spots) > 2 else "你的矛盾"

    body = (
        f"你的{b1}不是弱点，是你的天线；"
        f"你的{b2}不是问题，是你的深度；"
        f"你的{b3}不是缺陷，是你的丰富。"
    )

    closing = "这份报告只是一个开始。如果你愿意，我们可以继续聊下去。你不需要一个人面对所有困惑。"

    return f"{intro}\n\n{body}\n\n{closing}"


# ═══════════════════════════════════════════
# PDF 渲染引擎
# ═══════════════════════════════════════════

class ReportPDF(FPDF):

    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_auto_page_break(True, 18)
        # 注册中文字体
        if CN_FONT_PATH:
            self.add_font("CNBody", "", CN_FONT_PATH)
            self.add_font("CNBody", "B", CN_FONT_PATH)
            self.has_cn = True
        else:
            self.has_cn = False

    def header(self):
        """每页自动填充深色背景。"""
        self._fill(BG_DARK)
        self.rect(0, 0, 210, 297, "F")

    # ── helpers ──

    def _c(self, rgb_tuple):
        """设置颜色。"""
        self.set_text_color(*rgb_tuple)
        self.set_draw_color(*rgb_tuple)

    def _fill(self, rgb_tuple):
        self.set_fill_color(*rgb_tuple)

    def _line(self, rgb_tuple):
        self.set_draw_color(*rgb_tuple)

    def _cn(self, text, size=11, style="", color=TEXT_LIGHT):
        """输出中文文本（自动换行）。"""
        if self.x > self.l_margin + 5:
            self.set_x(self.l_margin)
        if self.has_cn:
            self.set_font("CNBody", style, size)
        else:
            self.set_font("Helvetica", style, size)
        self._c(color)
        self.multi_cell(0, size * 1.32, text, align="L")

    def _cn_center(self, text, size=11, style="", color=TEXT_LIGHT):
        if self.has_cn:
            self.set_font("CNBody", style, size)
        else:
            self.set_font("Helvetica", style, size)
        self._c(color)
        self.multi_cell(0, size * 1.45, text, align="C")

    def _section_title(self, text, color=GOLD):
        """区块大标题。"""
        self.ln(3)
        self._cn(text, size=15, style="B", color=color)
        self._draw_divider()
        self.ln(1)

    def _draw_divider(self):
        y = self.get_y()
        self._line(DIVIDER_COLOR)
        self.set_line_width(0.3)
        self.line(20, y, 190, y)
        self.ln(3)

    def _draw_gold_line(self, x1, y1, x2, y2):
        self._line(GOLD)
        self.set_line_width(0.6)
        self.line(x1, y1, x2, y2)

    # ── 页面渲染 ──

    def render_cover(self, content: dict):
        """封面页。"""
        self.add_page()
        # 顶部金色细线
        self._draw_gold_line(20, 38, 190, 38)

        # 小标签
        self._cn("YOUR PERSONALITY USER MANUAL", size=7, color=GOLD)
        self.ln(4)

        # 主标题
        self._cn(content["title_tagline"], size=16, style="B", color=TEXT_LIGHT)
        self.ln(8)

        # 说明
        self._cn("一份基于你的出生信息生成的性格深度报告 · 整合三种分析体系", size=9, color=GRAY_MEDIUM)
        self.ln(8)

        # 底部金色细线
        self._draw_gold_line(20, self.get_y() + 4, 190, self.get_y() + 4)
        self.ln(6)

        # 关键标识
        sun = content.get("sun_sign", "")
        moon = content.get("moon_sign", "")
        asc = content.get("asc_sign", "")
        dm = content.get("day_master", "")
        star = content.get("star_name", "")
        self._cn(f"日{sun} · 月{moon} · 升{asc}   |   {dm} · {star}",
                 size=9, color=GRAY_MEDIUM)

    def render_section_1_portrait(self, content: dict):
        """Part 1: 一句话画像。"""
        self._section_title("一、一句话画像")

        # 大号画像文字
        self.ln(4)
        self._cn(f"「{content['portrait']}」", size=14, style="B", color=TEXT_LIGHT)
        self.ln(4)

        # 辅助文字
        self._cn("这不是算命，这是一面镜子。最终的解释权在你手中——你才是最了解自己的人。", size=9, color=GRAY_MEDIUM)

        # 底部留一个引导
        self.ln(8)
        self._cn("下面，我们来一层一层地打开你的性格操作系统。", size=11, color=GOLD)

    def render_section_2_insights(self, content: dict):
        """Part 2: 底层操作系统。"""
        self.ln(2)
        self._section_title("二、你的底层操作系统")

        self._cn("八字和星宿共同构成了你的「出厂设置」——那些你天生就有的驱动力、反应模式和需求。理解它们，就是理解你自己的第一步。",
                 size=10, color=GRAY_MEDIUM)
        self.ln(6)

        for i, insight in enumerate(content.get("insights", [])):
            # 洞察标题
            self._cn(insight["title"], size=12, style="B", color=GOLD)

            # 主体
            self._cn(insight["body"], size=10, color=TEXT_LIGHT)

            # 场景描述
            if insight.get("scene"):
                self._cn(insight["scene"], size=9, color=GRAY_MEDIUM)

            # 引导提问
            if insight.get("question"):
                self._cn(f"→ {insight['question']}", size=9, style="B", color=GOLD_LIGHTER)

            self.ln(5)

    def render_section_3_talents(self, content: dict):
        """Part 3: 天赋与盲区表格。"""
        self.ln(6)
        self._section_title("三、你的天赋与盲区")

        self._cn("天赋用对了地方是武器，用错了地方是负担。你的盲区不是缺点，只是还没找到正确的使用方法。",
                 size=10, color=GRAY_MEDIUM)
        self.ln(8)

        talents = content.get("talents", [])
        blind_spots = content.get("blind_spots", [])

        # 表格头
        col_w = 82
        row_h = 42
        x_left = 22
        x_right = x_left + col_w + 6

        self._fill(CARD_BG)
        self._c(GOLD)
        self.set_font("CNBody", "B", 12) if self.has_cn else self.set_font("Helvetica", "B", 12)
        y0 = self.get_y()

        # 表头
        self.set_xy(x_left, y0)
        self.cell(col_w, 10, "  你的天赋", border=0, fill=True)
        self.set_xy(x_right, y0)
        self.cell(col_w, 10, "  你的盲区", border=0, fill=True)
        self.ln(14)

        for i in range(max(len(talents), len(blind_spots))):
            t_text = talents[i] if i < len(talents) else ""
            b_text = blind_spots[i] if i < len(blind_spots) else ""

            y_start = self.get_y()

            # 如果行数不够，换页
            if y_start + row_h > 270:
                self.add_page()
                y_start = 30
                self.set_y(y_start)

            bg = CARD_BG if i % 2 == 0 else TABLE_ALT
            self._fill(bg)

            # 左侧天赋
            self.set_xy(x_left, y_start)
            self._c(TEXT_LIGHT)
            self.set_font("CNBody", "", 10) if self.has_cn else self.set_font("Helvetica", "", 10)
            self.multi_cell(col_w, 6.5, f"•  {t_text}", border=0, fill=True)

            y_after_t = self.get_y()

            # 右侧盲区
            self.set_xy(x_right, y_start)
            self._c(GRAY_MEDIUM)
            self.set_font("CNBody", "", 10) if self.has_cn else self.set_font("Helvetica", "", 10)
            self.multi_cell(col_w, 6.5, f"△  {b_text}", border=0, fill=True)

            y_after_b = self.get_y()

            # 对齐行高
            y_end = max(y_after_t, y_after_b)
            self.set_y(y_end + 2)

        # 表格下方总结
        self.ln(6)
        self._cn("你的盲区不是缺点，只是还没找到正确的使用方法。", size=10, style="B", color=GOLD_LIGHTER)
        self.ln(2)
        self._cn("天赋用对了地方是武器，用错了地方是负担。接下来看看哪些场景最适合你。",
                 size=10, color=GRAY_MEDIUM)

    def render_section_4_scenarios(self, content: dict):
        """Part 4: 适配场景。"""
        self.ln(6)
        self._section_title("四、你的适配场景")

        # 工作场景
        self._cn("你适合的工作节奏", size=14, style="B", color=GOLD)
        self.ln(4)
        self._cn(content.get("work_style", ""), size=10, color=TEXT_LIGHT)
        self.ln(4)
        self._cn("如果你想深入了解自己在当前事业选择中的性格反应，可以扫码进入对话页面，和AI助手进行一对一的深度探索。",
                 size=9, color=GRAY_MEDIUM)
        self.ln(12)

        # 关系场景
        self._cn("你适合的关系模式", size=14, style="B", color=GOLD)
        self.ln(4)
        self._cn(content.get("relationship_style", ""), size=10, color=TEXT_LIGHT)
        self.ln(4)
        self._cn("如果你有一段让你困惑的关系想梳理，欢迎来和AI助手聊聊——它会结合你的完整画像帮你理清。",
                 size=9, color=GRAY_MEDIUM)

    def render_section_5_letter(self, content: dict):
        """Part 5: 一封信。"""
        self.ln(6)
        self._section_title("五、一封给你的信")

        self.ln(4)
        self._cn(content.get("letter", ""), size=11, color=TEXT_LIGHT)

        self.ln(12)
        self._cn("——————", size=10, color=GOLD)
        self.ln(8)

        # 署名
        self._cn("你的性格探索助手", size=11, style="B", color=TEXT_LIGHT)
        self.ln(4)
        self._cn("一份基于你的出生信息生成的分析报告", size=8, color=GRAY_MEDIUM)

    def render_footer_cta(self, content: dict, qr_image_path: str = ""):
        """报告末尾引流区域。"""
        self.ln(10)
        self._draw_divider()
        self.ln(4)
        self._cn_center("——————  想继续探索？  ——————", size=12, color=GOLD)
        self.ln(10)

        # QR 码
        if qr_image_path and os.path.exists(qr_image_path):
            self.image(qr_image_path, x=80, y=self.get_y(), w=50, h=50)
            self.ln(56)
        else:
            # 没有 QR 码时显示占位
            self._cn_center("[ 扫码区域 ]", size=11, color=GRAY_MEDIUM)
            self.ln(10)

        self._cn_center("扫码开始对话", size=13, style="B", color=TEXT_LIGHT)
        self.ln(6)
        self._cn_center("这份报告是静态的，但你是动态的。", size=10, color=GRAY_MEDIUM)
        self.ln(3)
        self._cn_center("如果你有具体的问题想聊，欢迎来和AI助手对话。", size=10, color=GRAY_MEDIUM)
        self.ln(3)
        self._cn_center("它会结合你的出生信息，陪你一起梳理。", size=10, color=GRAY_MEDIUM)
        self.ln(12)

        # 底部小字
        self._cn_center("本报告仅供娱乐参考 · 最终判断权在你手中", size=7, color=GRAY_MEDIUM)


# ═══════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════

def generate_pdf(chart_data: dict, app_url: str = "") -> bytes:
    """生成完整的 PDF 报告。

    Args:
        chart_data: 来自 /api/chart 的完整计算数据
        app_url: 前端应用 URL（用于生成 QR 码）

    Returns:
        PDF 文件的 bytes
    """
    content = generate_report_content(chart_data, app_url)

    pdf = ReportPDF()

    # 生成 QR 码
    qr_path = ""
    if app_url:
        try:
            qr_path = _generate_qr(app_url)
        except Exception:
            logger.warning("QR code generation failed", exc_info=True)

    # 逐页渲染
    pdf.render_cover(content)
    pdf.render_section_1_portrait(content)
    pdf.render_section_2_insights(content)
    pdf.render_section_3_talents(content)
    pdf.render_section_4_scenarios(content)
    pdf.render_section_5_letter(content)
    pdf.render_footer_cta(content, qr_path)

    # 清理临时文件
    if qr_path and os.path.exists(qr_path):
        try:
            os.remove(qr_path)
        except OSError:
            pass

    return bytes(pdf.output())


def _generate_qr(url: str) -> str:
    """生成 QR 码 PNG，返回临时文件路径。"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="white", back_color=(13, 13, 19))
    path = "/tmp/report_qr.png"
    img.save(path)
    return path
