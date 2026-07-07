<template>
  <div>
    <div class="kpi-row">
      <div class="kpi-card cost">
        <div class="kpi-label">总花费</div><div class="kpi-value">¥{{ formatMoney(kpi.cost) }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.cost)"><span class="arrow">{{ hb.cost > 0 ? '↑' : hb.cost < 0 ? '↓' : '' }}</span>{{ hbText(hb.cost) }} 环比</div>
      </div>
      <div class="kpi-card sales">
        <div class="kpi-label">总成交</div><div class="kpi-value">¥{{ formatMoney(kpi.totalSales) }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.totalSales)"><span class="arrow">{{ hb.totalSales > 0 ? '↑' : hb.totalSales < 0 ? '↓' : '' }}</span>{{ hbText(hb.totalSales) }} 环比</div>
      </div>
      <div class="kpi-card troi">
        <div class="kpi-label">总 ROI</div><div class="kpi-value">{{ kpi.totalRoi.toFixed(2) }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.totalRoi)"><span class="arrow">{{ hb.totalRoi > 0 ? '↑' : hb.totalRoi < 0 ? '↓' : '' }}</span>{{ hb.totalRoi > 0 ? '+' : '' }}{{ hb.totalRoi.toFixed(2) }} 环比</div>
      </div>
      <div class="kpi-card click">
        <div class="kpi-label">总点击</div><div class="kpi-value">{{ kpi.clicks.toLocaleString() }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.clicks)"><span class="arrow">{{ hb.clicks > 0 ? '↑' : hb.clicks < 0 ? '↓' : '' }}</span>{{ hbText(hb.clicks) }} 环比</div>
      </div>
      <div class="kpi-card cvr">
        <div class="kpi-label">转化率</div><div class="kpi-value">{{ formatPercent(kpi.cvr) }}</div>
        <div v-if="hb" class="kpi-change" :class="changeClass(hb.cvr)"><span class="arrow">{{ hb.cvr > 0 ? '↑' : hb.cvr < 0 ? '↓' : '' }}</span>{{ hb.cvr > 0 ? '+' : '' }}{{ (hb.cvr * 100).toFixed(2) }}pp 环比</div>
      </div>
    </div>

    <!-- Actionable Summary -->
    <div class="summary-box">
      <div class="chart-title">推广诊断与优化建议</div>
      <div v-for="(line, i) in summaryLines" :key="i" class="summary-line" v-html="line"></div>
    </div>

    <!-- Subjects Table -->
    <div class="panel-table">
      <div class="chart-title">主体推广数据 ({{ displaySubjects.length }}条)</div>
      <div class="table-wrap"><table>
        <thead><tr>
          <th class="sortable" @click="toggleSort('subjectId')">主体ID<span :class="['sort-arrow',{active:sortField==='subjectId'}]">{{ sortArrow('subjectId') }}</span></th>
          <th class="sortable" @click="toggleSort('subjectName')">主体名称<span :class="['sort-arrow',{active:sortField==='subjectName'}]">{{ sortArrow('subjectName') }}</span></th>
          <th class="sortable" @click="toggleSort('subCategory')">细类<span :class="['sort-arrow',{active:sortField==='subCategory'}]">{{ sortArrow('subCategory') }}</span></th>
          <th class="num sortable" @click="toggleSort('cost')">花费<span :class="['sort-arrow',{active:sortField==='cost'}]">{{ sortArrow('cost') }}</span></th>
          <th class="num sortable" @click="toggleSort('totalSales')">总成交<span :class="['sort-arrow',{active:sortField==='totalSales'}]">{{ sortArrow('totalSales') }}</span></th>
          <th class="num sortable" @click="toggleSort('totalRoi')">总 ROI<span :class="['sort-arrow',{active:sortField==='totalRoi'}]">{{ sortArrow('totalRoi') }}</span></th>
          <th class="num sortable" @click="toggleSort('clicks')">点击<span :class="['sort-arrow',{active:sortField==='clicks'}]">{{ sortArrow('clicks') }}</span></th>
          <th class="num sortable" @click="toggleSort('impressions')">展现<span :class="['sort-arrow',{active:sortField==='impressions'}]">{{ sortArrow('impressions') }}</span></th>
        </tr></thead>
        <tbody>
          <template v-for="s in displaySubjects" :key="s.subjectId">
            <tr :class="roiRowClass(s)">
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
                    <div class="table-wrap"><table>
                      <thead><tr><th>计划名称</th><th class="num">花费</th><th class="num">总成交</th><th class="num">ROI</th><th class="num">点击</th><th class="num">展现</th></tr></thead>
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
                    </table></div>
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

const props = defineProps({ filtered: { type: Array, required: true }, prevFiltered: { type: Array, default: [] } });
const expandedId = ref(null);
const sortField = ref('cost');
const sortDir = ref('desc');

const kpi = computed(() => { const t = sumMetrics(props.filtered); return { cost: t.cost, totalSales: t.totalSales, totalRoi: t.totalRoi, clicks: t.clicks, cvr: t.cvr }; });
const prevKpi = computed(() => { if (!props.prevFiltered.length) return null; const t = sumMetrics(props.prevFiltered); return { cost: t.cost, totalSales: t.totalSales, totalRoi: t.totalRoi, clicks: t.clicks, cvr: t.cvr }; });

const hb = computed(() => {
  if (!prevKpi.value) return null;
  const t = kpi.value; const p = prevKpi.value;
  return {
    cost: p.cost ? (t.cost - p.cost) / p.cost * 100 : 0,
    totalSales: p.totalSales ? (t.totalSales - p.totalSales) / p.totalSales * 100 : 0,
    totalRoi: t.totalRoi - p.totalRoi,
    clicks: p.clicks ? (t.clicks - p.clicks) / p.clicks * 100 : 0,
    cvr: t.cvr - p.cvr,
  };
});
function changeClass(v) { if (v == null) return ''; return v > 0 ? 'up' : v < 0 ? 'down' : 'flat'; }
function hbText(v) { if (v == null) return ''; return (v > 0 ? '+' : '') + v.toFixed(1) + '%'; }

const displaySubjects = computed(() => {
  const cats = new Set(props.filtered.map(r => r.category));
  const allCats = cats.size >= payload.categories.length;
  let result = payload.subjects;
  if (!allCats && cats.size > 0) result = result.filter(s => cats.has(s.category));
  return result.map(s => ({ ...s, totalRoi: s.cost > 0 ? s.totalSales / s.cost : 0 }))
    .sort((a, b) => { const mul = sortDir.value === 'desc' ? -1 : 1; const va = a[sortField.value], vb = b[sortField.value]; return typeof va === 'string' ? (va||'').localeCompare(vb||'') * mul : ((va||0)-(vb||0)) * mul; })
    .slice(0, 100);
});

// Actionable summary for individual category analysis
const summaryLines = computed(() => {
  const rows = displaySubjects.value; const t = kpi.value; const p = prevKpi.value;
  const lines = []; if (rows.length === 0) { lines.push('当前筛选条件下暂无数据'); return lines; }

  let hbStr = '';
  if (p) {
    const h = hb.value;
    const c = h.cost > 0 ? `<span class="highlight-red">↑${h.cost.toFixed(1)}%</span>` : h.cost < 0 ? `<span class="highlight-green">↓${Math.abs(h.cost).toFixed(1)}%</span>` : '持平';
    const s = h.totalSales > 0 ? `<span class="highlight-green">↑${h.totalSales.toFixed(1)}%</span>` : h.totalSales < 0 ? `<span class="highlight-red">↓${Math.abs(h.totalSales).toFixed(1)}%</span>` : '持平';
    hbStr = `（花费 ${c}，成交 ${s} 环比）`;
  }
  lines.push(`📊 总花费 <strong>¥${formatMoney(t.cost)}</strong>，总成交 <strong>¥${formatMoney(t.totalSales)}</strong>，整体 ROI <span class="highlight-blue">${t.totalRoi.toFixed(2)}</span> ${hbStr}`);

  // 🔴 问题主体：花得多 ROI 低
  const problem = rows.filter(s => s.cost > 500 && s.totalRoi < 2);
  if (problem.length > 0) {
    lines.push(`<br><b>🔴 需紧急处理的问题主体（花费高 ROI 低）</b>`);
    problem.slice(0, 5).forEach(s => {
      lines.push(`&nbsp;&nbsp;• <strong>${s.subjectId}</strong>（${s.category}）花费 ¥${formatMoney(s.cost)}，ROI <span class="highlight-red">${s.totalRoi.toFixed(2)}</span>`);
      if (s.totalRoi < 0.5) lines.push(`&nbsp;&nbsp;&nbsp;&nbsp;→ <b>建议立即暂停</b>，该主体严重亏损`);
      else if (s.totalRoi < 1) lines.push(`&nbsp;&nbsp;&nbsp;&nbsp;→ <b>建议暂停或大幅降低出价</b>，优化关键词和人群定向`);
      else lines.push(`&nbsp;&nbsp;&nbsp;&nbsp;→ 建议<b>降低预算</b>，检查落地页转化率及素材质量`);
    });
  }

  // 🟢 优质主体：花得多 ROI 高
  const good = rows.filter(s => s.cost > 500 && s.totalRoi >= 3).sort((a, b) => b.totalRoi - a.totalRoi);
  if (good.length > 0) {
    lines.push(`<br><b>🟢 表现优异可加量主体</b>`);
    good.slice(0, 3).forEach(s => {
      lines.push(`&nbsp;&nbsp;• <strong>${s.subjectId}</strong>（${s.category}）ROI <span class="highlight-green">${s.totalRoi.toFixed(2)}</span>，花费 ¥${formatMoney(s.cost)} → 建议<b>保持策略，可适当增加 20-30% 预算</b>`);
    });
  }

  // 📊 场景分布分析
  const sceneAgg = {}; let sceneTotal = 0;
  for (const s of rows) {
    for (const sc of s.scenarios) {
      if (!sceneAgg[sc.scenario]) sceneAgg[sc.scenario] = 0;
      sceneAgg[sc.scenario] += sc.cost; sceneTotal += sc.cost;
    }
  }
  if (sceneTotal > 0) {
    const sceneTop = Object.entries(sceneAgg).sort((a, b) => b[1] - a[1]).slice(0, 3);
    const sceneStr = sceneTop.map(([name, cost]) => `${name}占 <b>${(cost / sceneTotal * 100).toFixed(0)}%</b>`).join('、');
    lines.push(`<br>📈 推广场景分布：${sceneStr}`);
  }

  // 整体建议
  const roiAvg = t.totalRoi;
  if (roiAvg < 2) lines.push(`<br>💡 整体 ROI <span class="highlight-red">${roiAvg.toFixed(2)}</span> 偏低，建议<b>减少低 ROI 商品投放</b>，将预算集中到高 ROI 商品上，同时优化创意素材和人群精准度`);
  else if (roiAvg < 3) lines.push(`<br>💡 整体 ROI <span class="highlight-blue">${roiAvg.toFixed(2)}</span> 处于中等水平，建议<b>稳步优化</b>，重点处理 ROI < 2 的商品，提升整体投放效率`);
  else lines.push(`<br>💡 整体 ROI <span class="highlight-green">${roiAvg.toFixed(2)}</span> 表现良好，建议<b>持续当前策略</b>，对优质商品适当增加预算以扩大收益`);

  return lines;
});

function toggleSort(field) { if (sortField.value === field) { sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'; } else { sortField.value = field; sortDir.value = 'desc'; } }
function sortArrow(field) { if (sortField.value !== field) return '↕'; return sortDir.value === 'desc' ? '↓' : '↑'; }
function truncateName(name) { return name && name.length > 30 ? name.slice(0, 30) + '...' : name; }
function roiRowClass(s) { return s.totalRoi < 0.5 ? 'row-danger' : s.totalRoi >= 3 ? 'row-good' : ''; }
function roiClass(v) { return v >= 3 ? "roi-good" : v < 1 ? "roi-risk" : ""; }

function getScenarioGroups(subject) {
  const groups = {};
  for (const sc of subject.scenarios) {
    const roi = sc.cost > 0 ? sc.totalSales / sc.cost : 0;
    if (!groups[sc.scenario]) groups[sc.scenario] = { scenario: sc.scenario, plans: [], cost: 0, totalSales: 0, clicks: 0, impressions: 0 };
    const g = groups[sc.scenario];
    g.plans.push({ ...sc, totalRoi: roi }); g.cost += sc.cost; g.totalSales += sc.totalSales; g.clicks += sc.clicks; g.impressions += sc.impressions;
  }
  return Object.values(groups).map(g => ({ ...g, cost: Math.round(g.cost * 100) / 100, totalSales: Math.round(g.totalSales * 100) / 100, roi: g.cost > 0 ? g.totalSales / g.cost : 0 }));
}

function toggleDetail(id) { expandedId.value = expandedId.value === id ? null : id; }
</script>
