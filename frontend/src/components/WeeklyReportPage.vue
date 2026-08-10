<template>
  <div class="weekly-report">
    <div class="weekly-toolbar">
      <div>
        <div class="weekly-eyebrow">{{ periodTitle }}</div>
        <h2>{{ isOverview ? `三品类投放${periodTitle}` : `${category}品类${periodTitle}` }}</h2>
        <p>{{ periodDescription }} ｜ {{ currentRange.label }} 对比 {{ previousRange.label }}</p>
      </div>
      <div class="weekly-range-control">
        <div class="weekly-category-picker" role="group" :aria-label="`${periodText}品类`">
          <button v-for="item in reportCategories" :key="item" type="button" :class="{ active: selectedCategory === item }" @click="selectedCategory = item">{{ item }}</button>
        </div>
        <label>{{ periodEndLabel }}</label>
        <input v-model="periodEnd" type="date" :min="minEndDate" :max="payload.dateMax" @change="normalizePeriodEnd" />
      </div>
    </div>

    <section v-if="isOverview" class="panel-table weekly-overview-panel">
      <div class="weekly-section-heading">
        <div>
          <div class="chart-title">三品类汇总</div>
          <p>手机、DT、显示器{{ periodText }}核心数据及上{{ periodUnit }}环比</p>
        </div>
        <span class="weekly-section-meta">{{ currentRange.label }}</span>
      </div>
      <div class="table-wrap weekly-overview-table">
        <table>
          <thead>
            <tr>
              <th>品类</th>
              <th class="num">{{ periodText }}花费</th>
              <th class="num">花费环比</th>
              <th class="num">{{ periodText }}成交金额</th>
              <th class="num">成交环比</th>
              <th class="num">ROI</th>
              <th class="num">ROI变化</th>
              <th class="num">点击量</th>
              <th class="num">CTR</th>
              <th class="num">CVR</th>
              <th class="num">CPC</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in categorySummaryRows" :key="row.category" :class="{ 'weekly-total-row': row.isTotal }">
              <td><strong>{{ row.category }}</strong></td>
              <td class="num">¥{{ formatMoney(row.cost) }}</td>
              <td :class="['num', changeClass(row.costChange)]">{{ formatChange(row.costChange) }}</td>
              <td class="num">¥{{ formatMoney(row.totalSales) }}</td>
              <td :class="['num', changeClass(row.salesChange)]">{{ formatChange(row.salesChange) }}</td>
              <td :class="['num', roiClass(row.totalRoi)]">{{ row.totalRoi.toFixed(2) }}</td>
              <td :class="['num', changeClass(row.roiChange)]">{{ formatPointChange(row.roiChange) }}</td>
              <td class="num">{{ row.clicks.toLocaleString() }}</td>
              <td class="num">{{ formatPercent(row.ctr) }}</td>
              <td class="num">{{ formatPercent(row.cvr) }}</td>
              <td class="num">¥{{ row.cpc.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div v-if="!isOverview" class="weekly-layout">
      <section class="weekly-main">
        <div class="kpi-row weekly-kpis">
          <div v-for="card in kpiCards" :key="card.key" :class="['kpi-card', card.tone]">
            <div class="kpi-label">{{ card.label }}</div>
            <div class="kpi-value">{{ card.value }}</div>
            <div class="kpi-change" :class="card.changeClass">{{ card.changeText }}</div>
          </div>
        </div>

        <div class="summary-box">
          <div class="chart-title">{{ periodText }}结论</div>
          <div v-for="line in insightLines" :key="line" class="summary-line">{{ line }}</div>
        </div>

        <div class="chart-row">
          <div class="chart-container">
            <div class="chart-title">每日花费、成交与 ROI</div>
            <EChart :option="dailyTrendOption" />
          </div>
          <div class="chart-container">
            <div class="chart-title">渠道花费变化</div>
            <EChart :option="scenarioOption" />
          </div>
        </div>

        <div class="panel-table">
          <div class="chart-title">渠道变化</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>推广场景</th>
                  <th class="num">{{ periodText }}花费</th>
                  <th class="num">{{ periodUnit }}环比</th>
                  <th class="num">成交金额</th>
                  <th class="num">ROI</th>
                  <th class="num">点击率</th>
                  <th class="num">转化率</th>
                  <th class="num">CPC</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in scenarioRows" :key="row.scenario">
                  <td><strong>{{ row.scenario }}</strong></td>
                  <td class="num">¥{{ formatMoney(row.cost) }}</td>
                  <td :class="['num', changeClass(row.costChange)]">{{ formatChange(row.costChange) }}</td>
                  <td class="num">¥{{ formatMoney(row.totalSales) }}</td>
                  <td :class="['num', roiClass(row.totalRoi)]">{{ row.totalRoi.toFixed(2) }}</td>
                  <td class="num">{{ formatPercent(row.ctr) }}</td>
                  <td class="num">{{ formatPercent(row.cvr) }}</td>
                  <td class="num">¥{{ row.cpc.toFixed(2) }}</td>
                </tr>
                <tr v-if="scenarioRows.length === 0"><td colspan="8" class="empty">暂无渠道数据</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="panel-table">
          <div class="chart-title">计划变化</div>
          <div class="weekly-split">
            <div>
              <h3>花费增加 TOP 8</h3>
              <PlanChangeTable :rows="planIncreases" empty-text="暂无明显增加计划" />
            </div>
            <div>
              <h3>花费下降 TOP 8</h3>
              <PlanChangeTable :rows="planDecreases" empty-text="暂无明显下降计划" />
            </div>
          </div>
        </div>
      </section>

      <aside class="weekly-side">
        <div class="panel-table">
          <div class="chart-title">需要关注的计划</div>
          <div v-if="planDataLoading" class="empty">正在加载计划明细...</div>
          <div v-else-if="planDataError" class="empty">{{ planDataError }}</div>
          <ul v-else class="weekly-alert-list">
            <li v-for="item in watchPlans" :key="item.key">
              <strong>{{ item.planName }}</strong>
              <span>{{ item.reason }}</span>
            </li>
            <li v-if="watchPlans.length === 0">{{ periodText }}暂无明显异常计划。</li>
          </ul>
        </div>

        <div class="panel-table">
          <div class="chart-title">新启停计划</div>
          <div class="weekly-mini-section">
            <h3>{{ periodText }}新增</h3>
            <ol>
              <li v-for="p in newPlans" :key="p.key">{{ p.planName }} · ¥{{ formatMoney(p.cost) }}</li>
              <li v-if="newPlans.length === 0">暂无新增计划</li>
            </ol>
          </div>
          <div class="weekly-mini-section">
            <h3>{{ periodText }}停投或归零</h3>
            <ol>
              <li v-for="p in stoppedPlans" :key="p.key">{{ p.planName }} · 上{{ periodUnit }} ¥{{ formatMoney(p.prevCost) }}</li>
              <li v-if="stoppedPlans.length === 0">暂无停投计划</li>
            </ol>
          </div>
        </div>

        <div class="panel-table">
          <div class="chart-title">人群推广变化</div>
          <p class="weekly-note">{{ audienceNote }}</p>
          <ol class="weekly-rank-list">
            <li v-for="p in audienceRows" :key="p.key">
              <strong>{{ p.audienceName || p.planName }}</strong>
              <span>花费 ¥{{ formatMoney(p.cost) }} · {{ formatChange(p.costChange) }} · ROI {{ p.totalRoi.toFixed(2) }} · 点击 {{ p.clicks.toLocaleString() }}</span>
            </li>
            <li v-if="audienceRows.length === 0">{{ periodText }}暂无人群数据</li>
          </ol>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref } from "vue";
import EChart from "./EChart.vue";
import { formatMoney, formatPercent, sumMetrics } from "../utils/metrics";

const props = defineProps({
  payload: { type: Object, required: true },
  cryptoKey: { type: CryptoKey, required: true },
  category: { type: String, default: "汇总" },
  period: { type: String, default: "week" },
});

const preferredCategories = ["手机", "DT", "显示器"];
const isMonthly = computed(() => props.period === "month");
const periodText = computed(() => isMonthly.value ? "本月" : "本周");
const periodUnit = computed(() => isMonthly.value ? "月" : "周");
const periodTitle = computed(() => isMonthly.value ? "月报" : "周报");
const periodDescription = computed(() => isMonthly.value ? "自然月：每月1日至月末" : "自然周：周一至周日");
const periodEndLabel = computed(() => isMonthly.value ? "月份" : "周日");
const reportCategories = computed(() => ["汇总", ...preferredCategories.filter((item) => props.payload.categories?.includes(item))]);
const selectedCategory = ref(props.category && reportCategories.value.includes(props.category) ? props.category : "汇总");
const isOverview = computed(() => selectedCategory.value === "汇总");
const category = computed(() => isOverview.value ? null : selectedCategory.value);
const periodEnd = ref(latestPeriodEnd(props.payload.dateMax || ""));
const planRecords = ref([]);
const audiencePayload = ref(null);
const planDataLoading = ref(false);
const planDataError = ref("");

const PlanChangeTable = defineComponent({
  props: { rows: { type: Array, required: true }, emptyText: { type: String, default: "暂无数据" } },
  setup(tableProps) {
    return () => h("div", { class: "table-wrap compact-table" }, [
      h("table", [
        h("thead", [h("tr", [
          h("th", "计划"),
          h("th", { class: "num" }, "花费变化"),
          h("th", { class: "num" }, `${periodText.value} ROI`),
        ])]),
        h("tbody", tableProps.rows.length
          ? tableProps.rows.map((row) => h("tr", { key: row.key }, [
              h("td", { class: "weekly-plan-name", title: row.planName }, row.planName),
              h("td", { class: ["num", changeClass(row.costChange)] }, formatMoneyDelta(row.costDelta)),
              h("td", { class: ["num", roiClass(row.totalRoi)] }, row.totalRoi.toFixed(2)),
            ]))
          : [h("tr", [h("td", { class: "empty", colspan: 3 }, tableProps.emptyText)])]
        ),
      ]),
    ]);
  },
});

const currentRange = computed(() => buildRange(periodEnd.value, 0));
const previousRange = computed(() => buildRange(periodEnd.value, isMonthly.value ? 1 : 7));
const minEndDate = computed(() => props.payload.dateMin || "");

const currentRecords = computed(() => filterRecords(props.payload.records || [], currentRange.value));
const previousRecords = computed(() => filterRecords(props.payload.records || [], previousRange.value));
const categorySummaryRows = computed(() => {
  const rows = preferredCategories.map((item) => buildSummaryRow(
    item,
    sumMetrics(filterRecordsByCategory(props.payload.records || [], currentRange.value, item)),
    sumMetrics(filterRecordsByCategory(props.payload.records || [], previousRange.value, item)),
  ));
  const current = sumMetrics(filterRecordsByCategory(props.payload.records || [], currentRange.value, null));
  const previous = sumMetrics(filterRecordsByCategory(props.payload.records || [], previousRange.value, null));
  return [...rows, { ...buildSummaryRow("三品类合计", current, previous), isTotal: true }];
});
const subjectCategoryMap = computed(() => {
  const map = new Map();
  for (const subject of props.payload.subjects || []) map.set(String(subject.subjectId), subject.category);
  return map;
});
const totals = computed(() => sumMetrics(currentRecords.value));
const prevTotals = computed(() => sumMetrics(previousRecords.value));
const currentDaily = computed(() => dailyRows(currentRecords.value, currentRange.value));
const previousDaily = computed(() => dailyRows(previousRecords.value, previousRange.value));
const scenarioRows = computed(() => withPrevious(
  aggregateScenario(filterRecords(props.payload.categoryScenarioRecords || [], currentRange.value)),
  aggregateScenario(filterRecords(props.payload.categoryScenarioRecords || [], previousRange.value)),
));
const planRows = computed(() => withPrevious(
  aggregatePlans(filterPlanRecords(planRecords.value, currentRange.value)),
  aggregatePlans(filterPlanRecords(planRecords.value, previousRange.value)),
));

const kpiCards = computed(() => {
  const t = totals.value;
  const p = prevTotals.value;
  return [
    kpiCard("cost", "花费", `¥${formatMoney(t.cost)}`, pctChange(t.cost, p.cost), "cost"),
    kpiCard("sales", "成交金额", `¥${formatMoney(t.totalSales)}`, pctChange(t.totalSales, p.totalSales), "sales"),
    kpiCard("troi", "ROI", t.totalRoi.toFixed(2), t.totalRoi - p.totalRoi, "troi", "point"),
    kpiCard("click", "点击量", t.clicks.toLocaleString(), pctChange(t.clicks, p.clicks), "click"),
    kpiCard("ctr", "点击率", formatPercent(t.ctr), t.ctr - p.ctr, "ctr", "pp"),
    kpiCard("cpc", "CPC", `¥${t.cpc.toFixed(2)}`, pctChange(t.cpc, p.cpc), "cpc"),
  ];
});

const insightLines = computed(() => {
  const t = totals.value;
  const p = prevTotals.value;
  const topScenario = scenarioRows.value[0];
  const bestPlan = planRows.value.filter((r) => r.cost >= 200).sort((a, b) => b.totalRoi - a.totalRoi)[0];
  const riskPlan = planRows.value.filter((r) => r.cost >= 200 && r.totalRoi < 3).sort((a, b) => b.cost - a.cost)[0];
  const lines = [
    `${category.value}${periodText.value}花费 ¥${formatMoney(t.cost)}，成交 ¥${formatMoney(t.totalSales)}，ROI ${t.totalRoi.toFixed(2)}；花费较上${periodUnit.value} ${formatChange(pctChange(t.cost, p.cost))}，成交较上${periodUnit.value} ${formatChange(pctChange(t.totalSales, p.totalSales))}。`,
  ];
  if (topScenario) lines.push(`${periodText.value}花费最高渠道是 ${topScenario.scenario}，占${periodText.value}花费 ${topScenario.costShare.toFixed(1)}%，ROI ${topScenario.totalRoi.toFixed(2)}。`);
  if (bestPlan) lines.push(`高效计划：${bestPlan.planName}，花费 ¥${formatMoney(bestPlan.cost)}，ROI ${bestPlan.totalRoi.toFixed(2)}，可优先观察是否具备加预算空间。`);
  if (riskPlan) lines.push(`低效高花费计划：${riskPlan.planName}，花费 ¥${formatMoney(riskPlan.cost)}，ROI ${riskPlan.totalRoi.toFixed(2)}，建议复查出价、关键词/人群和素材。`);
  if (!planRecords.value.length) lines.push("计划明细尚未加载完成，计划变化和人群推广变化会在加载后自动刷新。");
  return lines;
});

const planIncreases = computed(() => planRows.value.filter((r) => r.costDelta > 0).sort((a, b) => b.costDelta - a.costDelta).slice(0, 8));
const planDecreases = computed(() => planRows.value.filter((r) => r.costDelta < 0).sort((a, b) => a.costDelta - b.costDelta).slice(0, 8));
const newPlans = computed(() => planRows.value.filter((r) => r.cost > 0 && r.prevCost === 0).sort((a, b) => b.cost - a.cost).slice(0, 8));
const stoppedPlans = computed(() => planRows.value.filter((r) => r.cost === 0 && r.prevCost > 0).sort((a, b) => b.prevCost - a.prevCost).slice(0, 8));
const watchPlans = computed(() => planRows.value
  .filter((r) => r.cost >= 200 && (r.totalRoi < 3 || r.costChange > 50 || r.totalSalesChange < -30))
  .sort((a, b) => b.cost - a.cost)
  .slice(0, 8)
  .map((r) => ({ ...r, reason: riskReason(r) })));
const audiencePlans = computed(() => planRows.value
  .filter((r) => r.scenario === "人群推广" && (r.cost > 0 || r.prevCost > 0))
  .sort((a, b) => Math.abs(b.costDelta) - Math.abs(a.costDelta))
  .slice(0, 8));
const audienceRows = computed(() => {
  if (audiencePayload.value?.records?.length) {
    const currentAudience = filterRecords(audiencePayload.value.records, currentRange.value);
    const previousAudience = filterRecords(audiencePayload.value.records, previousRange.value);
    if (!currentAudience.length && !previousAudience.length) return audiencePlans.value;
    return withPrevious(
      aggregateAudiences(currentAudience),
      aggregateAudiences(previousAudience),
    ).filter((r) => r.cost > 0 || r.prevCost > 0).slice(0, 10);
  }
  return audiencePlans.value;
});
const audienceNote = computed(() => {
  if (audiencePayload.value?.records?.length) {
    return `已读取手机人群明细，数据范围 ${audiencePayload.value.dateMin} ~ ${audiencePayload.value.dateMax}。当前文件只有一天数据时，${periodUnit.value}环比会显示为新增或无上${periodUnit.value}对比。`;
  }
  return "当前未加载具体人群包明细，先展示“人群推广”场景下的计划变化。";
});

const dailyTrendOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { top: 0, data: [`${periodText.value}花费`, `上${periodUnit.value}花费`, `${periodText.value}成交`, `${periodText.value} ROI`] },
  grid: { left: 58, right: 58, top: 44, bottom: 46 },
  xAxis: { type: "category", data: currentDaily.value.map((r) => shortDate(r.date)) },
  yAxis: [
    { type: "value", name: "金额", axisLabel: { formatter: (value) => formatMoney(value) } },
    { type: "value", name: "ROI", splitLine: { show: false } },
  ],
  series: [
    { name: `${periodText.value}花费`, type: "bar", data: currentDaily.value.map((r) => round2(r.cost)), itemStyle: { color: "#ee6a5f" }, barMaxWidth: 24 },
    { name: `上${periodUnit.value}花费`, type: "bar", data: previousDaily.value.map((r) => round2(r.cost)), itemStyle: { color: "#c6d0df" }, barMaxWidth: 24 },
    { name: `${periodText.value}成交`, type: "line", data: currentDaily.value.map((r) => round2(r.totalSales)), smooth: true, itemStyle: { color: "#4ecdc4" }, lineStyle: { width: 3 } },
    { name: `${periodText.value} ROI`, type: "line", yAxisIndex: 1, data: currentDaily.value.map((r) => round2(r.totalRoi)), smooth: true, itemStyle: { color: "#667eea" }, lineStyle: { width: 3 } },
  ],
}));

const scenarioOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { top: 0, data: [`${periodText.value}花费`, `上${periodUnit.value}花费`] },
  grid: { left: 72, right: 24, top: 44, bottom: 36 },
  xAxis: { type: "value", axisLabel: { formatter: (value) => formatMoney(value) } },
  yAxis: { type: "category", data: scenarioRows.value.map((r) => r.scenario).reverse() },
  series: [
    { name: `${periodText.value}花费`, type: "bar", data: scenarioRows.value.map((r) => round2(r.cost)).reverse(), itemStyle: { color: "#667eea" }, barMaxWidth: 22 },
    { name: `上${periodUnit.value}花费`, type: "bar", data: scenarioRows.value.map((r) => round2(r.prevCost)).reverse(), itemStyle: { color: "#c6d0df" }, barMaxWidth: 22 },
  ],
}));

onMounted(() => {
  loadPlanRecords();
  loadAudienceRecords();
});

function buildRange(endDate, offsetDays) {
  const fallback = latestPeriodEnd(props.payload.dateMax || "");
  if (isMonthly.value) {
    const end = endOfMonth(addMonths(endDate || fallback, -offsetDays));
    const start = `${end.slice(0, 8)}01`;
    return { start, end, label: `${start} ~ ${end}` };
  }
  const end = addDays(endDate || fallback, -offsetDays);
  const start = addDays(end, -6);
  return { start, end, label: `${start} ~ ${end}` };
}
function latestPeriodEnd(dateString) {
  if (!dateString) return "";
  const date = new Date(`${dateString}T00:00:00`);
  if (isMonthly.value) {
    const monthEnd = endOfMonth(dateString);
    return dateString === monthEnd ? monthEnd : endOfMonth(addMonths(dateString, -1));
  }
  date.setDate(date.getDate() - date.getDay());
  return localDateString(date);
}
function normalizePeriodEnd() {
  periodEnd.value = latestPeriodEnd(periodEnd.value);
}
function addDays(dateString, days) {
  const d = new Date(`${dateString}T00:00:00`);
  d.setDate(d.getDate() + days);
  return localDateString(d);
}
function addMonths(dateString, months) {
  const d = new Date(`${dateString}T00:00:00`);
  d.setDate(1);
  d.setMonth(d.getMonth() + months);
  return localDateString(d);
}
function endOfMonth(dateString) {
  const d = new Date(`${dateString}T00:00:00`);
  d.setDate(1);
  d.setMonth(d.getMonth() + 1, 0);
  return localDateString(d);
}
function localDateString(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
function filterRecords(records, range) {
  return filterRecordsByCategory(records, range, category.value);
}
function filterRecordsByCategory(records, range, selected) {
  return records.filter((r) => r.date >= range.start && r.date <= range.end && preferredCategories.includes(r.category) && (!selected || r.category === selected));
}
function filterPlanRecords(records, range) {
  return records.filter((r) => {
    if (r.date < range.start || r.date > range.end) return false;
    const rowCategory = subjectCategoryMap.value.get(String(r.subjectId));
    return preferredCategories.includes(rowCategory) && (!category.value || rowCategory === category.value);
  });
}
function buildSummaryRow(categoryName, current, previous) {
  return {
    category: categoryName,
    ...current,
    costChange: pctChange(current.cost, previous.cost),
    salesChange: pctChange(current.totalSales, previous.totalSales),
    roiChange: current.totalRoi - previous.totalRoi,
  };
}
function dailyRows(records, range) {
  const map = {};
  const days = Math.round((new Date(`${range.end}T00:00:00`) - new Date(`${range.start}T00:00:00`)) / 86400000) + 1;
  for (let i = 0; i < days; i += 1) map[addDays(range.start, i)] = [];
  for (const r of records) if (map[r.date]) map[r.date].push(r);
  return Object.entries(map).map(([date, rows]) => ({ date, ...sumMetrics(rows) }));
}
function aggregateScenario(records) {
  const map = {};
  for (const r of records) {
    const key = r.scenario || "未分类";
    if (!map[key]) map[key] = emptyMetric({ scenario: key });
    addMetric(map[key], r);
  }
  return finalizeRows(Object.values(map), "scenario");
}
function aggregatePlans(records) {
  const map = {};
  for (const r of records) {
    const key = `${r.scenario || "未分类"}|${r.planId || r.planName}`;
    if (!map[key]) map[key] = emptyMetric({ key, scenario: r.scenario || "未分类", planId: r.planId, planName: r.planName || "未关联计划" });
    addMetric(map[key], r);
  }
  return finalizeRows(Object.values(map), "planName");
}
function aggregateAudiences(records) {
  const map = {};
  for (const r of records) {
    const key = r.audienceName || "未命名人群";
    if (!map[key]) map[key] = emptyMetric({ key, audienceName: key, scenario: r.scenario || "未分类", planName: r.planName || "" });
    addMetric(map[key], r);
  }
  return finalizeRows(Object.values(map), "audienceName");
}
function withPrevious(current, previous) {
  const prevMap = new Map(previous.map((r) => [r.key || r.scenario, r]));
  const currentMap = new Map(current.map((r) => [r.key || r.scenario, r]));
  const totalCost = current.reduce((sum, r) => sum + r.cost, 0);
  const union = [
    ...current,
    ...previous.filter((r) => !currentMap.has(r.key || r.scenario)).map((r) => ({ ...r, cost: 0, totalSales: 0, directSales: 0, orders: 0, clicks: 0, impressions: 0, carts: 0, totalRoi: 0, ctr: 0, cvr: 0, cpc: 0 })),
  ];
  return union.map((r) => {
    const p = prevMap.get(r.key || r.scenario) || emptyMetric({});
    return {
      ...r,
      prevCost: p.cost,
      prevTotalSales: p.totalSales,
      costDelta: r.cost - p.cost,
      costChange: pctChange(r.cost, p.cost),
      totalSalesChange: pctChange(r.totalSales, p.totalSales),
      costShare: totalCost > 0 ? r.cost / totalCost * 100 : 0,
    };
  }).sort((a, b) => b.cost - a.cost);
}
function emptyMetric(extra) {
  return { ...extra, cost: 0, totalSales: 0, directSales: 0, orders: 0, clicks: 0, impressions: 0, carts: 0 };
}
function addMetric(target, row) {
  target.cost += row.cost || 0;
  target.totalSales += row.totalSales || 0;
  target.directSales += row.directSales || 0;
  target.orders += row.orders || 0;
  target.clicks += row.clicks || 0;
  target.impressions += row.impressions || 0;
  target.carts += row.carts || 0;
}
function finalizeRows(rows, fallbackKey) {
  return rows.map((r) => {
    const metric = sumMetrics([r]);
    return { ...r, ...metric, key: r.key || r[fallbackKey] };
  }).sort((a, b) => b.cost - a.cost);
}
function kpiCard(key, label, value, change, tone, mode = "pct") {
  return { key, label, value, tone, changeText: mode === "point" ? formatPointChange(change) : mode === "pp" ? formatPpChange(change) : formatChange(change), changeClass: changeClass(change) };
}
function pctChange(current, previous) {
  if (!previous) return current ? 100 : 0;
  return (current - previous) / previous * 100;
}
function formatChange(value) {
  if (value == null) return "-";
  if (!Number.isFinite(value)) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}
function formatMoneyDelta(value) {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}¥${formatMoney(Math.abs(value))}`;
}
function formatPointChange(value) {
  if (value == null || !Number.isFinite(value)) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}`;
}
function formatPpChange(value) {
  if (value == null || !Number.isFinite(value)) return "-";
  return `${value > 0 ? "+" : ""}${(value * 100).toFixed(2)}pp`;
}
function changeClass(value) {
  if (value == null || Math.abs(value) < 0.0001) return "flat";
  return value > 0 ? "up" : "down";
}
function roiClass(value) {
  return value >= 3 ? "roi-good" : value < 1 ? "roi-risk" : "";
}
function riskReason(row) {
  if (row.totalRoi < 1) return `ROI ${row.totalRoi.toFixed(2)}，建议优先排查或降预算`;
  if (row.totalRoi < 3) return `ROI ${row.totalRoi.toFixed(2)}，效率低于当前品类参考线`;
  if (row.costChange > 50) return `花费 ${formatChange(row.costChange)}，需确认放量是否可控`;
  return `成交 ${formatChange(row.totalSalesChange)}，需检查转化波动`;
}
function round2(value) {
  return Math.round((value || 0) * 100) / 100;
}
function shortDate(date) {
  return date.slice(5);
}
function base64Bytes(value) {
  const binary = atob(value);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}
async function decodePayload(envelope, decrypted) {
  if (envelope.compression !== "gzip") return JSON.parse(new TextDecoder().decode(decrypted));
  const stream = new Blob([decrypted]).stream().pipeThrough(new DecompressionStream("gzip"));
  return JSON.parse(new TextDecoder().decode(await new Response(stream).arrayBuffer()));
}
async function loadPlanRecords() {
  if (planRecords.value.length || planDataLoading.value) return;
  planDataLoading.value = true;
  planDataError.value = "";
  try {
    const response = await fetch(`${import.meta.env.BASE_URL}data/product-details.enc.json`, { cache: "no-store" });
    if (!response.ok) throw new Error("未找到计划明细数据");
    const envelope = await response.json();
    const decrypted = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: base64Bytes(envelope.iv) },
      props.cryptoKey,
      base64Bytes(envelope.ciphertext),
    );
    const payload = await decodePayload(envelope, decrypted);
    planRecords.value = payload.subjectPlanRecords || [];
  } catch (error) {
    planDataError.value = "计划明细加载失败，请刷新后重试。";
  } finally {
    planDataLoading.value = false;
  }
}
async function loadAudienceRecords() {
  try {
    const response = await fetch(`${import.meta.env.BASE_URL}data/mobile-audience-data.enc.json`, { cache: "no-store" });
    if (!response.ok) return;
    const envelope = await response.json();
    const decrypted = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: base64Bytes(envelope.iv) },
      props.cryptoKey,
      base64Bytes(envelope.ciphertext),
    );
    audiencePayload.value = await decodePayload(envelope, decrypted);
  } catch (error) {
    audiencePayload.value = null;
  }
}
</script>
