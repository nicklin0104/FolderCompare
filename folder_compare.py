import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import filecmp
from datetime import datetime
import threading
import sv_ttk  # 引入現代化主題

class FolderComparer:
    def __init__(self, root):
        self.root = root
        self.root.title("資料夾內容比對工具 - Folder Compare")
        self.root.geometry("1000x700")
        
        # 套用現代化主題 (Sun Valley)
        sv_ttk.set_theme("light")
        
        self.is_comparing = False

        # UI Layout
        self.setup_ui()

    def setup_ui(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Paths selection area (Card layout)
        path_frame = ttk.LabelFrame(main_frame, text="路徑設定", padding=15)
        path_frame.pack(fill=tk.X, pady=(0, 15))

        # Path A
        ttk.Label(path_frame, text="資料夾 A (基準):").grid(row=0, column=0, sticky="e", padx=(0, 10))
        self.path_a_entry = ttk.Entry(path_frame, width=70)
        self.path_a_entry.grid(row=0, column=1, padx=(0, 10))
        ttk.Button(path_frame, text="瀏覽...", command=lambda: self.browse_folder(self.path_a_entry)).grid(row=0, column=2)

        # Path B
        ttk.Label(path_frame, text="資料夾 B (目標):").grid(row=1, column=0, sticky="e", pady=10, padx=(0, 10))
        self.path_b_entry = ttk.Entry(path_frame, width=70)
        self.path_b_entry.grid(row=1, column=1, pady=10, padx=(0, 10))
        ttk.Button(path_frame, text="瀏覽...", command=lambda: self.browse_folder(self.path_b_entry)).grid(row=1, column=2, pady=10)

        # 2. Control buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.btn_compare = ttk.Button(btn_frame, text="開始比對", command=self.start_compare_thread, style="Accent.TButton")
        self.btn_compare.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_clear = ttk.Button(btn_frame, text="清空結果", command=self.clear_results)
        self.btn_clear.pack(side=tk.LEFT)

        # Progress bar (Indeterminate mode for loading state)
        self.progress = ttk.Progressbar(btn_frame, mode='indeterminate')

        # 3. Results area (Treeview)
        result_frame = ttk.LabelFrame(main_frame, text="比對結果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("path", "status", "size_a", "size_b", "mtime_a", "mtime_b")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings", selectmode="browse")
        
        # Configure columns
        headings = [
            ("path", "相對路徑", 350),
            ("status", "狀態", 100),
            ("size_a", "大小 (A)", 100),
            ("size_b", "大小 (B)", 100),
            ("mtime_a", "修改時間 (A)", 160),
            ("mtime_b", "修改時間 (B)", 160)
        ]

        for col_id, title, width in headings:
            self.tree.heading(col_id, text=title)
            self.tree.column(col_id, width=width, anchor=tk.W if col_id == "path" else tk.CENTER)

        # Scrollbars
        y_scroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        x_scroll = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        
        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)

        # 4. Status Bar
        self.status_var = tk.StringVar(value="請輸入路徑後點擊「開始比對」")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, padding=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Setup Tag Colors (Semantic coloring for better UX)
        # Using background colors instead of foreground for better visibility
        self.tree.tag_configure('only_a', background='#fce8e6', foreground='#c5221f') # Light Red
        self.tree.tag_configure('only_b', background='#e6f4ea', foreground='#137333') # Light Green
        self.tree.tag_configure('diff', background='#fef7e0', foreground='#b06000')   # Light Yellow
        self.tree.tag_configure('evenrow', background='#f5f5f5')
        self.tree.tag_configure('oddrow', background='#ffffff')

    def browse_folder(self, entry):
        path = filedialog.askdirectory()
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path.replace("/", "\\"))

    def get_file_info(self, full_path):
        try:
            stats = os.stat(full_path)
            size = f"{stats.st_size:,} B"
            mtime = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            return size, mtime
        except:
            return "-", "-"

    def clear_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.status_var.set("結果已清空")

    def set_ui_state(self, is_running):
        """控制比對期間的 UI 狀態，防止重複操作"""
        self.is_comparing = is_running
        state = tk.DISABLED if is_running else tk.NORMAL
        
        self.btn_compare.config(state=state)
        self.btn_clear.config(state=state)
        self.path_a_entry.config(state=state)
        self.path_b_entry.config(state=state)
        
        if is_running:
            self.progress.pack(side=tk.RIGHT, padx=10, fill=tk.X, expand=True)
            self.progress.start(10)
        else:
            self.progress.stop()
            self.progress.pack_forget()

    def start_compare_thread(self):
        if self.is_comparing: return
        
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
        self.status_var.set(f"正在比對：{dir_a} 與 {dir_b}，請稍候...")
        
        # 啟動背景執行緒，避免 UI 凍結
        thread = threading.Thread(target=self.compare_folders_task, args=(dir_a, dir_b))
        thread.daemon = True
        thread.start()

    def compare_folders_task(self, dir_a, dir_b):
        """背景比對邏輯"""
        try:
            all_files_a = set()
            for root, dirs, files in os.walk(dir_a):
                for f in files:
                    rel_path = os.path.relpath(os.path.join(root, f), dir_a)
                    all_files_a.add(rel_path)

            all_files_b = set()
            for root, dirs, files in os.walk(dir_b):
                for f in files:
                    rel_path = os.path.relpath(os.path.join(root, f), dir_b)
                    all_files_b.add(rel_path)

            common_files = all_files_a.intersection(all_files_b)
            only_in_a = sorted(list(all_files_a - all_files_b))
            only_in_b = sorted(list(all_files_b - all_files_a))

            count_diff = 0
            results = []

            # Process Only in A (遺失/刪除)
            for f in only_in_a:
                size, mtime = self.get_file_info(os.path.join(dir_a, f))
                results.append((f, "僅在 A", size, "-", mtime, "-", 'only_a'))

            # Process Only in B (新增)
            for f in only_in_b:
                size, mtime = self.get_file_info(os.path.join(dir_b, f))
                results.append((f, "僅在 B", "-", size, "-", mtime, 'only_b'))

            # Process Common but maybe different (修改)
            for f in sorted(list(common_files)):
                file_a = os.path.join(dir_a, f)
                file_b = os.path.join(dir_b, f)
                
                if not filecmp.cmp(file_a, file_b, shallow=False):
                    size_a, mtime_a = self.get_file_info(file_a)
                    size_b, mtime_b = self.get_file_info(file_b)
                    results.append((f, "內容不同", size_a, size_b, mtime_a, mtime_b, 'diff'))
                    count_diff += 1

            results.sort(key=lambda x: x[0].lower())

            # 透過 after 方法將結果更新排程回主執行緒
            self.root.after(0, self.update_treeview, results, len(only_in_a), len(only_in_b), count_diff)
            
        except Exception as e:
            self.root.after(0, self.show_error, str(e))

    def update_treeview(self, results, a_count, b_count, diff_count):
        """在主執行緒更新 UI"""
        for i, res in enumerate(results):
            # 決定是否加上斑馬紋標籤 (僅針對未特別標示顏色的列，雖然目前都有標示)
            # 若未來有相同檔案的顯示需求，斑馬紋會很有用
            tags = (res[-1],)
            self.tree.insert("", tk.END, values=res[:-1], tags=tags)

        total_diff = a_count + b_count + diff_count
        self.status_var.set(f"比對完成！發現 {total_diff} 處差異。(僅在A: {a_count}, 僅在B: {b_count}, 不同: {diff_count})")
        self.set_ui_state(False)

    def show_error(self, err_msg):
        """顯示背景執行緒發生的錯誤"""
        messagebox.showerror("執行錯誤", f"比對過程中發生錯誤:\n{err_msg}")
        self.status_var.set("比對失敗。")
        self.set_ui_state(False)


if __name__ == "__main__":
    root = tk.Tk()
    app = FolderComparer(root)
    root.mainloop()
