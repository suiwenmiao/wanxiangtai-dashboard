# 万相台投放数据看板

这是一个正式的「自动化数据 + Vue 前端 + GitHub Pages 部署」项目。

核心链路：

```text
万相台网页下载报表 -> 更新本地 Excel 大表 -> 生成前端 JSON 数据 -> Vue 构建 -> GitHub Pages 发布
```

## 目录结构

```text
.
├── frontend/                 # 真正的 Vue 3 + Vite 前端项目
│   ├── src/
│   │   ├── App.vue
│   │   ├── components/
│   │   ├── data/             # 自动生成 dashboard-data.json
│   │   └── utils/
│   ├── package.json
│   └── vite.config.js
├── automation/               # 本地自动化脚本
│   ├── wanxiangtai_download.py
│   ├── generate_dashboard_data.py
│   ├── deploy_static.py
│   ├── run_daily.py
│   ├── match_category.py
│   └── config.py
├── data/                     # 本地数据目录，已被 git 忽略
├── site/                     # Vue 构建产物，GitHub Pages 发布这里
├── docs/                     # 运维和正式化文档
├── scripts/                  # 项目维护脚本
├── .github/workflows/        # CI 和 Pages 部署
├── Makefile                  # 常用命令入口
├── requirements.txt          # Python 依赖
└── .env.example              # 本地配置模板
```

## 本地启动

Windows 和 macOS 都推荐使用同一个 Python 入口，避免 `make`、环境变量写法、换行差异在两台电脑之间互相影响。

安装依赖：

```bash
python scripts/dev.py setup
```

复制配置：

```bash
cp .env.example .env
```

至少检查 `.env` 里的这些路径：

```text
WORKBUDDY_DATA_FILE
WORKBUDDY_BASE_TABLE
WORKBUDDY_REPORT_DIR
WORKBUDDY_ALIMAMA_STATE
```

启动 Vue 前端：

```bash
python scripts/dev.py dev
```

构建前端：

```bash
python scripts/dev.py build
```

## 自动化流程

首次扫码登录万相台：

```bash
python scripts/dev.py login
```

手动下载昨日报表并更新 Excel 大表：

```bash
python scripts/dev.py download
```

只生成前端数据：

```bash
python scripts/dev.py data
```

打包发布目录：

```bash
python scripts/dev.py package
```

发布到 GitHub Pages：

```bash
python scripts/dev.py deploy
```

每日自动下载并发布：

```bash
python scripts/dev.py daily-loop
```

## 部署方式

项目使用 GitHub Pages：

1. 本机运行 `make deploy`
2. 脚本生成 `frontend/src/data/dashboard-data.json`
3. Vite 构建前端到 `site/`
4. 脚本提交并 push `site/`
5. GitHub Actions 发布 `site/`

GitHub 仓库设置：

1. `Settings` -> `Pages`
2. `Build and deployment` 选择 `GitHub Actions`
3. push 后查看 `Actions` 页面确认部署状态

## 常用命令

```bash
python scripts/dev.py check       # Python 语法检查 + 前端构建
python scripts/dev.py dev         # 生成数据并启动 Vue 开发服务器
python scripts/dev.py build       # 生成数据并构建 Vue 到 site/
python scripts/dev.py package     # 完整生成数据和构建 site/
python scripts/dev.py deploy      # 构建并提交/推送 site/
python scripts/dev.py daily-once  # 单次执行每日下载和发布
python scripts/dev.py clean       # 清理缓存
```

如果只在 macOS/Linux 上开发，也可以继续使用 `make`。两台电脑共同开发时，优先使用 `python scripts/dev.py ...`。

## 数据安全

这些内容不会提交到 GitHub：

- `data/`
- `.env`
- `frontend/node_modules/`
- 登录态文件
- 原始 Excel、CSV、ZIP 报表

注意：`site/` 是公开发布内容，里面包含构建后的前端页面和已打包进前端的数据。

## 进一步说明

- [运维手册](docs/OPERATIONS.md)
- [从 Demo 到正式项目的改造路径](docs/PRODUCTIONIZATION.md)
- [Windows / macOS 双电脑开发说明](docs/CROSS_PLATFORM.md)
