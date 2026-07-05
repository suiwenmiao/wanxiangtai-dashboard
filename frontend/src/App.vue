<template>
  <main class="page">
    <header class="topbar">
      <div>
        <h1>万相台投放数据看板</h1>
        <p>{{ dataRangeLabel }} · 更新 {{ generatedAtLabel }}</p>
      </div>
      <div class="status-pill">{{ filtered.length }} 条聚合记录</div>
    </header>

    <section class="toolbar">
      <label>
        <span>开始</span>
        <input v-model="startDate" type="date" :min="payload.dateMin" :max="payload.dateMax" />
      </label>
      <label>
        <span>结束</span>
        <input v-model="endDate" type="date" :min="payload.dateMin" :max="payload.dateMax" />
      </label>
      <label>
        <span>品类</span>
        <select v-model="category">
          <option value="all">全部品类</option>
          <option v-for="item in payload.categories" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <div class="quick-actions">
        <button :class="{ active: quickDays === 1 }" @click="setQuickRange(1)">今天</button>
        <button :class="{ active: quickDays === 7 }" @click="setQuickRange(7)">近7天</button>
        <button :class="{ active: quickDays === 30 }" @click="setQuickRange(30)">近30天</button>
        <button :class="{ active: quickDays === 0 }" @click="setQuickRange(0)">全部</button>
      </div>
    </section>

    <section class="kpi-grid">
      <article v-for="item in kpiCards" :key="item.label" class="kpi-card">
        <span class="kpi-label">{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </article>
    </section>

    <section class="chart-grid">
      <article class="panel wide">
        <div class="panel-head">
          <h2>每日花费与成交金额</h2>
        </div>
        <EChart :option="trendOption" />
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>每日 ROI 趋势</h2>
        </div>
        <EChart :option="roiOption" />
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>品类花费占比</h2>
        </div>
        <EChart :option="pieOption" />
      </article>
    </section>

    <section class="panel table-panel">
      <div class="panel-head">
        <h2>品类效果明细</h2>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>品类</th>
              <th>花费</th>
              <th>成交金额</th>
              <th>总 ROI</th>
              <th>点击</th>
              <th>展现</th>
              <th>转化率</th>
              <th>CPC</th>
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
  </main>
</template>

<script setup>
import { computed, ref } from "vue";
import EChart from "./components/EChart.vue";
import payload from "./data/dashboard-data.json";
import { byCategory, byDate, formatMoney, formatPercent, sumMetrics } from "./utils/metrics";

const startDate = ref(payload.dateMax || "");
const endDate = ref(payload.dateMax || "");
const category = ref("all");
const quickDays = ref(1);

const filtered = computed(() =>
  payload.records.filter((row) => {
    if (startDate.value && row.date < startDate.value) return false;
    if (endDate.value && row.date > endDate.value) return false;
    if (category.value !== "all" && row.category !== category.value) return false;
    return true;
  })
);

const totals = computed(() => sumMetrics(filtered.value));
const dailyRows = computed(() => byDate(filtered.value));
const categoryRows = computed(() => byCategory(filtered.value));

const dataRangeLabel = computed(() => {
  if (!payload.dateMin || !payload.dateMax) return "暂无数据";
  return `数据范围 ${payload.dateMin} 至 ${payload.dateMax}`;
});

const generatedAtLabel = computed(() => {
  if (!payload.generatedAt) return "未生成";
  return payload.generatedAt.replace("T", " ");
});

const kpiCards = computed(() => [
  { label: "花费", value: `¥${formatMoney(totals.value.cost)}`, hint: "筛选周期投放消耗" },
  { label: "总成交", value: `¥${formatMoney(totals.value.totalSales)}`, hint: "直接与间接成交合计" },
  { label: "直接 ROI", value: totals.value.directRoi.toFixed(2), hint: "直接成交金额 / 花费" },
  { label: "总 ROI", value: totals.value.totalRoi.toFixed(2), hint: "总成交金额 / 花费" },
  { label: "转化率", value: formatPercent(totals.value.cvr), hint: "成交笔数 / 点击量" }
]);

function setQuickRange(days) {
  quickDays.value = days;
  if (!payload.dateMax) return;
  const end = new Date(payload.dateMax);
  let start;
  if (days === 0) {
    start = new Date(payload.dateMin);
  } else {
    start = new Date(end);
    start.setDate(start.getDate() - days + 1);
  }
  startDate.value = start.toISOString().slice(0, 10);
  endDate.value = end.toISOString().slice(0, 10);
}

function roiClass(value) {
  if (value >= 3) return "roi-good";
  if (value < 1) return "roi-risk";
  return "";
}

const axisDates = computed(() => dailyRows.value.map((row) => row.date));

const trendOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { top: 0, data: ["花费", "总成交"] },
  grid: { left: 56, right: 24, top: 42, bottom: 48 },
  xAxis: { type: "category", data: axisDates.value, axisLabel: { rotate: 30 } },
  yAxis: { type: "value", axisLabel: { formatter: (value) => formatMoney(value) } },
  series: [
    {
      name: "花费",
      type: "line",
      smooth: true,
      data: dailyRows.value.map((row) => Number(row.cost.toFixed(2))),
      itemStyle: { color: "#e85d5d" },
      areaStyle: { opacity: 0.08 }
    },
    {
      name: "总成交",
      type: "line",
      smooth: true,
      data: dailyRows.value.map((row) => Number(row.totalSales.toFixed(2))),
      itemStyle: { color: "#168f7a" },
      areaStyle: { opacity: 0.08 }
    }
  ]
}));

const roiOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { top: 0, data: ["直接 ROI", "总 ROI"] },
  grid: { left: 44, right: 20, top: 42, bottom: 48 },
  xAxis: { type: "category", data: axisDates.value, axisLabel: { rotate: 30 } },
  yAxis: { type: "value" },
  series: [
    {
      name: "直接 ROI",
      type: "line",
      smooth: true,
      data: dailyRows.value.map((row) => Number(row.directRoi.toFixed(2))),
      itemStyle: { color: "#3b82c4" }
    },
    {
      name: "总 ROI",
      type: "line",
      smooth: true,
      data: dailyRows.value.map((row) => Number(row.totalRoi.toFixed(2))),
      itemStyle: { color: "#168f7a" }
    }
  ]
}));

const pieOption = computed(() => ({
  tooltip: { trigger: "item", formatter: "{b}: ¥{c} ({d}%)" },
  legend: { type: "scroll", bottom: 0 },
  series: [
    {
      type: "pie",
      radius: ["42%", "68%"],
      center: ["50%", "45%"],
      label: { formatter: "{b}\n{d}%" },
      data: categoryRows.value.map((row) => ({
        name: row.category,
        value: Number(row.cost.toFixed(2))
      }))
    }
  ]
}));
</script>
