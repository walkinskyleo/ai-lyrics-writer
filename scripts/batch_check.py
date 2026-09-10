#!/usr/bin/env python3
"""
批量检测脚本（提速方案） - 一次 Python 进程完成多首成品的
原创性自检 + 可唱性自检 + （可选）生成记录，避免逐首冷启动 10+ 次脚本进程。

用法:
    python batch_check.py batch.json [--record] [--ngram N] [--threshold T]

batch.json 结构（列表，每首一个对象）:
[
  {
    "file": "成品文件路径(.txt/.md)",
    "ref": "参考歌曲原版歌词路径",
    "title": "歌名",
    "song": "参考歌-歌手",
    "style": "R&B", "theme": "亲情", "bpm": "76", "structure": "ACBACB",
    "chorus": "", "notes": "备注"
  }
]

说明:
- 原创性：复用 originality_check.py 的清洗/n-gram 逻辑，重复率 < 阈值(默认5%) 为 PASS。
- 可唱性：复用 singability_check.py 的解析与检测逻辑（通过其 run_check 的 JSON 输出取评分），
  评分口径与 singability_check.py 完全一致，无需另行同步维护。
- --record：对每首追加写入生成记录并更新已用参考歌库（等价于逐首跑 log_generation.py record）。
"""

import sys
import io
import json
import argparse
import contextlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from originality_check import extract_lyrics_section, clean_text, get_ngrams
import singability_check as sc
from log_generation import record_generation


def check_originality(new_file, ref_file, ngram=4, threshold=5.0):
    """返回 (重复率%, 提示文本)；无法比对时重复率为 None。"""
    try:
        new_raw = Path(new_file).read_text(encoding='utf-8')
        orig_raw = Path(ref_file).read_text(encoding='utf-8')
    except Exception as e:
        return None, f'读取失败: {e}'
    new_text = clean_text(extract_lyrics_section(new_raw))
    orig_text = clean_text(extract_lyrics_section(orig_raw))
    if not new_text or not orig_text:
        return None, '歌词内容为空，无法比对'
    new_ngrams = get_ngrams(new_text, ngram)
    orig_ngrams = get_ngrams(orig_text, ngram)
    if not new_ngrams:
        return None, '新歌词过短，无法比对'
    rate = len(new_ngrams & orig_ngrams) / len(new_ngrams) * 100
    msg = f"PASS（重复率 {rate:.2f}% < {threshold:.1f}%）" if rate < threshold else f"FAIL（重复率 {rate:.2f}% ≥ {threshold:.1f}%）"
    return rate, msg


def check_singability(filepath):
    """复用 singability_check.run_check 的 JSON 输出（同进程调用，无进程冷启动）。返回 (report, 错误信息)。"""
    if not Path(filepath).exists():
        return None, '文件不存在'
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            sc.run_check(filepath, output_json=True)
        except SystemExit as e:
            return None, f'解析失败（{e}）'
    try:
        return json.loads(buf.getvalue()), None
    except json.JSONDecodeError:
        return None, '检测输出无法解析'


def main():
    parser = argparse.ArgumentParser(description='批量检测：一次进程完成多首成品的原创性+可唱性+记录（提速方案）')
    parser.add_argument('manifest', help='批量清单 JSON 文件路径')
    parser.add_argument('--record', action='store_true', help='同时写入生成记录并更新已用参考歌库')
    parser.add_argument('--ngram', type=int, default=4, help='原创性 n-gram 大小（默认4）')
    parser.add_argument('--threshold', type=float, default=5.0, help='原创性重复率阈值(默认5.0)')
    args = parser.parse_args()

    try:
        entries = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    except Exception as e:
        print(f'❌ 清单读取失败: {e}')
        return 2
    if not isinstance(entries, list) or not entries:
        print('❌ 清单必须是非空列表')
        return 2

    print('=' * 66)
    print('🎵 批量检测报告（batch_check v1 · 单进程提速版）')
    print('=' * 66)
    results = []
    for i, entry in enumerate(entries, 1):
        file = entry.get('file', '')
        ref = entry.get('ref', '')
        title = entry.get('title', '') or f'第{i}首'
        # 原创性
        if ref:
            dup_rate, orig_msg = check_originality(file, ref, args.ngram, args.threshold)
        else:
            dup_rate, orig_msg = None, '未提供参考词，跳过原创性比对'
        # 可唱性
        report, sing_err = check_singability(file)
        if sing_err:
            total, verdict, failed = None, 'ERROR', []
        else:
            total = report.get('total_score')
            verdict = report.get('verdict', 'ERROR')
            failed = report.get('failed_gates', [])
        results.append({'title': title, 'file': file, 'dup_rate': dup_rate,
                        'total': total, 'verdict': verdict, 'failed': failed,
                        'orig_msg': orig_msg, 'sing_err': sing_err})
        orig_disp = f"{100 - dup_rate:g}%" if dup_rate is not None else '-'
        sing_disp = f"{total}分" if total is not None else '-'
        gate_txt = ','.join(failed) if failed else '无'
        print(f"#{i:>2} | {title:<8} | 原创:{orig_disp:>6} | 可唱:{sing_disp:>4} | {verdict:<5} | 门禁:{gate_txt}")
        if sing_err or 'FAIL' in (orig_msg or ''):
            print(f"      ↳ {orig_msg or ''} {sing_err or ''}")

    n_ok = sum(1 for r in results if r['verdict'] == 'PASS')
    print('-' * 66)
    print(f"汇总: {n_ok}/{len(results)} 首 PASS")

    # 生成记录
    if args.record:
        print('-' * 66)
        for entry in entries:
            r = next((x for x in results if x['file'] == entry.get('file')), None)
            if r is None:
                continue
            ns = argparse.Namespace(
                song=entry.get('song', ''), title=entry.get('title', ''),
                path=entry.get('file', ''), style=entry.get('style', ''),
                theme=entry.get('theme', ''), bpm=entry.get('bpm', ''),
                structure=entry.get('structure', ''),
                originality=r['dup_rate'], singability=r['total'],
                chorus=entry.get('chorus', ''), notes=entry.get('notes', ''),
            )
            try:
                record_generation(ns)
            except Exception as e:
                print(f'❌ 记录失败 [{entry.get("title", "")}]: {e}')

    return 0 if all(r['verdict'] in ('PASS', 'WARN') for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
