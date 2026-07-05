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

安装依赖：

```bash
make setup
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
make dev
```

构建前端：

```bash
make build
```

## 自动化流程

首次扫码登录万相台：

```bash
make login
```

手动下载昨日报表并更新 Excel 大表：

```bash
make download
```

只生成前端数据：

```bash
make data
```

打包发布目录：

```bash
make package
```

发布到 GitHub Pages：

```bash
make deploy
```

每日自动下载并发布：

```bash
make daily
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
make check      # Python 语法检查 + 前端构建
make dev        # 生成数据并启动 Vue 开发服务器
make build      # 生成数据并构建 Vue 到 site/
make package    # 完整生成数据和构建 site/
make deploy     # 构建并提交/推送 site/
make clean      # 清理缓存
```

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
