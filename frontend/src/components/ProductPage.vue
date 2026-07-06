<template>
  <div>
    <div class="kpi-row">
      <div class="kpi-card cost"><div class="kpi-label">总花费</div><div class="kpi-value">¥{{ formatMoney(kpi.cost) }}</div></div>
      <div class="kpi-card sales"><div class="kpi-label">总成交</div><div class="kpi-value">¥{{ formatMoney(kpi.totalSales) }}</div></div>
      <div class="kpi-card troi"><div class="kpi-label">总 ROI</div><div class="kpi-value">{{ kpi.totalRoi.toFixed(2) }}</div></div>
      <div class="kpi-card click"><div class="kpi-label">总点击</div><div class="kpi-value">{{ kpi.clicks.toLocaleString() }}</div></div>
      <div class="kpi-card cvr"><div class="kpi-label">转化率</div><div class="kpi-value">{{ formatPercent(kpi.cvr) }}</div></div>
    </div>

    <!-- Summary -->
    <div class="summary-box">
      <div class="chart-title">推广总结</div>
      <div v-for="(line, i) in summaryLines" :key="i" class="summary-line" v-html="line"></div>
    </div>

    <div class="panel-table">
      <div class="chart-title">主体推广数据 ({{ displaySubjects.length }}条)</div>
      <div class="table-wrap"><table>
        <thead><tr>
          <th class="sortable" @click="toggleSort('subjectId')">主体ID<span :class="['sort-arrow', {active: sortField==='subjectId'}]">{{ sortArrow('subjectId') }}</span></th>
          <th class="sortable" @click="toggleSort('subjectName')">主体名称<span :class="['sort-arrow', {active: sortField==='subjectName'}]">{{ sortArrow('subjectName') }}</span></th>
          <th class="sortable" @click="toggleSort('subCategory')">细类<span :class="['sort-arrow', {active: sortField==='subCategory'}]">{{ sortArrow('subCategory') }}</span></th>
          <th class="num sortable" @click="toggleSort('cost')">花费<span :class="['sort-arrow', {active: sortField==='cost'}]">{{ sortArrow('cost') }}</span></th>
          <th class="num sortable" @click="toggleSort('totalSales')">总成交<span :class="['sort-arrow', {active: sortField==='totalSales'}]">{{ sortArrow('totalSales') }}</span></th>
          <th class="num sortable" @click="toggleSort('totalRoi')">总 ROI<span :class="['sort-arrow', {active: sortField==='totalRoi'}]">{{ sortArrow('totalRoi') }}</span></th>
          <th class="num sortable" @click="toggleSort('clicks')">点击<span :class="['sort-arrow', {active: sortField==='clicks'}]">{{ sortArrow('clicks') }}</span></th>
          <th class="num sortable" @click="toggleSort('impressions')">展现<span :class="['sort-arrow', {active: sortField==='impressions'}]">{{ sortArrow('impressions') }}</span></th>
        </tr></thead>
        <tbody>
          <template v-for="s in displaySubjects" :key="s.subjectId">
            <tr>
              <td class="subject-click" @click="toggleDetail(s.subjectId)">{{ s.subjectId }}</td>
              <td>{{ truncateName(s.subjectName) }}</td>
              <td>{{ s.subCategory }}</td>
              <td class="num">¥{{ formatMoney(s.cost) }}</td>
              <td class="num">¥{{ formatMoney(s.totalSales) }}</td>
              <td :class="['num', roiClass(s.totalRoi)]">{{ s.totalRoi.toFixed(2) }}</td>
              <td class="num">{{ s.clicks.toLocaleString() }}</td>
              <td class="num">{{ s.impressions.toLocaleString() }}</td>
            </tr>
            <tr v-if="expandedId === s.subjectId">
              <td colspan="8" style="padding:0">
                <div class="subj-inline-detail">
                  <div v-for="group in getScenarioGroups(s)" :key="group.scenario" class="scenario-block">
                    <div class="scenario-header">
                      推广场景：{{ group.scenario }}
                      <span class="summary">花费 ¥{{ formatMoney(group.cost) }} · 成交 ¥{{ formatMoney(group.totalSales) }} · ROI {{ group.roi.toFixed(2) }}</span>
                    </div>
                    <div class="table-wrap">
                      <table>
                        <thead><tr>
                          <th>计划名称</th><th class="num">花费</th><th class="num">总成交</th>
                          <th class="num">ROI</th><th class="num">点击</th><th class="num">展现</th>
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
              </td>
            </tr>
          </template>
          <tr v-if="displaySubjects.length === 0"><td colspan="8" class="empty">暂无数据</td></tr>
        </tbody>
      </table></div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { formatMoney, formatPercent, sumMetrics } from "../utils/metrics";
import payload from "../data/dashboard-data.json";

const props = defineProps({ filtered: { type: Array, required: true } });
const expandedId = ref(null);
const sortField = ref('cost');
const sortDir = ref('desc');

const kpi = computed(() => {
  const t = sumMetrics(props.filtered);
  return { cost: t.cost, totalSales: t.totalSales, totalRoi: t.totalRoi, clicks: t.clicks, cvr: t.cvr };
});

const displaySubjects = computed(() => {
  const cats = new Set(props.filtered.map(r => r.category));
  const allCats = cats.size >= payload.categories.length;
  let result = payload.subjects;
  if (!allCats && cats.size > 0) result = result.filter(s => cats.has(s.category));
  return result
    .map(s => ({ ...s, totalRoi: s.cost > 0 ? s.totalSales / s.cost : 0 }))
    .sort((a, b) => {
      const mul = sortDir.value === 'desc' ? -1 : 1;
      const va = a[sortField.value], vb = b[sortField.value];
      if (typeof va === 'string') return (va || '').localeCompare(vb || '') * mul;
      return ((va || 0) - (vb || 0)) * mul;
    })
    .slice(0, 100);
});

// Summary
const summaryLines = computed(() => {
  const rows = displaySubjects.value;
  const t = kpi.value;
  const lines = [];
  if (rows.length === 0) { lines.push('当前筛选条件下暂无数据'); return lines; }
  lines.push(`📊 当前筛选周期内总花费 <strong>¥${formatMoney(t.cost)}</strong>，总成交 <strong>¥${formatMoney(t.totalSales)}</strong>，整体 ROI <span class="highlight-blue">${t.totalRoi.toFixed(2)}</span>`);

  const top3 = rows.slice(0, 3).map(s => `${s.subjectId}（¥${formatMoney(s.cost)}，ROI ${s.totalRoi.toFixed(2)}）`);
  lines.push(`💡 花费 TOP 3：${top3.join('、')}`);

  const best = rows.reduce((a, b) => a.totalRoi > b.totalRoi ? a : b, rows[0]);
  if (best && best.totalRoi > 0 && best.cost > 100) {
    lines.push(`✅ ROI 表现最好的是 <strong>${best.subjectId}</strong>，ROI 达 <span class="highlight-green">${best.totalRoi.toFixed(2)}</span>，花费 ¥${formatMoney(best.cost)}，建议持续关注并优化其投放策略`);
  }

  const worst = rows.filter(s => s.cost > 100).reduce((a, b) => a.totalRoi < b.totalRoi ? a : b, rows[0]);
  if (worst && worst.totalRoi < 3 && worst.cost > 100) {
    lines.push(`⚠️ <strong>${worst.subjectId}</strong> 的 ROI 较低（<span class="highlight-red">${worst.totalRoi.toFixed(2)}</span>），花费 ¥${formatMoney(worst.cost)}，建议优化投放策略或调整预算分配`);
  }

  if (t.clicks > 0 && t.impressions > 0) {
    const ctr = t.clicks / t.impressions * 100;
    lines.push(`📈 整体点击率 ${ctr.toFixed(2)}%，展现量 ${t.impressions.toLocaleString()}，点击量 ${t.clicks.toLocaleString()}`);
  }
  return lines;
});

function toggleSort(field) {
  if (sortField.value === field) { sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'; }
  else { sortField.value = field; sortDir.value = 'desc'; }
}
function sortArrow(field) {
  if (sortField.value !== field) return '↕';
  return sortDir.value === 'desc' ? '↓' : '↑';
}
function truncateName(name) { return name && name.length > 30 ? name.slice(0, 30) + '...' : name; }

function getScenarioGroups(subject) {
  const groups = {};
  for (const sc of subject.scenarios) {
    const roi = sc.cost > 0 ? sc.totalSales / sc.cost : 0;
    if (!groups[sc.scenario]) groups[sc.scenario] = { scenario: sc.scenario, plans: [], cost: 0, totalSales: 0, clicks: 0, impressions: 0 };
    const g = groups[sc.scenario];
    g.plans.push({ ...sc, totalRoi: roi }); g.cost += sc.cost; g.totalSales += sc.totalSales; g.clicks += sc.clicks; g.impressions += sc.impressions;
  }
  return Object.values(groups).map(g => ({
    ...g, cost: Math.round(g.cost * 100) / 100, totalSales: Math.round(g.totalSales * 100) / 100, roi: g.cost > 0 ? g.totalSales / g.cost : 0
  }));
}

function toggleDetail(id) { expandedId.value = expandedId.value === id ? null : id; }
function roiClass(v) { return v >= 3 ? "roi-good" : v < 1 ? "roi-risk" : ""; }
</script>
