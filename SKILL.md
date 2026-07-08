# 万相台每日数据下载标准流程 (SKILL)

## 8. 数据计算核心原则：绝不估算

### 8.1 铁律
**所有展示在看板上的数据，必须是在筛选时间范围内对原始数据进行实际分类求和的结果，绝不允许使用比例推算、分摊、按权重缩放等任何形式的估算。**

估算 = 错误。不可接受。

### 8.2 正确的计算方式
数据流水线按所需维度（日期、品类、主体、计划、场景等）对原始行数据进行 `groupby + sum` 聚合，生成预汇总数据。前端仅做过滤过滤求和（filter + reduce），不做任何比例计算。

```
原始大表（63,911行，含日期+品类+主体+场景+计划）
  ↓
实际汇总（按筛选维度 groupby + sum）
  ↓
前端直接过滤求和
```

### 8.3 哪些地方用了实际汇总（正确 ✓）
| 数据源 | 分组维度 | 记录数 | 用途 |
|---|---|---|---|
| `records` | 日期 + 品类 | 1,082 | 第一页 KPI / 趋势图 / 品类表 |
| `categoryScenarioRecords` | 日期 + 品类 + 场景名字 | 3,098 | 渠道推广概览、饼图 |
| `subCategoryRecords` | 日期 + 品类 + 细类 | 5,498 | 细类下钻 |
| `subjectDateRecords` | 日期 + 主体ID | 23,647 | 第二页主体表 |
| `subjectPlanRecords` | 日期 + 主体ID + 计划ID | **63,911** | **展开计划详情** |

### 8.4 哪些情况容易误用估算（错误 ✗）
| 错误做法 | 说明 | 正确做法 |
|---|---|---|
| `ratio = subject.cost / full.cost; plan.cost * ratio` | 用全周期计划花费按比例推算筛选期的花费 | 预汇总 `subjectPlanRecords`，前端直接过滤 |
| `subject.orders × (scenario.cost / subject.cost)` | 用主体总订单按花费占比分摊到场景 | 场景订单直接在数据流水线中 `sum` |
| `scenario.clicks * (subject.cost / full.cost)` | 用全周期场景点击量按花费比例缩放 | 场景点击量在 `categoryScenarioRecords` 中实际汇总 |

### 8.5 如何判断是否正确
1. 检查数据流水线：是否在 `build_xxx` 函数中用 `groupby + sum` 预汇总
2. 检查前端：`getScenarioGroups`、`scenarioSummary` 等函数是否直接用 `payload.xxxRecords` 做 `filter + reduce`，不出现 `* ratio` 或 `/ full.cost` 等比例表达式
3. 验证方法：选「全部」日期范围时，汇总后数据必须等于原始数据直接求和（`差异=0`）

### 8.6 新增维度时的标准流程
当需要按新的维度（如计划、细类、场景等）展示数据时：

1. **数据流水线**：在 `generate_dashboard_data.py` 中新增 `build_xxx_records(df)` 函数，用 `pandas.groupby([维度列]) + agg(sum)` 做实际汇总
2. **JSON 字段**：将结果加入 payload
3. **前端**：组件中直接用 `payload.xxxRecords.filter(...).reduce(...)` 获取数据
4. **禁止**：在前端或数据流水线中用全周期数据乘以比值来推算筛选期数据

### 8.7 检查清单
- [ ] `getScenarioGroups` 无 `ratio = subject.cost / full.cost`
- [ ] `scenarioSummary` 直接使用 `categoryScenarioRecords`
- [ ] 所有 `build_*` 函数只做 `groupby + sum`，不做比例运算
- [ ] `displaySubjects` 的 `orders` 来自 `subjectDateRecords`（日期筛选后），不是 `...meta`（全周期）
## 1. 目的
确保每天下载的万相台报表格式与看板数据流水线一致，避免因数据格式不匹配导致的场景数据丢失。

## 2. 正确数据格式标准

### 2.1 CSV列数
正确格式必须包含 **79列**（含场景/计划维度），区别于**78列**的默认商品主体报表。

### 2.2 关键列
| 索引 | 列名 | 必须 |
|---|---|---|
| 1 | 场景ID | ✓ |
| 2 | 场景名字 | ✓ |
| 3 | 原二级场景ID | ✓ |
| 4 | 原二级场景名字 | ✓ |
| 5 | 计划ID | ✓ |
| 6 | 计划名字 | ✓ |

缺少以上任一列的均为错误格式，数据不可用。

### 2.3 场景名字的值
- 必须包含：`人群推广`、`关键词推广`、`货品全站推广`
- 不允许有空值、NaN、空字符串

## 3. 下载操作标准流程

### 步骤1：切换报表维度
进入商品报表页面后，在点击「下载报表」**前**，先在页面维度选择器中选中「按计划」或「按场景」。

### 步骤2：点击「下载报表」
保持默认设置，在弹窗中确认日期范围正确。

### 步骤3：点击「确定」
提交下载任务。

### 步骤4：下载完成
从下载任务管理页下载生成的CSV文件（必须79列）。

## 4. 数据流水线标准流程

下载完成后必须依序执行：

1. `wanxiangtai_download.py download` -> 下载CSV（79列格式）
2. `match_category.py` -> 匹配品类/细类
3. 追加到大表（万相台数据表.xlsx）-> 合并+去重
4. `generate_dashboard_data.py` -> 生成前端JSON
5. `pnpm build` -> 构建静态站点
6. `git push` -> 触发GitHub Pages部署

## 5. 格式验证

每次下载后自动在 `run_daily.py` 中执行：
- 检查CSV是否包含 `场景名字` 列
- 检查 `场景名字` 列是否有空值
- 不通过则记录错误日志

## 6. 常见问题

Q: 格式又错了怎么办？
A: 立即删除该CSV文件，重新下载并确保执行步骤1（切换维度）。

Q: 大表已有该日期的数据，想重新下载替换？
A: 先删除大表中该日期的数据行，再重新执行完整流水线。

## 7. 关键脚本位置

| 脚本 | 路径 |
|---|---|
| 下载脚本 | `automation/wanxiangtai_download.py` |
| 匹配脚本 | `automation/match_category.py` |
| 数据生成 | `automation/generate_dashboard_data.py` |
| 完整流水线 | `automation/run_daily.py` |
| 商品ID基础表 | `~/Desktop/商品ID基础表最新6.23.xlsx` |
| 大表 | `~/Workbuddy/万相台数据表.xlsx` |
