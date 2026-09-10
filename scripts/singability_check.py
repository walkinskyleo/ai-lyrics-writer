#!/usr/bin/env python3
"""
可唱性自动检测脚本 + 质量评分（v3 放宽版）

修复记录：
v2（2026-09-09）：
1. 韵脚检测改用 pypinyin（Style.FINALS + 多音字），按韵组归一化（an/ian/uan 同一韵等），
   不再依赖存在大量错配与常用字缺失的静态 FINAL_MAP；无 pypinyin 时回退到内置常用字韵母表。
2. 修复 'chorus' in tag 子串误判：prechorus 不再被套用副歌韵脚规则，报错文案改为动态段落名。
3. 画面描写（≤4 句）计入总分（5 分），情绪递进 10 分，总分仍为 100。
4. 新增硬性门禁：Hook / 副歌韵脚(≥60%) / 字数合规(≥80%) / 情绪递进 / Call-back / 结构完整 /
   画面≤2 句，任一不达标即 FAIL（退出码 1），不再出现"多项规则失败仍 PASS"。
5. 达标线提高：≥85 分 PASS，60-84 分 WARN，<60 分或硬门禁失败 FAIL。

v3（2026-09-09）：放宽检测规则，与创作规范对齐，消除"合格成品被 FAIL"：
1. 情绪递进改为容差制：预副歌均值允许高于主歌 ≤2.0 字，副歌均值允许低于主歌 ≤2.0 字
   （Hook 拆短行、短句堆叠会拉低副歌均值，属规范允许写法），不再要求严格"副歌必长于主歌"。
2. Hook 检测支持拆行 Hook：单行 8-12 字，或相邻两行合并（去标点）合计 8-16 字
   （规范允许 Hook 拆为两行留气口，如"说散就散是嘴硬，翻聊天记录才是真心"）。
3. 画面描写判定优化并放宽：删除时间词与弱生活词（外套/手机/天亮等易误判词），
   补充具象画面词（灰头像/玄关/纸箱/走廊/聊天记录等），画面句数 ≤4 句、不设下限（硬门禁，与创作规范对齐）。
4. 副歌韵脚门禁保持取各副歌实例最高统一度（放宽口径），但报告打印每个副歌实例的
   韵脚统一度明细，供人工复核。
5. 修复 v2 注释与实现不符：重复片段排序为"按新歌词首次出现位置"。

检测项目：
1. 每句字数 5-12 字（Bridge/Outro 短句豁免）
2. 同一段落韵脚统一度（副歌 ≥60% 为硬门禁，取实例最高值）
3. 副歌 Hook 存在性（单行8-12字 / 相邻两行合并8-16字）
4. 画面描写句数（≤4句，不设下限，硬门禁；仅统计主歌段落）
5. 尾声 Call-back（复现副歌关键词）
6. 结构完整性
7. 情绪递进（容差制：预副歌≤主歌+2.0字，副歌≥主歌-2.0字）

质量评分（0-100）：
- Hook 质量 20分
- 韵脚统一度 15分
- 字数合规率 15分
- 情绪递进 10分
- Call-back 15分
- 结构完整 20分
- 画面克制 5分

用法：
    python singability_check.py <成品歌词.txt>
    python singability_check.py <成品歌词.txt> --json  # 输出JSON格式
"""

import sys
import re
import json
import argparse
from pathlib import Path

try:
    from pypinyin import lazy_pinyin, Style as PyStyle
    PY_AVAILABLE = True
except ImportError:
    PY_AVAILABLE = False

# ============================================================
# 韵组归一化表（pypinyin 韵母 -> 押韵组）
# 按歌词押韵习惯分组：an/ian/uan/üan 同押 an 韵，ang/iang/uang 同押 ang 韵，等。
# ============================================================
RHYME_GROUP_MAP = {
    'a': 'a', 'ia': 'a', 'ua': 'a',
    'o': 'o', 'uo': 'o',
    'e': 'e', 'ie': 'e', 've': 'e', 'ue': 'e', 'er': 'e',
    'an': 'an', 'ian': 'an', 'uan': 'an', 'van': 'an', 'uan2': 'an',
    'ang': 'ang', 'iang': 'ang', 'uang': 'ang',
    'ao': 'ao', 'iao': 'ao',
    'ou': 'ou', 'iu': 'ou', 'iou': 'ou',
    'ai': 'ai', 'uai': 'ai',
    'ei': 'ei', 'ui': 'ei', 'uei': 'ei',
    'i': 'i', 'u': 'u', 'v': 'ü',
    'in': 'in', 'ing': 'ing',
    'un': 'un', 'vn': 'un', 'uen': 'un',
    'ong': 'ong', 'iong': 'ong',
    'en': 'en', 'eng': 'eng', 'ueng': 'eng',
}

# ============================================================
# 离线回退常用字韵母表（仅当 pypinyin 不可用时使用）
# 按韵组分组的常用字；多音字只取最常见读音，精度低于 pypinyin。
# ============================================================
_CURATED = {
    'a': '啊阿吧把爸罢霸拔八差查茶察岔达答打大发法罚哈花华滑画话化划家加佳夹甲假价架嫁卡拉啦妈麻马码骂嘛拿哪那怕爬帕撒沙纱傻啥她他它塔踏挖瓦袜呀牙哑亚压扎咋炸眨下夏霞虾',
    'o': '哦波播伯博拨破婆迫摸模磨摩墨佛多朵躲夺舵惰拖脱托驼妥拓挪诺罗螺逻落络洛锅国果过裹阔扩活火伙货或祸桌捉卓说烁硕缩所索锁作做坐座左昨措错挫窝卧握我',
    'e': '歌哥格阁个各喝合河何荷和贺热惹这遮折哲车扯彻蛇舌舍射涉色涩侧测策册则责择泽客课克刻可科棵颗额饿鹅乐了别憋跌爹碟蝶叠铁贴帖捏聂列烈裂猎接节杰洁结解姐界借介届街阶切且怯写谢卸懈血学雪靴穴月越约悦阅岳跃缺却决绝觉',
    'an': '安半伴办暗岸残惨餐参惭灿单胆淡但蛋凡烦反返泛感敢赶干寒喊汉汗含涵间简见件建健剑渐脸连恋练怜满慢漫难男南判盼然燃染散伞三山闪善谈弹叹探完玩晚万挽弯先现线限选显险言眼演艳燕验远圆原愿怨院站战占展穿传串川船团暖关欢换唤环还缓幻湾碗婉缘源权全圈劝泉悬绚倦卷转专砖',
    'ang': '昂帮棒榜傍仓藏苍长常场唱尝床创窗当党挡荡方房防放访芳刚钢港岗行航将讲奖酱江康抗浪狼郎朗忙盲茫旁胖强墙抢枪让伤商上尚汤堂糖躺烫王网往望忘旺乡想响向像象香箱详享项巷羊阳样养洋仰痒葬脏丈仗帐账胀涨掌障光广逛黄荒慌皇晃况矿框双爽霜庄装状撞壮',
    'ao': '熬傲奥包宝保抱报暴爆跑泡抛毛矛帽冒刀导岛倒到道盗涛掏逃桃陶淘讨套脑恼闹劳牢老高搞稿告烤靠好号浩招找照超朝潮吵炒少烧稍绕早澡造草骚扫飘漂票表标苗描秒妙庙掉吊钓调叼鸟尿叫教交娇胶脚角敲桥瞧巧俏窍小笑孝校晓消销宵邀腰妖摇遥谣尧咬要耀药条跳挑',
    'ou': '欧鸥偶抽仇绸愁筹丑臭抖斗豆逗透偷投头楼搂漏陋谋眸某亩牛扭纽柔揉肉收手首守寿受瘦售熟走奏凑够购构沟狗口扣候猴喉吼后厚就九久酒救旧秋球求休修羞秀袖流留柳六刘邮忧优由游有友右又幼幽油尤',
    'ai': '爱哀挨矮碍白百摆败拜采彩菜猜才材财该改盖概开凯来赖埋买卖奶乃耐排牌拍派赛腮台抬太态泰外歪快块筷怀坏帅摔甩衰摘宅窄债在再载海孩',
    'ei': '杯背悲贝倍被备北配赔培陪佩没梅媒眉美妹味位为违围唯维伟伪尾未畏卫谓飞非肥费废累泪雷类内给黑谁水睡税随岁碎穗推腿退归规贵鬼柜亏会回灰挥辉毁悔惠慧汇对队堆追坠最罪醉嘴吹垂锤脆催翠威危微',
    'i': '一衣医依伊仪宜姨遗移疑以已椅义亿艺忆议亦异役易疫益谊逸意溢毅翼译比必闭壁避笔彼鼻皮疲脾匹屁迷弥米密密蜜低滴笛敌底抵地第帝递弟提题蹄体替泥尼你逆腻离梨理里李礼力立粒栗历厉机鸡积基激击吉极集及急级挤几己纪记技际济寄寂计期欺妻七齐奇骑棋启起气弃泣器西希稀息惜熄喜洗系戏细知织之支枝执直值职指止只纸志制治质致置智吃痴迟持尺齿赤翅师狮施湿失十石时识实拾史使驶始士世市示事是适逝释誓日资姿滋子字自紫此次刺词辞慈思丝私死四寺似',
    'u': '乌污屋无吴吾梧五午伍武舞物误悟雾不布步部怖补捕普谱扑铺仆蒲葡母亩木目牧穆夫肤扶服浮符幅福抚府腐父付附妇负富副复赋覆都督毒读独堵赌杜肚度渡妒路露鹿录陆卢炉鲁绿律虑旅吕屡缕略掠姑孤辜估股骨鼓古谷故顾固枯哭苦酷库裤呼乎忽糊狐胡虎互户护朱珠株猪诸逐竹烛主著柱助住注驻祝铸筑出初除厨楚处触书舒输蔬梳殊叔淑熟暑署鼠属术束树竖数如乳辱入儒汝若弱租足卒族阻组祖苏素速宿塑诉醋粗促',
    'ü': '女绿吕律虑旅缕曲取去趣区渠虚需须许絮叙序徐续鱼余于雨语玉域遇欲郁狱预愈育浴裕愚娱愉渔迂',
    'in': '心新欣辛信芯馨金今斤津禁尽近进紧仅锦亲琴勤侵寝沁民敏品贫频林临淋邻您因音阴银引隐印饮姻吟宾彬滨濒',
    'ing': '冰兵丙柄饼并病丁顶定订亭停庭挺艇听厅青清轻情晴请庆星行形型醒幸性姓京经精睛惊井景警境镜敬静净竞竟灵零龄铃岭领令另明名鸣命宁凝平评萍凭瓶屏英应樱婴鹰迎盈营影映硬赢',
    'un': '温瘟文纹闻蚊吻稳问浑混昏婚魂困昆坤轮伦沦论尊遵存村寸孙损吞屯顿盾蹲春纯唇蠢顺瞬准润闰迅讯训巡循旬勋熏云运韵允孕晕匀陨君军均菌俊骏裙群郡',
    'ong': '东冬懂动冻洞通同童铜统痛农浓弄龙笼聋隆垄公功攻宫恭供巩共贡空孔恐控红洪宏虹鸿中钟终忠衷肿种重众冲虫崇宠松耸送宋容融熔荣绒冗从丛匆葱聪工弓兄胸雄熊穷琼拥庸永勇涌用',
    'en': '恩奔本笨喷盆闷门们分纷芬粉份奋愤根跟很狠恨痕肯恳申伸身深神沈审婶肾甚渗慎认任忍刃韧人仁怎诊枕阵镇震真针珍尘沉陈衬趁辰晨',
    'eng': '风丰封疯峰锋蜂逢缝讽凤奉灯登等凳瞪更庚耕耿亨哼横衡恒轰烘冷愣蒙萌盟猛梦孟能朋鹏棚蓬捧碰扔仍僧疼腾藤增憎曾赠层蹭称城诚成承程乘惩撑澄圣胜盛剩升生声牲省绳政挣睁征争整正证郑症',
}

CURATED_FINALS = {}
for _g, _chars in _CURATED.items():
    for _c in _chars:
        CURATED_FINALS.setdefault(_c, _g)
_CURATED.clear()


def normalize_final(fin):
    """将 pypinyin 韵母归一到押韵组；无法归一时返回 None。"""
    fin = (fin or '').strip()
    if not fin:
        return None
    if fin == 'r':  # 儿化
        fin = 'er'
    return RHYME_GROUP_MAP.get(fin)


def get_rhyme_groups(char):
    """获取一个汉字可能押韵的韵组集合（支持多音字）。"""
    groups = set()
    if not char:
        return groups
    if PY_AVAILABLE:
        try:
            finals = lazy_pinyin(char, style=PyStyle.FINALS, heteronym=True)
        except Exception:
            finals = []
        for item in finals:
            if isinstance(item, list):
                for f in item:
                    g = normalize_final(f)
                    if g:
                        groups.add(g)
            else:
                g = normalize_final(item)
                if g:
                    groups.add(g)
    if not groups:
        g = CURATED_FINALS.get(char)
        if g:
            groups.add(g)
    return groups


# 画面描写关键词（用于检测画面句数）
# v3 调整：删除易误判的时间词（凌晨/深夜/天亮等，属氛围非画面）与弱生活词（外套/手机等），
# 补充具象可感画面词（灰头像/玄关/纸箱/走廊/聊天记录等），与创作规范"具象画面点缀"语义对齐。
VISUAL_KEYWORDS = [
    '路灯', '窗外', '街角', '房间', '照片', '合照', '灰头像', '头像', '杯子', '咖啡', '雨', '雪', '风', '月', '星',
    '街', '路', '车', '楼', '窗', '门', '墙', '桌', '椅', '床', '灯', '花', '树', '海', '河', '山',
    '影子', '背影', '身影', '笑容', '眼泪', '手心', '指尖', '头发', '围巾', '戒指', '项链',
    '屏幕', '信', '纸条', '车票', '机票', '钥匙', '玄关', '门牌号', '纸箱', '走廊', '抽屉', '电梯',
    '天台', '阳台', '沙发', '枕头', '窗帘', '台灯', '蜡烛', '打火机', '烟灰缸', '聊天记录',
    '便利店', '超市', '餐厅', '烟花', '落叶', '路灯下', '屋檐', '台阶', '斑马线', '红绿灯',
]


def clean_line(line):
    """清理歌词行，去掉标点和空格，返回纯汉字"""
    return re.sub(r'[^\u4e00-\u9fff]', '', line)


def count_chars(line):
    """统计一行中的汉字数"""
    return len(clean_line(line))


def is_visual_line(line):
    """判断一行是否包含画面描写关键词"""
    for kw in VISUAL_KEYWORDS:
        if kw in line:
            return True
    return False


def parse_lyrics(filepath):
    """解析成品文件，提取歌词段落（兼容 TXT 的【原创歌词】标记与 MD 的"## 原创歌词"标题）"""
    text = Path(filepath).read_text(encoding='utf-8')
    # 提取【原创歌词】/## 原创歌词 到 歌曲简介/发布物料 之间的内容
    match = re.search(r'(?:【原创歌词】|##\s*原创歌词)(.*?)(?:【歌曲简介】|##\s*歌曲简介|【发布物料】|##\s*发布物料|$)', text, re.DOTALL)
    if not match:
        return {}
    lyrics_text = match.group(1)
    segments = {}
    current_tag = None
    current_lines = []
    for line in lyrics_text.split('\n'):
        line = line.strip()
        tag_match = re.match(r'\[(Verse\s*\d*|Pre-Chorus|Chorus|Bridge|Outro|Intro|Hook|Interlude)\]', line, re.IGNORECASE)
        if tag_match:
            if current_tag:
                segments.setdefault(current_tag, []).append(current_lines)
            current_tag = tag_match.group(1).lower().replace(' ', '')
            current_lines = []
        elif line.startswith('`'):
            continue  # 跳过 MD 代码围栏行（```text / ```）
        elif line and not line.startswith('（') and not line.startswith('('):
            current_lines.append(line)
    if current_tag and current_lines:
        segments.setdefault(current_tag, []).append(current_lines)
    return segments


def check_word_count(segments):
    """检查每句字数 5-12 字（Bridge/Outro 短句豁免）"""
    issues = []
    total = 0
    valid = 0
    for tag, instances in segments.items():
        is_bridge_or_outro = 'bridge' in tag or 'outro' in tag
        for lines in instances:
            for line in lines:
                chars = count_chars(line)
                if chars == 0:
                    continue
                total += 1
                if is_bridge_or_outro and chars <= 4:
                    valid += 1  # 桥段/尾声短句豁免
                    continue
                if 5 <= chars <= 12:
                    valid += 1
                else:
                    issues.append(f"[{tag}] {line.strip()} ({chars}字)")
    rate = valid / total if total > 0 else 0
    return rate, issues, total, valid


def check_rhyme(segments):
    """检查同一段落韵脚统一度（副歌为硬门禁，取各副歌实例中的最高统一度）"""
    issues = []
    segment_stats = []
    chorus_rates = []
    for tag, instances in segments.items():
        for idx, lines in enumerate(instances):
            counts = {}
            total_finals = 0
            for line in lines:
                cleaned = clean_line(line)
                if not cleaned:
                    continue
                groups = get_rhyme_groups(cleaned[-1])
                if not groups:
                    continue
                total_finals += 1
                for g in groups:
                    counts[g] = counts.get(g, 0) + 1
            if total_finals == 0:
                continue
            dominant, dom_count = max(counts.items(), key=lambda kv: kv[1])
            rate = dom_count / total_finals
            segment_stats.append((tag, idx, rate, dominant, total_finals))
            if tag == 'chorus':
                chorus_rates.append(rate)
            if tag == 'chorus' and rate < 0.6:
                issues.append(f"[{tag}#{idx+1}] 韵脚不统一（{dominant}韵占{rate:.0%}，需≥60%）")
    overall_rate = sum(s[2] for s in segment_stats) / len(segment_stats) if segment_stats else 0
    chorus_rate = max(chorus_rates) if chorus_rates else 0
    return overall_rate, issues, segment_stats, chorus_rate


def check_hook(segments):
    """检查副歌 Hook：单行 8-12 字，或相邻两行合并（去标点）合计 8-16 字（拆行 Hook，v3）"""
    chorus_segments = segments.get('chorus', [])
    if not chorus_segments:
        return False, "未找到副歌段落", 0
    max_len = 0
    hook_line = None
    for lines in chorus_segments:
        cleaned_lines = [clean_line(l) for l in lines]
        for i, cleaned in enumerate(cleaned_lines):
            chars = len(cleaned)
            # 单行 8-12 字
            if 8 <= chars <= 12 and chars > max_len:
                max_len = chars
                hook_line = lines[i].strip()
            # 拆行 Hook：当前行 + 下一行合并 8-16 字（去掉标点）
            if i + 1 < len(cleaned_lines):
                combined = cleaned + cleaned_lines[i + 1]
                if 8 <= len(combined) <= 16 and len(combined) > max_len:
                    max_len = len(combined)
                    hook_line = lines[i].strip() + "，" + lines[i + 1].strip()
    if hook_line:
        return True, hook_line, max_len
    return False, "副歌未找到Hook句（单行8-12字或相邻两行合并8-16字）", max_len


def check_visual(segments):
    """检查画面描写句数 ≤4（不设下限，与创作规范"画面点缀≤4句"对齐）"""
    count = 0
    visual_lines = []
    for tag, instances in segments.items():
        if 'verse' in tag:  # 只统计主歌中的画面描写
            for lines in instances:
                for line in lines:
                    if is_visual_line(line):
                        count += 1
                        visual_lines.append(f"[{tag}] {line.strip()}")
    return count, visual_lines


def check_callback(segments):
    """检查尾声是否复现副歌关键词"""
    chorus_segments = segments.get('chorus', [])
    outro_segments = segments.get('outro', [])
    if not chorus_segments or not outro_segments:
        return False, "未找到副歌或尾声段落"
    # 提取副歌高频词（2字词）
    chorus_words = set()
    for lines in chorus_segments:
        for line in lines:
            cleaned = clean_line(line)
            for i in range(len(cleaned) - 1):
                chorus_words.add(cleaned[i:i + 2])
    # 检查尾声是否包含副歌关键词
    outro_text = ''
    for lines in outro_segments:
        for line in lines:
            outro_text += clean_line(line)
    matched = []
    for word in chorus_words:
        if word in outro_text and len(word) == 2:
            matched.append(word)
    if matched:
        return True, f"尾声复现副歌关键词: {', '.join(matched[:5])}"
    return False, "尾声未复现副歌关键词"


def check_structure(segments):
    """检查结构完整性"""
    required = ['verse', 'chorus']
    missing = []
    for req in required:
        if not any(req in tag for tag in segments.keys()):
            missing.append(req)
    has_bridge = any('bridge' in tag for tag in segments.keys())
    has_outro = any('outro' in tag for tag in segments.keys())
    return missing, has_bridge, has_outro


def check_emotional_progression(segments):
    """检查情绪递进（v3 容差制）：预副歌均值 ≤ 主歌+1.5字，副歌均值 ≥ 主歌-1.5字"""
    verse_total = 0
    pre_total = 0
    chorus_total = 0
    verse_count = 0
    pre_count = 0
    chorus_count = 0
    for tag, instances in segments.items():
        for lines in instances:
            for line in lines:
                chars = count_chars(line)
                if chars == 0:
                    continue
                if 'verse' in tag:
                    verse_total += chars
                    verse_count += 1
                elif 'pre' in tag:
                    pre_total += chars
                    pre_count += 1
                elif 'chorus' in tag:
                    chorus_total += chars
                    chorus_count += 1
    verse_avg = verse_total / verse_count if verse_count else 0
    pre_avg = pre_total / pre_count if pre_count else 0
    chorus_avg = chorus_total / chorus_count if chorus_count else 0
    # 容差制：预副歌可复制主歌节奏（允许略长），副歌允许因 Hook 拆短行而略短
    PRE_TOLERANCE = 2.0   # 预副歌均值可高于主歌均值的容差（字）
    CHORUS_TOLERANCE = 2.0  # 副歌均值可低于主歌均值的容差（字，短句/Hook拆行）
    pre_ok = (pre_count == 0) or (pre_avg <= verse_avg + PRE_TOLERANCE)
    chorus_ok = chorus_avg >= verse_avg - CHORUS_TOLERANCE
    has_progression = pre_ok and chorus_ok
    return has_progression, verse_avg, pre_avg, chorus_avg


def run_check(filepath, output_json=False):
    """运行全部检测，返回报告"""
    segments = parse_lyrics(filepath)
    if not segments:
        print("❌ 无法解析歌词，请检查文件格式")
        sys.exit(1)

    # 各项检测
    wc_rate, wc_issues, wc_total, wc_valid = check_word_count(segments)
    rhyme_rate, rhyme_issues, rhyme_stats, chorus_rhyme_rate = check_rhyme(segments)
    hook_ok, hook_msg, hook_len = check_hook(segments)
    visual_count, visual_lines = check_visual(segments)
    callback_ok, callback_msg = check_callback(segments)
    missing, has_bridge, has_outro = check_structure(segments)
    prog_ok, verse_avg, pre_avg, chorus_avg = check_emotional_progression(segments)

    # 质量评分（满分 100）
    score_hook = 20 if hook_ok else 0
    score_rhyme = int(15 * chorus_rhyme_rate)
    score_word = int(15 * wc_rate)
    score_prog = 10 if prog_ok else 5
    score_callback = 15 if callback_ok else 0
    score_visual = 5 if visual_count <= 4 else 0
    score_structure = 20
    if missing:
        score_structure -= 10
    if not has_bridge:
        score_structure -= 3
    if not has_outro:
        score_structure -= 3
    score_structure = max(0, score_structure)
    total_score = (score_hook + score_rhyme + score_word + score_prog +
                   score_callback + score_visual + score_structure)

    # 硬性门禁：任一失败即 FAIL
    failed_gates = []
    if not hook_ok:
        failed_gates.append('Hook金句')
    if chorus_rhyme_rate < 0.6:
        failed_gates.append('副歌韵脚统一(≥60%)')
    if wc_rate < 0.8:
        failed_gates.append('字数合规(≥80%)')
    if not prog_ok:
        failed_gates.append('情绪递进')
    if not callback_ok:
        failed_gates.append('Call-back')
    if missing:
        failed_gates.append('结构完整')
    if visual_count > 4:
        failed_gates.append('画面≤4句')

    if failed_gates or total_score < 60:
        verdict = 'FAIL'
        passed = False
    elif total_score >= 85:
        verdict = 'PASS'
        passed = True
    else:
        verdict = 'WARN'
        passed = True

    # 输出报告
    report = {
        'file': filepath,
        'total_score': total_score,
        'verdict': verdict,
        'failed_gates': failed_gates,
        'checks': {
            'hook': {'pass': hook_ok, 'score': score_hook, 'message': hook_msg},
            'rhyme': {'pass': chorus_rhyme_rate >= 0.6, 'score': score_rhyme, 'chorus_rate': f"{chorus_rhyme_rate:.0%}", 'overall_rate': f"{rhyme_rate:.0%}", 'issues': rhyme_issues},
            'word_count': {'pass': wc_rate >= 0.8, 'score': score_word, 'rate': f"{wc_rate:.0%}", 'issues': wc_issues},
            'emotional_progression': {'pass': prog_ok, 'score': score_prog, 'verse_avg': f"{verse_avg:.1f}", 'pre_avg': f"{pre_avg:.1f}", 'chorus_avg': f"{chorus_avg:.1f}"},
            'callback': {'pass': callback_ok, 'score': score_callback, 'message': callback_msg},
            'structure': {'pass': not missing, 'score': score_structure, 'missing': missing, 'has_bridge': has_bridge, 'has_outro': has_outro},
            'visual_lines': {'pass': visual_count <= 4, 'score': score_visual, 'count': visual_count, 'lines': visual_lines},
        }
    }

    if output_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print("🎵 可唱性检测报告 + 质量评分（v3）")
        print("=" * 50)
        print(f"文件: {filepath}")
        print(f"总评分: {total_score}/100")
        print(f"引擎: {'pypinyin' if PY_AVAILABLE else '内置韵母表(离线回退)'}")
        print("-" * 50)
        print(f"[Hook] {'✅' if hook_ok else '❌'} {hook_msg} ({score_hook}/20)")
        print(f"[韵脚统一] {'✅' if chorus_rhyme_rate >= 0.6 else '❌'} 副歌统一度 {chorus_rhyme_rate:.0%}（全文均值 {rhyme_rate:.0%}）({score_rhyme}/15)")
        for tag, idx, rate, dominant, total in rhyme_stats:
            if tag == 'chorus':
                print(f"       - [Chorus#{idx+1}] {dominant}韵 {rate:.0%}（{total}句）")
        if rhyme_issues:
            for iss in rhyme_issues[:3]:
                print(f"       - {iss}")
        print(f"[字数合规] {'✅' if wc_rate >= 0.8 else '❌'} 合规率 {wc_rate:.0%} ({wc_valid}/{wc_total}句) ({score_word}/15)")
        if wc_issues:
            for iss in wc_issues[:3]:
                print(f"       - {iss}")
        print(f"[情绪递进] {'✅' if prog_ok else '❌'} 主歌{verse_avg:.1f}字/预副歌{pre_avg:.1f}字/副歌{chorus_avg:.1f}字（容差:预≤主+2.0 副≥主-2.0）({score_prog}/10)")
        print(f"[Call-back] {'✅' if callback_ok else '❌'} {callback_msg} ({score_callback}/15)")
        print(f"[结构完整] {'✅' if not missing else '❌'} 缺失:{missing if missing else '无'} 桥段:{'有' if has_bridge else '无'} 尾声:{'有' if has_outro else '无'} ({score_structure}/20)")
        print(f"[画面克制] {'✅' if visual_count <= 4 else '❌'} {visual_count}句 (≤4句) ({score_visual}/5)")
        if visual_lines:
            for vl in visual_lines:
                print(f"       - {vl}")
        print("-" * 50)
        if failed_gates:
            print(f"❌ FAIL — 硬门禁未通过: {'、'.join(failed_gates)}")
        elif total_score >= 85:
            print("✅ PASS — 可唱性良好，质量达标")
        elif total_score >= 60:
            print("⚠️ WARN — 可唱性一般，建议优化")
        else:
            print("❌ FAIL — 可唱性不足，请修改后重检")

    return passed


def main():
    parser = argparse.ArgumentParser(description='可唱性自动检测 + 质量评分')
    parser.add_argument('filepath', help='成品歌词TXT文件路径')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')
    args = parser.parse_args()
    if not Path(args.filepath).exists():
        print(f"❌ 文件不存在: {args.filepath}")
        sys.exit(2)
    passed = run_check(args.filepath, output_json=args.json)
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
