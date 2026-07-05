# 运维手册

## 每天怎么跑

本机常驻：

```bash
make daily
```

cron 示例：

```bash
0 9 * * * cd /path/to/project && AUTO_DEPLOY=1 /path/to/python automation/run_daily.py >> /tmp/alimama_cron.log 2>&1
```

## 手动发布

```bash
make download
make package
make deploy
```

## 前端开发

```bash
make dev
```

前端目录是 `frontend/`，使用 Vue 3 + Vite。

构建产物输出到：

```text
site/
```

## 数据生成

```bash
make data
```

输出文件：

```text
frontend/src/data/dashboard-data.json
```

## 日志

默认日志：

```text
/tmp/alimama_download.log
/tmp/alimama_cron.log
```

默认失败截图：

```text
/tmp/alimama_screenshots
```

## 故障排查

登录态过期：

```bash
make login
```

下载失败：

```bash
HEADED=1 python3 automation/wanxiangtai_download.py download
```

前端依赖缺失：

```bash
cd frontend
pnpm install
```

构建失败：

```bash
make check
```

GitHub Pages 没更新：

1. 查看 GitHub 仓库 `Actions`
2. 确认 `Deploy Dashboard to GitHub Pages` 成功
3. 确认 `Settings -> Pages` 使用 `GitHub Actions`

## 发布前检查

```bash
make check
make package
```

确认 `site/` 内容可以公开后再执行：

```bash
make deploy
```
