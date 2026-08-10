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
      <div class="chart-title">推广诊断与优化建议（近 7 日滚动）</div>
      <div v-for="(line, i) in summaryLines" :key="i" class="summary-line" v-html="line"></div>
    </div>

    <section class="plan-action-board" aria-label="计划行动看板">
      <div class="chart-title">计划行动看板（近 7 日滚动）</div>
      <div v-if="planDataLoading" class="plan-action-loading">正在汇总计划表现...</div>
      <div v-else-if="planDataError" class="plan-action-loading">{{ planDataError }}</div>
      <div v-else class="plan-action-grid">
        <div v-for="group in planActionGroups" :key="group.key" :class="['plan-action-group', group.tone]">
          <div class="plan-action-group-head"><span>{{ group.title }}</span><strong>{{ group.items.length }} 个</strong></div>
          <button v-for="item in group.items.slice(0, 5)" :key="item.key" class="plan-action-item" type="button" @click="openPlanAction(item)" :title="item.advice.reason">
            <span class="plan-action-name">{{ item.subjectId }} · {{ item.planName }}</span>
            <span class="plan-action-metrics">ROI {{ item.roi.toFixed(2) }} · ¥{{ formatMoney(item.cost) }}</span>
          </button>
          <div v-if="group.items.length > 5" class="plan-action-more">另有 {{ group.items.length - 5 }} 个计划，请在下方主体明细查看</div>
          <div v-if="group.items.length === 0" class="plan-action-empty">暂无计划</div>
        </div>
      </div>
    </section>

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
          <th class="num">加购率</th>
          <th class="num sortable" @click="toggleSort('totalRoi')">ROI<span :class="['sort-arrow',{active:sortField==='totalRoi'}]">{{ sortArrow('totalRoi') }}</span></th>
          <th>AI 建议（近 7 日）</th>
        </tr></thead>
        <tbody>
          <template v-for="s in displaySubjects" :key="s.subjectId">
            <tr :id="subjectRowId(s.subjectId)" :class="roiRowClass(s)">
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
              <td class="num">{{ formatPercent(s.clicks > 0 ? s.carts / s.clicks : 0) }}</td>
              <td :class="['num', roiClass(s.totalRoi)]">{{ s.totalRoi.toFixed(2) }}</td>
              <td><span :class="['plan-advice', subjectAdvice(s).tone]" :title="subjectAdvice(s).reason">{{ subjectAdvice(s).label }}</span></td>
            </tr>
            <tr v-if="expandedId === s.subjectId" :key="'detail-'+s.subjectId">
              <td colspan="14" style="padding:0">
                <div class="subj-inline-detail">
                  <div v-if="planDataLoading" class="empty">正在加载计划明细...</div>
                  <div v-else-if="planDataError" class="empty">{{ planDataError }}</div>
                  <template v-else>
                    <div v-for="group in getScenarioGroups(s)" :key="group.scenario" class="scenario-block">
                      <div class="scenario-header"><span>推广场景：{{ group.scenario }}</span><span class="summary">花费 ¥{{ formatMoney(group.cost) }} · 成交 ¥{{ formatMoney(group.totalSales) }} · ROI {{ group.roi.toFixed(2) }}</span></div>
                      <div class="table-wrap"><table>
                        <thead><tr><th>计划名称</th><th class="num">花费</th><th class="num">总成交金额</th><th class="num">ROI</th><th class="num">点击率</th><th class="num">转化率</th><th class="num">加购率</th><th class="num">CPC</th><th>AI 建议（近 7 日）</th></tr></thead>
                        <tbody>
                          <tr v-for="(p, i) in group.plans" :key="i" :class="{ 'plan-focus': p.planId === activePlanId }">
                            <td>{{ p.planName }}</td>
                            <td class="num">¥{{ formatMoney(p.cost) }}</td>
                            <td class="num">¥{{ formatMoney(p.totalSales) }}</td>
                            <td :class="['num', roiClass(p.totalRoi)]">{{ p.totalRoi.toFixed(2) }}</td>
                            <td class="num">{{ formatPercent(p.impressions > 0 ? p.clicks / p.impressions : 0) }}</td>
                            <td class="num">{{ formatPercent(p.clicks > 0 ? p.orders / p.clicks : 0) }}</td>
                            <td class="num">{{ formatPercent(p.clicks > 0 ? p.carts / p.clicks : 0) }}</td>
                            <td class="num">¥{{ p.clicks > 0 ? (p.cost / p.clicks).toFixed(2) : '0.00' }}</td>
                            <td><span :class="['plan-advice', p.advice.tone]" :title="p.advice.reason">{{ p.advice.label }}</span></td>
                          </tr>
                        </tbody>
                      </table></div>
                    </div>
                  </template>
                </div>
              </td>
            </tr>
          </template>
          <tr v-if="displaySubjects.length === 0"><td colspan="14" class="empty">暂无数据</td></tr>
        </tbody>
      </table></div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { formatMoney, formatPercent, sumMetrics } from "../utils/metrics";

const props = defineProps({ payload: { type: Object, required: true }, filtered: { type: Array, required: true }, prevFiltered: { type: Array, default: [] }, cryptoKey: { type: CryptoKey, required: true } });
const expandedId = ref(null);
const planRecords = ref(null);
const planDataLoading = ref(false);
const planDataError = ref("");
const activePlanId = ref(null);
const sortField = ref('cost');
const sortDir = ref('desc');
const selectedDates = computed(() => new Set(props.filtered.map(r => r.date)));
const subjectMeta = computed(() => new Map(props.payload.subjects.map(subject => [String(subject.subjectId), subject])));

const planBenchmarks = computed(() => {
  const sums = new Map();
  for (const row of planRecords.value || []) {
    if (!adviceWindows.value.current.has(row.date)) continue;
    const subject = subjectMeta.value.get(String(row.subjectId));
    if (!subject) continue;
    const key = `${subject.category}|${row.scenario || '未分类'}`;
    const value = sums.get(key) || emptyMetric();
    addMetric(value, row); value.days.add(row.date);
    sums.set(key, value);
  }
  return sums;
});

const planActionGroups = computed(() => {
  const categories = new Set(props.filtered.map(row => row.category));
  const current = new Map();
  const previous = new Map();
  const metadata = new Map();
  for (const row of planRecords.value || []) {
    const subject = subjectMeta.value.get(String(row.subjectId));
    if (!subject || (categories.size && !categories.has(subject.category))) continue;
    const key = `${row.subjectId}|${row.planId}`;
    metadata.set(key, { subjectId: row.subjectId, planId: row.planId, planName: row.planName, scenario: row.scenario || '未分类', category: subject.category });
    const target = adviceWindows.value.current.has(row.date) ? current : adviceWindows.value.previous.has(row.date) ? previous : null;
    if (!target) continue;
    const metric = target.get(key) || emptyMetric();
    addMetric(metric, row); metric.days.add(row.date);
    target.set(key, metric);
  }
  const groups = {
    urgent: { key: 'urgent', title: '急需调整', tone: 'urgent', items: [] },
    optimize: { key: 'optimize', title: '重点优化', tone: 'optimize', items: [] },
    grow: { key: 'grow', title: '优质可加投', tone: 'grow', items: [] },
    observe: { key: 'observe', title: '维持观察', tone: 'observe', items: [] },
  };
  for (const [key, info] of metadata) {
    const now = current.get(key) || emptyMetric();
    if (!now.days.size) continue;
    const benchmark = planBenchmarks.value.get(`${info.category}|${info.scenario}`) || emptyMetric();
    const advice = planAdvice(now, previous.get(key) || emptyMetric(), benchmark);
    const bucket = advice.tone === 'stop' || advice.tone === 'reduce' ? 'urgent' : advice.tone === 'optimize' ? 'optimize' : advice.tone === 'grow' ? 'grow' : 'observe';
    groups[bucket].items.push({ ...info, key, advice, cost: now.cost, roi: metricRoi(now) });
  }
  for (const group of Object.values(groups)) group.items.sort((a, b) => b.cost - a.cost);
  return Object.values(groups);
});

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
    const sorted = result.map(s => ({ ...s, totalRoi: s.cost > 0 ? s.totalSales / s.cost : 0 }))
      .sort((a, b) => { const mul = sortDir.value==='desc'?-1:1; const va=a[sortField.value],vb=b[sortField.value]; return typeof va==='string'?(va||'').localeCompare(vb||'')*mul:((va||0)-(vb||0))*mul; });
    return sorted;
  }

  // Filter subjectDateRecords by selected dates
  let sdr = props.payload.subjectDateRecords.filter(r => dates.has(r.date));
  // Aggregate by subjectId
  const agg = {};
  for (const r of sdr) {
    if (!agg[r.subjectId]) agg[r.subjectId] = { cost:0, totalSales:0, clicks:0, impressions:0, orders:0, carts:0 };
    const a = agg[r.subjectId]; a.cost += r.cost; a.totalSales += r.totalSales; a.clicks += r.clicks; a.impressions += r.impressions; a.orders += r.orders; a.carts += r.carts || 0;
  }
  // Build result with metadata, filter by category
  let result = Object.entries(agg).map(([sid, m]) => {
    const meta = metaMap[sid]; if (!meta) return null;
    if (!allCats && cats.size > 0 && !cats.has(meta.category)) return null;
    return { ...meta, cost:Math.round(m.cost*100)/100, totalSales:Math.round(m.totalSales*100)/100, clicks:m.clicks, impressions:m.impressions, orders:m.orders || 0, carts:m.carts || 0, totalRoi:m.cost>0?m.totalSales/m.cost:0 };
  }).filter(Boolean);

  const sorted = result.sort((a, b) => { const mul=sortDir.value==='desc'?-1:1; const va=a[sortField.value],vb=b[sortField.value]; return typeof va==='string'?(va||'').localeCompare(vb||'')*mul:((va||0)-(vb||0))*mul; });
  return sorted;
});

const adviceWindows = computed(() => {
  const end = [...selectedDates.value].sort().at(-1);
  if (!end) return { current: new Set(), previous: new Set() };
  return { current: dateWindow(end, 7, 0), previous: dateWindow(end, 7, 7) };
});

const subjectAdviceWindows = computed(() => {
  const map = new Map();
  for (const row of props.payload.subjectDateRecords || []) {
    const period = adviceWindows.value.current.has(row.date) ? "current" : adviceWindows.value.previous.has(row.date) ? "previous" : null;
    if (!period) continue;
    const entry = map.get(String(row.subjectId)) || { current: emptyMetric(), previous: emptyMetric() };
    addMetric(entry[period], row);
    entry[period].days.add(row.date);
    map.set(String(row.subjectId), entry);
  }
  return map;
});

const subjectBenchmarks = computed(() => {
  const sums = new Map();
  for (const [subjectId, window] of subjectAdviceWindows.value) {
    const subject = subjectMeta.value.get(subjectId);
    if (!subject) continue;
    const value = sums.get(subject.category) || emptyMetric();
    mergeMetric(value, window.current);
    sums.set(subject.category, value);
  }
  return sums;
});

function subjectAdvice(subject) {
  const window = subjectAdviceWindows.value.get(String(subject.subjectId));
  const current = window?.current || emptyMetric();
  const previous = window?.previous || emptyMetric();
  const benchmark = subjectBenchmarks.value.get(subject.category) || emptyMetric();
  return recommendation(current, previous, benchmark, "品类");
}

// Actionable summary: all budget actions use the rolling 7-day evaluator.
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

  // All action recommendations use the rolling 7-day evaluator, not one-day values.
  const crit = [], lowEff = [], goodList = [];
  for (const s of rows) {
    const advice = subjectAdvice(s);
    if (advice.tone === 'grow') goodList.push({ ...s, advice });
    else if (advice.tone === 'reduce' || advice.tone === 'stop') crit.push({ ...s, advice });
    else if (advice.tone === 'optimize') lowEff.push({ ...s, advice });
  }

  // 🔴 Critical: below warn threshold
  if (crit.length > 0) {
    lines.push(`<br><b>🔴 近7日建议减投/暂停（共 ${crit.length} 条）</b>`);
    crit.sort((a,b) => b.cost - a.cost).slice(0, 6).forEach(s => {
      const cpc = s.clicks ? s.cost / s.clicks : 0; const cartRate = s.clicks ? (s.carts || 0) / s.clicks : 0;
      lines.push(`&nbsp;&nbsp;• <strong>${s.subjectId}</strong>（${s.category}）ROI <span class="highlight-red">${s.totalRoi.toFixed(2)}</span>，CPC ¥${cpc.toFixed(2)}，加购率 ${formatPercent(cartRate)} → <b>${s.advice.label}</b>：${s.advice.reason}`);
    });
  }

  // 🟡 Low efficiency: below ok line, above warn
  if (lowEff.length > 0) {
    lines.push(`<br><b>🟡 近7日需要优化（共 ${lowEff.length} 条）</b>`);
    lowEff.sort((a,b) => b.cost - a.cost).slice(0, 6).forEach(s => {
      lines.push(`&nbsp;&nbsp;• <strong>${s.subjectId}</strong>（${s.category}）→ <b>${s.advice.label}</b>：${s.advice.reason}`);
    });
  }

  // 🟢 Good performers
  if (goodList.length > 0) {
    lines.push(`<br><b>🟢 近7日优质主体，可分步加投（共 ${goodList.length} 条）</b>`);
    goodList.sort((a,b) => b.totalRoi - a.totalRoi).slice(0, 4).forEach(s => {
      lines.push(`&nbsp;&nbsp;• <strong>${s.subjectId}</strong>（${s.category}）→ <b>${s.advice.label}</b>：${s.advice.reason}`);
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
  const subjectRecords = (planRecords.value || []).filter(r => r.subjectId === subject.subjectId);
  const records = selectedDates.value.size ? subjectRecords.filter(r => selectedDates.value.has(r.date)) : subjectRecords;
  const adviceCurrentPlans = aggregatePlanWindow(subjectRecords, adviceWindows.value.current);
  const advicePreviousPlans = aggregatePlanWindow(subjectRecords, adviceWindows.value.previous);
  if (records.length === 0) return [];
  const planMap = {};
  for (const r of records) {
    if (!planMap[r.planId]) {
      planMap[r.planId] = { scenario: r.scenario, planName: r.planName, cost: 0, totalSales: 0, clicks: 0, impressions: 0, orders: 0, carts: 0 };
    }
    const p = planMap[r.planId];
    p.cost += r.cost;
    p.totalSales += r.totalSales;
    p.clicks += r.clicks;
    p.impressions += r.impressions;
    p.orders += r.orders;
    p.carts += r.carts || 0;
  }
  // Group by scenario
  const groups = {};
  for (const [planId, plan] of Object.entries(planMap)) {
    if (!groups[plan.scenario]) {
      groups[plan.scenario] = { scenario: plan.scenario, plans: [], cost: 0, totalSales: 0, clicks: 0, impressions: 0 };
    }
    const g = groups[plan.scenario];
    const pd = {
      planId, scenario: plan.scenario, planName: plan.planName,
      cost: Math.round(plan.cost * 100) / 100,
      totalSales: Math.round(plan.totalSales * 100) / 100,
      clicks: Math.round(plan.clicks), impressions: Math.round(plan.impressions),
      orders: Math.round(plan.orders),
      carts: Math.round(plan.carts),
      totalRoi: plan.cost > 0 ? plan.totalSales / plan.cost : 0,
    };
    const benchmark = planBenchmarks.value.get(`${subject.category}|${plan.scenario}`);
    pd.advice = planAdvice(adviceCurrentPlans.get(planId) || emptyMetric(), advicePreviousPlans.get(planId) || emptyMetric(), benchmark);
    g.plans.push(pd);
    g.cost += pd.cost; g.totalSales += pd.totalSales; g.clicks += pd.clicks; g.impressions += pd.impressions;
  }
  return Object.values(groups).map(g => ({
    ...g, cost: Math.round(g.cost * 100) / 100,
    totalSales: Math.round(g.totalSales * 100) / 100,
    roi: g.cost > 0 ? g.totalSales / g.cost : 0,
  }));
}

function planAdvice(current, previous, benchmark) { return recommendation(current, previous, benchmark, "同场景"); }

function recommendation(current, previous, benchmark, scope) {
  const roi = metricRoi(current), cpc = metricCpc(current), cvr = metricCvr(current), cartRate = metricCartRate(current);
  const refRoi = metricRoi(benchmark), refCpc = metricCpc(benchmark), refCvr = metricCvr(benchmark), refCartRate = metricCartRate(benchmark);
  const previousRoi = metricRoi(previous);
  const enoughSample = current.days.size >= 4 && current.cost >= 500 && current.clicks >= 100;
  const trendDown = previous.cost >= 300 && previousRoi > 0 && roi < previousRoi * 0.8;
  const trendUp = previous.cost >= 300 && previousRoi > 0 && roi >= previousRoi * 0.9;
  const sampleText = `近7日投放 ${current.days.size} 天、花费 ¥${formatMoney(current.cost)}、点击 ${Math.round(current.clicks).toLocaleString()}`;

  if (!enoughSample) return { label: "观察样本", tone: "neutral", reason: `${sampleText}，未达到连续 4 天、¥500、100 点击的预算动作门槛。` };
  if (current.orders === 0 && current.clicks >= 100 && refCartRate > 0 && cartRate < refCartRate * 0.6) {
    return { label: "建议暂停/换素材", tone: "stop", reason: `${sampleText}；有点击无成交且加购率显著低于${scope}均值。` };
  }
  if (refRoi > 0 && roi >= refRoi * 1.15 && (!refCpc || cpc <= refCpc * 1.1) && (!refCartRate || cartRate >= refCartRate * 0.9) && (!previous.cost || trendUp)) {
    return { label: "建议加投", tone: "grow", reason: `${sampleText}；ROI、CPC、加购率均优于${scope}均值，且较前7日未走弱，可分步上调 10-20%。` };
  }
  if (refRoi > 0 && roi < refRoi * 0.65 && current.cost >= 800 && (trendDown || (previous.cost >= 300 && previousRoi < refRoi * 0.7))) {
    return { label: "建议减投", tone: "reduce", reason: `${sampleText}；ROI连续两个周期偏弱或较前7日明显回落，建议先收缩预算。` };
  }
  if (refCpc > 0 && cpc > refCpc * 1.2 && roi < refRoi) return { label: "优化 CPC", tone: "optimize", reason: `${sampleText}；CPC高于${scope}均值，先优化出价、关键词或人群。` };
  if (refCvr > 0 && cvr < refCvr * 0.7) return { label: "优化转化", tone: "optimize", reason: `${sampleText}；CVR低于${scope}均值，检查素材、权益和商品承接。` };
  return { label: "维持观察", tone: "neutral", reason: `${sampleText}；近7日表现接近${scope}均值，继续观察下一周期。` };
}

function dateWindow(end, days, offset) { return new Set(Array.from({ length: days }, (_, index) => addDays(end, -(offset + index)))); }
function addDays(date, days) { const [year, month, day] = date.split("-").map(Number); return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10); }
function emptyMetric() { return { cost: 0, totalSales: 0, clicks: 0, impressions: 0, orders: 0, carts: 0, days: new Set() }; }
function addMetric(target, row) { target.cost += row.cost || 0; target.totalSales += row.totalSales || 0; target.clicks += row.clicks || 0; target.impressions += row.impressions || 0; target.orders += row.orders || 0; target.carts += row.carts || 0; }
function mergeMetric(target, source) { target.cost += source.cost; target.totalSales += source.totalSales; target.clicks += source.clicks; target.impressions += source.impressions; target.orders += source.orders; target.carts += source.carts; for (const day of source.days) target.days.add(day); }
function aggregatePlanWindow(records, dates) { const map = new Map(); for (const row of records) { if (!dates.has(row.date)) continue; const value = map.get(row.planId) || emptyMetric(); addMetric(value, row); value.days.add(row.date); map.set(row.planId, value); } return map; }
function metricRoi(value) { return value.cost ? value.totalSales / value.cost : 0; }
function metricCpc(value) { return value.clicks ? value.cost / value.clicks : 0; }
function metricCvr(value) { return value.clicks ? value.orders / value.clicks : 0; }
function metricCartRate(value) { return value.clicks ? value.carts / value.clicks : 0; }

function base64Bytes(value) {
  const binary = atob(value);
  return Uint8Array.from(binary, char => char.charCodeAt(0));
}
async function decodePayload(envelope, decrypted) {
  if (envelope.compression !== "gzip") return JSON.parse(new TextDecoder().decode(decrypted));
  const stream = new Blob([decrypted]).stream().pipeThrough(new DecompressionStream("gzip"));
  return JSON.parse(new TextDecoder().decode(await new Response(stream).arrayBuffer()));
}
async function loadPlanRecords() {
  if (planRecords.value || planDataLoading.value) return;
  planDataLoading.value = true;
  planDataError.value = "";
  try {
    const response = await fetch(`${import.meta.env.BASE_URL}data/product-details.enc.json`, { cache: "no-store" });
    if (!response.ok) throw new Error("未找到计划明细数据");
    const envelope = await response.json();
    const decrypted = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: base64Bytes(envelope.iv) },
      props.cryptoKey,
      base64Bytes(envelope.ciphertext),
    );
    const payload = await decodePayload(envelope, decrypted);
    planRecords.value = payload.subjectPlanRecords || [];
  } catch (error) {
    planDataError.value = "计划明细加载失败，请刷新后重试。";
  } finally {
    planDataLoading.value = false;
  }
}
function toggleDetail(id) {
  expandedId.value = expandedId.value === id ? null : id;
  if (expandedId.value) loadPlanRecords();
}
function subjectRowId(id) { return `subject-${id}`; }
function openPlanAction(item) {
  activePlanId.value = item.planId;
  expandedId.value = item.subjectId;
  loadPlanRecords();
  nextTick(() => document.getElementById(subjectRowId(item.subjectId))?.scrollIntoView({ behavior: 'smooth', block: 'center' }));
}
onMounted(loadPlanRecords);
</script>
