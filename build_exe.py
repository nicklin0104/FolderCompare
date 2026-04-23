import PyInstaller.__main__
import os
import shutil

# 定義路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(current_dir, "folder_compare.py")
output_name = "FolderCompare"

print(f"正在打包 {script_path}...")

PyInstaller.__main__.run([
    script_path,
    "--onefile",           # 打包成單一檔案
    "--noconsole",         # 執行時不顯示主控台視窗
    f"--name={output_name}", # 輸出的檔名
    f"--distpath={os.path.join(current_dir, 'dist')}", # 指定輸出 dist 路徑
    f"--workpath={os.path.join(current_dir, 'build')}", # 指定 build 路徑
    f"--specpath={current_dir}", # 指定 spec 路徑
    "--clean",             # 清除臨時快取
])

print("\n打包完成！")
print(f"您的 EXE 檔案位於: {os.path.join(current_dir, 'dist', output_name + '.exe')}")
