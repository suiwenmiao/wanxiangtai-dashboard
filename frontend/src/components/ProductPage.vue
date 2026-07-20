<template>
  <div>
    <div class="kpi-row">
      <div class="kpi-card cost"><div class="kpi-label">总花费</div><div class="kpi-value">¥{{ formatMoney(kpi.cost) }}</div><div v-if="hb" class="kpi-change" :class="changeClass(hb.cost)"><span class="arrow">{{ hb.cost > 0 ? '↑' : hb.cost < 0 ? '↓' : '' }}</span>{{ hbText(hb.cost) }} 环比</div></div>
      <div class="kpi-card sales"><div class="kpi-label">总成交金额</div><div class="kpi-value">¥{{ formatMoney(kpi.totalSales) }}</div><div v-if="hb" class="kpi-change" :class="changeClass(hb.totalSales)"><span class="arrow">{{ hb.totalSales > 0 ? '↑' : hb.totalSales < 0 ? '↓' : '' }}</span>{{ hbText(hb.totalSales) }} 环比</div></div>
      <div class="kpi-card click"><div class="kpi-label">总点击量</div><div class="kpi-value">{{ kpi.clicks.toLocaleString() }}</div><div v-if="hb" class="kpi-change" :class="changeClass(hb.clicks)"><span class="arrow">{{ hb.clicks > 0 ? '↑' : hb.clicks < 0 ? '↓' : '' }}</span>{{ hbText(hb.clicks) }} 环比</div></div>
      <div class="kpi-card troi"><div class="kpi-label">总 ROI</div><div class="kpi-value">{{ kpi.totalRoi.toFixed(2) }}</div><div v-if="hb" class="kpi-change" :class="changeClass(hb.totalRoi)"><span class="arrow">{{ hb.totalRoi > 0 ? '↑' : hb.totalRoi < 0 ? '↓' : '' }}</span>{{ hb.totalRoi > 0 ? '+' : '' }}{{ hb.totalRoi.toFixed(2) }} 环比</div></div>
      <div class="kpi-card cpc"><div class="kpi-label">CPC</div><div class="kpi-value">¥{{ kpi.cpc.toFixed(2) }}</div><div v-if="hb" class="kpi-change" :class="changeClass(hb.cpc)"><span class="arrow">{{ hb.cpc > 0 ? '↑' : hb.cpc < 0 ? '↓' : '' }}</span>{{ hbText(hb.cpc) }} 环比</div></div>
      <div class="kpi-card cvr"><div class="kpi-label">转化率</div><div class="kpi-value">{{ formatPercent(kpi.cvr) }}</div><div v-if="hb" class="kpi-change" :class="changeClass(hb.cvr)"><span class="arrow">{{ hb.cvr > 0 ? '↑' : hb.cvr < 0 ? '↓' : '' }}</span>{{ hb.cvr > 0 ? '+' : '' }}{{ (hb.cvr * 100).toFixed(2) }}pp 环比</div></div>
    </div>

    <!-- Actionable Summary -->
    <div class="summary-box">
      <div class="chart-title">推广诊断与优化建议</div>
      <div v-for="(line, i) in summaryLines" :key="i" class="summary-line" v-html="line"></div>
    </div>

    <!-- Channel Summary -->
    <div class="panel-table">
      <div class="chart-title">渠道推广概览（按推广场景）</div>
      <div class="table-wrap"><table>
        <thead><tr>
          <th>推广场景</th>
          <th class="num">花费占比</th>
          <th class="num">花费</th>
          <th class="num">总成交金额</th>
          <th class="num">点击量</th>
          <th class="num">ROI</th>
          <th class="num">点击率</th>
          <th class="num">转化率</th>
          <th class="num">CPC</th>
        </tr></thead>
        <tbody>
          <tr v-for="sc in scenarioSummary" :key="sc.scenario">
            <td><strong>{{ sc.scenario }}</strong></td>
            <td class="num">{{ sc.costPct.toFixed(1) }}%</td>
            <td class="num">¥{{ formatMoney(sc.cost) }}<span v-if="sc.costHb != null" :class="['hb-inline', sc.costHb>0?'up':'down']">{{ sc.costHb>0?'+':'' }}{{ sc.costHb.toFixed(1) }}%</span></td>
            <td class="num">¥{{ sc.totalSales ? formatMoney(sc.totalSales) : '-' }}<span v-if="sc.totalSalesHb != null" :class="['hb-inline', sc.totalSalesHb>0?'up':'down']">{{ sc.totalSalesHb>0?'+':'' }}{{ sc.totalSalesHb.toFixed(1) }}%</span></td>
            <td class="num">{{ sc.clicks ? sc.clicks.toLocaleString() : '-' }}<span v-if="sc.clicksHb != null" :class="['hb-inline', sc.clicksHb>0?'up':'down']">{{ sc.clicksHb>0?'+':'' }}{{ sc.clicksHb.toFixed(1) }}%</span></td>
            <td :class="['num', roiClass(sc.roi)]">{{ sc.roi.toFixed(2) }}</td>
            <td class="num">{{ formatPercent(sc.ctr) }}<span v-if="sc.ctrHb != null" :class="['hb-inline', sc.ctrHb>0?'up':'down']">{{ sc.ctrHb>0?'+':'' }}{{ (sc.ctrHb*100).toFixed(2) }}pp</span></td>
            <td class="num">{{ formatPercent(sc.cvr) }}<span v-if="sc.cvrHb != null" :class="['hb-inline', sc.cvrHb>0?'up':'down']">{{ sc.cvrHb>0?'+':'' }}{{ (sc.cvrHb*100).toFixed(2) }}pp</span></td>
            <td class="num">¥{{ sc.cpc.toFixed(2) }}</td>
          </tr>
          <tr v-if="scenarioSummary.length === 0"><td colspan="9" class="empty">暂无数据</td></tr>
        </tbody>
      </table></div>
    </div>

    <!-- Subjects Table -->
    <div class="panel-table">
      <div class="chart-title">主体推广数据 ({{ displaySubjects.length }}条)</div>
      <div class="table-wrap"><table>
        <thead><tr>
          <th class="sortable" @click="toggleSort('subjectId')">主体ID<span :class="['sort-arrow',{active:sortField==='subjectId'}]">{{ sortArrow('subjectId') }}</span></th>
          <th class="sortable" @click="toggleSort('subjectName')">主体名称<span :class="['sort-arrow',{active:sortField==='subjectName'}]">{{ sortArrow('subjectName') }}</span></th>
          <th class="sortable" @click="toggleSort('subCategory')">细类<span :class="['sort-arrow',{active:sortField==='subCategory'}]">{{ sortArrow('subCategory') }}</span></th>
          <th class="num">展现量</th>
          <th class="num">点击量</th>
          <th class="num sortable" @click="toggleSort('cost')">花费<span :class="['sort-arrow',{active:sortField==='cost'}]">{{ sortArrow('cost') }}</span></th>
          <th class="num sortable" @click="toggleSort('totalSales')">总成交金额<span :class="['sort-arrow',{active:sortField==='totalSales'}]">{{ sortArrow('totalSales') }}</span></th>
          <th class="num">订单量</th>
          <th class="num">CPC</th>
          <th class="num">点击率</th>
          <th class="num">转化率</th>
          <th class="num sortable" @click="toggleSort('totalRoi')">ROI<span :class="['sort-arrow',{active:sortField==='totalRoi'}]">{{ sortArrow('totalRoi') }}</span></th>
        </tr></thead>
        <tbody>
          <template v-for="s in displaySubjects" :key="s.subjectId">
            <tr :class="roiRowClass(s)">
              <td class="subject-click" @click="toggleDetail(s.subjectId)">{{ s.subjectId }}</td>
              <td>{{ truncateName(s.subjectName) }}</td>
              <td>{{ s.subCategory }}</td>
              <td class="num">{{ s.impressions.toLocaleString() }}</td>
              <td class="num">{{ s.clicks.toLocaleString() }}</td>
              <td class="num">¥{{ formatMoney(s.cost) }}</td>
              <td class="num">¥{{ formatMoney(s.totalSales) }}</td>
              <td class="num">{{ s.orders.toLocaleString() }}</td>
              <td class="num">¥{{ s.clicks > 0 ? (s.cost / s.clicks).toFixed(2) : '0.00' }}</td>
              <td class="num">{{ formatPercent(s.impressions > 0 ? s.clicks / s.impressions : 0) }}</td>
              <td class="num">{{ formatPercent(s.clicks > 0 ? s.orders / s.clicks : 0) }}</td>
              <td :class="['num', roiClass(s.totalRoi)]">{{ s.totalRoi.toFixed(2) }}</td>
            </tr>
            <tr v-if="expandedId === s.subjectId" :key="'detail-'+s.subjectId">
              <td colspan="12" style="padding:0">
                <div class="subj-inline-detail">
                  <div v-for="group in getScenarioGroups(s)" :key="group.scenario" class="scenario-block">
                    <div class="scenario-header"><span>推广场景：{{ group.scenario }}</span><span class="summary">花费 ¥{{ formatMoney(group.cost) }} · 成交 ¥{{ formatMoney(group.totalSales) }} · ROI {{ group.roi.toFixed(2) }}</span></div>
                    <div class="table-wrap"><table>
                      <thead><tr><th>计划名称</th><th class="num">花费</th><th class="num">总成交金额</th><th class="num">ROI</th><th class="num">点击率</th><th class="num">转化率</th><th class="num">CPC</th></tr></thead>
                      <tbody>
                        <tr v-for="(p, i) in group.plans" :key="i">
                          <td>{{ p.planName }}</td>
                          <td class="num">¥{{ formatMoney(p.cost) }}</td>
                          <td class="num">¥{{ formatMoney(p.totalSales) }}</td>
                          <td :class="['num', roiClass(p.totalRoi)]">{{ p.totalRoi.toFixed(2) }}</td>
                          <td class="num">{{ formatPercent(p.impressions > 0 ? p.clicks / p.impressions : 0) }}</td>
                          <td class="num">{{ formatPercent(p.clicks > 0 ? p.orders / p.clicks : 0) }}</td>
                          <td class="num">¥{{ p.clicks > 0 ? (p.cost / p.clicks).toFixed(2) : '0.00' }}</td>
                        </tr>
                      </tbody>
                    </table></div>
                  </div>
                </div>
              </td>
            </tr>
          </template>
          <tr v-if="displaySubjects.length === 0"><td colspan="12" class="empty">暂无数据</td></tr>
        </tbody>
      </table></div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { formatMoney, formatPercent, sumMetrics } from "../utils/metrics";

const props = defineProps({ payload: { type: Object, required: true }, filtered: { type: Array, required: true }, prevFiltered: { type: Array, default: [] } });
const expandedId = ref(null);
const sortField = ref('cost');
const sortDir = ref('desc');

const kpi = computed(() => { const t = sumMetrics(props.filtered); const cpc = t.clicks > 0 ? t.cost / t.clicks : 0; return { cost: t.cost, totalSales: t.totalSales, totalRoi: t.totalRoi, clicks: t.clicks, cvr: t.cvr, cpc }; });
const prevKpi = computed(() => { if (!props.prevFiltered.length) return null; const t = sumMetrics(props.prevFiltered); const cpc = t.clicks > 0 ? t.cost / t.clicks : 0; return { cost: t.cost, totalSales: t.totalSales, totalRoi: t.totalRoi, clicks: t.clicks, cvr: t.cvr, cpc }; });

const hb = computed(() => {
  if (!prevKpi.value) return null;
  const t = kpi.value; const p = prevKpi.value;
  return {
    cost: p.cost ? (t.cost - p.cost) / p.cost * 100 : 0,
    totalSales: p.totalSales ? (t.totalSales - p.totalSales) / p.totalSales * 100 : 0,
    totalRoi: t.totalRoi - p.totalRoi,
    clicks: p.clicks ? (t.clicks - p.clicks) / p.clicks * 100 : 0,
    cvr: t.cvr - p.cvr,
    cpc: p.cpc > 0 ? (t.cpc - p.cpc) / p.cpc * 100 : 0,
  };
});
function changeClass(v) { if (v == null) return ''; return v > 0 ? 'up' : v < 0 ? 'down' : 'flat'; }
function hbText(v) { if (v == null) return ''; return (v > 0 ? '+' : '') + v.toFixed(1) + '%'; }

// Channel scenario summary — estimate date-filtered metrics from subjects' full-period scenario proportions
const scenarioSummary = computed(() => {
  const dates = new Set(props.filtered.map(r => r.date));
  const allDates = dates.size >= props.payload.records.length;
  const cats = new Set(props.filtered.map(r => r.category));
  const isAllCats = cats.size >= props.payload.categories.length;
  function aggregate(records) {
    const agg = {};
    for (const r of records) {
      if (!r.scenario) continue;
      if (!agg[r.scenario]) agg[r.scenario] = { scenario: r.scenario, cost: 0, totalSales: 0, clicks: 0, impressions: 0, orders: 0 };
      const a = agg[r.scenario];
      a.cost += r.cost;
      a.totalSales += r.totalSales;
      a.clicks += r.clicks;
      a.impressions += r.impressions;
      a.orders += r.orders;
    }
    const totalCost = Object.values(agg).reduce((s, a) => s + a.cost, 0);
    return Object.values(agg).map(a => ({
      scenario: a.scenario,
      cost: Math.round(a.cost * 100) / 100,
      totalSales: Math.round(a.totalSales * 100) / 100,
      clicks: Math.round(a.clicks),
      costPct: totalCost > 0 ? a.cost / totalCost * 100 : 0,
      roi: a.cost > 0 ? a.totalSales / a.cost : 0,
      cvr: a.clicks > 0 ? a.orders / a.clicks : 0,
      ctr: a.impressions > 0 ? a.clicks / a.impressions : 0,
      cpc: a.clicks > 0 ? a.cost / a.clicks : 0,
    })).sort((a, b) => b.cost - a.cost);
  }
  let curRecs = props.payload.categoryScenarioRecords;
  if (!isAllCats && cats.size > 0) curRecs = curRecs.filter(r => cats.has(r.category));
  if (!allDates && dates.size > 0) curRecs = curRecs.filter(r => dates.has(r.date));
  const current = aggregate(curRecs);
  let prevRecs = props.prevFiltered.length ? [...props.payload.categoryScenarioRecords] : [];
  if (prevRecs.length) {
    const prevDates = new Set(props.prevFiltered.map(r => r.date));
    if (!isAllCats && cats.size > 0) prevRecs = prevRecs.filter(r => cats.has(r.category));
    if (prevDates.size > 0) prevRecs = prevRecs.filter(r => prevDates.has(r.date));
  }
  const prev = prevRecs.length ? aggregate(prevRecs) : [];
  const pm = {}; for (const p of prev) pm[p.scenario] = p;
  return current.map(c => {
    const p = pm[c.scenario];
    return { ...c, costHb: p ? (p.cost > 0 ? (c.cost - p.cost) / p.cost * 100 : 0) : null, totalSalesHb: p ? (p.totalSales > 0 ? (c.totalSales - p.totalSales) / p.totalSales * 100 : 0) : null, clicksHb: p ? (p.clicks > 0 ? (c.clicks - p.clicks) / p.clicks * 100 : 0) : null, ctrHb: p ? c.ctr - p.ctr : null, cvrHb: p ? c.cvr - p.cvr : null };
  });
});
const displaySubjects = computed(() => {
  // Compute from date-filtered records + subjectDateRecords
  const dates = new Set(props.filtered.map(r => r.date));
  const cats = new Set(props.filtered.map(r => r.category));
  const allCats = cats.size >= props.payload.categories.length;
  const isFullRange = dates.size >= props.payload.records.length;

  // Build subject metadata lookup
  const metaMap = {};
  for (const s of props.payload.subjects) metaMap[s.subjectId] = s;

  // If full date range, use cached subjects (much faster)
  if (isFullRange || dates.size === 0 || !props.payload.subjectDateRecords) {
    let result = props.payload.subjects;
    if (!allCats && cats.size > 0) result = result.filter(s => cats.has(s.category));
    return result.map(s => ({ ...s, totalRoi: s.cost > 0 ? s.totalSales / s.cost : 0 }))
      .sort((a, b) => { const mul = sortDir.value==='desc'?-1:1; const va=a[sortField.value],vb=b[sortField.value]; return typeof va==='string'?(va||'').localeCompare(vb||'')*mul:((va||0)-(vb||0))*mul; })
      .slice(0, 100);
  }

  // Filter subjectDateRecords by selected dates
  let sdr = props.payload.subjectDateRecords.filter(r => dates.has(r.date));
  // Aggregate by subjectId
  const agg = {};
  for (const r of sdr) {
    if (!agg[r.subjectId]) agg[r.subjectId] = { cost:0, totalSales:0, clicks:0, impressions:0, orders:0 };
    const a = agg[r.subjectId]; a.cost += r.cost; a.totalSales += r.totalSales; a.clicks += r.clicks; a.impressions += r.impressions; a.orders += r.orders;
  }
  // Build result with metadata, filter by category
  let result = Object.entries(agg).map(([sid, m]) => {
    const meta = metaMap[sid]; if (!meta) return null;
    if (!allCats && cats.size > 0 && !cats.has(meta.category)) return null;
    return { ...meta, cost:Math.round(m.cost*100)/100, totalSales:Math.round(m.totalSales*100)/100, clicks:m.clicks, impressions:m.impressions, orders:m.orders || 0, totalRoi:m.cost>0?m.totalSales/m.cost:0 };
  }).filter(Boolean);

  return result.sort((a, b) => { const mul=sortDir.value==='desc'?-1:1; const va=a[sortField.value],vb=b[sortField.value]; return typeof va==='string'?(va||'').localeCompare(vb||'')*mul:((va||0)-(vb||0))*mul; }).slice(0, 100);
});

// Category-specific ROI thresholds per industry experience
const THRESHOLDS = {
  'DT':  { good: 61, ok: 31, warn: 12 },   // 台式机: P50/P25/P10 历史数据
  'NB':  { good: 57, ok: 28, warn: 11 },   // 笔记本: 同级别
  '手机': { good: 10, ok: 3, warn: 1.5 },  // 手机: 整体ROI 15.81
  '平板': { good: 30, ok: 15, warn: 3 },   // 平板: 整体ROI 37.84
  '显示器': { good: 19, ok: 10, warn: 3 },  // 显示器: 整体ROI 32.07
  '服务': { good: 4, ok: 3, warn: 1.8 },   // 服务: 整体ROI 6.61，低客单高频
  '选件': { good: 19, ok: 9, warn: 3 },    // 选件: 整体ROI 22.64
  'IP':  { good: 6, ok: 2, warn: 0.8 },    // 平板配件: 整体ROI 9.79
  'SIOT': { good: 6, ok: 2, warn: 0.8 },
  '其他': { good: 6, ok: 2, warn: 0.8 },
};
function getT(cat) { return THRESHOLDS[cat] || THRESHOLDS['其他']; }

// Actionable summary with category-specific thresholds
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

  // Categorize subjects by category-specific thresholds
  const crit = [], lowEff = [], goodList = [];
  for (const s of rows) {
    if (s.cost < 200) continue;
    const thr = getT(s.category);
    if (s.totalRoi >= thr.good) goodList.push(s);
    else if (s.totalRoi >= thr.ok) { /* normal - no action needed */ }
    else if (s.totalRoi >= thr.warn) lowEff.push(s);
    else crit.push(s);
  }

  // 🔴 Critical: below warn threshold
  if (crit.length > 0) {
    lines.push(`<br><b>🔴 需紧急处理（ROI 低于品类警戒线，共 ${crit.length} 条）</b>`);
    crit.sort((a,b) => b.cost - a.cost).slice(0, 6).forEach(s => {
      const thr = getT(s.category);
      lines.push(`&nbsp;&nbsp;• <strong>${s.subjectId}</strong>（${s.category}）花费 ¥${formatMoney(s.cost)}，ROI <span class="highlight-red">${s.totalRoi.toFixed(2)}</span>（品类警戒线 ${thr.warn}）`);
      if (s.totalRoi < thr.warn * 0.4) lines.push(`&nbsp;&nbsp;&nbsp;&nbsp;→ <b>建议立即暂停</b>，严重低于品类标准`);
      else if (s.totalRoi < thr.warn * 0.7) lines.push(`&nbsp;&nbsp;&nbsp;&nbsp;→ <b>建议暂停或大幅降价</b>，优化人群与关键词`);
      else lines.push(`&nbsp;&nbsp;&nbsp;&nbsp;→ 建议<b>降低预算</b>，检查转化及素材质量`);
    });
  }

  // 🟡 Low efficiency: below ok line, above warn
  if (lowEff.length > 0) {
    lines.push(`<br><b>🟡 效率偏低需关注（ROI 低于品类及格线，共 ${lowEff.length} 条）</b>`);
    lowEff.sort((a,b) => b.cost - a.cost).slice(0, 6).forEach(s => {
      const thr = getT(s.category);
      lines.push(`&nbsp;&nbsp;• <strong>${s.subjectId}</strong>（${s.category}）ROI <span style="color:#e67e22">${s.totalRoi.toFixed(2)}</span>，品类及格线 ${thr.ok}，花费 ¥${formatMoney(s.cost)} → 建议<b>优化出价和定向</b>，观察 3-5 天无改善则降低预算`);
    });
  }

  // 🟢 Good performers
  if (goodList.length > 0) {
    lines.push(`<br><b>🟢 表现优异可加量主体（ROI 高于品类优秀线，共 ${goodList.length} 条）</b>`);
    goodList.sort((a,b) => b.totalRoi - a.totalRoi).slice(0, 4).forEach(s => {
      lines.push(`&nbsp;&nbsp;• <strong>${s.subjectId}</strong>（${s.category}）ROI <span class="highlight-green">${s.totalRoi.toFixed(2)}</span>，花费 ¥${formatMoney(s.cost)} → 建议<b>保持策略，可增加 20-30% 预算</b>`);
    });
  }

  // 📊 场景分布：与下方“渠道推广概览（按推广场景）”使用同一批日期/品类筛选后的数据。
  const topScenes = scenarioSummary.value.slice(0, 3);
  if (topScenes.length > 0) {
    lines.push(`<br>📈 推广场景分布：${topScenes.map(sc => `${sc.scenario}占 <b>${sc.costPct.toFixed(1)}%</b>`).join('、')}`);
  }

  // 💡 Overall advice
  const roiAvg = t.totalRoi;
  if (roiAvg < 2) lines.push(`<br>💡 整体 ROI <span class="highlight-red">${roiAvg.toFixed(2)}</span> 偏低，建议<b>暂停低 ROI 商品</b>，预算集中到高 ROI 商品上，同时优化素材和人群精准度`);
  else if (roiAvg < 3) lines.push(`<br>💡 整体 ROI <span class="highlight-blue">${roiAvg.toFixed(2)}</span> 处于中等水平，建议<b>稳步优化</b>，重点处理低效商品，提升整体投放效率`);
  else lines.push(`<br>💡 整体 ROI <span class="highlight-green">${roiAvg.toFixed(2)}</span> 表现良好，建议<b>持续当前策略</b>，优质商品适当增加预算`);

  return lines;
});

function toggleSort(field) { if (sortField.value === field) { sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'; } else { sortField.value = field; sortDir.value = 'desc'; } }
function sortArrow(field) { if (sortField.value !== field) return '↕'; return sortDir.value === 'desc' ? '↓' : '↑'; }
function truncateName(name) { return name && name.length > 30 ? name.slice(0, 30) + '...' : name; }
function roiRowClass(s) { return s.totalRoi < 0.5 ? 'row-danger' : s.totalRoi >= 3 ? 'row-good' : ''; }
function roiClass(v) { return v >= 3 ? "roi-good" : v < 1 ? "roi-risk" : ""; }

function getScenarioGroups(subject) {
  // Filter subjectPlanRecords by subjectId and selected dates
  const dates = new Set(props.filtered.map(r => r.date));
  const allDates = dates.size >= props.payload.records.length;
  let records = props.payload.subjectPlanRecords.filter(r => r.subjectId === subject.subjectId);
  if (!allDates && dates.size > 0) {
    records = records.filter(r => dates.has(r.date));
  }
  if (records.length === 0) return [];
  // Aggregate by planId (unique across scenarios)
  const planMap = {};
  for (const r of records) {
    if (!planMap[r.planId]) {
      planMap[r.planId] = { scenario: r.scenario, planName: r.planName, cost: 0, totalSales: 0, clicks: 0, impressions: 0, orders: 0 };
    }
    const p = planMap[r.planId];
    p.cost += r.cost;
    p.totalSales += r.totalSales;
    p.clicks += r.clicks;
    p.impressions += r.impressions;
    p.orders += r.orders;
  }
  // Group by scenario
  const groups = {};
  for (const plan of Object.values(planMap)) {
    if (!groups[plan.scenario]) {
      groups[plan.scenario] = { scenario: plan.scenario, plans: [], cost: 0, totalSales: 0, clicks: 0, impressions: 0 };
    }
    const g = groups[plan.scenario];
    const pd = {
      scenario: plan.scenario, planName: plan.planName,
      cost: Math.round(plan.cost * 100) / 100,
      totalSales: Math.round(plan.totalSales * 100) / 100,
      clicks: Math.round(plan.clicks), impressions: Math.round(plan.impressions),
      orders: Math.round(plan.orders),
      totalRoi: plan.cost > 0 ? plan.totalSales / plan.cost : 0,
    };
    g.plans.push(pd);
    g.cost += pd.cost; g.totalSales += pd.totalSales; g.clicks += pd.clicks; g.impressions += pd.impressions;
  }
  return Object.values(groups).map(g => ({
    ...g, cost: Math.round(g.cost * 100) / 100,
    totalSales: Math.round(g.totalSales * 100) / 100,
    roi: g.cost > 0 ? g.totalSales / g.cost : 0,
  }));
}

function toggleDetail(id) { expandedId.value = expandedId.value === id ? null : id; }
</script>
