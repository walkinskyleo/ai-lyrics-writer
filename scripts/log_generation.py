#!/usr/bin/env python3
"""
生成记录脚本 - 维护生成记录表、参考歌去重库、用户偏好学习

功能：
1. 记录一次生成（日期、参考歌、歌名、参数、路径、检测结果）
2. 自动更新已用参考歌库
3. 查询：列出所有、搜索、统计
4. 偏好分析：总结用户选A/B版、曲风偏好、韵脚偏好等
5. 检查参考歌是否已用过

用法：
    python log_generation.py record --song "孤独患者-陈奕迅" --title "千百种" --path "xxx.txt" --originality 0.59 --singability 88 --style "流行抒情" --theme "城市孤独" --bpm 80 --structure "ACBACB"
    python log_generation.py list
    python log_generation.py search "关键词"
    python log_generation.py stats
    python log_generation.py preferences
    python log_generation.py check-song "孤独患者-陈奕迅"
    python log_generation.py export "生成记录.csv"
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter

# 技能根目录（脚本在 scripts/ 下，根目录是上一级）
SKILL_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = SKILL_ROOT / 'logs' / 'generation-log.json'
USED_SONGS_FILE = SKILL_ROOT / 'references' / 'used-songs.json'


def load_json(filepath, default=None):
    """加载JSON文件，不存在则返回默认值"""
    if not filepath.exists():
        return default if default is not None else {}
    try:
        return json.loads(filepath.read_text(encoding='utf-8'))
    except Exception:
        return default if default is not None else {}


def save_json(filepath, data):
    """保存JSON文件"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def parse_song(song_str):
    """解析"歌名-歌手"格式"""
    if '-' in song_str:
        parts = song_str.split('-', 1)
        return parts[0].strip(), parts[1].strip()
    return song_str.strip(), ''


def record_generation(args):
    """记录一次生成"""
    log = load_json(LOG_FILE, default=[])
    song, artist = parse_song(args.song) if args.song else ('', '')

    entry = {
        'id': len(log) + 1,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'reference_song': song,
        'reference_artist': artist,
        'title': args.title or '',
        'style': args.style or '',
        'theme': args.theme or '',
        'bpm': args.bpm or '',
        'structure': args.structure or '',
        'file_path': args.path or '',
        'originality_rate': args.originality if args.originality is not None else None,
        'singability_score': args.singability if args.singability is not None else None,
        'chorus_choice': args.chorus or '',  # A/B/未选
        'notes': args.notes or '',
    }
    log.append(entry)
    save_json(LOG_FILE, log)

    # 自动更新已用参考歌库
    if song:
        used = load_json(USED_SONGS_FILE, default={'used_songs': []})
        found = False
        for s in used['used_songs']:
            if s['song'] == song and s['artist'] == artist:
                s['used_count'] = s.get('used_count', 0) + 1
                s['last_used'] = entry['date']
                found = True
                break
        if not found:
            used['used_songs'].append({
                'song': song,
                'artist': artist,
                'used_count': 1,
                'last_used': entry['date']
            })
        save_json(USED_SONGS_FILE, used)

    print(f"✅ 已记录生成 #{entry['id']}: {entry['title'] or '未命名'} (参考: {song}-{artist})")
    print(f"   时间: {entry['timestamp']}")
    rate = entry['originality_rate']
    orig_disp = f"{100 - rate:g}%" if rate is not None else '-'
    print(f"   原创率: {orig_disp} | 可唱性: {entry['singability_score']}分")
    return entry


def list_records():
    """列出所有生成记录"""
    log = load_json(LOG_FILE, default=[])
    if not log:
        print("📭 暂无生成记录")
        return
    print(f"📋 共 {len(log)} 条生成记录")
    print("-" * 80)
    for entry in log:
        title = entry.get('title', '未命名')
        song = entry.get('reference_song', '')
        artist = entry.get('reference_artist', '')
        date = entry.get('date', '')
        orig = entry.get('originality_rate')
        orig_disp = f"{100 - orig:g}%" if orig is not None else '-'
        sing = entry.get('singability_score', '-')
        print(f"#{entry['id']:>3} | {date} | {title:<12} | 参考:{song}-{artist} | 原创:{orig_disp} | 可唱:{sing}分")


def search_records(keyword):
    """搜索生成记录"""
    log = load_json(LOG_FILE, default=[])
    results = []
    for entry in log:
        text = json.dumps(entry, ensure_ascii=False)
        if keyword.lower() in text.lower():
            results.append(entry)
    if not results:
        print(f"🔍 未找到包含 '{keyword}' 的记录")
        return
    print(f"🔍 找到 {len(results)} 条包含 '{keyword}' 的记录")
    print("-" * 80)
    for entry in results:
        print(f"#{entry['id']} | {entry.get('date','')} | {entry.get('title','')} | 参考:{entry.get('reference_song','')}-{entry.get('reference_artist','')}")
        if entry.get('file_path'):
            print(f"     路径: {entry['file_path']}")


def show_stats():
    """显示统计信息"""
    log = load_json(LOG_FILE, default=[])
    if not log:
        print("📭 暂无生成记录，无法统计")
        return

    total = len(log)
    songs = [f"{e.get('reference_song','')}-{e.get('reference_artist','')}" for e in log if e.get('reference_song')]
    styles = [e.get('style', '') for e in log if e.get('style')]
    themes = [e.get('theme', '') for e in log if e.get('theme')]
    structures = [e.get('structure', '') for e in log if e.get('structure')]
    orig_rates = [e.get('originality_rate') for e in log if e.get('originality_rate') is not None]
    sing_scores = [e.get('singability_score') for e in log if e.get('singability_score') is not None]
    dates = [e.get('date', '') for e in log if e.get('date')]

    print("=" * 50)
    print("📊 生成统计")
    print("=" * 50)
    print(f"总生成数: {total} 首")
    print(f"时间范围: {min(dates) if dates else '-'} ~ {max(dates) if dates else '-'}")
    print()

    if songs:
        print("【参考歌 Top 5】")
        for song, count in Counter(songs).most_common(5):
            print(f"  {song}: {count}次")
        print()

    if styles:
        print("【曲风分布】")
        for style, count in Counter(styles).most_common():
            print(f"  {style}: {count}首 ({count/total*100:.0f}%)")
        print()

    if themes:
        print("【主题分布】")
        for theme, count in Counter(themes).most_common():
            print(f"  {theme}: {count}首 ({count/total*100:.0f}%)")
        print()

    if structures:
        print("【结构分布】")
        for struct, count in Counter(structures).most_common():
            print(f"  {struct}: {count}首")
        print()

    if orig_rates:
        avg_dup = sum(orig_rates) / len(orig_rates)
        print(f"【原创率】平均 {100 - avg_dup:.2f}% (最低 {100 - max(orig_rates):.2f}% / 最高 {100 - min(orig_rates):.2f}%)")
    if sing_scores:
        print(f"【可唱性】平均 {sum(sing_scores)/len(sing_scores):.1f}分 (最低 {min(sing_scores)} / 最高 {max(sing_scores)})")

    # 已用参考歌总数
    used = load_json(USED_SONGS_FILE, default={'used_songs': []})
    print(f"\n【已用参考歌库】共 {len(used.get('used_songs', []))} 首")


def show_preferences():
    """用户偏好分析"""
    log = load_json(LOG_FILE, default=[])
    if len(log) < 3:
        print(f"📊 记录不足（当前 {len(log)} 条），至少需要 3 条才能进行偏好分析")
        return

    print("=" * 50)
    print("🎯 用户偏好分析")
    print("=" * 50)

    # 曲风偏好
    styles = [e.get('style', '') for e in log if e.get('style')]
    if styles:
        top_style = Counter(styles).most_common(1)[0]
        print(f"【曲风偏好】最常用: {top_style[0]} ({top_style[1]}次, {top_style[1]/len(styles)*100:.0f}%)")

    # 主题偏好
    themes = [e.get('theme', '') for e in log if e.get('theme')]
    if themes:
        top_theme = Counter(themes).most_common(1)[0]
        print(f"【主题偏好】最常用: {top_theme[0]} ({top_theme[1]}次)")

    # A/B副歌选择
    choices = [e.get('chorus_choice', '') for e in log if e.get('chorus_choice')]
    if choices:
        a_count = choices.count('A') + choices.count('a')
        b_count = choices.count('B') + choices.count('b')
        print(f"【副歌选择】A版炸版: {a_count}次 | B版克制版: {b_count}次")
        if a_count > b_count:
            print(f"  → 偏好 A 版（更炸更直接），后续创作可侧重 A 版风格")
        elif b_count > a_count:
            print(f"  → 偏好 B 版（更克制更戳心），后续创作可侧重 B 版风格")

    # BPM偏好
    bpms = [e.get('bpm') for e in log if e.get('bpm')]
    if bpms:
        try:
            avg_bpm = sum(int(b) for b in bpms) / len(bpms)
            print(f"【BPM偏好】平均 {avg_bpm:.0f} BPM")
        except:
            pass

    # 结构偏好
    structures = [e.get('structure', '') for e in log if e.get('structure')]
    if structures:
        top_struct = Counter(structures).most_common(1)[0]
        print(f"【结构偏好】最常用: {top_struct[0]}")

    # 质量趋势
    sing_scores = [(e.get('date',''), e.get('singability_score')) for e in log if e.get('singability_score') is not None]
    if len(sing_scores) >= 3:
        first_half = [s[1] for s in sing_scores[:len(sing_scores)//2]]
        second_half = [s[1] for s in sing_scores[len(sing_scores)//2:]]
        if first_half and second_half:
            trend = sum(second_half)/len(second_half) - sum(first_half)/len(first_half)
            if trend > 2:
                print(f"【质量趋势】可唱性评分上升 (+{trend:.1f}分)，创作质量在提升")
            elif trend < -2:
                print(f"【质量趋势】可唱性评分下降 ({trend:.1f}分)，建议关注质量")
            else:
                print(f"【质量趋势】可唱性评分稳定 (±{abs(trend):.1f}分)")

    print("\n💡 建议：积累 10 首以上记录后，偏好分析会更准确")


def check_song(song_str):
    """检查参考歌是否已用过"""
    song, artist = parse_song(song_str)
    used = load_json(USED_SONGS_FILE, default={'used_songs': []})
    for s in used.get('used_songs', []):
        if s['song'] == song and (not artist or s['artist'] == artist):
            print(f"⚠️  已使用过: {s['song']}-{s['artist']}")
            print(f"   使用次数: {s.get('used_count', 1)}")
            print(f"   最近使用: {s.get('last_used', '未知')}")
            return True
    print(f"✅ 未使用过: {song}-{artist}")
    return False


def export_records(output_path):
    """导出全部生成记录为 CSV（UTF-8-BOM，Excel 直接打开不乱码）"""
    import csv
    log = load_json(LOG_FILE, default=[])
    if not log:
        print("📭 暂无生成记录，无法导出")
        return
    fields = ['id', 'date', 'timestamp', 'title', 'reference_song', 'reference_artist',
              'style', 'theme', 'bpm', 'structure', 'chorus_choice',
              'file_path', 'originality_rate', 'singability_score', 'notes']
    headers = ['ID', '日期', '时间', '标题', '参考歌', '歌手', '曲风', '主题', 'BPM',
               '结构', '副歌版本', '存储路径', '原创率(%)', '可唱性(分)', '备注']
    try:
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for entry in log:
                row = []
                for k in fields:
                    if k == 'originality_rate':
                        v = entry.get('originality_rate')
                        row.append(f"{100 - v:g}" if v is not None else '')
                    else:
                        row.append(entry.get(k, ''))
                writer.writerow(row)
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        return
    print(f"✅ 已导出 {len(log)} 条生成记录 -> {output_path}")


def main():
    parser = argparse.ArgumentParser(description='生成记录管理 - 记录表/参考歌去重/统计/偏好分析')
    subparsers = parser.add_subparsers(dest='command')

    # record
    # record（--song 非必填：用户未指定参考歌、由 skill 自动随机检索时可为空）
    p_record = subparsers.add_parser('record', help='记录一次生成')
    p_record.add_argument('--song', default='', help='参考歌曲（格式：歌名-歌手；未指定参考歌时可为空）')
    p_record.add_argument('--title', help='最终歌名')
    p_record.add_argument('--path', help='成品文件路径')
    p_record.add_argument('--style', help='曲风')
    p_record.add_argument('--theme', help='主题')
    p_record.add_argument('--bpm', help='BPM')
    p_record.add_argument('--structure', help='结构模板')
    p_record.add_argument('--originality', type=float, help='原创性检测重复率(%%)')
    p_record.add_argument('--singability', type=int, help='可唱性评分')
    p_record.add_argument('--chorus', choices=['A', 'B', ''], help='用户选择的副歌版本')
    p_record.add_argument('--notes', help='备注')

    # list
    subparsers.add_parser('list', help='列出所有生成记录')

    # search
    p_search = subparsers.add_parser('search', help='搜索生成记录')
    p_search.add_argument('keyword', help='搜索关键词')

    # stats
    subparsers.add_parser('stats', help='显示统计信息')

    # preferences
    subparsers.add_parser('preferences', help='用户偏好分析')

    # check-song
    p_check = subparsers.add_parser('check-song', help='检查参考歌是否已用过')
    p_check.add_argument('song', help='参考歌曲（格式：歌名-歌手）')

    # export
    p_export = subparsers.add_parser('export', help='导出生成记录为CSV')
    p_export.add_argument('output', help='CSV输出路径')

    args = parser.parse_args()

    if args.command == 'record':
        record_generation(args)
    elif args.command == 'list':
        list_records()
    elif args.command == 'search':
        search_records(args.keyword)
    elif args.command == 'stats':
        show_stats()
    elif args.command == 'preferences':
        show_preferences()
    elif args.command == 'check-song':
        check_song(args.song)
    elif args.command == 'export':
        export_records(args.output)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
