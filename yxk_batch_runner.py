# -*- coding: utf-8 -*-
"""易学酷批量查询 - 一键运行入口。"""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import requests

from yxk_api_login import login_by_api_adaptive
from yxk_core import LoginStatus, load_title_dict_with_retry
from yxk_excel import ensure_template, export_results, read_accounts
from yxk_paths import get_base_dir

BASE_DIR = get_base_dir()


class BatchRunnerApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("易学酷批量查询")
        self.root.geometry("620x360")
        self.root.resizable(False, False)

        self.input_file: Path | None = None
        self.running = False

        self._build_ui()
        self.root.after(300, self._auto_select_file)

    def _build_ui(self) -> None:
        title = tk.Label(
            self.root,
            text="易学酷账号批量查询（API 直连登录）",
            font=("Microsoft YaHei UI", 14, "bold"),
        )
        title.pack(pady=16)

        file_frame = tk.Frame(self.root)
        file_frame.pack(fill="x", padx=20)

        tk.Label(file_frame, text="输入文件：", font=("Microsoft YaHei UI", 10)).pack(side="left")
        self.file_var = tk.StringVar(value="尚未选择文件")
        tk.Entry(
            file_frame,
            textvariable=self.file_var,
            width=52,
            state="readonly",
            readonlybackground="#F5F5F5",
        ).pack(side="left", padx=8)
        tk.Button(file_frame, text="重新选择", command=self._select_file).pack(side="left")

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=18)

        self.run_btn = tk.Button(
            btn_frame,
            text="一键运行",
            width=16,
            height=2,
            bg="#4472C4",
            fg="white",
            font=("Microsoft YaHei UI", 11, "bold"),
            command=self._start_run,
        )
        self.run_btn.pack(side="left", padx=8)

        tk.Button(
            btn_frame,
            text="打开输入模板",
            width=16,
            height=2,
            command=self._open_template,
        ).pack(side="left", padx=8)

        tk.Button(
            btn_frame,
            text="打开结果目录",
            width=16,
            height=2,
            command=self._open_output_dir,
        ).pack(side="left", padx=8)

        self.progress = ttk.Progressbar(self.root, mode="indeterminate", length=560)
        self.progress.pack(pady=8)

        self.log = tk.Text(self.root, height=10, width=74, font=("Consolas", 10))
        self.log.pack(padx=20, pady=8)
        self._append_log("程序已启动，正在等待选择输入 Excel...")

    def _append_log(self, text: str) -> None:
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.root.update_idletasks()

    def _output_dir(self) -> Path:
        if self.input_file:
            return self.input_file.parent
        return BASE_DIR / "output"

    def _select_file(self) -> None:
        template = ensure_template()
        selected = filedialog.askopenfilename(
            title="选择账号导入 Excel 文件",
            initialdir=str(template.parent),
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
        )
        if selected:
            self.input_file = Path(selected)
            self.file_var.set(str(self.input_file))
            self._append_log(f"已选择文件: {self.input_file}")
            self._append_log(f"结果将导出到: {self.input_file.parent}")

    def _auto_select_file(self) -> None:
        self._select_file()
        if not self.input_file:
            if messagebox.askyesno("提示", "未选择输入文件。\n是否打开输入模板所在目录？"):
                self._open_template()

    def _open_template(self) -> None:
        template = ensure_template()
        os.startfile(template)

    def _open_output_dir(self) -> None:
        output_dir = self._output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(output_dir)

    def _start_run(self) -> None:
        if self.running:
            return
        if not self.input_file or not self.input_file.exists():
            messagebox.showwarning("提示", "请先选择有效的输入 Excel 文件。")
            self._select_file()
            return

        self.running = True
        self.run_btn.config(state="disabled")
        self.progress.start(12)
        threading.Thread(target=self._run_batch, daemon=True).start()

    def _run_batch(self) -> None:
        input_file = self.input_file
        output_dir = input_file.parent if input_file else BASE_DIR / "output"

        try:
            accounts = read_accounts(input_file)
            if not accounts:
                self.root.after(0, lambda: messagebox.showwarning("提示", "Excel 中没有可处理的账号数据。"))
                return

            self.root.after(
                0,
                lambda: self._append_log(
                    f"共读取 {len(accounts)} 个账号，开始 API 直连登录（失败可重试）..."
                ),
            )
            title_dict = load_title_dict_with_retry(
                on_retry=lambda attempt, msg: self.root.after(
                    0,
                    lambda a=attempt, m=msg: self._append_log(f"  [字典加载重试 {a}] {m}"),
                )
            )
            results = []
            session = requests.Session()

            for index, account in enumerate(accounts, start=1):
                self.root.after(
                    0,
                    lambda i=index, u=account.username: self._append_log(f"[{i}/{len(accounts)}] 正在处理: {u}"),
                )

                def on_retry(attempt: int, detail: object, u=account.username) -> None:
                    if isinstance(detail, str):
                        reason = detail
                    else:
                        reason = getattr(detail, "error_msg", "") or getattr(detail, "status", "")
                        if hasattr(reason, "value"):
                            reason = reason.value
                    self.root.after(
                        0,
                        lambda a=attempt, r=reason, name=u: self._append_log(
                            f"  [重试 {a}] {name}: {r}"
                        ),
                    )

                result = login_by_api_adaptive(account, title_dict, session=session, on_retry=on_retry)
                results.append(result)
                status_text = result.status.value
                if result.is_problem:
                    status_text = f"{result.problem_label} | {status_text}"
                if result.retry_count:
                    status_text += f" (重试{result.retry_count}次)"
                self.root.after(
                    0,
                    lambda s=status_text, u=account.username: self._append_log(f"  -> {u}: {s}"),
                )

            output_path = export_results(results, output_dir=output_dir)
            problem_count = sum(1 for item in results if item.is_problem)
            password_count = sum(1 for item in results if item.status == LoginStatus.PASSWORD_ERROR)

            def finish() -> None:
                self._append_log(f"导出完成: {output_path}")
                self._append_log(f"有问题账号 {problem_count} 个，其中账号密码错误 {password_count} 个（已排在表前并标色）")
                messagebox.showinfo(
                    "完成",
                    f"处理完成！\n\n总账号: {len(results)}\n有问题: {problem_count}\n账号密码错误: {password_count}\n\n结果文件:\n{output_path}",
                )
                if messagebox.askyesno("打开结果", "是否立即打开结果 Excel？"):
                    os.startfile(output_path)

            self.root.after(0, finish)
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror("运行失败", str(exc)))
            self.root.after(0, lambda: self._append_log(f"错误: {exc}"))
        finally:
            def reset() -> None:
                self.running = False
                self.run_btn.config(state="normal")
                self.progress.stop()

            self.root.after(0, reset)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print("易学酷批量查询已启动（API 直连，无需浏览器）")
    print(f"工作目录: {BASE_DIR}")
    app = BatchRunnerApp()
    app.run()


if __name__ == "__main__":
    main()
