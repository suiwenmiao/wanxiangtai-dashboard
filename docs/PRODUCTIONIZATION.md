# 正式化路线图

## 当前项目分层

```text
frontend/   Vue 3 + Vite 前端
automation/ 本地自动下载、数据生成、部署脚本
site/       GitHub Pages 发布产物
data/       本地私有数据，不提交 Git
docs/       文档
```

## 已完成

- 前端改造成真正的 Vue/Vite 项目。
- 自动化脚本集中到 `automation/`。
- 前端数据由 `automation/generate_dashboard_data.py` 生成 JSON。
- Vite 构建产物统一输出到 `site/`。
- GitHub Pages workflow 发布 `site/`。
- `.gitignore` 隔离本地数据、登录态和依赖目录。
- `Makefile` 统一常用命令。
- CI 同时检查 Python 和前端构建。

## 推荐运行链路

```text
make daily
  -> automation/wanxiangtai_download.py download
  -> automation/generate_dashboard_data.py
  -> frontend pnpm build
  -> git commit site/
  -> git push
  -> GitHub Pages deploy
```

## 还可以继续优化

- 把 `wanxiangtai_download.py` 拆成登录、下载、解析、追加数据几个模块。
- 给 Excel 字段做更严格的数据校验。
- 增加失败通知，比如飞书、企业微信或邮件。
- 前端增加更多下钻维度，如商品主体、计划、场景。
- 将大数据从打包进 JS 改成 `public/data.json` 按需加载。
- 加入 E2E 截图检查，保证页面发布后不空白。

## 公开部署风险

`site/` 是公开发布产物，前端构建会包含聚合后的投放数据。公开仓库或公开 Pages 前，请确认这些数据可以让外部看到。

绝不能提交：

- `.env`
- `data/`
- 万相台登录态
- 原始 Excel、CSV、ZIP 报表
