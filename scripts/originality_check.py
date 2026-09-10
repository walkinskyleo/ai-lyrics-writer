#!/usr/bin/env python3
"""
原创性自检脚本 - Ai Lyrics Writer（AI歌词创作器）Skill

将新创作的歌词与原曲歌词做 n-gram 重复率比对，
检测是否存在无意识抄袭或洗稿。

用法:
    python originality_check.py <新歌词文件> <原曲歌词文件> [--ngram N] [--threshold T]

参数:
    新歌词文件    创作完成的歌词 TXT 文件路径
    原曲歌词文件  参考歌曲的原版歌词 TXT 文件路径
    --ngram N     n-gram 大小，默认 4（中文按字计算）
    --threshold T 重复率阈值（百分比），默认 5.0，超过则报警

输出:
    - 总重复率（%）
    - 重复片段列表（前 10 条）
    - PASS / FAIL 判定（重复率 < 阈值为 PASS）

修复记录（2026-09-09）：
1. 新歌词只比对【原创歌词】区（跳过【歌曲简介】/【发布物料】等模板文本），
   避免非歌词内容稀释重复率导致误判 PASS。
2. 重复片段改为按在原词中出现位置排序（与注释语义一致）。

退出码:
    0 = PASS（重复率低于阈值）
    1 = FAIL（重复率达到或超过阈值）
    2 = 参数错误或文件读取失败
"""

import sys
import argparse
from pathlib import Path


def extract_lyrics_section(text: str) -> str:
    """提取歌词区（兼容【原创歌词】标记或 MD 的"## 原创歌词"标题，含段落标签），未找到标记时返回全文。"""
    import re
    m = re.search(r'(?:【原创歌词】|##\s*原创歌词)(.*?)(?:【歌曲简介】|##\s*歌曲简介|【发布物料】|##\s*发布物料|$)', text, re.DOTALL)
    return m.group(1) if m else text


def clean_text(text: str) -> str:
    """清洗文本：去除空白、标点、英文标签，保留中文字符和字母数字。"""
    import re
    # 移除 Suno 段落标签 [Verse 1] [Chorus] 等
    text = re.sub(r'\[[^\]]*\]', '', text)
    # 移除【字段名】标记
    text = re.sub(r'【[^】]*】', '', text)
    # 只保留中文字符、字母、数字
    text = re.sub(r'[^\u4e00-\u9fff a-zA-Z0-9]', '', text)
    # 移除所有空白
    text = re.sub(r'\s+', '', text)
    return text


def get_ngrams(text: str, n: int) -> set:
    """生成文本的 n-gram 集合（中文按字）。"""
    if len(text) < n:
        return set()
    return {text[i:i+n] for i in range(len(text) - n + 1)}


def find_overlapping_segments(new_text: str, orig_text: str, n: int, max_results: int = 10):
    """找出新歌词中与原歌词重复的 n-gram 片段，按在新歌词中的首次出现位置排序后去重返回。"""
    orig_ngrams = get_ngrams(orig_text, n)
    new_ngrams = get_ngrams(new_text, n)
    overlap = new_ngrams & orig_ngrams
    # 按在新歌词中首次出现位置排序（便于创作者定位修改点），取前 max_results
    return sorted(list(overlap), key=lambda g: new_text.find(g))[:max_results]


def main():
    parser = argparse.ArgumentParser(description='AI歌词原创性自检（n-gram 重复率比对）')
    parser.add_argument('new_file', help='新创作歌词文件路径')
    parser.add_argument('orig_file', help='原曲歌词文件路径')
    parser.add_argument('--ngram', type=int, default=4, help='n-gram 大小（默认 4）')
    parser.add_argument('--threshold', type=float, default=5.0, help='重复率阈值%%（默认 5.0）')
    args = parser.parse_args()

    # 读取文件（新歌词只取【原创歌词】区，避免模板文本稀释重复率）
    try:
        new_raw = Path(args.new_file).read_text(encoding='utf-8')
        orig_raw = Path(args.orig_file).read_text(encoding='utf-8')
        new_text = clean_text(extract_lyrics_section(new_raw))
        orig_text = clean_text(extract_lyrics_section(orig_raw))
    except Exception as e:
        print(f'❌ 文件读取失败: {e}')
        sys.exit(2)

    if not new_text:
        print('❌ 新歌词文件为空或无有效内容')
        sys.exit(2)
    if not orig_text:
        print('❌ 原曲歌词文件为空或无有效内容')
        sys.exit(2)

    n = args.ngram
    new_ngrams = get_ngrams(new_text, n)
    orig_ngrams = get_ngrams(orig_text, n)

    if not new_ngrams:
        print(f'❌ 新歌词过短（少于 {n} 字），无法检测')
        sys.exit(2)

    overlap = new_ngrams & orig_ngrams
    repeat_rate = len(overlap) / len(new_ngrams) * 100

    print('=' * 50)
    print('🔍 原创性自检报告')
    print('=' * 50)
    print('比对范围: 【原创歌词】区（已剔除简介/发布物料等模板文本）')
    print(f'新歌词有效字数: {len(new_text)}')
    print(f'原曲歌词有效字数: {len(orig_text)}')
    print(f'n-gram 大小: {n}')
    print(f'新歌词 n-gram 总数: {len(new_ngrams)}')
    print(f'重复 n-gram 数: {len(overlap)}')
    print(f'重复率: {repeat_rate:.2f}%')
    print(f'阈值: {args.threshold:.1f}%')
    print('-' * 50)

    if overlap:
        print(f'重复片段（前 10 条）:')
        segments = find_overlapping_segments(new_text, orig_text, n)
        for i, seg in enumerate(segments, 1):
            print(f'  {i}. 「{seg}」')
    else:
        print('未检测到重复片段。')

    print('-' * 50)

    if repeat_rate < args.threshold:
        print('✅ PASS — 原创性通过，重复率低于阈值')
        sys.exit(0)
    else:
        print(f'❌ FAIL — 重复率 {repeat_rate:.2f}% 达到/超过阈值 {args.threshold:.1f}%')
        print('   请修改上述重复片段后重新检测。')
        sys.exit(1)


if __name__ == '__main__':
    main()
