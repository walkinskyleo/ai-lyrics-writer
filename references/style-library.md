# 曲风 / 主题 / 语言参数库

本文件供创作时按需加载，提供各参数的措辞规范与 Suno Prompt 对应写法。

## 一、曲风分支

### 1. 现代流行抒情（默认·伤感类）
- 歌词语感：通俗直给、口语化、情绪外放
- Suno Style: `modern pop ballad, sad, 70-80 BPM`
- 典型乐器：piano, strings, light drums, acoustic guitar
- 参考艺人风格：于文文、袁娅维、薛之谦

### 2. R&B
- 歌词语感：转音多、节奏切分、慵懒性感、情绪内敛
- Suno Style: `contemporary R&B, soulful, slow jam, 75-85 BPM`
- 典型乐器：electric piano, bass, drums, synth pad, ad-libs
- 参考艺人风格：方大同、陶喆、The Weeknd

### 3. 民谣
- 歌词语感：叙事性强、画面感稍多、质朴真诚、娓娓道来
- Suno Style: `folk pop, acoustic, storytelling, 75-90 BPM`
- 典型乐器：acoustic guitar, harmonica, light percussion, strings
- 参考艺人风格：赵雷、陈鸿宇、宋冬野

### 4. 说唱
- 歌词语感：节奏密集、flow 变化、押韵密集、态度鲜明
- Suno Style: `hip hop, rap, emotional, 85-100 BPM`
- 典型乐器：808 drums, bass, piano loop, synth
- 注意：副歌仍需 Hook 金句，主歌 flow 可自由
- 参考艺人风格：Jony J、艾热、GAI

### 5. 古风
- 歌词语感：文言与白话结合、意象古典（月/酒/剑/花/雪）、情绪含蓄
- Suno Style: `chinese ancient style, gufeng, cinematic, 70-85 BPM`
- 典型乐器：guzheng, dizi, erhu, piano, strings
- 参考艺人风格：银临、河图、HITA

### 6. 电子
- 歌词语感：短句重复、节奏感强、未来感、情绪直接
- Suno Style: `electronic pop, EDM, synthwave, 100-128 BPM`
- 典型乐器：synth, drums, bass, pads, arpeggiator
- 参考艺人风格：蔡徐坤、刘柏辛、Charli XCX

## 二、主题分支

| 主题 | 核心情绪 | 典型关键词 | 适配曲风 |
|---|---|---|---|
| 爱情伤感（默认） | 遗憾、错过、意难平、自我拉扯 | 错过、遗憾、放不下、告别、想念 | 流行抒情、R&B、民谣 |
| 友情 | 陪伴、离别、珍惜、成长 | 兄弟、朋友、一起、岁月、干杯 | 民谣、流行、说唱 |
| 亲情 | 感恩、愧疚、思念、时光 | 妈妈、爸爸、家、白发、时光 | 流行抒情、民谣 |
| 成长励志 | 蜕变、坚持、不服输、自愈 | 梦想、坚持、自己、未来、勇敢 | 流行、说唱、电子 |
| 城市孤独 | 疏离、漂泊、深夜、麻木 | 城市、深夜、地铁、一个人、霓虹 | R&B、电子、流行抒情 |
| 治愈释怀 | 放下、和解、温柔、向前看 | 放下、和解、温柔、明天、光 | 民谣、流行抒情 |

## 三、语言分支

### 1. 国语（默认）
- 所有规则直接适用。

### 2. 粤语
- 歌词用粤语口语/书面语，注意粤语九声六调的押韵（粤语韵脚比国语更丰富）；
- Suno Style 加 `cantonese pop`；
- 参考：陈奕迅、张国荣、杨千嬅的粤语词作；
- 避免国语词直接翻译成粤语（如"什么"→"咩"/"乜"，"的"→"嘅"）。

### 3. 英文
- 歌词用英文，注意英文流行歌的常见句式（短句、省略、口语化）；
- 押韵用英文韵脚（AABB / ABAB / 自由韵）；
- Suno Style 正常写英文；
- 副歌 Hook 必须是英文金句（8-12 words）。

## 四、人声风格参考写法

用户指定人声参考时，写入 Suno Prompt 的 Vocal 字段：

| 参考艺人 | Vocal 描述关键词 |
|---|---|
| 薛之谦 | male, warm, slightly husky, breathy tail, emotional falsetto |
| 林俊杰 | male, clear, bright, powerful high notes, smooth R&B runs |
| 陈奕迅 | male, deep, rich, narrative, restrained emotion |
| 周杰伦 | male, unique timbre, mumble-style, R&B inflections |
| 邓紫棋 | female, powerful, belting, emotional, wide range |
| 田馥甄 | female, clear, airy, delicate, indie-pop tone |
| 袁娅维 | female, soulful, R&B runs, powerful, ad-libs |
| 于文文 | female, husky, rock-inflected, emotional, mid-range |

未指定时按曲风自动匹配默认人声描述。
