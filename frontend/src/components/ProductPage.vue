<template>
  <section>
    <section class="kpi-grid">
      <article v-for="item in productKpi" :key="item.label" class="kpi-card">
        <span class="kpi-label">{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </article>
    </section>

    <section class="chart-grid">
      <article class="panel">
        <div class="panel-head"><h2>品类花费 vs 成交</h2></div>
        <EChart :option="scatterOption" />
      </article>
      <article class="panel">
        <div class="panel-head"><h2>各品类 ROI 对比</h2></div>
        <EChart :option="barRoiOption" />
      </article>
      <article class="panel wide">
        <div class="panel-head"><h2>品类每日花费热力</h2></div>
        <EChart :option="heatOption" />
      </article>
    </section>

    <section class="panel table-panel">
      <div class="panel-head"><h2>数据明细</h2></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>日期</th><th>品类</th><th>花费</th><th>总成交</th>
              <th>总 ROI</th><th>点击</th><th>展现</th><th>转化率</th><th>收藏加购</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in detailRows" :key="i">
              <td>{{ row.date }}</td>
              <td>{{ row.category }}</td>
              <td>¥{{ formatMoney(row.cost) }}</td>
              <td>¥{{ formatMoney(row.totalSales) }}</td>
              <td :class="roiClass(row.totalRoi)">{{ row.totalRoi.toFixed(2) }}</td>
              <td>{{ row.clicks.toLocaleString() }}</td>
              <td>{{ row.impressions.toLocaleString() }}</td>
              <td>{{ formatPercent(row.cvr) }}</td>
              <td>{{ row.favCart != null ? row.favCart.toLocaleString() : '-' }}</td>
            </tr>
            <tr v-if="detailRows.length === 0">
              <td colspan="9" class="empty">当前筛选条件下暂无数据</td>
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
import { formatMoney, formatPercent, sumMetrics } from "../utils/metrics";

const props = defineProps({ filtered: { type: Array, required: true } });
const totals = computed(() => sumMetrics(props.filtered));

const productKpi = computed(() => [
  { label: "总花费", value: `¥${formatMoney(totals.value.cost)}`, hint: "所有筛选记录合计" },
  { label: "总成交", value: `¥${formatMoney(totals.value.totalSales)}`, hint: "直接与间接成交合计" },
  { label: "总 ROI", value: totals.value.totalRoi.toFixed(2), hint: "总成交 / 花费" },
  { label: "总点击", value: totals.value.clicks.toLocaleString(), hint: "筛选周期内总点击量" },
  { label: "总展现", value: totals.value.impressions.toLocaleString(), hint: "筛选周期内总展现量" }
]);

const detailRows = computed(() => {
  const rows = [...props.filtered];
  rows.sort((a, b) => b.date.localeCompare(a.date) || b.cost - a.cost);
  return rows;
});

function roiClass(v) { return v >= 3 ? "roi-good" : v < 1 ? "roi-risk" : ""; }

const categoryAgg = computed(() => {
  const map = {};
  for (const r of props.filtered) {
    if (!map[r.category]) map[r.category] = { cost: 0, sales: 0, count: 0 };
    map[r.category].cost += r.cost;
    map[r.category].sales += r.totalSales;
    map[r.category].count++;
  }
  return Object.entries(map)
    .map(([name, v]) => ({ name, cost: v.cost, sales: v.sales, roi: v.sales / (v.cost || 1) }))
    .sort((a, b) => b.cost - a.cost);
});

const scatterOption = computed(() => ({
  tooltip: { trigger: "item", formatter: (p) => `${p.name}<br/>花费: ¥${formatMoney(p.value[0])}<br/>成交: ¥${formatMoney(p.value[1])}` },
  xAxis: { type: "value", name: "花费", axisLabel: { formatter: (v) => formatMoney(v) } },
  yAxis: { type: "value", name: "成交金额", axisLabel: { formatter: (v) => formatMoney(v) } },
  series: [{
    type: "scatter", symbolSize: 16,
    data: categoryAgg.value.map((c) => ({ value: [Number(c.cost.toFixed(2)), Number(c.sales.toFixed(2))], name: c.name })),
    itemStyle: { color: "#3b82c4" },
    label: { show: true, formatter: "{b}", position: "right", fontSize: 11 }
  }]
}));

const barRoiOption = computed(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 60, right: 20, top: 10, bottom: 40 },
  xAxis: { type: "category", data: categoryAgg.value.map((c) => c.name), axisLabel: { rotate: 25 } },
  yAxis: { type: "value", name: "ROI" },
  series: [{ type: "bar", data: categoryAgg.value.map((c) => Number(c.roi.toFixed(2))), itemStyle: { color: "#168f7a" } }]
}));

const heatOption = computed(() => {
  const cats = [...new Set(props.filtered.map((r) => r.category))].sort();
  const dates = [...new Set(props.filtered.map((r) => r.date))].sort();
  const map = {};
  for (const r of props.filtered) map[r.date + "|" + r.category] = r.cost;
  const data = [];
  for (let i = 0; i < dates.length; i++)
    for (let j = 0; j < cats.length; j++)
      data.push([i, j, map[dates[i] + "|" + cats[j]] || 0]);
  return {
    tooltip: { position: "top", formatter: (p) => `${dates[p.data[0]]} ${cats[p.data[1]]}<br/>花费: ¥${formatMoney(p.data[2])}` },
    grid: { left: 60, right: 60, top: 10, bottom: 40 },
    xAxis: { type: "category", data: dates, splitArea: { show: true }, axisLabel: { rotate: 30, fontSize: 10 } },
    yAxis: { type: "category", data: cats, splitArea: { show: true } },
    visualMap: { min: 0, max: Math.max(...data.map((d) => d[2]) || [1]), calculable: true, orient: "vertical", right: 0, top: 10, bottom: 40 },
    series: [{ type: "heatmap", data, label: { show: false }, emphasis: { itemStyle: { shadowBlur: 10 } } }]
  };
});
</script>
