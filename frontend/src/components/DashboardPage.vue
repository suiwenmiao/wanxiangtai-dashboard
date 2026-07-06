<template>
  <section>
    <section class="kpi-grid">
      <article v-for="item in kpiCards" :key="item.label" class="kpi-card">
        <span class="kpi-label">{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </article>
    </section>

    <section class="chart-grid">
      <article class="panel wide">
        <div class="panel-head"><h2>每日花费与成交金额</h2></div>
        <EChart :option="trendOption" />
      </article>
      <article class="panel">
        <div class="panel-head"><h2>每日 ROI 趋势</h2></div>
        <EChart :option="roiOption" />
      </article>
      <article class="panel">
        <div class="panel-head"><h2>品类花费占比</h2></div>
        <EChart :option="pieOption" />
      </article>
    </section>

    <section class="panel table-panel">
      <div class="panel-head"><h2>品类效果明细</h2></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>品类</th><th>花费</th><th>成交金额</th><th>总 ROI</th>
              <th>点击</th><th>展现</th><th>转化率</th><th>CPC</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in categoryRows" :key="row.category">
              <td>{{ row.category }}</td>
              <td>¥{{ formatMoney(row.cost) }}</td>
              <td>¥{{ formatMoney(row.totalSales) }}</td>
              <td :class="roiClass(row.totalRoi)">{{ row.totalRoi.toFixed(2) }}</td>
              <td>{{ row.clicks.toLocaleString() }}</td>
              <td>{{ row.impressions.toLocaleString() }}</td>
              <td>{{ formatPercent(row.cvr) }}</td>
              <td>¥{{ row.cpc.toFixed(2) }}</td>
            </tr>
            <tr v-if="categoryRows.length === 0">
              <td colspan="8" class="empty">当前筛选条件下暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed } from "vue";
import EChart from "./EChart.vue";
import { byDate, byCategory, formatMoney, formatPercent, sumMetrics } from "../utils/metrics";

const props = defineProps({ filtered: { type: Array, required: true } });
const totals = computed(() => sumMetrics(props.filtered));
const dailyRows = computed(() => byDate(props.filtered));
const categoryRows = computed(() => byCategory(props.filtered));

const kpiCards = computed(() => [
  { label: "花费", value: `¥${formatMoney(totals.value.cost)}`, hint: "筛选周期投放消耗" },
  { label: "总成交", value: `¥${formatMoney(totals.value.totalSales)}`, hint: "直接与间接成交合计" },
  { label: "直接 ROI", value: totals.value.directRoi.toFixed(2), hint: "直接成交金额 / 花费" },
  { label: "总 ROI", value: totals.value.totalRoi.toFixed(2), hint: "总成交金额 / 花费" },
  { label: "转化率", value: formatPercent(totals.value.cvr), hint: "成交笔数 / 点击量" }
]);

function roiClass(v) { return v >= 3 ? "roi-good" : v < 1 ? "roi-risk" : ""; }

const axisDates = computed(() => dailyRows.value.map((r) => r.date));

const trendOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { top: 0, data: ["花费", "总成交"] },
  grid: { left: 56, right: 24, top: 42, bottom: 48 },
  xAxis: { type: "category", data: axisDates.value, axisLabel: { rotate: 30 } },
  yAxis: { type: "value", axisLabel: { formatter: (v) => formatMoney(v) } },
  series: [
    { name: "花费", type: "line", smooth: true, data: dailyRows.value.map((r) => Number(r.cost.toFixed(2))), itemStyle: { color: "#e85d5d" }, areaStyle: { opacity: 0.08 } },
    { name: "总成交", type: "line", smooth: true, data: dailyRows.value.map((r) => Number(r.totalSales.toFixed(2))), itemStyle: { color: "#168f7a" }, areaStyle: { opacity: 0.08 } }
  ]
}));

const roiOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { top: 0, data: ["直接 ROI", "总 ROI"] },
  grid: { left: 44, right: 20, top: 42, bottom: 48 },
  xAxis: { type: "category", data: axisDates.value, axisLabel: { rotate: 30 } },
  yAxis: { type: "value" },
  series: [
    { name: "直接 ROI", type: "line", smooth: true, data: dailyRows.value.map((r) => Number(r.directRoi.toFixed(2))), itemStyle: { color: "#3b82c4" } },
    { name: "总 ROI", type: "line", smooth: true, data: dailyRows.value.map((r) => Number(r.totalRoi.toFixed(2))), itemStyle: { color: "#168f7a" } }
  ]
}));

const pieOption = computed(() => ({
  tooltip: { trigger: "item", formatter: "{b}: ¥{c} ({d}%)" },
  legend: { type: "scroll", bottom: 0 },
  series: [{
    type: "pie", radius: ["42%", "68%"], center: ["50%", "45%"],
    label: { formatter: "{b}\n{d}%" },
    data: categoryRows.value.map((r) => ({ name: r.category, value: Number(r.cost.toFixed(2)) }))
  }]
}));
</script>
