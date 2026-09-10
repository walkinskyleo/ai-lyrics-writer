#!/usr/bin/env python3
"""
Ai Lyrics Writer（AI歌词创作器）- GUI 界面
Ai Lyrics Writer Skill 的可视化操作界面

功能：
1. 存储目录设置（歌词成品输出目录，skill 生成时同步读取）
2. 创作参数配置（曲风、主题、语言、BPM、结构、Suno版本、副歌版本、人声、参考歌、数量）
3. 参考歌查重（检查是否已用过）
4. 命令录入框（自然语言补充说明）
5. 一键生成精简指令（一句话 + 全部参数，可复制发给 AI 执行）
6. 作品列表（全部生成记录：日期/标题/参考歌/评分/路径，支持搜索、双击打开）
7. 快捷工具（可唱性检测、生成记录统计、偏好分析、打开目录、导出CSV）
8. 状态栏（参考歌库/生成记录数/存储目录）
9. 操作日志 + 关闭窗口自动保存配置

用法：
    python lyrics_gui.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# 技能根目录（兼容 exe 模式和脚本模式）
if getattr(sys, 'frozen', False):
    # exe 模式：exe 放在技能根目录下
    SKILL_ROOT = Path(sys.executable).resolve().parent
else:
    # 脚本模式：scripts/ 的上一级是技能根目录
    SKILL_ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = SKILL_ROOT / 'gui_config.json'
LOG_FILE = SKILL_ROOT / 'logs' / 'generation-log.json'
USED_SONGS_FILE = SKILL_ROOT / 'references' / 'used-songs.json'

# 参数选项
STYLE_OPTIONS = ['流行抒情', 'R&B', '民谣', '说唱', '古风', '电子']
THEME_OPTIONS = ['爱情伤感', '友情', '亲情', '成长励志', '城市孤独', '治愈释怀']
LANGUAGE_OPTIONS = ['国语', '粤语', '英文']
STRUCTURE_OPTIONS = ['ABAB', 'ABABCB', 'ACBACB']
SUNO_VERSION_OPTIONS = ['v4（自然真实）', 'v3.5（风格化强）']
CHORUS_OPTIONS = ['两版都给', 'A版（炸版）', 'B版（克制版）']


def load_records():
    """读取全部生成记录"""
    if not LOG_FILE.exists():
        return []
    try:
        data = json.loads(LOG_FILE.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def load_used_songs_count():
    """读取参考歌库歌曲数"""
    try:
        data = json.loads(USED_SONGS_FILE.read_text(encoding='utf-8'))
        return len(data.get('used_songs', []))
    except Exception:
        return 0


class LyricsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ai Lyrics Writer（AI歌词创作器）")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)

        # 设置中文字体
        self.font_default = ('Microsoft YaHei UI', 10)
        self.font_title = ('Microsoft YaHei UI', 11, 'bold')
        self.font_mono = ('Consolas', 10)
        self.root.option_add('*Font', self.font_default)

        # 加载配置
        self.config = self.load_config()

        # 关闭窗口时自动保存配置
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 构建界面
        self.build_ui()

        # 刷新作品列表
        self.refresh_works()

    def load_config(self):
        """加载配置"""
        default = {
            'output_dir': str(Path.home() / 'Documents' / 'lyrics_output'),
            'style': '流行抒情',
            'theme': '爱情伤感',
            'language': '国语',
            'structure': 'ABABCB',
            'suno_version': 'v4（自然真实）',
            'bpm': '76',
            'vocal': '',
            'reference_song': '',
            'count': '1',
            'chorus': '两版都给',
        }
        if CONFIG_FILE.exists():
            try:
                saved = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
                default.update(saved)
            except Exception:
                pass
        return default

    def save_config(self):
        """保存配置"""
        self.config['output_dir'] = self.var_output_dir.get()
        self.config['style'] = self.var_style.get()
        self.config['theme'] = self.var_theme.get()
        self.config['language'] = self.var_language.get()
        self.config['structure'] = self.var_structure.get()
        self.config['suno_version'] = self.var_suno.get()
        self.config['bpm'] = self.var_bpm.get()
        self.config['vocal'] = self.var_vocal.get()
        self.config['reference_song'] = self.var_ref_song.get()
        self.config['count'] = self.var_count.get()
        self.config['chorus'] = self.var_chorus.get()
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(json.dumps(self.config, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            self.log(f"⚠️ 配置保存失败: {e}")

    def build_ui(self):
        """构建界面"""
        # 顶部标题
        title_frame = ttk.Frame(self.root, padding=(10, 8))
        title_frame.pack(fill=tk.X)
        ttk.Label(title_frame, text="🎵 Ai Lyrics Writer", font=self.font_title).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="AI歌词创作器 · 可视化操作界面", foreground='gray').pack(side=tk.LEFT, padx=(10, 0))

        # 主内容区：整体套入可滚动容器（避免窗口缩小/内容过长时显示不全）
        scroll_container = ttk.Frame(self.root)
        scroll_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        self.canvas = tk.Canvas(scroll_container, highlightthickness=0)
        v_scroll = ttk.Scrollbar(scroll_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=v_scroll.set)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        main_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=main_frame, anchor=tk.NW)
        main_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        # 左侧：参数配置
        left_frame = ttk.LabelFrame(main_frame, text="参数配置", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.configure(width=320)
        left_frame.pack_propagate(False)

        self.build_params(left_frame)

        # 右侧：命令录入 + 作品列表
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.build_command_area(right_frame)
        self.build_works_area(right_frame)

        # 底部：日志（固定）
        bottom_frame = ttk.LabelFrame(self.root, text="操作日志", padding=(10, 5))
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.log_text = scrolledtext.ScrolledText(bottom_frame, height=5, font=self.font_mono, state=tk.DISABLED)
        self.log_text.pack(fill=tk.X)

        # 状态栏
        self.status_var = tk.StringVar()
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(10, 3)).pack(fill=tk.X, side=tk.BOTTOM)

        self.log("✅ 界面初始化完成")
        self.refresh_status()

    def _on_mousewheel(self, event):
        """鼠标滚轮：Treeview/文本区自行滚动，其余区域驱动整体滚动容器"""
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if widget is not None and widget.winfo_class() in ('Treeview', 'Text'):
            return
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    def build_params(self, parent):
        """构建参数配置区"""
        row = 0

        # 存储目录
        ttk.Label(parent, text="存储目录:").grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        dir_frame = ttk.Frame(parent)
        dir_frame.grid(row=row, column=0, sticky=tk.EW, pady=3)
        self.var_output_dir = tk.StringVar(value=self.config['output_dir'])
        ttk.Entry(dir_frame, textvariable=self.var_output_dir, width=28).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="浏览", width=6, command=self.browse_dir).pack(side=tk.LEFT, padx=(5, 0))
        row += 1

        # 分隔线
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=row, column=0, sticky=tk.EW, pady=8)
        row += 1

        # 参考歌曲
        ttk.Label(parent, text="参考歌曲（歌名-歌手，可空）:").grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        ref_frame = ttk.Frame(parent)
        ref_frame.grid(row=row, column=0, sticky=tk.EW, pady=3)
        self.var_ref_song = tk.StringVar(value=self.config['reference_song'])
        ttk.Entry(ref_frame, textvariable=self.var_ref_song).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(ref_frame, text="查重", width=5, command=self.tool_check_song).pack(side=tk.LEFT, padx=(4, 0))
        row += 1

        # 曲风
        ttk.Label(parent, text="曲风:").grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        self.var_style = tk.StringVar(value=self.config['style'])
        ttk.Combobox(parent, textvariable=self.var_style, values=STYLE_OPTIONS, state='readonly').grid(row=row, column=0, sticky=tk.EW, pady=3)
        row += 1

        # 主题
        ttk.Label(parent, text="主题:").grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        self.var_theme = tk.StringVar(value=self.config['theme'])
        ttk.Combobox(parent, textvariable=self.var_theme, values=THEME_OPTIONS, state='readonly').grid(row=row, column=0, sticky=tk.EW, pady=3)
        row += 1

        # 语言
        ttk.Label(parent, text="语言:").grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        self.var_language = tk.StringVar(value=self.config['language'])
        ttk.Combobox(parent, textvariable=self.var_language, values=LANGUAGE_OPTIONS, state='readonly').grid(row=row, column=0, sticky=tk.EW, pady=3)
        row += 1

        # BPM
        ttk.Label(parent, text="BPM（60-108）:").grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        self.var_bpm = tk.StringVar(value=self.config['bpm'])
        ttk.Entry(parent, textvariable=self.var_bpm, width=10).grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1

        # 结构
        ttk.Label(parent, text="歌曲结构:").grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        self.var_structure = tk.StringVar(value=self.config['structure'])
        ttk.Combobox(parent, textvariable=self.var_structure, values=STRUCTURE_OPTIONS, state='readonly').grid(row=row, column=0, sticky=tk.EW, pady=3)
        row += 1

        # Suno 版本
        ttk.Label(parent, text="Suno 版本:").grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        self.var_suno = tk.StringVar(value=self.config['suno_version'])
        ttk.Combobox(parent, textvariable=self.var_suno, values=SUNO_VERSION_OPTIONS, state='readonly').grid(row=row, column=0, sticky=tk.EW, pady=3)
        row += 1

        # 人声参考
        ttk.Label(parent, text="人声风格参考（可空）:").grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        self.var_vocal = tk.StringVar(value=self.config['vocal'])
        ttk.Entry(parent, textvariable=self.var_vocal).grid(row=row, column=0, sticky=tk.EW, pady=3)
        row += 1

        # 数量
        ttk.Label(parent, text="生成数量:").grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        self.var_count = tk.StringVar(value=self.config['count'])
        ttk.Spinbox(parent, from_=1, to=20, textvariable=self.var_count, width=8).grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1

        # 副歌版本
        ttk.Label(parent, text="副歌版本:").grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        self.var_chorus = tk.StringVar(value=self.config['chorus'])
        ttk.Combobox(parent, textvariable=self.var_chorus, values=CHORUS_OPTIONS, state='readonly').grid(row=row, column=0, sticky=tk.EW, pady=3)
        row += 1

        # 分隔线
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=row, column=0, sticky=tk.EW, pady=8)
        row += 1

        # 快捷工具
        ttk.Label(parent, text="快捷工具:", font=self.font_title).grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        tools_frame = ttk.Frame(parent)
        tools_frame.grid(row=row, column=0, sticky=tk.EW, pady=3)
        ttk.Button(tools_frame, text="可唱性检测", command=self.tool_singability).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(tools_frame, text="打开存储目录", command=self.open_output_dir).pack(side=tk.LEFT, padx=3)
        row += 1
        tools_frame2 = ttk.Frame(parent)
        tools_frame2.grid(row=row, column=0, sticky=tk.EW, pady=3)
        ttk.Button(tools_frame2, text="生成记录统计", command=self.tool_stats).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(tools_frame2, text="偏好分析", command=self.tool_preferences).pack(side=tk.LEFT, padx=3)
        row += 1
        tools_frame3 = ttk.Frame(parent)
        tools_frame3.grid(row=row, column=0, sticky=tk.EW, pady=3)
        ttk.Button(tools_frame3, text="导出记录CSV", command=self.tool_export_csv).pack(side=tk.LEFT, padx=(0, 3))
        row += 1
        ttk.Button(parent, text="🔄 刷新列表", command=self.refresh_works).grid(row=row, column=0, sticky=tk.EW, pady=5)

    def build_command_area(self, parent):
        """构建命令录入区"""
        frame = ttk.LabelFrame(parent, text="命令录入", padding=10)
        frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(frame, text="自然语言指令（补充说明，如主题/情绪/特定要求，可空）:").pack(anchor=tk.W)
        self.cmd_text = scrolledtext.ScrolledText(frame, height=3, font=self.font_default)
        self.cmd_text.pack(fill=tk.X, pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="📝 生成指令", command=self.generate_command).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="📋 复制指令", command=self.copy_command).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)

        ttk.Label(frame, text="生成的指令（一句话，可直接粘贴发给 AI）:").pack(anchor=tk.W, pady=(8, 0))
        self.output_text = scrolledtext.ScrolledText(frame, height=3, font=self.font_mono, state=tk.DISABLED)
        self.output_text.pack(fill=tk.X, pady=5)

    def build_works_area(self, parent):
        """构建作品列表区（全部生成记录）"""
        frame = ttk.LabelFrame(parent, text="作品列表（全部生成记录 · 双击打开文件）", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # 搜索框
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(search_frame, text="搜索", command=self.refresh_works).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(search_frame, text="清空", command=self.clear_search).pack(side=tk.LEFT)
        self.search_entry = None

        # 表格
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('date', 'title', 'song', 'orig', 'sing', 'chorus', 'path')
        self.works_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='browse')
        headings = {'date': '日期', 'title': '标题', 'song': '参考歌', 'orig': '原创率',
                    'sing': '可唱性', 'chorus': '副歌版', 'path': '存储路径'}
        widths = {'date': 88, 'title': 110, 'song': 130, 'orig': 66, 'sing': 66, 'chorus': 80, 'path': 260}
        for col in columns:
            self.works_tree.heading(col, text=headings[col])
            self.works_tree.column(col, width=widths[col], anchor=tk.CENTER if col not in ('title', 'path') else tk.W,
                                   stretch=(col in ('title', 'path')))
        v_sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.works_tree.yview)
        h_sb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.works_tree.xview)
        self.works_tree.configure(yscrollcommand=v_sb.set, xscrollcommand=h_sb.set)
        self.works_tree.grid(row=0, column=0, sticky=tk.NSEW)
        v_sb.grid(row=0, column=1, sticky=tk.NS)
        h_sb.grid(row=1, column=0, sticky=tk.EW)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.works_tree.bind('<Double-1>', self.open_selected_work)

        # 操作按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_frame, text="打开文件", command=self.open_selected_work_btn).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text="打开所在目录", command=self.open_file_location).pack(side=tk.LEFT, padx=3)

    # ========== 功能函数 ==========

    def browse_dir(self):
        """浏览选择存储目录"""
        directory = filedialog.askdirectory(initialdir=self.var_output_dir.get(), title="选择存储目录")
        if directory:
            self.var_output_dir.set(directory)
            self.log(f"📂 存储目录已设置: {directory}")
            self.refresh_works()
            self.refresh_status()

    def generate_command(self):
        """根据参数生成精简指令（一句话 + 全部参数，执行规范由 skill 自动遵循）"""
        ref = self.var_ref_song.get().strip()
        style = self.var_style.get()
        theme = self.var_theme.get()
        language = self.var_language.get()
        bpm = self.var_bpm.get().strip()
        structure = self.var_structure.get()
        suno = self.var_suno.get()
        chorus = self.var_chorus.get()
        vocal = self.var_vocal.get().strip()
        count = self.var_count.get().strip()
        cmd_extra = self.cmd_text.get("1.0", tk.END).strip()

        # BPM 范围校验（SKILL.md 规范：60-108）
        try:
            bpm_val = int(bpm)
            if not (60 <= bpm_val <= 108):
                messagebox.showwarning("参数提示", "BPM 应在 60-108 之间，请调整后再生成指令。")
                return
        except ValueError:
            messagebox.showwarning("参数提示", "BPM 请输入整数（范围 60-108）。")
            return

        params = [f"曲风{style}", f"主题{theme}", language, f"BPM {bpm}",
                  f"结构{structure}", f"Suno {suno}", f"副歌{chorus}"]
        if vocal:
            params.append(f"人声参考{vocal}")

        if ref:
            command = f"请用 Ai Lyrics Writer 创作 {count} 首歌，参考《{ref}》：{'、'.join(params)}。"
        else:
            command = f"请用 Ai Lyrics Writer 创作 {count} 首歌（未指定参考歌，自动随机检索未使用过的歌曲）：{'、'.join(params)}。"
        if cmd_extra:
            command += f"补充要求：{cmd_extra}。"
        command += f"成品导出到 {self.var_output_dir.get()}。"

        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", command)
        self.output_text.config(state=tk.DISABLED)

        self.log("📝 已生成精简指令")

    def copy_command(self):
        """复制生成的指令到剪贴板"""
        content = self.output_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "请先生成指令")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.log("📋 指令已复制到剪贴板")
        messagebox.showinfo("成功", "指令已复制到剪贴板\n可直接粘贴发给 AI 执行")

    def refresh_works(self):
        """从生成记录加载作品列表（支持搜索筛选）"""
        for item in self.works_tree.get_children():
            self.works_tree.delete(item)
        records = load_records()
        keyword = self.search_var.get().strip()
        shown = 0
        for r in sorted(records, key=lambda x: x.get('date', ''), reverse=True):
            title = r.get('title', '') or '未命名'
            song = r.get('reference_song', '') or ''
            if r.get('reference_artist'):
                song = f"{song}-{r.get('reference_artist')}"
            orig = r.get('originality_rate')
            # 存储的是重复率（0%=完全原创），界面按用户心智显示"原创率=100-重复率"
            orig_txt = f"{100 - orig:g}%" if orig is not None else '-'
            sing = r.get('singability_score')
            sing_txt = f"{sing}分" if sing is not None else '-'
            chorus = r.get('chorus_choice', '') or '-'
            path = r.get('file_path', '')
            if keyword:
                blob = f"{title}{song}{path}".lower()
                if keyword.lower() not in blob:
                    continue
            shown += 1
            display_path = path if len(path) <= 60 else '…' + path[-59:]
            self.works_tree.insert('', tk.END, values=(r.get('date', ''), title, song, orig_txt, sing_txt, chorus, display_path), tags=(path,))
        if keyword:
            self.log(f"📚 作品列表已刷新，共 {shown} 条（筛选: {keyword}）")
        else:
            self.log(f"📚 作品列表已刷新，共 {shown} 条生成记录")
        self.refresh_status()

    def clear_search(self):
        """清空搜索框并刷新"""
        self.search_var.set("")
        self.refresh_works()

    def get_selected_path(self):
        """获取选中记录的完整存储路径"""
        sel = self.works_tree.selection()
        if not sel:
            return None
        item = sel[0]
        tags = self.works_tree.item(item, 'tags')
        return tags[0] if tags else None

    def open_selected_work(self, event=None):
        """打开选中作品"""
        path = self.get_selected_path()
        if not path:
            return
        filepath = Path(path)
        if filepath.exists():
            os.startfile(str(filepath))
            self.log(f"📖 已打开: {filepath.name}")
        else:
            messagebox.showwarning("文件缺失", f"文件不存在（可能已被移动或删除）:\n{filepath}")
            self.log(f"❌ 文件不存在: {filepath}")

    def open_selected_work_btn(self):
        """按钮触发打开选中作品"""
        self.open_selected_work()

    def open_file_location(self):
        """打开选中作品的所在目录（文件缺失时打开当前存储目录）"""
        path = self.get_selected_path()
        if not path:
            messagebox.showinfo("提示", "请先在列表中选择一条记录")
            return
        p = Path(path)
        target = p.parent if p.exists() else Path(self.var_output_dir.get())
        if target.exists():
            os.startfile(str(target))
            self.log(f"📂 已打开所在目录: {target}")
        else:
            messagebox.showerror("错误", f"目录不存在: {target}")

    def open_output_dir(self):
        """打开存储目录"""
        output_dir = self.var_output_dir.get()
        if Path(output_dir).exists():
            os.startfile(output_dir)
            self.log(f"📂 已打开存储目录: {output_dir}")
        else:
            messagebox.showerror("错误", f"目录不存在: {output_dir}")

    def refresh_status(self):
        """刷新底部状态栏"""
        records = load_records()
        used = load_used_songs_count()
        self.status_var.set(f"参考歌库 {used} 首 | 生成记录 {len(records)} 条 | 存储目录: {self.var_output_dir.get()}")

    def tool_singability(self):
        """可唱性检测工具"""
        filepath = filedialog.askopenfilename(
            title="选择成品歌词文件",
            initialdir=self.var_output_dir.get(),
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if not filepath:
            return
        script = SKILL_ROOT / 'scripts' / 'singability_check.py'
        try:
            result = subprocess.run(
                [sys.executable, str(script), filepath],
                capture_output=True, text=True, encoding='utf-8'
            )
            self.log("🎵 可唱性检测结果:")
            for line in result.stdout.strip().split('\n'):
                self.log(f"  {line}")
        except Exception as e:
            self.log(f"❌ 检测失败: {e}")

    def tool_stats(self):
        """生成记录统计"""
        script = SKILL_ROOT / 'scripts' / 'log_generation.py'
        try:
            result = subprocess.run(
                [sys.executable, str(script), 'stats'],
                capture_output=True, text=True, encoding='utf-8'
            )
            self.log("📊 生成记录统计:")
            for line in result.stdout.strip().split('\n'):
                self.log(f"  {line}")
        except Exception as e:
            self.log(f"❌ 统计失败: {e}")

    def tool_preferences(self):
        """用户偏好分析（需 ≥3 条记录）"""
        script = SKILL_ROOT / 'scripts' / 'log_generation.py'
        try:
            result = subprocess.run(
                [sys.executable, str(script), 'preferences'],
                capture_output=True, text=True, encoding='utf-8'
            )
            self.log("🎯 用户偏好分析:")
            for line in result.stdout.strip().split('\n'):
                self.log(f"  {line}")
        except Exception as e:
            self.log(f"❌ 偏好分析失败: {e}")

    def tool_export_csv(self):
        """导出生成记录为 CSV"""
        default_name = f"生成记录_{datetime.now().strftime('%Y%m%d')}.csv"
        path = filedialog.asksaveasfilename(
            title="导出生成记录CSV",
            defaultextension=".csv",
            initialfile=default_name,
            initialdir=str(Path.home() / 'Documents'),
            filetypes=[("CSV文件", "*.csv")]
        )
        if not path:
            return
        script = SKILL_ROOT / 'scripts' / 'log_generation.py'
        try:
            result = subprocess.run(
                [sys.executable, str(script), 'export', path],
                capture_output=True, text=True, encoding='utf-8'
            )
            for line in result.stdout.strip().split('\n'):
                self.log(f"  {line}")
            messagebox.showinfo("导出成功", f"生成记录已导出:\n{path}")
        except Exception as e:
            self.log(f"❌ 导出失败: {e}")

    def tool_check_song(self):
        """参考歌查重（检查是否已用过）"""
        ref = self.var_ref_song.get().strip()
        if not ref:
            messagebox.showinfo("提示", "请先输入参考歌曲（格式：歌名-歌手）")
            return
        script = SKILL_ROOT / 'scripts' / 'log_generation.py'
        try:
            result = subprocess.run(
                [sys.executable, str(script), 'check-song', ref],
                capture_output=True, text=True, encoding='utf-8'
            )
            self.log("🔍 参考歌查重:")
            for line in result.stdout.strip().split('\n'):
                self.log(f"  {line}")
        except Exception as e:
            self.log(f"❌ 查重失败: {e}")

    def on_close(self):
        """关闭窗口前自动保存配置"""
        try:
            self.save_config()
        except Exception as e:
            self.log(f"⚠️ 退出保存配置失败: {e}")
        self.root.destroy()

    def log(self, message):
        """写入日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    # 设置主题
    try:
        style = ttk.Style()
        style.theme_use('clam')
    except Exception:
        pass
    app = LyricsGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
