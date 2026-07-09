# 运维手册

## 每天怎么跑

本机常驻：

```bash
make daily
```

`make daily` 会进入常驻循环，等待下一个 7:30 再执行；不会启动后立刻跑一次。

cron 示例：

```bash
30 7 * * * cd /path/to/project && AUTO_DEPLOY=1 /path/to/python automation/run_daily.py once >> /tmp/alimama_cron.log 2>&1
```

## 手动发布

```bash
make download
make deploy
```

`make download` 会下载报表、验证关键字段、只把目标日期写入大表，并匹配品类/细类。不要在每日链路里再手动运行 `match_category.py` 追加同一份数据。

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

日志里出现 `登录态已过期` 时，先运行上面的登录命令，扫码完成后再手动跑一次 `make download`。

下载失败：

```bash
HEADED=1 python3 automation/wanxiangtai_download.py download
```

重点检查 `/tmp/alimama_screenshots/02_dialog.png` 和 `04_dl_list.png`：脚本会读取弹窗里的精确任务名，并只等待这个任务，避免下载旧任务。

如果下载文件包含多日数据，脚本会在写入大表前只保留目标日期；这是正常保护，不是失败。

如果本地已有当天报表 CSV，`make download` 会优先复用并重新校验写表；需要强制重新创建下载任务时使用：

```bash
FORCE_DOWNLOAD=1 python3 automation/wanxiangtai_download.py download
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
