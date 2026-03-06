# 币安 KYC Telegram 机器人

> 通过 Telegram 聊天完成身份验证 — 无需离开对话即可完成 KYC。

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

[English](README.md)

---

## ✨ 功能特性

- **对话式流程** — 通过自然聊天逐步完成身份验证
- **12 状态机** — 健壮的状态管理，完整的流程控制
- **多语言支持** — 中文、英文（可扩展至任意语言）
- **输入校验** — 姓名、出生日期（≥18岁）、国籍、地址、证件照片
- **多种证件** — 护照、身份证、驾驶证
- **演示模式** — 无需真实 API 即可运行，方便开发测试
- **会话持久化** — 每个用户的状态以 JSON 保存，重启不丢失
- **Docker 部署** — 一条命令完成部署

## 🌐 交互式 Web 演示

在浏览器中体验完整 KYC 流程 — 无需 Telegram：

```bash
./scripts/demo.sh
```

打开：
- **http://localhost:8099** — 💬 聊天演示（模拟 Telegram 对话）
- **http://localhost:8099/business** — 💼 商业分析（市场数据、ROI 计算器、竞品分析）

演示包含：
- 模拟 Telegram 的实时聊天界面
- 逐步进度跟踪
- 与传统 KYC 的对比面板
- 交互式 ROI 计算器
- 完整竞品分析（Jumio、Onfido、Sumsub）

## 📋 架构

```
用户 (Telegram) ←→ python-telegram-bot ←→ 状态机 ←→ 会话存储 (JSON)
                                              ↓
                                  [生产环境] 币安 KYC API
```

### KYC 流程

```
/start_kyc → 同意条款 → 姓名 → 出生日期 → 国籍 → 地址
→ 选择证件类型 → 上传正面 → [上传背面] → 自拍
→ 确认信息 → 提交 → 审核通过 ✅
```

### 项目结构

```
binance-kyc-skill/
├── src/binance_kyc/             # 核心包
│   ├── __init__.py              # 包元数据
│   ├── cli.py                   # CLI 入口
│   ├── config.py                # 配置（环境变量 + .env）
│   ├── models/
│   │   ├── enums.py             # KYCState, DocumentType 等枚举
│   │   └── session.py           # Pydantic 会话模型
│   ├── services/
│   │   ├── state_machine.py     # 状态转换 & 流程逻辑
│   │   ├── session_store.py     # JSON 文件持久化
│   │   └── validators.py        # 输入校验器
│   ├── handlers/
│   │   └── telegram.py          # Telegram 消息处理器
│   ├── messages/
│   │   ├── __init__.py          # 消息加载 + 语言检测
│   │   ├── en.json              # 英文模板
│   │   └── zh.json              # 中文模板
│   └── utils/
│       └── logging.py           # 结构化日志 (structlog)
├── demo_server/                 # 交互式 Web 演示
│   └── app.py                   # FastAPI 演示服务器
├── static/                      # Web 演示前端
│   ├── index.html               # 聊天演示页
│   ├── business.html            # 商业分析页
│   ├── style.css                # 暗黑主题 UI
│   ├── app.js                   # 聊天演示逻辑
│   └── i18n.js                  # 中英文切换
├── tests/                       # pytest 测试套件（76 个测试）
├── scripts/
│   ├── start.sh                 # 一键启动 Telegram Bot
│   ├── demo.sh                  # 一键启动 Web 演示
│   └── lint.sh                  # 代码检查 + 类型检查 + 测试
├── pyproject.toml               # PEP 621 项目配置
├── Dockerfile                   # 容器镜像
├── docker-compose.yml           # 一键部署
├── .env.example                 # 配置模板
├── SKILL.md                     # OpenClaw Skill 定义
└── LICENSE                      # MIT 许可证
```

## 🚀 快速开始

### 方式一：一键启动

```bash
git clone https://github.com/alfred-bot-001/binance-kyc-skill.git
cd binance-kyc-skill

# 首次运行会创建 .env 文件 — 填入你的 Telegram Bot Token
./scripts/start.sh

# 编辑 .env 后再次运行
./scripts/start.sh
```

### 方式二：手动安装

```bash
# 克隆项目
git clone https://github.com/alfred-bot-001/binance-kyc-skill.git
cd binance-kyc-skill

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e ".[dev]"

# 配置
cp .env.example .env
# 编辑 .env — 设置 BINANCE_KYC_TELEGRAM_TOKEN

# 启动
binance-kyc run
```

### 方式三：Docker

```bash
cp .env.example .env
# 编辑 .env — 设置 BINANCE_KYC_TELEGRAM_TOKEN

docker compose up -d
```

## ⚙️ 配置说明

所有配置通过环境变量（或 `.env` 文件）控制：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BINANCE_KYC_TELEGRAM_TOKEN` | *（必填）* | Telegram Bot Token（从 @BotFather 获取） |
| `BINANCE_KYC_MODE` | `demo` | `demo`（演示）或 `production`（生产） |
| `BINANCE_KYC_LOG_LEVEL` | `INFO` | `DEBUG`、`INFO`、`WARNING`、`ERROR` |
| `BINANCE_KYC_DEFAULT_LANGUAGE` | `en` | 默认语言代码 |
| `BINANCE_KYC_DATA_DIR` | `data` | 会话 & 上传文件存储路径 |
| `BINANCE_KYC_SESSION_TIMEOUT_MINUTES` | `30` | 会话超时时间（分钟） |
| `BINANCE_KYC_API_KEY` | — | 币安 API Key（仅生产环境） |
| `BINANCE_KYC_API_SECRET` | — | 币安 API Secret（仅生产环境） |

## 🤖 Telegram Bot 设置

1. 在 Telegram 上搜索 [@BotFather](https://t.me/BotFather)
2. 创建新 Bot：发送 `/newbot`
3. 复制 Token 到 `.env` 文件
4. 在 BotFather 注册命令：

```
start_kyc - 开始身份验证
status - 查询验证状态
cancel - 取消当前验证
help - 显示帮助信息
```

## 🧪 开发指南

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check src/ tests/

# 类型检查
mypy src/

# 格式化代码
ruff format src/ tests/

# 一键运行所有检查
./scripts/lint.sh
```

## 🌍 添加新语言

1. 基于 `en.json` 创建 `src/binance_kyc/messages/<语言代码>.json`
2. 翻译所有消息字符串
3. （可选）在 `messages/__init__.py` 中添加语言检测规则

## 📦 演示模式 vs 生产模式

### 演示模式（默认）
- 不调用真实 API
- 提交后 10 秒自动审核通过
- 图片仅本地保存，不传输
- 适合开发和演示

### 生产模式
设置 `BINANCE_KYC_MODE=production` 并提供 API 凭据后，Bot 将：
- 向币安 KYC API 提交数据
- 执行真实的证件验证
- 返回实际的审核结果

## 📄 许可证

[MIT](LICENSE)
