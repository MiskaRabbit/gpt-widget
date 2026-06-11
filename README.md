# GPT Usage Widget

一个桌面悬浮小工具，用于展示 ChatGPT / Codex 的 5 小时额度和周额度。

当前支持：

- Windows 10/11：源码运行、托盘、设置、Windows 注册表开机自启。
- macOS：源码运行、菜单栏托盘、系统钥匙串 Cookie 存储。

## 功能

- 双环展示 5 小时额度和周额度。
- 支持普通模式和极简双环模式。
- 支持手动刷新、定时刷新、主题和透明度设置。
- Cookie 通过 `keyring` 存储到系统凭据后端；旧版 JSON Cookie 会在首次读取时自动迁移。
- 代理支持手动填写 `proxy_url`，也会读取 `HTTPS_PROXY`、`HTTP_PROXY`、`ALL_PROXY` 环境变量。
- Windows 可自动读取系统代理和设置开机自启；macOS 暂不支持系统代理自动探测和开机自启。

## 项目结构

```text
gpt-widget/
├── main.py
├── requirements.txt
├── start.ps1
├── start.command
├── config/
│   └── config_manager.py
├── core/
│   ├── api_client.py
│   ├── data_cache.py
│   └── scheduler.py
├── tray/
│   └── tray_icon.py
└── ui/
    ├── components/
    ├── settings_dialog.py
    ├── themes.py
    └── widget.py
```

## 运行要求

- Python 3.11+ 推荐。
- Windows 10/11 或 macOS。
- macOS 首次保存 Cookie 时可能会弹出钥匙串访问授权。

依赖说明：

| 包 | 用途 |
| --- | --- |
| PyQt6 | 桌面界面 |
| curl_cffi | 带 Chrome TLS 指纹的请求 |
| keyring | Windows 凭据管理器 / macOS 钥匙串存储 |
| pywin32 | 仅 Windows 安装，用于注册表自启和代理读取 |

## Windows 启动

```powershell
cd C:\Users\xujin\Desktop\xn\ed-util\gpt-widget
.\start.ps1
```

手动启动：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## macOS 启动

第一次运行建议先给脚本执行权限：

```bash
cd /path/to/gpt-widget
chmod +x start.command
./start.command
```

也可以手动启动：

```bash
cd /path/to/gpt-widget
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

macOS 说明：

- Cookie 会通过 `keyring` 写入系统钥匙串，不再写入 `~/.gpt-widget/settings.json`。
- 如果旧配置里已有 `_raw_cookies` 或旧 session token 字段，首次读取时会迁移到钥匙串并清理旧字段。
- macOS 暂不显示“开机自动启动”设置项。
- macOS 暂不读取系统代理设置；请手动填写代理，或设置 `HTTPS_PROXY` / `HTTP_PROXY` / `ALL_PROXY`。

## 配置 Cookie

1. 浏览器打开 [chatgpt.com](https://chatgpt.com) 并登录。
2. 打开开发者工具，进入 Network。
3. 刷新页面，点开任意 chatgpt.com 请求。
4. 在 Request Headers 中找到 `Cookie`。
5. 复制 `Cookie:` 后面的完整内容。
6. 粘贴到小工具设置面板里并保存。

建议复制完整 Cookie，而不仅是 session token。ChatGPT 可能还需要 `cf_clearance` 等 cookie 才能通过校验。

## 配置位置

- 非敏感设置：`~/.gpt-widget/settings.json`
- 日志：`~/.gpt-widget/logs/app.log`
- Cookie：系统凭据后端，由 `keyring` 管理。

## 常见问题

### macOS 上提示无法写入钥匙串

确认系统弹出的钥匙串授权已允许。如果仍失败，程序会退回到 JSON 配置保存，但这不是推荐路径。

### 提示网络连接失败

如果浏览器能打开 ChatGPT，但小工具失败，通常需要配置代理。优先在设置面板填写类似 `http://127.0.0.1:7890` 的代理地址。

### 提示 Session 已过期

重新从浏览器 Network 面板复制最新完整 Cookie 并保存。

### macOS 没有开机自启

当前 macOS 版本只支持源码运行和基础功能，不包含 LaunchAgent、自启、签名、notarization 或 `.dmg` 发布。

## 致谢

特别感谢 [linux.do](https://linux.do/) 社区的反馈与支持。
