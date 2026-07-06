<template>
  <div>
    <!-- KPI Cards -->
    <div class="kpi-row">
      <div class="kpi-card cost">
        <div class="kpi-label">花费</div>
        <div class="kpi-value">¥{{ formatMoney(totals.cost) }}</div>
      </div>
      <div class="kpi-card sales">
        <div class="kpi-label">总成交</div>
        <div class="kpi-value">¥{{ formatMoney(totals.totalSales) }}</div>
      </div>
      <div class="kpi-card droi">
        <div class="kpi-label">直接 ROI</div>
        <div class="kpi-value">{{ totals.directRoi.toFixed(2) }}</div>
      </div>
      <div class="kpi-card troi">
        <div class="kpi-label">总 ROI</div>
        <div class="kpi-value">{{ totals.totalRoi.toFixed(2) }}</div>
      </div>
      <div class="kpi-card cvr">
        <div class="kpi-label">转化率</div>
        <div class="kpi-value">{{ formatPercent(totals.cvr) }}</div>
      </div>
    </div>

    <!-- Charts -->
    <div class="chart-row full">
      <div class="chart-container">
        <div class="chart-title">每日花费与成交金额趋势</div>
        <EChart :option="trendOption" classes="echart tall" />
      </div>
    </div>
    <div class="chart-row">
      <div class="chart-container">
        <div class="chart-title">每日 ROI 趋势</div>
        <EChart :option="roiOption" />
      </div>
      <div class="chart-container">
        <div class="chart-title">品类花费占比</div>
        <EChart :option="pieOption" />
      </div>
    </div>

    <!-- Category table -->
    <div class="panel-table">
      <div class="chart-title">品类效果明细</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>品类</th><th class="num">花费</th><th class="num">成交金额</th><th class="num">总 ROI</th>
              <th class="num">点击</th><th class="num">展现</th><th class="num">转化率</th><th class="num">CPC</th></tr>
          </thead>
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
        </table>
      </div>
    </div>

    <!-- Sub-category table (shown when a specific category is selected) -->
    <div class="panel-table sub-section" v-if="selectedCategory && subRows.length > 0">
      <div class="chart-title">{{ selectedCategory }} — 细类明细</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>细类</th><th class="num">花费</th><th class="num">成交金额</th><th class="num">总 ROI</th>
              <th class="num">点击</th><th class="num">展现</th></tr>
          </thead>
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
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import EChart from "./EChart.vue";
import { byDate, byCategory, formatMoney, formatPercent, sumMetrics } from "../utils/metrics";

const props = defineProps({ filtered: { type: Array, required: true }, category: String, allSubCats: { type: Array, default: () => [] } });

const selectedCategory = computed(() => props.category && props.category !== "all" ? props.category : null);

const totals = computed(() => sumMetrics(props.filtered));
const dailyRows = computed(() => byDate(props.filtered));
const categoryRows = computed(() => byCategory(props.filtered));

const subRows = computed(() => {
  if (!selectedCategory.value) return [];
  const agg = {};
  for (const r of props.allSubCats) {
    if (r.category !== selectedCategory.value) continue;
    const key = r.subCategory;
    if (!agg[key]) { agg[key] = { subCategory: key, cost: 0, totalSales: 0, directSales: 0, clicks: 0, impressions: 0, orders: 0, carts: 0 }; }
    const a = agg[key];
    a.cost += r.cost; a.totalSales += r.totalSales; a.directSales += r.directSales;
    a.clicks += r.clicks; a.impressions += r.impressions; a.orders += r.orders; a.carts += r.carts;
  }
  return Object.values(agg).map(r => ({
    ...r, cost: Math.round(r.cost * 100) / 100, totalSales: Math.round(r.totalSales * 100) / 100,
    totalRoi: r.cost > 0 ? r.totalSales / r.cost : 0
  })).sort((a, b) => b.cost - a.cost);
});

function roiClass(v) { return v >= 3 ? "roi-good" : v < 1 ? "roi-risk" : ""; }

const axisDates = computed(() => dailyRows.value.map((r) => r.date));
const mks = { formatter: (v) => typeof v === 'number' ? formatMoney(v) : v };

const trendOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { top: 0, data: ["花费", "总成交"] },
  grid: { left: 56, right: 24, top: 42, bottom: 48 },
  xAxis: { type: "category", data: axisDates.value, axisLabel: { rotate: 30 } },
  yAxis: { type: "value", axisLabel: mks },
  series: [
    { name: "花费", type: "line", smooth: true, data: dailyRows.value.map(r => Number(r.cost.toFixed(2))), itemStyle: { color: "#ff6b6b" }, areaStyle: { opacity: 0.08 } },
    { name: "总成交", type: "line", smooth: true, data: dailyRows.value.map(r => Number(r.totalSales.toFixed(2))), itemStyle: { color: "#4ecdc4" }, areaStyle: { opacity: 0.08 } }
  ]
}));

const roiOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { top: 0, data: ["直接 ROI", "总 ROI"] },
  grid: { left: 44, right: 20, top: 42, bottom: 48 },
  xAxis: { type: "category", data: axisDates.value, axisLabel: { rotate: 30 } },
  yAxis: { type: "value" },
  series: [
    { name: "直接 ROI", type: "line", smooth: true, data: dailyRows.value.map(r => Number(r.directRoi.toFixed(2))), itemStyle: { color: "#45b7d1" } },
    { name: "总 ROI", type: "line", smooth: true, data: dailyRows.value.map(r => Number(r.totalRoi.toFixed(2))), itemStyle: { color: "#96ceb4" } }
  ]
}));

const pieOption = computed(() => ({
  tooltip: { trigger: "item", formatter: "{b}: ¥{c} ({d}%)" },
  legend: { type: "scroll", bottom: 0 },
  series: [{ type: "pie", radius: ["42%", "68%"], center: ["50%", "45%"], label: { formatter: "{b}\n{d}%" },
    data: categoryRows.value.map(r => ({ name: r.category, value: Number(r.cost.toFixed(2)) }))
  }]
}));
</script>
