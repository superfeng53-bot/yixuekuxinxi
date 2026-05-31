# 易学酷信息获取

批量登录 [易学酷](https://yxk.cmnt.cn/) 平台，导出姓名、身份证号码、单位名称、专业职称等信息。

## 功能

- Excel 批量导入账号密码
- **纯 API 直连登录**（无需浏览器，密码 MD5 后提交）
- 可重试错误自动重试（网络超时、服务端繁忙等）
- 问题账号排在导出表最前并标色
- **结果 Excel 保存在输入文件同目录**

## 快速使用

### 方式一：一键运行（源码）

双击 `一键运行.bat`，选择输入 Excel，等待导出。

### 方式二：独立 exe

运行 `dist/易学酷信息获取_MMDD.exe`（MMDD 为打包月日，如 0531 表示 5 月 31 日）。

## 输入模板

| 列名 | 必填 | 说明 |
|------|------|------|
| 账号 | 是 | 手机号 / 证件号 / 用户名 |
| 密码 | 是 | 明文密码（程序内 MD5 后提交） |
| 备注 | 否 | 原样带入导出结果 |

## 输出说明

结果文件：`输入文件目录/易学酷查询结果_时间戳.xlsx`

- 问题账号自动排在表前并标色
- 账号密码错误（10013）单独高亮
- **重试次数**列记录实际重试次数

## 登录方式说明

网关接口 `POST /auth/v1/open/loginValid/login` 可直接登录，**不需要滑块验证码**（验证码仅前端页面校验）。因此本工具不使用浏览器，速度更快、依赖更少。

## 环境要求

- Windows 10/11
- Python 3.10+（源码运行）
- 可访问 `yxk.cmnt.cn` / `gwssl.cmnt.cn`

## 源码安装

```bash
pip install -r requirements.txt
python yxk_batch_runner.py
```

## 打包 exe

```bash
pip install -r requirements-dev.txt
python build_exe.py
```

## 项目结构

```
yxk_batch_runner.py   # GUI 主入口
yxk_api_login.py      # API 登录（含重试）
yxk_core.py           # 常量 / 状态 / 字典
yxk_retry.py          # 重试策略
yxk_excel.py          # Excel 导入导出
build_exe.py          # 打包脚本
一键运行.bat
```

## 注意事项

- 仅用于已授权账号的信息查询
- 账号密码错误不会重试，会直接标记
- 网络不稳定时程序会自动重试最多 3 次
