# GPT Usage Widget

一个 Windows 桌面小组件，用于实时监控 ChatGPT / Codex 计算额度使用情况。

---

## 📁 项目结构

```
gpt-widget/
├── main.py                 # 程序入口
├── requirements.txt        # Python 依赖
├── start.ps1               # 一键启动脚本（PowerShell）
├── config/
│   └── config_manager.py   # 配置管理（Cookie 存储、开机自启等）
├── core/
│   ├── api_client.py       # ChatGPT API 调用（认证 + 额度查询）
│   ├── scheduler.py        # 定时刷新调度器
│   └── data_cache.py       # 数据缓存
├── ui/
│   ├── widget.py           # 主窗口小组件
│   ├── settings_dialog.py  # 设置对话框
│   └── themes.py           # 主题管理
└── tray/
    └── tray_icon.py        # 系统托盘图标
```

---

## 🚀 快速启动（开发模式）

### 前置要求

- **Python 3.9+**（推荐 3.9 ~ 3.12）
- **Windows 10/11**

### 方式一：一键启动脚本（推荐）

在项目根目录下右键打开 PowerShell，运行：

```powershell
.\start.ps1
```

该脚本会自动：
1. 查找本地 Python 安装
2. 创建虚拟环境（`.venv-py39` 或类似）
3. 安装依赖
4. 启动程序

### 方式二：手动启动

```powershell
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动程序
python main.py
```

### 依赖列表

| 包名 | 版本要求 | 用途 |
|------|---------|------|
| PyQt6 | >=6.6.0, <6.11 | GUI 界面 |
| requests | >=2.31.0 | HTTP 请求 |
| keyring | >=24.0.0 | 安全凭据存储 |
| pywin32 | >=306 | Windows 注册表操作（开机自启） |

---

## 🔑 配置 Cookie

程序启动后会弹出设置对话框，需要配置 ChatGPT 的 Cookie：

1. 浏览器打开 [chatgpt.com](https://chatgpt.com) 并登录
2. 按 **F12** → 点击 **Network（网络）** 标签
3. 刷新页面（Ctrl+R）
4. 点击请求列表中的任意请求
5. 在右侧 **Request Headers** 中找到 `Cookie:` 那一行
6. 复制 `Cookie:` 后面的 **完整内容**
7. 粘贴到设置对话框的输入框中，点击保存

> **为什么需要完整 Cookie？**
> ChatGPT 使用 Cloudflare 防护，除了 session token 外还需要 `cf_clearance` 等 cookie 才能正常访问 API。

---

## 📦 打包为 EXE

### 方式一：PyInstaller（推荐）

#### 1. 安装 PyInstaller

```powershell
# 确保在虚拟环境中
pip install pyinstaller
```

#### 2. 打包命令

**单文件打包**（生成单个 exe，体积较大，启动稍慢）：

```powershell
pyinstaller --noconfirm --onefile --windowed --name "GPTWidget" --icon=NONE main.py
```

**目录打包**（生成文件夹，启动更快，推荐）：

```powershell
pyinstaller --noconfirm --onedir --windowed --name "GPTWidget" --icon=NONE main.py
```

参数说明：
| 参数 | 说明 |
|------|------|
| `--onefile` | 打包为单个 exe 文件 |
| `--onedir` | 打包为文件夹（推荐，启动更快） |
| `--windowed` | 不显示控制台窗口 |
| `--name "GPTWidget"` | 输出文件名 |
| `--icon=icon.ico` | 自定义图标（需准备 .ico 文件） |

#### 3. 打包输出

- 单文件模式：`dist/GPTWidget.exe`
- 目录模式：`dist/GPTWidget/GPTWidget.exe`

#### 4. 使用 .spec 文件（高级）

首次打包会生成 `GPTWidget.spec` 文件，可编辑后复用：

```powershell
# 编辑 spec 文件后重新打包
pyinstaller GPTWidget.spec
```

完整 spec 文件示例：

```python
# GPTWidget.spec
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6.sip',
        'keyring.backends',
        'keyring.backends.Windows',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,        # 单文件模式包含此行
    a.zipfiles,        # 单文件模式包含此行
    a.datas,           # 单文件模式包含此行
    [],
    name='GPTWidget',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,     # 不显示控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',  # 取消注释并指定图标文件
)
```

### 方式二：Nuitka（性能更好）

```powershell
# 安装 Nuitka
pip install nuitka

# 打包
nuitka --standalone --onefile --windows-console-mode=disable --output-filename=GPTWidget.exe main.py
```

> **注意**：Nuitka 首次打包需要下载 C 编译器，耗时较长。

---

## ❓ 常见问题

### Q: 提示 "Session 已过期"
确保从浏览器复制的是**完整的 Cookie 请求头**（包含 `cf_clearance`），而不仅是 session token。

### Q: 打包后运行报错找不到模块
在 PyInstaller 命令中添加 `--hidden-import` 参数：
```powershell
pyinstaller --onefile --windowed --hidden-import=keyring.backends.Windows --hidden-import=PyQt6.sip main.py
```

### Q: 打包后的 exe 被杀毒软件误报
这是 PyInstaller 打包的常见问题，可以：
- 使用 `--onedir` 模式替代 `--onefile`
- 对 exe 进行数字签名
- 在杀毒软件中添加白名单

### Q: Cookie 多久过期？
ChatGPT 的 session cookie 通常有效期为 **1-2 周**，过期后需要重新从浏览器获取。

---

## 📝 配置文件位置

程序配置保存在：`%USERPROFILE%\.gpt-widget\settings.json`

日志文件位于：`%USERPROFILE%\.gpt-widget\logs\app.log`
