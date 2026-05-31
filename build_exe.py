# -*- coding: utf-8 -*-
"""打包为单文件 exe（控制台可见）。"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
EXE_NAME = f"易学酷信息获取_{datetime.now().strftime('%m%d')}"


def main() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("正在安装 PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0.0"])

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--console",
        f"--name={EXE_NAME}",
        "--distpath",
        str(BASE_DIR / "dist"),
        "--workpath",
        str(BASE_DIR / "build"),
        "--specpath",
        str(BASE_DIR),
        "--hidden-import=openpyxl.cell._writer",
        str(BASE_DIR / "yxk_batch_runner.py"),
    ]

    print(f"开始打包: {EXE_NAME}.exe")
    subprocess.check_call(cmd, cwd=BASE_DIR)
    output = BASE_DIR / "dist" / f"{EXE_NAME}.exe"
    print(f"\n打包完成: {output}")
    print("纯 API 登录，无需安装 Chromium。")


if __name__ == "__main__":
    main()
