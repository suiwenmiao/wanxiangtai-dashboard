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
        <div class="kpi-label">总成交</div>
        <div class="kpi-value">¥{{ formatMoney(totals.totalSales) }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.totalSales)"><span class="arrow">{{ hb.totalSales > 0 ? '↑' : hb.totalSales < 0 ? '↓' : '' }}</span>{{ hbText(hb.totalSales) }} 环比</div>
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
      <div class="kpi-card cvr">
        <div class="kpi-label">转化率</div>
        <div class="kpi-value">{{ formatPercent(totals.cvr) }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.cvr)"><span class="arrow">{{ hb.cvr > 0 ? '↑' : hb.cvr < 0 ? '↓' : '' }}</span>{{ hb.cvr > 0 ? '+' : '' }}{{ (hb.cvr * 100).toFixed(2) }}pp 环比</div>
      </div>
    </div>

    <!-- Summary at TOP -->
    <div class="summary-box">
      <div class="chart-title">推广总结与建议</div>
      <div v-for="(line, i) in summaryLines" :key="i" class="summary-line" v-html="line"></div>
    </div>

    <!-- Charts -->
    <div class="chart-row full">
      <div class="chart-container"><div class="chart-title">每日花费与成交金额趋势</div><EChart :option="trendOption" classes="echart tall" /></div>
    </div>
    <div class="chart-row">
      <div class="chart-container"><div class="chart-title">每日 ROI 趋势</div><EChart :option="roiOption" /></div>
      <div class="chart-container"><div class="chart-title">推广场景花费占比</div><EChart :option="pieOption" /></div>
    </div>

    <!-- Tables -->
    <div class="panel-table">
      <div class="chart-title">品类效果明细</div>
      <div class="table-wrap"><table>
        <thead><tr><th>品类</th><th class="num">花费</th><th class="num">成交金额</th><th class="num">总 ROI</th><th class="num">点击</th><th class="num">展现</th><th class="num">转化率</th><th class="num">CPC</th></tr></thead>
        <tbody>
          <tr v-for="row in categoryRows" :key="row.category">
            <td><strong>{{ row.category }}</strong></td>
            <td class="num">¥{{ formatMoney(row.cost) }}</td>
            <td class="num">¥{{ formatMoney(row.totalSales) }}</td>
            <td :class="['num', roiClass(row.totalRoi)]">{{ row.totalRoi.toFixed(2) }}</td>
            <td class="num">{{ row.clicks.toLocaleString() }}</td>
            <td class="num">{{ row.impressions.toLocaleString() }}</td>
            <td class="num">{{ formatPercent(row.cvr) }}</td>
            <td class="num">¥{{ row.cpc.toFixed(2) }}</td>
          </tr>
          <tr v-if="categoryRows.length === 0"><td colspan="8" class="empty">暂无数据</td></tr>
        </tbody>
      </table></div>
    </div>

    <div class="panel-table sub-section" v-if="selectedCategory && subRows.length > 0">
      <div class="chart-title">{{ selectedCategory }} — 细类明细</div>
      <div class="table-wrap"><table>
        <thead><tr><th>细类</th><th class="num">花费</th><th class="num">成交金额</th><th class="num">总 ROI</th><th class="num">点击</th><th class="num">展现</th></tr></thead>
        <tbody>
          <tr v-for="row in subRows" :key="row.subCategory">
            <td>{{ row.subCategory }}</td>
            <td class="num">¥{{ formatMoney(row.cost) }}</td>
            <td class="num">¥{{ formatMoney(row.totalSales) }}</td>
            <td :class="['num', roiClass(row.totalRoi)]">{{ row.totalRoi.toFixed(2) }}</td>
            <td class="num">{{ row.clicks.toLocaleString() }}</td>
            <td class="num">{{ row.impressions.toLocaleString() }}</td>
          </tr>
        </tbody>
      </table></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import EChart from "./EChart.vue";
import payload from "../data/dashboard-data.json";
import { byDate, byCategory, formatMoney, formatPercent, sumMetrics } from "../utils/metrics";

const props = defineProps({ filtered: { type: Array, required: true }, prevFiltered: { type: Array, default: [] }, category: String, allSubCats: { type: Array, default: () => [] } });

const selectedCategory = computed(() => props.category && props.category !== "all" ? props.category : null);
const totals = computed(() => sumMetrics(props.filtered));
const prevTot = computed(() => props.prevFiltered.length ? sumMetrics(props.prevFiltered) : null);
const dailyRows = computed(() => byDate(props.filtered));
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
  return Object.values(agg).map(r => ({ ...r, cost: Math.round(r.cost * 100) / 100, totalSales: Math.round(r.totalSales * 100) / 100, totalRoi: r.cost > 0 ? r.totalSales / r.cost : 0 })).sort((a, b) => b.cost - a.cost);
});

function roiClass(v) { return v >= 3 ? "roi-good" : v < 1 ? "roi-risk" : ""; }

const axisDates = computed(() => dailyRows.value.map((r) => r.date));
const mks = { formatter: (v) => typeof v === 'number' ? formatMoney(v) : v };

const trendOption = computed(() => ({
  tooltip: { trigger: "axis" }, legend: { top: 0, data: ["花费", "总成交"] },
  grid: { left: 56, right: 24, top: 42, bottom: 48 },
  xAxis: { type: "category", data: axisDates.value, axisLabel: { rotate: 30 } },
  yAxis: { type: "value", axisLabel: mks },
  series: [
    { name: "花费", type: "line", smooth: true, data: dailyRows.value.map(r => Number(r.cost.toFixed(2))), itemStyle: { color: "#ff6b6b" }, areaStyle: { opacity: 0.08 } },
    { name: "总成交", type: "line", smooth: true, data: dailyRows.value.map(r => Number(r.totalSales.toFixed(2))), itemStyle: { color: "#4ecdc4" }, areaStyle: { opacity: 0.08 } }
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
  for (const s of payload.subjects) {
    for (const sc of s.scenarios) {
      if (!agg[sc.scenario]) agg[sc.scenario] = 0;
      agg[sc.scenario] += sc.cost;
    }
  }
  return Object.entries(agg).map(([name, cost]) => ({ name, value: Number(cost.toFixed(2)) })).sort((a, b) => b.value - a.value);
});
const pieOption = computed(() => ({
  tooltip: { trigger: "item", formatter: "{b}: ¥{c} ({d}%)" },
  legend: { type: "scroll", bottom: 0 },
  series: [{ type: "pie", radius: ["42%", "68%"], center: ["50%", "45%"], label: { formatter: "{b}\n{d}%" }, data: scenarioRows.value }]
}));
</script>
