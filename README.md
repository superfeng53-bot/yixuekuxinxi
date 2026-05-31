# 易学酷信息获取

批量登录 [易学酷](https://yxk.cmnt.cn/) 平台，自动完成滑块验证码，导出姓名、身份证号码、单位名称、专业职称等信息。

## 功能

- Excel 批量导入账号密码
- Playwright 自动滑块登录
- 可重试错误自动重试（网络超时、验证码失败等）
- 问题账号排在导出表最前并标色
- 账号密码错误（10013）单独高亮

## 快速使用

### 方式一：一键运行（开发/源码）

双击 `一键运行.bat`，按提示选择输入 Excel，等待导出结果。

### 方式二：独立 exe

在 `dist/` 目录运行：

```
易学酷信息获取_02_25_MMDD.exe
```

文件名末尾 `MMDD` 为打包日期（月日）。首次运行会在 `%LOCALAPPDATA%\yxk-playwright-browsers` 下载 Chromium。

## 输入模板

程序启动后会弹出文件选择框。也可点击「打开输入模板」生成/打开 `template/账号导入模板.xlsx`。

| 列名 | 必填 | 说明 |
|------|------|------|
| 账号 | 是 | 手机号 / 证件号 / 用户名 |
| 密码 | 是 | 明文密码（程序内 MD5 后提交） |
| 备注 | 否 | 原样带入导出结果 |

## 输出说明

结果保存在 `output/易学酷查询结果_时间戳.xlsx`：

- **问题标记**：账号密码错误等会标注 ⚠
- **重试次数**：本次查询实际重试次数
- 问题账号自动排在表前

## 环境要求

- Windows 10/11
- Python 3.10+（源码运行）
- 可访问 `yxk.cmnt.cn` / `gwssl.cmnt.cn`

## 源码安装

```bash
pip install -r requirements.txt
playwright install chromium
python yxk_batch_runner.py
```

## 打包 exe

```bash
pip install -r requirements-dev.txt
python build_exe.py
```

产物输出到 `dist/`，控制台窗口可见运行日志。

## 项目结构

```
yxk_batch_runner.py   # GUI 主入口
yxk_playwright_login.py
yxk_core.py           # API / 状态 / 字典
yxk_retry.py          # 重试策略
yxk_excel.py          # Excel 导入导出
yxk_paths.py          # 路径与浏览器安装
build_exe.py          # PyInstaller 打包脚本
一键运行.bat
requirements.txt
```

## 注意事项

- 仅用于已授权账号的信息查询
- 账号密码错误不会重试，会直接标记
- 网络不稳定时程序会自动重试最多 3 次
