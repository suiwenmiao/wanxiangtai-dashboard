<template>
  <div>
    <!-- KPI -->
    <div class="kpi-row">
      <div class="kpi-card cost">
        <div class="kpi-label">花费</div>
        <div class="kpi-value">¥{{ formatMoney(totals.cost) }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.cost)"><span class="arrow">{{ hb.cost > 0 ? '↑' : hb.cost < 0 ? '↓' : '' }}</span>{{ hbText(hb.cost) }} 环比</div>
      </div>
      <div class="kpi-card sales">
        <div class="kpi-label">总成交金额</div>
        <div class="kpi-value">¥{{ formatMoney(totals.totalSales) }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.totalSales)"><span class="arrow">{{ hb.totalSales > 0 ? '↑' : hb.totalSales < 0 ? '↓' : '' }}</span>{{ hbText(hb.totalSales) }} 环比</div>
      </div>
      <div class="kpi-card ctr">
        <div class="kpi-label">点击率</div>
        <div class="kpi-value">{{ formatPercent(totals.ctr) }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.ctr)"><span class="arrow">{{ hb.ctr > 0 ? '↑' : hb.ctr < 0 ? '↓' : '' }}</span>{{ hb.ctr > 0 ? '+' : '' }}{{ (hb.ctr * 100).toFixed(2) }}pp 环比</div>
      </div>
      <div class="kpi-card droi">
        <div class="kpi-label">直接 ROI</div>
        <div class="kpi-value">{{ totals.directRoi.toFixed(2) }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.directRoi)"><span class="arrow">{{ hb.directRoi > 0 ? '↑' : hb.directRoi < 0 ? '↓' : '' }}</span>{{ hb.directRoi > 0 ? '+' : '' }}{{ hb.directRoi.toFixed(2) }} 环比</div>
      </div>
      <div class="kpi-card troi">
        <div class="kpi-label">总 ROI</div>
        <div class="kpi-value">{{ totals.totalRoi.toFixed(2) }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.totalRoi)"><span class="arrow">{{ hb.totalRoi > 0 ? '↑' : hb.totalRoi < 0 ? '↓' : '' }}</span>{{ hb.totalRoi > 0 ? '+' : '' }}{{ hb.totalRoi.toFixed(2) }} 环比</div>
      </div>
      <div class="kpi-card cpc">
        <div class="kpi-label">CPC</div>
        <div class="kpi-value">¥{{ totals.cpc.toFixed(2) }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.cpc)"><span class="arrow">{{ hb.cpc > 0 ? '↑' : hb.cpc < 0 ? '↓' : '' }}</span>{{ hbText(hb.cpc) }} 环比</div>
      </div>
    </div>

    <!-- Summary at TOP -->
    <div class="summary-box">
      <div class="chart-title">推广总结与建议</div>
      <div v-for="(line, i) in summaryLines" :key="i" class="summary-line" v-html="line"></div>
    </div>

    <!-- Charts -->
    <div class="chart-row">
      <div class="chart-container"><div class="chart-title">每日花费与 CVR 环比趋势</div><EChart :option="trendOption" /></div>
      <div class="chart-container"><div class="chart-title">每日点击量与 CPC 环比趋势</div><EChart :option="clickCpcOption" /></div>
    </div>
    <div class="chart-row">
      <div class="chart-container"><div class="chart-title">每日 ROI 趋势</div><EChart :option="roiOption" /></div>
      <div class="chart-container"><div class="chart-title">推广场景花费占比</div><EChart :option="pieOption" /></div>
    </div>

    <!-- Combined Table -->
    <div class="panel-table">
      <div class="chart-title">{{ selectedCategory ? selectedCategory + ' — 细类明细' : '品类效果明细' }}</div>
      <div class="table-wrap"><table>
        <thead><tr>
          <th>{{ selectedCategory ? '细类' : '品类' }}</th>
          <th class="num">展现量</th>
          <th class="num">点击量</th>
          <th class="num">花费</th>
          <th class="num">总成交金额</th>
          <th class="num">订单量</th>
          <th class="num">CPC</th>
          <th class="num">点击率</th>
          <th class="num">转化率</th>
          <th class="num">ROI</th>
        </tr></thead>
        <tbody>
          <template v-if="selectedCategory">
            <tr v-for="row in subRows" :key="row.subCategory">
              <td>{{ row.subCategory }}</td>
              <td class="num">{{ row.impressions.toLocaleString() }}</td>
              <td class="num">{{ row.clicks.toLocaleString() }}</td>
              <td class="num">¥{{ formatMoney(row.cost) }}</td>
              <td class="num">¥{{ formatMoney(row.totalSales) }}</td>
              <td class="num">{{ row.orders.toLocaleString() }}</td>
              <td class="num">¥{{ row.cpc.toFixed(2) }}</td>
              <td class="num">{{ formatPercent(row.ctr) }}</td>
              <td class="num">{{ formatPercent(row.cvr) }}</td>
              <td :class="['num', roiClass(row.totalRoi)]">{{ row.totalRoi.toFixed(2) }}</td>
            </tr>
            <tr class="summary-row" v-if="subRows.length > 0">
              <td><strong>{{ selectedCategory }}</strong></td>
              <td class="num"><strong>{{ categoryTotal.impressions.toLocaleString() }}</strong></td>
              <td class="num"><strong>{{ categoryTotal.clicks.toLocaleString() }}</strong></td>
              <td class="num"><strong>¥{{ formatMoney(categoryTotal.cost) }}</strong></td>
              <td class="num"><strong>¥{{ formatMoney(categoryTotal.totalSales) }}</strong></td>
              <td class="num"><strong>{{ categoryTotal.orders.toLocaleString() }}</strong></td>
              <td class="num"><strong>¥{{ categoryTotal.cpc.toFixed(2) }}</strong></td>
              <td class="num"><strong>{{ formatPercent(categoryTotal.ctr) }}</strong></td>
              <td class="num"><strong>{{ formatPercent(categoryTotal.cvr) }}</strong></td>
              <td :class="['num', roiClass(categoryTotal.totalRoi)]"><strong>{{ categoryTotal.totalRoi.toFixed(2) }}</strong></td>
            </tr>
          </template>
          <template v-else>
            <tr v-for="row in categoryRows" :key="row.category">
              <td><strong>{{ row.category }}</strong></td>
              <td class="num">{{ row.impressions.toLocaleString() }}</td>
              <td class="num">{{ row.clicks.toLocaleString() }}</td>
              <td class="num">¥{{ formatMoney(row.cost) }}</td>
              <td class="num">¥{{ formatMoney(row.totalSales) }}</td>
              <td class="num">{{ row.orders.toLocaleString() }}</td>
              <td class="num">¥{{ row.cpc.toFixed(2) }}</td>
              <td class="num">{{ formatPercent(row.ctr) }}</td>
              <td class="num">{{ formatPercent(row.cvr) }}</td>
              <td :class="['num', roiClass(row.totalRoi)]">{{ row.totalRoi.toFixed(2) }}</td>
            </tr>
          </template>
          <tr v-if="(selectedCategory ? subRows.length : categoryRows.length) === 0"><td colspan="10" class="empty">暂无数据</td></tr>
        </tbody>
      </table></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import EChart from "./EChart.vue";
import { byDate, byCategory, formatMoney, formatPercent, sumMetrics } from "../utils/metrics";

const props = defineProps({ payload: { type: Object, required: true }, filtered: { type: Array, required: true }, prevFiltered: { type: Array, default: [] }, category: String, allSubCats: { type: Array, default: () => [] } });

const selectedCategory = computed(() => props.category && props.category !== "all" ? props.category : null);
const totals = computed(() => sumMetrics(props.filtered));
const prevTot = computed(() => props.prevFiltered.length ? sumMetrics(props.prevFiltered) : null);
const dailyRows = computed(() => byDate(props.filtered));
const prevDailyRows = computed(() => byDate(props.prevFiltered));
const dailyComparisonRows = computed(() => dailyRows.value.map((row, index) => ({
  ...row,
  prevCost: prevDailyRows.value[index]?.cost ?? null,
  prevClicks: prevDailyRows.value[index]?.clicks ?? null,
  prevCpc: prevDailyRows.value[index]?.cpc ?? null,
  prevCvr: prevDailyRows.value[index]?.cvr ?? null,
})));
const categoryRows = computed(() => byCategory(props.filtered));

const hb = computed(() => {
  if (!prevTot.value) return null;
  const t = totals.value, p = prevTot.value;
  return {
    cost: p.cost ? (t.cost - p.cost) / p.cost * 100 : 0,
    totalSales: p.totalSales ? (t.totalSales - p.totalSales) / p.totalSales * 100 : 0,
    directRoi: t.directRoi - p.directRoi,
    totalRoi: t.totalRoi - p.totalRoi,
    cvr: t.cvr - p.cvr,
    ctr: t.ctr - p.ctr,
    cpc: p.cpc > 0 ? (t.cpc - p.cpc) / p.cpc * 100 : 0,
  };
});
function changeClass(v) { if (v == null) return ''; return v > 0 ? 'up' : v < 0 ? 'down' : 'flat'; }
function hbText(v) { if (v == null) return ''; return (v > 0 ? '+' : '') + v.toFixed(1) + '%'; }

// Summary at top
const summaryLines = computed(() => {
  const rows = categoryRows.value;
  const t = totals.value; const p = prevTot.value;
  const lines = [];
  if (rows.length === 0) { lines.push('当前筛选条件下暂无数据'); return lines; }

  let hbStr = '';
  if (p) {
    const h = hb.value;
    const c = h.cost > 0 ? `<span class="highlight-red">↑${h.cost.toFixed(1)}%</span>` : h.cost < 0 ? `<span class="highlight-green">↓${Math.abs(h.cost).toFixed(1)}%</span>` : '持平';
    const s = h.totalSales > 0 ? `<span class="highlight-green">↑${h.totalSales.toFixed(1)}%</span>` : h.totalSales < 0 ? `<span class="highlight-red">↓${Math.abs(h.totalSales).toFixed(1)}%</span>` : '持平';
    hbStr = `（花费 ${c}，成交 ${s}，环比上一同期段）`;
  }
  lines.push(`📊 总花费 <strong>¥${formatMoney(t.cost)}</strong>，总成交 <strong>¥${formatMoney(t.totalSales)}</strong>，整体 ROI <span class="highlight-blue">${t.totalRoi.toFixed(2)}</span> ${hbStr}`);

  const top3 = rows.slice(0, 3).map(r => `${r.category}（¥${formatMoney(r.cost)}，ROI ${r.totalRoi.toFixed(2)}）`);
  lines.push(`💡 花费 TOP 3：${top3.join('、')}`);

  const best = rows.reduce((a, b) => a.totalRoi > b.totalRoi ? a : b, rows[0]);
  if (best && best.totalRoi > 0 && best.cost > 100) {
    lines.push(`✅ 表现最佳品类 <strong>${best.category}</strong>，ROI <span class="highlight-green">${best.totalRoi.toFixed(2)}</span>，花费 ¥${formatMoney(best.cost)} → 建议<b>关注其投放策略，可适当增加预算</b>`);
  }

  const worst = rows.filter(r => r.cost > 100).reduce((a, b) => a.totalRoi < b.totalRoi ? a : b, rows[0]);
  if (worst && worst.totalRoi < 3 && worst.cost > 100) {
    lines.push(`⚠️ 需优化品类 <strong>${worst.category}</strong>，ROI <span class="highlight-red">${worst.totalRoi.toFixed(2)}</span>，花费 ¥${formatMoney(worst.cost)} → 建议<b>暂停或降低预算</b>，检查落地页转化和关键词匹配度`);
  }

  const ctr = t.impressions > 0 ? t.clicks / t.impressions * 100 : 0;
  lines.push(`📈 整体点击率 ${ctr.toFixed(2)}%，展现 ${t.impressions.toLocaleString()}，点击 ${t.clicks.toLocaleString()}`);
  return lines;
});

const subRows = computed(() => {
  if (!selectedCategory.value) return [];
  const agg = {};
  for (const r of props.allSubCats) {
    if (r.category !== selectedCategory.value) continue;
    const key = r.subCategory;
    if (!agg[key]) agg[key] = { subCategory: key, cost: 0, totalSales: 0, directSales: 0, clicks: 0, impressions: 0, orders: 0, carts: 0 };
    const a = agg[key]; a.cost += r.cost; a.totalSales += r.totalSales; a.directSales += r.directSales;
    a.clicks += r.clicks; a.impressions += r.impressions; a.orders += r.orders; a.carts += r.carts;
  }
  return Object.values(agg).map(r => ({ ...r, cost: Math.round(r.cost * 100) / 100, totalSales: Math.round(r.totalSales * 100) / 100, totalRoi: r.cost > 0 ? r.totalSales / r.cost : 0, ctr: r.impressions > 0 ? r.clicks / r.impressions : 0, cvr: r.clicks > 0 ? r.orders / r.clicks : 0, cpc: r.clicks > 0 ? r.cost / r.clicks : 0 })).sort((a, b) => b.cost - a.cost);
});

const categoryTotal = computed(() => { if (!selectedCategory.value) return null; return categoryRows.value.find(r => r.category === selectedCategory.value); });

function roiClass(v) { return v >= 3 ? "roi-good" : v < 1 ? "roi-risk" : ""; }

const axisDates = computed(() => dailyComparisonRows.value.map((r) => r.date));
const mks = { formatter: (v) => typeof v === 'number' ? formatMoney(v) : v };

const trendOption = computed(() => ({
  tooltip: { trigger: "axis" }, legend: { top: 0, data: ["花费", "环比花费", "CVR", "环比 CVR"] },
  grid: { left: 56, right: 58, top: 42, bottom: 48 },
  xAxis: { type: "category", data: axisDates.value, axisLabel: { rotate: 30 } },
  yAxis: [
    { type: "value", name: "花费", axisLabel: mks },
    { type: "value", name: "CVR", axisLabel: { formatter: value => formatPercent(value) }, splitLine: { show: false } },
  ],
  series: [
    { name: "花费", type: "bar", yAxisIndex: 0, data: dailyComparisonRows.value.map(r => Number(r.cost.toFixed(2))), itemStyle: { color: "#ee6a5f" }, barMaxWidth: 28 },
    { name: "环比花费", type: "bar", yAxisIndex: 0, data: dailyComparisonRows.value.map(r => r.prevCost == null ? null : Number(r.prevCost.toFixed(2))), itemStyle: { color: "#b9c4d4" }, barMaxWidth: 28 },
    { name: "CVR", type: "line", yAxisIndex: 1, smooth: true, data: dailyComparisonRows.value.map(r => Number(r.cvr.toFixed(4))), itemStyle: { color: "#3b82b6" }, lineStyle: { width: 3 }, symbolSize: 7 },
    { name: "环比 CVR", type: "line", yAxisIndex: 1, smooth: true, data: dailyComparisonRows.value.map(r => r.prevCvr == null ? null : Number(r.prevCvr.toFixed(4))), itemStyle: { color: "#7f8fa6" }, lineStyle: { type: "dashed", width: 2 }, symbolSize: 6 },
  ]
}));
const clickCpcOption = computed(() => ({
  tooltip: { trigger: "axis" }, legend: { top: 0, data: ["点击量", "环比点击量", "CPC", "环比 CPC"] },
  grid: { left: 56, right: 58, top: 42, bottom: 48 },
  xAxis: { type: "category", data: axisDates.value, axisLabel: { rotate: 30 } },
  yAxis: [
    { type: "value", name: "点击量", minInterval: 1 },
    { type: "value", name: "CPC", axisLabel: { formatter: value => `¥${Number(value).toFixed(2)}` }, splitLine: { show: false } },
  ],
  series: [
    { name: "点击量", type: "bar", yAxisIndex: 0, data: dailyComparisonRows.value.map(r => r.clicks), itemStyle: { color: "#49a6a0" }, barMaxWidth: 28 },
    { name: "环比点击量", type: "bar", yAxisIndex: 0, data: dailyComparisonRows.value.map(r => r.prevClicks), itemStyle: { color: "#b9c4d4" }, barMaxWidth: 28 },
    { name: "CPC", type: "line", yAxisIndex: 1, smooth: true, data: dailyComparisonRows.value.map(r => Number(r.cpc.toFixed(2))), itemStyle: { color: "#6b7fd7" }, lineStyle: { width: 3 }, symbolSize: 7 },
    { name: "环比 CPC", type: "line", yAxisIndex: 1, smooth: true, data: dailyComparisonRows.value.map(r => r.prevCpc == null ? null : Number(r.prevCpc.toFixed(2))), itemStyle: { color: "#7f8fa6" }, lineStyle: { type: "dashed", width: 2 }, symbolSize: 6 },
  ]
}));
const roiOption = computed(() => ({
  tooltip: { trigger: "axis" }, legend: { top: 0, data: ["直接 ROI", "总 ROI"] },
  grid: { left: 44, right: 20, top: 42, bottom: 48 },
  xAxis: { type: "category", data: axisDates.value, axisLabel: { rotate: 30 } }, yAxis: { type: "value" },
  series: [
    { name: "直接 ROI", type: "line", smooth: true, data: dailyRows.value.map(r => Number(r.directRoi.toFixed(2))), itemStyle: { color: "#45b7d1" } },
    { name: "总 ROI", type: "line", smooth: true, data: dailyRows.value.map(r => Number(r.totalRoi.toFixed(2))), itemStyle: { color: "#96ceb4" } }
  ]
}));
const scenarioRows = computed(() => {
  const agg = {};
  for (const s of props.payload.subjects) {
    if (selectedCategory.value && s.category !== selectedCategory.value) continue;
    for (const sc of s.scenarios) {
      if (!sc.scenario) continue;
      if (!agg[sc.scenario]) agg[sc.scenario] = 0;
      agg[sc.scenario] += sc.cost;
    }
  }
  const total = Object.values(agg).reduce((s, v) => s + v, 0);
  return Object.entries(agg).map(([name, cost]) => ({ name, value: Number(cost.toFixed(2)), pct: total > 0 ? cost / total * 100 : 0 })).sort((a, b) => b.value - a.value);
});
const pieOption = computed(() => ({
  tooltip: { trigger: "item", formatter: "{b}: ¥{c} ({d}%)" },
  legend: { type: "scroll", bottom: 0 },
  series: [{ type: "pie", radius: ["42%", "68%"], center: ["50%", "45%"], label: { formatter: "{b}\n{d}%" }, data: scenarioRows.value }]
}));
</script>
