# FolderCompare - 資料夾內容比對工具

這是一個基於 Python 撰寫的輕量級資料夾比對工具，具備圖形介面（GUI），專為需要快速、精確比對兩個目錄差異的開發者或維運人員設計。

特別針對多層級子目錄（如 BIOS、CPLD 等版本資料夾）進行了排序優化，讓相關檔案能集中呈現。

## 🌟 主要功能

- **遞迴比對**：自動掃描所有子目錄下的檔案。
- **三種差異狀態標示**：
  - <font color="blue">**僅在 A**</font> (藍色)：檔案只存在於左側路徑。
  - <font color="purple">**僅在 B**</font> (紫色)：檔案只存在於右側路徑。
  - <font color="red">**內容不同**</font> (紅色)：兩邊皆有同名檔案，但大小或最後修改時間不一致。
- **路徑優化排序**：結果依照「相對路徑」字母排序，讓同一個子目錄下的檔案（不論是在 A、B 或是內容不同）都能排列在一起，方便視覺對比。
- **支援 UNC 路徑**：支援直接貼上網路芳鄰路徑（例如 `\\synofiles\...\`）。
- **詳細資訊顯示**：列出檔案大小（Bytes）與精確的修改時間戳記。

## 🚀 如何使用

### 方法 A：直接執行 (推薦)
1. 進入 `dist` 資料夾。
2. 雙擊執行 `FolderCompare.exe` 即可啟動。

### 方法 B：透過 Python 啟動
如果你已經安裝了 Python 3.10+：
```bash
python folder_compare.py
```

## 🛠️ 開發與打包

### 環境要求
- Python 3.10 或以上版本
- `PyInstaller` (僅打包時需要)

### 安裝依賴
```bash
pip install pyinstaller
```

### 打包為單一 EXE
專案內附帶了 `build_exe.py` 自動化腳本，執行它即可完成打包：
```bash
python build_exe.py
```
打包後的產物會自動產生成在 `dist/FolderCompare.exe`。

## 📂 檔案結構
- `folder_compare.py`: 主要 GUI 程式邏輯。
- `build_exe.py`: 自動化打包腳本。
- `run_compare.bat`: 快速啟動批次檔。
- `dist/`: 存放打包完成的 EXE 檔案。
- `README.md`: 專案說明文件。

## 📝 授權
此專案採用 [MIT License](LICENSE) 授權。
