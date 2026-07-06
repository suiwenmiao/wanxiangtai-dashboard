<template>
  <div>
    <div class="kpi-row">
      <div class="kpi-card cost"><div class="kpi-label">总花费</div><div class="kpi-value">¥{{ formatMoney(subjTotals.cost) }}</div></div>
      <div class="kpi-card sales"><div class="kpi-label">总成交</div><div class="kpi-value">¥{{ formatMoney(subjTotals.totalSales) }}</div></div>
      <div class="kpi-card troi"><div class="kpi-label">总 ROI</div><div class="kpi-value">{{ subjTotals.totalRoi.toFixed(2) }}</div></div>
      <div class="kpi-card click"><div class="kpi-label">总点击</div><div class="kpi-value">{{ subjTotals.clicks.toLocaleString() }}</div></div>
      <div class="kpi-card cvr"><div class="kpi-label">转化率</div><div class="kpi-value">{{ formatPercent(subjTotals.cvr) }}</div></div>
    </div>

    <div class="panel-table">
      <div class="chart-title">主体推广数据 ({{ displaySubjects.length }}条)</div>
      <div class="table-wrap"><table>
        <thead><tr>
          <th>主体ID</th><th>主体名称</th><th>品类</th>
          <th class="num">花费</th><th class="num">总成交</th><th class="num">总 ROI</th><th class="num">点击</th><th class="num">展现</th>
        </tr></thead>
        <tbody>
          <tr v-for="s in displaySubjects" :key="s.subjectId">
            <td class="subject-click" @click="toggleDetail(s.subjectId)">{{ s.subjectId }}</td>
            <td>{{ s.subjectName }}</td><td>{{ s.category }}</td>
            <td class="num">¥{{ formatMoney(s.cost) }}</td>
            <td class="num">¥{{ formatMoney(s.totalSales) }}</td>
            <td :class="['num', roiClass(s.totalRoi)]">{{ s.totalRoi.toFixed(2) }}</td>
            <td class="num">{{ s.clicks.toLocaleString() }}</td>
            <td class="num">{{ s.impressions.toLocaleString() }}</td>
          </tr>
          <tr v-if="displaySubjects.length === 0"><td colspan="8" class="empty">暂无数据</td></tr>
        </tbody>
      </table></div>
    </div>

    <!-- Detail Panel with scenarios grouped by scenario name -->
    <div class="panel-table" v-if="detailSubject">
      <div class="chart-title">
        主体 {{ detailSubject.subjectId }} — {{ detailSubject.subjectName }}
        <span style="font-weight:400;font-size:13px;color:#888;margin-left:12px">
          品类: {{ detailSubject.category }} · 总花费: ¥{{ formatMoney(detailSubject.cost) }}
        </span>
        <button class="btn-quick" style="float:right;margin-top:-4px" @click="expandedId = null">关闭</button>
      </div>

      <div v-for="group in groupedScenarios" :key="group.scenario" style="margin-bottom:16px">
        <div style="background:#f0f2f5;padding:10px 16px;font-weight:700;font-size:14px;border-radius:6px;margin-bottom:8px">
          推广场景：{{ group.scenario }}
          <span style="font-weight:400;color:#888;margin-left:16px">
            花费 ¥{{ formatMoney(group.cost) }} · 成交 ¥{{ formatMoney(group.totalSales) }} · ROI {{ group.roi.toFixed(2) }}
          </span>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th>计划名称</th><th class="num">花费</th><th class="num">总成交</th><th class="num">ROI</th><th class="num">点击</th><th class="num">展现</th>
            </tr></thead>
            <tbody>
              <tr v-for="(p, i) in group.plans" :key="i">
                <td>{{ p.planName }}</td>
                <td class="num">¥{{ formatMoney(p.cost) }}</td>
                <td class="num">¥{{ formatMoney(p.totalSales) }}</td>
                <td :class="['num', roiClass(p.totalRoi)]">{{ p.totalRoi.toFixed(2) }}</td>
                <td class="num">{{ p.clicks.toLocaleString() }}</td>
                <td class="num">{{ p.impressions.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { formatMoney, formatPercent } from "../utils/metrics";
import payload from "../data/dashboard-data.json";

const props = defineProps({ filtered: { type: Array, required: true } });
const expandedId = ref(null);

const displaySubjects = computed(() => {
  const cats = new Set(props.filtered.map(r => r.category));
  const hasAllCats = cats.size >= payload.categories.length;
  let result = payload.subjects;
  if (!hasAllCats && cats.size > 0) result = result.filter(s => cats.has(s.category));
  return result.map(s => ({ ...s, totalRoi: s.cost > 0 ? s.totalSales / s.cost : 0 })).sort((a, b) => b.cost - a.cost).slice(0, 100);
});

const subjTotals = computed(() => {
  const rows = displaySubjects.value;
  const total = { cost: 0, totalSales: 0, directSales: 0, orders: 0, clicks: 0, impressions: 0, carts: 0 };
  for (const s of rows) { total.cost += s.cost; total.totalSales += s.totalSales; total.directSales += s.directSales; total.orders += s.orders; total.clicks += s.clicks; total.impressions += s.impressions; total.carts += s.carts; }
  return { ...total, totalRoi: total.cost > 0 ? total.totalSales / total.cost : 0, cvr: total.clicks > 0 ? total.orders / total.clicks : 0 };
});

const detailSubject = computed(() => {
  if (!expandedId.value) return null;
  const s = payload.subjects.find(x => x.subjectId === expandedId.value);
  if (!s) return null;
  return { ...s, scenarios: s.scenarios.map(sc => ({ ...sc, totalRoi: sc.cost > 0 ? sc.totalSales / sc.cost : 0 })) };
});

const groupedScenarios = computed(() => {
  if (!detailSubject.value) return [];
  const groups = {};
  for (const sc of detailSubject.value.scenarios) {
    if (!groups[sc.scenario]) groups[sc.scenario] = { scenario: sc.scenario, plans: [], cost: 0, totalSales: 0, clicks: 0, impressions: 0 };
    const g = groups[sc.scenario]; g.plans.push(sc); g.cost += sc.cost; g.totalSales += sc.totalSales; g.clicks += sc.clicks; g.impressions += sc.impressions;
  }
  return Object.values(groups).map(g => ({ ...g, cost: Math.round(g.cost * 100) / 100, totalSales: Math.round(g.totalSales * 100) / 100, roi: g.cost > 0 ? g.totalSales / g.cost : 0 }));
});

function toggleDetail(id) { expandedId.value = expandedId.value === id ? null : id; }
function roiClass(v) { return v >= 3 ? "roi-good" : v < 1 ? "roi-risk" : ""; }
</script>
