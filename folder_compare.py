import os
import sys
import csv
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import filecmp
import hashlib
from datetime import datetime
import threading
import sv_ttk

# ─────────────────────────────────────────────
# 修復 3：Size 自動換算（B → KB → MB → GB）
# 設計原則：人類可讀優先，使用 1024 進制
# ─────────────────────────────────────────────
def format_size(byte_count):
    if byte_count < 1024:
        return f"{byte_count} B"
    elif byte_count < 1024 ** 2:
        return f"{byte_count / 1024:.1f} KB"
    elif byte_count < 1024 ** 3:
        return f"{byte_count / 1024 ** 2:.1f} MB"
    else:
        return f"{byte_count / 1024 ** 3:.2f} GB"


# ─────────────────────────────────────────────
# 修復 1：Windows 路徑正規化
# 設計原則：在 Windows 上將相對路徑轉為小寫 key，
# 但保留原始大小寫用於顯示，避免誤報。
# ─────────────────────────────────────────────
def normalize_key(path):
    """產生用於比對的 key（Windows 不分大小寫）"""
    if sys.platform == "win32":
        return path.lower()
    return path


# ─────────────────────────────────────────────
# 修復 4：效能優化版 deep compare
# 策略：size 不同 → 直接判定不同（O(1)）
#        size 相同 → 用 MD5 checksum 比對，避免逐位元組讀取大檔
# ─────────────────────────────────────────────
def files_are_different(path_a, path_b):
    """
    比較兩個檔案是否不同。
    - 先比 size（快速篩選）
    - size 相同再做 MD5（正確但仍比 shallow 安全）
    """
    try:
        size_a = os.path.getsize(path_a)
        size_b = os.path.getsize(path_b)
        if size_a != size_b:
            return True
        # size 相同才做 checksum
        return md5_of(path_a) != md5_of(path_b)
    except OSError:
        return True


def md5_of(filepath, chunk_size=8192):
    h = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


# ─────────────────────────────────────────────
# 主應用程式
# ─────────────────────────────────────────────
class FolderComparer:
    # ── VS Code 設計語言色票 ────────────────────
    VS = {
        "bg_editor":  "#1e1e1e",   # 主背景（編輯器）
        "bg_sidebar": "#252526",   # 側邊欄 / LabelFrame
        "bg_panel":   "#2d2d30",   # 工具列 / 按鈕背景
        "bg_hover":   "#3e3e42",   # Hover 狀態
        "bg_select":  "#094771",   # 選取列（VS Code 藍色選取）
        "accent":     "#007acc",   # VS Code 藍色 Accent
        "accent_dim": "#005f9e",   # Accent 按下狀態
        "text_pri":   "#d4d4d4",   # 主要文字（VS Code 淺灰）
        "text_sec":   "#858585",   # 次要文字（VS Code 灰）
        "border":     "#3e3e42",   # 邊框
        # 語義顏色（暗色調，VS Code 風格）
        "del_bg":     "#3d1a1a",   "del_fg": "#f48771",  # 刪除：暗紅
        "add_bg":     "#1e3829",   "add_fg": "#4ec9b0",  # 新增：暗青
        "mod_bg":     "#35300a",   "mod_fg": "#dcdcaa",  # 修改：暗黃
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Folder Compare  —  資料夾比對工具")
        self.root.geometry("1100x720")
        self.root.configure(bg=self.VS["bg_editor"])

        sv_ttk.set_theme("dark")       # 先載入 dark 主題作為基底
        self._apply_vscode_theme()     # 再以 VS Code 色票覆蓋

        self.is_comparing = False
        self._all_results = []          # 儲存完整結果，供篩選使用
        self._sort_col = None           # 目前排序欄位
        self._sort_reverse = False      # 排序方向

        self.setup_ui()

    def _apply_vscode_theme(self):
        """以 ttk.Style 覆蓋 sv_ttk dark，打造 VS Code 視覺語言"""
        v  = self.VS
        st = ttk.Style()
        FONT    = ("Segoe UI", 9)
        FONT_B  = ("Segoe UI", 9, "bold")

        st.configure("TFrame",       background=v["bg_editor"])
        st.configure("TLabel",       background=v["bg_editor"],  foreground=v["text_pri"], font=FONT)
        st.configure("TSeparator",   background=v["border"])

        # LabelFrame：仿 VS Code Section Header
        st.configure("TLabelframe",
            background=v["bg_sidebar"], relief="flat",
            bordercolor=v["border"], borderwidth=1
        )
        st.configure("TLabelframe.Label",
            background=v["bg_sidebar"], foreground=v["text_sec"],
            font=FONT, padding=(4, 0)
        )

        # Entry
        st.configure("TEntry",
            fieldbackground=v["bg_panel"], foreground=v["text_pri"],
            selectbackground=v["accent"],  selectforeground="white",
            bordercolor=v["border"],       insertcolor=v["text_pri"],
            font=FONT
        )

        # 一般按鈕
        st.configure("TButton",
            background=v["bg_panel"], foreground=v["text_pri"],
            bordercolor=v["border"],  relief="flat",
            font=FONT, padding=(10, 5)
        )
        st.map("TButton",
            background=[("active", v["bg_hover"]), ("pressed", v["bg_editor"])],
            bordercolor=[("active", v["accent"])]
        )

        # Accent 按鈕（開始比對）
        st.configure("Accent.TButton",
            background=v["accent"], foreground="white",
            bordercolor=v["accent"], relief="flat",
            font=FONT_B, padding=(12, 5)
        )
        st.map("Accent.TButton",
            background=[("active", "#1177bb"), ("pressed", v["accent_dim"])]
        )

        # Treeview
        st.configure("Treeview",
            background=v["bg_editor"], foreground=v["text_pri"],
            fieldbackground=v["bg_editor"], bordercolor=v["border"],
            rowheight=26, font=FONT
        )
        st.configure("Treeview.Heading",
            background=v["bg_panel"], foreground=v["text_sec"],
            relief="flat", font=FONT_B, padding=(8, 5)
        )
        st.map("Treeview",
            background=[("selected", v["bg_select"])],
            foreground=[("selected", "white")]
        )
        st.map("Treeview.Heading",
            background=[("active", v["bg_hover"])]
        )

        # Checkbutton
        st.configure("TCheckbutton",
            background=v["bg_editor"], foreground=v["text_pri"],
            focuscolor=v["accent"], font=FONT
        )

        # Progressbar
        st.configure("TProgressbar",
            troughcolor=v["bg_panel"], background=v["accent"], thickness=4
        )

        # Scrollbar
        st.configure("TScrollbar",
            background=v["bg_panel"], troughcolor=v["bg_editor"],
            bordercolor=v["bg_editor"], arrowcolor=v["text_sec"]
        )

    # ──────────────────────────────────────────
    # UI 建立
    # ──────────────────────────────────────────
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 路徑選擇區
        path_frame = ttk.LabelFrame(main_frame, text="路徑設定", padding=15)
        path_frame.pack(fill=tk.X, pady=(0, 12))

        for row, (label, attr) in enumerate([
            ("資料夾 A (基準):", "path_a_entry"),
            ("資料夾 B (目標):", "path_b_entry"),
        ]):
            ttk.Label(path_frame, text=label).grid(row=row, column=0, sticky="e", padx=(0, 10), pady=5)
            entry = ttk.Entry(path_frame, width=70)
            entry.grid(row=row, column=1, padx=(0, 10), pady=5, sticky="ew")
            ttk.Button(
                path_frame, text="瀏覽...",
                command=lambda e=entry: self.browse_folder(e)
            ).grid(row=row, column=2, pady=5)
            setattr(self, attr, entry)

        path_frame.columnconfigure(1, weight=1)

        # 2. 控制列（按鈕 + 篩選 + 進度條）
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(fill=tk.X, pady=(0, 12))

        self.btn_compare = ttk.Button(
            ctrl_frame, text="▶ 開始比對",
            command=self.start_compare_thread, style="Accent.TButton"
        )
        self.btn_compare.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_clear = ttk.Button(ctrl_frame, text="清空結果", command=self.clear_results)
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 16))

        # 修復 7：顯示類型過濾 Checkboxes
        ttk.Separator(ctrl_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        ttk.Label(ctrl_frame, text="顯示：").pack(side=tk.LEFT)

        self.filter_only_a = tk.BooleanVar(value=True)
        self.filter_only_b = tk.BooleanVar(value=True)
        self.filter_diff   = tk.BooleanVar(value=True)

        for text, var in [
            ("僅在 A", self.filter_only_a),
            ("僅在 B", self.filter_only_b),
            ("內容不同", self.filter_diff),
        ]:
            ttk.Checkbutton(
                ctrl_frame, text=text, variable=var,
                command=self.apply_filter
            ).pack(side=tk.LEFT, padx=4)

        # 修復 6：匯出 CSV 按鈕
        self.btn_export = ttk.Button(
            ctrl_frame, text="📄 匯出 CSV",
            command=self.export_csv, state=tk.DISABLED
        )
        self.btn_export.pack(side=tk.RIGHT)

        # Progress bar
        self.progress = ttk.Progressbar(ctrl_frame, mode='indeterminate')

        # 3. 結果 Treeview
        result_frame = ttk.LabelFrame(main_frame, text="比對結果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("path", "status", "size_a", "size_b", "mtime_a", "mtime_b")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings", selectmode="browse")

        headings = [
            ("path",   "相對路徑",      350),
            ("status", "狀態",          100),
            ("size_a", "大小 (A)",      100),
            ("size_b", "大小 (B)",      100),
            ("mtime_a","修改時間 (A)",  160),
            ("mtime_b","修改時間 (B)",  160),
        ]
        for col_id, title, width in headings:
            # 修復 5：欄位標題點擊排序
            self.tree.heading(
                col_id, text=title,
                command=lambda c=col_id: self.sort_by_column(c)
            )
            self.tree.column(
                col_id, width=width,
                anchor=tk.W if col_id == "path" else tk.CENTER
            )

        y_scroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL,   command=self.tree.yview)
        x_scroll = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)

        # 4. 狀態列（仿 VS Code 藍色 Status Bar）
        self.status_var = tk.StringVar(value="請輸入路徑後點擊「開始比對」")
        status_bar = tk.Label(
            self.root, textvariable=self.status_var,
            bg=self.VS["accent"], fg="white",
            font=("Segoe UI", 9), anchor="w", padx=12, pady=3
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 語義顏色（VS Code 深色風格：暗底 + 高飽和前景色）
        v = self.VS
        self.tree.tag_configure('only_a', background=v["del_bg"], foreground=v["del_fg"])
        self.tree.tag_configure('only_b', background=v["add_bg"], foreground=v["add_fg"])
        self.tree.tag_configure('diff',   background=v["mod_bg"], foreground=v["mod_fg"])

    # ──────────────────────────────────────────
    # 互動邏輯
    # ──────────────────────────────────────────
    def browse_folder(self, entry):
        path = filedialog.askdirectory()
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path.replace("/", "\\"))

    def get_file_info(self, full_path):
        # 修復 2：縮小異常捕獲範圍到 OSError
        try:
            stats = os.stat(full_path)
            size  = format_size(stats.st_size)   # 修復 3：使用換算函式
            mtime = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
            return size, mtime
        except OSError:
            return "-", "-"

    def clear_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._all_results = []
        self.btn_export.config(state=tk.DISABLED)
        self.status_var.set("結果已清空")

    def set_ui_state(self, is_running):
        self.is_comparing = is_running
        state = tk.DISABLED if is_running else tk.NORMAL
        for widget in (self.btn_compare, self.btn_clear,
                       self.path_a_entry, self.path_b_entry):
            widget.config(state=state)
        if is_running:
            self.progress.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            self.progress.start(10)
        else:
            self.progress.stop()
            self.progress.pack_forget()

    # ──────────────────────────────────────────
    # 修復 5：欄位排序
    # 設計原則：點擊同欄位切換升/降序，欄位標題加箭頭指示
    # ──────────────────────────────────────────
    COL_INDEX = {"path": 0, "status": 1, "size_a": 2, "size_b": 3, "mtime_a": 4, "mtime_b": 5}

    def sort_by_column(self, col):
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col    = col
            self._sort_reverse = False

        idx = self.COL_INDEX[col]
        self._all_results.sort(
            key=lambda x: x[idx].lower() if isinstance(x[idx], str) else x[idx],
            reverse=self._sort_reverse
        )

        # 更新標題箭頭
        headings_map = {
            "path": "相對路徑", "status": "狀態",
            "size_a": "大小 (A)", "size_b": "大小 (B)",
            "mtime_a": "修改時間 (A)", "mtime_b": "修改時間 (B)",
        }
        for c, title in headings_map.items():
            arrow = (" ▲" if not self._sort_reverse else " ▼") if c == col else ""
            self.tree.heading(c, text=title + arrow)

        self.apply_filter()

    # ──────────────────────────────────────────
    # 修復 7：篩選邏輯
    # ──────────────────────────────────────────
    def apply_filter(self):
        """根據 Checkbox 狀態重新渲染 Treeview"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        tag_map = {"僅在 A": "only_a", "僅在 B": "only_b", "內容不同": "diff"}
        show_map = {
            "只在 A":  self.filter_only_a.get(),
            "僅在 A":  self.filter_only_a.get(),
            "僅在 B":  self.filter_only_b.get(),
            "內容不同": self.filter_diff.get(),
        }

        shown = 0
        for row in self._all_results:
            status = row[1]
            if show_map.get(status, True):
                tag = tag_map.get(status, "")
                self.tree.insert("", tk.END, values=row, tags=(tag,))
                shown += 1

        total = len(self._all_results)
        self.status_var.set(
            f"顯示 {shown} / {total} 筆差異"
            + ("（已篩選）" if shown < total else "")
        )

    # ──────────────────────────────────────────
    # 比對執行緒
    # ──────────────────────────────────────────
    def start_compare_thread(self):
        if self.is_comparing:
            return

        dir_a = self.path_a_entry.get().strip()
        dir_b = self.path_b_entry.get().strip()

        if not dir_a or not dir_b:
            messagebox.showwarning("警告", "請填寫兩個資料夾路徑！")
            return
        if not os.path.isdir(dir_a) or not os.path.isdir(dir_b):
            messagebox.showerror("錯誤", "資料夾路徑無效，請檢查。")
            return

        self.clear_results()
        self.set_ui_state(True)
        self.status_var.set(f"正在比對：{dir_a} ⟺ {dir_b}，請稍候...")

        thread = threading.Thread(
            target=self.compare_folders_task, args=(dir_a, dir_b)
        )
        thread.daemon = True
        thread.start()

    def compare_folders_task(self, dir_a, dir_b):
        try:
            # 修復 1：建立 {normalize_key: original_path} 的映射
            def walk_dir(base):
                mapping = {}   # key（正規化）→ rel_path（原始大小寫）
                for root, _, files in os.walk(base):
                    for f in files:
                        full  = os.path.join(root, f)
                        rel   = os.path.relpath(full, base)
                        key   = normalize_key(rel)
                        mapping[key] = rel
                return mapping

            map_a = walk_dir(dir_a)
            map_b = walk_dir(dir_b)

            keys_a = set(map_a.keys())
            keys_b = set(map_b.keys())

            only_a_keys  = sorted(keys_a - keys_b)
            only_b_keys  = sorted(keys_b - keys_a)
            common_keys  = sorted(keys_a & keys_b)

            results = []
            count_a = count_b = count_diff = 0

            for key in only_a_keys:
                rel = map_a[key]
                size, mtime = self.get_file_info(os.path.join(dir_a, rel))
                results.append((rel, "僅在 A", size, "-", mtime, "-", "only_a"))
                count_a += 1

            for key in only_b_keys:
                rel = map_b[key]
                size, mtime = self.get_file_info(os.path.join(dir_b, rel))
                results.append((rel, "僅在 B", "-", size, "-", mtime, "only_b"))
                count_b += 1

            for key in common_keys:
                rel_a = map_a[key]
                rel_b = map_b[key]
                fa = os.path.join(dir_a, rel_a)
                fb = os.path.join(dir_b, rel_b)

                # 修復 4：size 預篩 → checksum 精比
                if files_are_different(fa, fb):
                    sa, ma = self.get_file_info(fa)
                    sb, mb = self.get_file_info(fb)
                    results.append((rel_a, "內容不同", sa, sb, ma, mb, "diff"))
                    count_diff += 1

            self.root.after(
                0, self.update_results,
                results, count_a, count_b, count_diff
            )

        except Exception as e:
            self.root.after(0, self.show_error, str(e))

    def update_results(self, results, a_count, b_count, diff_count):
        self._all_results = [r[:-1] for r in results]   # 去掉 tag 欄
        self._tag_map     = {r[:-1]: r[-1] for r in results}

        # 重建 tag_map（以 tuple 作 key）
        self._row_tags = {}
        for r in results:
            key = r[:-1]
            self._row_tags[key] = r[-1]

        self.apply_filter()

        total = a_count + b_count + diff_count
        self.status_var.set(
            f"比對完成！共 {total} 處差異 "
            f"（僅在A: {a_count}，僅在B: {b_count}，內容不同: {diff_count}）"
        )
        self.set_ui_state(False)

        if total > 0:
            self.btn_export.config(state=tk.NORMAL)

    # 讓 apply_filter 能讀取 tag
    def apply_filter(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        tag_map = {"僅在 A": "only_a", "僅在 B": "only_b", "內容不同": "diff"}
        show_map = {
            "僅在 A":  self.filter_only_a.get(),
            "僅在 B":  self.filter_only_b.get(),
            "內容不同": self.filter_diff.get(),
        }

        shown = 0
        for row in self._all_results:
            status = row[1]
            if show_map.get(status, True):
                tag = tag_map.get(status, "")
                self.tree.insert("", tk.END, values=row, tags=(tag,))
                shown += 1

        total = len(self._all_results)
        if total > 0:
            self.status_var.set(
                f"顯示 {shown} / {total} 筆差異"
                + ("（已篩選）" if shown < total else "")
            )

    def show_error(self, err_msg):
        messagebox.showerror("執行錯誤", f"比對過程中發生錯誤：\n{err_msg}")
        self.status_var.set("比對失敗。")
        self.set_ui_state(False)

    # ──────────────────────────────────────────
    # 修復 6：匯出 CSV
    # 設計原則：匯出所有結果（忽略當前篩選），時間戳命名避免覆蓋
    # ──────────────────────────────────────────
    def export_csv(self):
        if not self._all_results:
            messagebox.showinfo("提示", "目前沒有比對結果可匯出。")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"folder_compare_{timestamp}.csv"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 檔案", "*.csv"), ("所有檔案", "*.*")],
            initialfile=default_name,
            title="儲存比對結果"
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["相對路徑", "狀態", "大小(A)", "大小(B)", "修改時間(A)", "修改時間(B)"])
                writer.writerows(self._all_results)
            messagebox.showinfo("匯出成功", f"已儲存至：\n{filepath}")
        except OSError as e:
            messagebox.showerror("匯出失敗", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = FolderComparer(root)
    root.mainloop()
