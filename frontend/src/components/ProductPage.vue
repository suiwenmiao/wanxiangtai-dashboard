<template>
  <div>
    <!-- KPI -->
    <div class="kpi-row">
      <div class="kpi-card cost">
        <div class="kpi-label">总花费</div>
        <div class="kpi-value">¥{{ formatMoney(subjTotals.cost) }}</div>
      </div>
      <div class="kpi-card sales">
        <div class="kpi-label">总成交</div>
        <div class="kpi-value">¥{{ formatMoney(subjTotals.totalSales) }}</div>
      </div>
      <div class="kpi-card troi">
        <div class="kpi-label">总 ROI</div>
        <div class="kpi-value">{{ subjTotals.totalRoi.toFixed(2) }}</div>
      </div>
      <div class="kpi-card click">
        <div class="kpi-label">总点击</div>
        <div class="kpi-value">{{ subjTotals.clicks.toLocaleString() }}</div>
      </div>
      <div class="kpi-card cvr">
        <div class="kpi-label">转化率</div>
        <div class="kpi-value">{{ formatPercent(subjTotals.cvr) }}</div>
      </div>
    </div>

    <!-- Subjects Table -->
    <div class="panel-table">
      <div class="chart-title">主体推广数据 ({{ displaySubjects.length }}条)</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>主体ID</th><th>主体名称</th><th>品类</th><th>细类</th><th class="num">花费</th><th class="num">总成交</th>
              <th class="num">总 ROI</th><th class="num">点击</th><th class="num">展现</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="s in displaySubjects" :key="s.subjectId">
              <td class="subject-click" @click="toggleDetail(s.subjectId)">{{ s.subjectId }}</td>
              <td>{{ s.subjectName }}</td>
              <td>{{ s.category }}</td>
              <td>{{ s.subCategory }}</td>
              <td class="num">¥{{ formatMoney(s.cost) }}</td>
              <td class="num">¥{{ formatMoney(s.totalSales) }}</td>
              <td :class="['num', roiClass(s.totalRoi)]">{{ s.totalRoi.toFixed(2) }}</td>
              <td class="num">{{ s.clicks.toLocaleString() }}</td>
              <td class="num">{{ s.impressions.toLocaleString() }}</td>
              <td><button class="btn-quick" @click="toggleDetail(s.subjectId)">{{ expandedId === s.subjectId ? '收起' : '查看' }}</button></td>
            </tr>
            <tr v-if="displaySubjects.length === 0">
              <td colspan="10" class="empty">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Detail Panel -->
    <div class="panel-table" v-if="detailSubject">
      <div class="chart-title">
        主体 {{ detailSubject.subjectId }} — {{ detailSubject.subjectName }}
      </div>
      <div style="font-size:13px;color:#888;margin-bottom:12px;padding-left:10px;">
        品类: {{ detailSubject.category }} · 细类: {{ detailSubject.subCategory }} · 总花费: ¥{{ formatMoney(detailSubject.cost) }}
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>推广场景</th><th>计划名称</th><th class="num">花费</th><th class="num">总成交</th><th class="num">ROI</th><th class="num">点击</th><th class="num">展现</th></tr>
          </thead>
          <tbody>
            <tr v-for="(sc, i) in detailSubject.scenarios" :key="i">
              <td>{{ sc.scenario }}</td>
              <td>{{ sc.planName }}</td>
              <td class="num">¥{{ formatMoney(sc.cost) }}</td>
              <td class="num">¥{{ formatMoney(sc.totalSales) }}</td>
              <td :class="['num', roiClass(sc.totalRoi)]">{{ sc.totalRoi.toFixed(2) }}</td>
              <td class="num">{{ sc.clicks.toLocaleString() }}</td>
              <td class="num">{{ sc.impressions.toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { formatMoney, formatPercent } from "../utils/metrics";
import payload from "../data/dashboard-data.json";

const props = defineProps({
  filtered: { type: Array, required: true }
});

const expandedId = ref(null);

// Show subjects filtered by category only, ignore date filter
const displaySubjects = computed(() => {
  // Get selected categories from the filtered data
  const cats = new Set(props.filtered.map(r => r.category));
  const hasAllCats = cats.size >= payload.categories.length;

  let result = payload.subjects;
  // If not all categories are selected, filter by category
  if (!hasAllCats && cats.size > 0) {
    result = result.filter(s => cats.has(s.category));
  }

  // Recalculate totalRoi for each subject
  return result.map(s => ({
    ...s,
    totalRoi: s.cost > 0 ? s.totalSales / s.cost : 0
  })).sort((a, b) => b.cost - a.cost).slice(0, 100);
});

const subjTotals = computed(() => {
  const rows = displaySubjects.value;
  const total = { cost: 0, totalSales: 0, directSales: 0, orders: 0, clicks: 0, impressions: 0, carts: 0 };
  for (const s of rows) {
    total.cost += s.cost; total.totalSales += s.totalSales;
    total.directSales += s.directSales; total.orders += s.orders;
    total.clicks += s.clicks; total.impressions += s.impressions; total.carts += s.carts;
  }
  return {
    ...total,
    totalRoi: total.cost > 0 ? total.totalSales / total.cost : 0,
    cvr: total.clicks > 0 ? total.orders / total.clicks : 0,
  };
});

const detailSubject = computed(() => {
  if (!expandedId.value) return null;
  const s = payload.subjects.find(x => x.subjectId === expandedId.value);
  if (!s) return null;
  return {
    ...s,
    scenarios: s.scenarios.map(sc => ({
      ...sc,
      totalRoi: sc.cost > 0 ? sc.totalSales / sc.cost : 0,
    }))
  };
});

function toggleDetail(id) {
  expandedId.value = expandedId.value === id ? null : id;
}

function roiClass(v) { return v >= 3 ? "roi-good" : v < 1 ? "roi-risk" : ""; }
</script>
