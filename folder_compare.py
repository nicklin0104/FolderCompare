import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import filecmp
from datetime import datetime

class FolderComparer:
    def __init__(self, root):
        self.root = root
        self.root.title("資料夾內容比對工具 - Folder Compare")
        self.root.geometry("900x600")

        # UI Layout
        self.setup_ui()

    def setup_ui(self):
        # Paths selection area
        path_frame = tk.Frame(self.root, pady=10)
        path_frame.pack(fill=tk.X, padx=10)

        # Path A
        tk.Label(path_frame, text="資料夾 A:").grid(row=0, column=0, sticky="e")
        self.path_a_entry = tk.Entry(path_frame, width=80)
        self.path_a_entry.grid(row=0, column=1, padx=5)
        tk.Button(path_frame, text="瀏覽...", command=lambda: self.browse_folder(self.path_a_entry)).grid(row=0, column=2)

        # Path B
        tk.Label(path_frame, text="資料夾 B:").grid(row=1, column=0, sticky="e", pady=5)
        self.path_b_entry = tk.Entry(path_frame, width=80)
        self.path_b_entry.grid(row=1, column=1, padx=5)
        tk.Button(path_frame, text="瀏覽...", command=lambda: self.browse_folder(self.path_b_entry)).grid(row=1, column=2)

        # Control buttons
        btn_frame = tk.Frame(self.root, pady=10)
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="開始比對", command=self.compare_folders, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="清空結果", command=self.clear_results, width=15).pack(side=tk.LEFT, padx=5)

        # Results area (Treeview)
        result_frame = tk.Frame(self.root)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("path", "status", "size_a", "size_b", "mtime_a", "mtime_b")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings")
        
        self.tree.heading("path", text="相對路徑")
        self.tree.heading("status", text="狀態")
        self.tree.heading("size_a", text="大小 (A)")
        self.tree.heading("size_b", text="大小 (B)")
        self.tree.heading("mtime_a", text="修改時間 (A)")
        self.tree.heading("mtime_b", text="修改時間 (B)")

        self.tree.column("path", width=300)
        self.tree.column("status", width=100)
        self.tree.column("size_a", width=80)
        self.tree.column("size_b", width=80)
        self.tree.column("mtime_a", width=140)
        self.tree.column("mtime_b", width=140)

        # Scrollbar
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Status Bar
        self.status_var = tk.StringVar(value="請輸入路徑後點擊「開始比對」")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

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

    def compare_folders(self):
        dir_a = self.path_a_entry.get().strip()
        dir_b = self.path_b_entry.get().strip()

        if not dir_a or not dir_b:
            messagebox.showwarning("警告", "請填寫兩個資料夾路徑！")
            return

        if not os.path.isdir(dir_a) or not os.path.isdir(dir_b):
            messagebox.showerror("錯誤", "資料夾路徑無效，請檢查。")
            return

        self.clear_results()
        self.status_var.set(f"正在比對：{dir_a} 與 {dir_b}...")
        self.root.update()

        # Core logic: scan all files
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
        
        # 建立一個列表來統一存放所有的差異結果，方便後續依照路徑排序
        results = []

        # Process Only in A
        for f in only_in_a:
            size, mtime = self.get_file_info(os.path.join(dir_a, f))
            results.append((f, "僅在 A", size, "-", mtime, "-", 'only_a'))

        # Process Only in B
        for f in only_in_b:
            size, mtime = self.get_file_info(os.path.join(dir_b, f))
            results.append((f, "僅在 B", "-", size, "-", mtime, 'only_b'))

        # Process Common but maybe different
        for f in sorted(list(common_files)):
            file_a = os.path.join(dir_a, f)
            file_b = os.path.join(dir_b, f)
            
            # Use filecmp to check shallowly (size/mtime)
            if not filecmp.cmp(file_a, file_b, shallow=False):
                size_a, mtime_a = self.get_file_info(file_a)
                size_b, mtime_b = self.get_file_info(file_b)
                results.append((f, "內容不同", size_a, size_b, mtime_a, mtime_b, 'diff'))
                count_diff += 1

        # 將所有結果依照「相對路徑」進行排序，讓同一個目錄（例如 BIOS_U51）的檔案能排在一起顯示
        results.sort(key=lambda x: x[0].lower())

        for res in results:
            self.tree.insert("", tk.END, values=res[:-1], tags=(res[-1],))

        # Coloring tags
        self.tree.tag_configure('only_a', foreground='blue')
        self.tree.tag_configure('only_b', foreground='purple')
        self.tree.tag_configure('diff', foreground='red')

        total_diff = len(only_in_a) + len(only_in_b) + count_diff
        self.status_var.set(f"比對完成！發現 {total_diff} 處差異。 (僅在A: {len(only_in_a)}, 僅在B: {len(only_in_b)}, 不同: {count_diff})")

if __name__ == "__main__":
    root = tk.Tk()
    app = FolderComparer(root)
    root.mainloop()
