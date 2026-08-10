<template>
  <div class="daily-report">
    <section class="daily-report-header">
      <div>
        <div class="daily-report-eyebrow">推广日报</div>
        <h2>推广日报 · {{ category }}</h2>
        <p>报告日期：{{ reportDate }} ｜ 对比基准：{{ previousDate }}（日环比 =（今日 - 昨日）/ 昨日）</p>
        <p class="daily-report-legend">配色：绿 = 向好指标改善，红 = 承压指标恶化 ｜ 口径：全渠道（货品全站 + 关键词 + 人群），GMV = 总成交金额，ROI = 总成交金额 / 花费。</p>
      </div>
      <div class="daily-report-filters">
        <label>品类<select v-model="category"><option v-for="item in reportCategories" :key="item" :value="item">{{ item }}</option></select></label>
        <label>报告日期<input v-model="reportDate" type="date" :min="payload.dateMin" :max="payload.dateMax" /></label>
      </div>
    </section>

    <section class="daily-section">
      <h3>一、核心结论</h3>
      <ol class="daily-insights"><li v-for="(line, index) in emphasizedInsightLines" :key="index" :class="`daily-insight-item ${line.tone}`"><template v-for="(part, partIndex) in line.parts" :key="partIndex"><strong v-if="part.tone" :class="`daily-insight-${part.tone}`">{{ part.text }}</strong><span v-else>{{ part.text }}</span></template></li></ol>
    </section>

    <section class="daily-section">
      <div class="daily-heading-row"><h3>二、KPI 卡片</h3><span>今日值 / 日环比</span></div>
      <div class="daily-kpis"><article v-for="card in kpiCards" :key="card.label" class="daily-kpi"><div>{{ card.label }}</div><strong>{{ card.value }}</strong><em :class="changeTone(card.change, card.direction)">{{ formatChange(card.change) }} 环比</em></article></div>
    </section>

    <ReportTable title="三、核心指标日环比" :headers="['指标', '今日', '昨日', '日环比']" :rows="overallRows" />
    <ReportTable title="四、场景维度" :headers="['场景', '今日花费', '昨日花费', '花费环比', '今日GMV', '昨日GMV', 'GMV环比', '今日ROI', '昨日ROI']" :rows="scenarioRows" />
    <ReportTable title="五、细类维度" :headers="['细类', '今日花费', '昨日花费', '花费环比', '今日GMV', '昨日GMV', 'GMV环比', '今日笔数', '今日ROI', '昨日ROI']" :rows="subCategoryRows" />
    <ReportTable title="六、计划维度" subtitle="按今日 GMV 排序，含投放动作" :headers="['计划（动作）', '今日花费', '昨日花费', '花费环比', '今日GMV', '昨日GMV', 'GMV环比', '今日ROI', '昨日ROI', 'ROI变化']" :rows="planRows" :loading="planLoading" />
    <ReportTable title="七、商品主体" :subtitle="category === 'DT' ? '按今日 GMV，前 10' : '按今日 GMV，全部商品主体'" :headers="['商品（主体）', '今日GMV', '今日花费', 'ROI', '笔数']" :rows="productRows" />
    <ReportTable title="八、平台撬动贡献" subtitle="GMV 内部组成，不额外累加" :headers="['来源', '今日金额', '昨日金额', '日环比', '占今日GMV比']" :rows="platformRows" />
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref } from "vue";

const props = defineProps({ payload: { type: Object, required: true }, cryptoKey: { type: CryptoKey, required: true } });
const preferredCategories = ["手机", "DT", "显示器"];
const reportCategories = computed(() => preferredCategories.filter(item => props.payload.categories?.includes(item)));
const category = ref(reportCategories.value[0] || props.payload.categories?.[0] || "手机");
const reportDate = ref(props.payload.dateMax || "");
const planRecords = ref([]);
const planLoading = ref(false);

const previousDate = computed(() => addDays(reportDate.value, -1));
const today = computed(() => aggregate(filterByDay(props.payload.records || [], reportDate.value)));
const yesterday = computed(() => aggregate(filterByDay(props.payload.records || [], previousDate.value)));
const subjectById = computed(() => new Map((props.payload.subjects || []).map(item => [String(item.subjectId), item])));
const currentScenario = computed(() => compareRows(aggregateDimension(props.payload.categoryScenarioRecords || [], "scenario", reportDate.value), aggregateDimension(props.payload.categoryScenarioRecords || [], "scenario", previousDate.value)));
const currentSubCategory = computed(() => compareRows(aggregateDimension(props.payload.subCategoryRecords || [], "subCategory", reportDate.value), aggregateDimension(props.payload.subCategoryRecords || [], "subCategory", previousDate.value)));

const kpiCards = computed(() => [
  card("总花费", money(today.value.cost), pct(today.value.cost, yesterday.value.cost), "cost"),
  card("总成交金额 GMV", money(today.value.totalSales), pct(today.value.totalSales, yesterday.value.totalSales), "positive"),
  card("直接 ROI", ratio(today.value.directSales, today.value.cost), pct(ratio(today.value.directSales, today.value.cost), ratio(yesterday.value.directSales, yesterday.value.cost)), "positive", true),
  card("总 ROI", ratio(today.value.totalSales, today.value.cost), pct(ratio(today.value.totalSales, today.value.cost), ratio(yesterday.value.totalSales, yesterday.value.cost)), "positive", true),
  card("平均点击花费 CPC", money(ratio(today.value.cost, today.value.clicks), 2), pct(ratio(today.value.cost, today.value.clicks), ratio(yesterday.value.cost, yesterday.value.clicks)), "cost"),
  card("点击率 CTR", percent(ratio(today.value.clicks, today.value.impressions)), pct(ratio(today.value.clicks, today.value.impressions), ratio(yesterday.value.clicks, yesterday.value.impressions)), "positive"),
  card("点击转化率 CVR", percent(ratio(today.value.orders, today.value.clicks)), pct(ratio(today.value.orders, today.value.clicks), ratio(yesterday.value.orders, yesterday.value.clicks)), "positive"),
  card("加购率", percent(ratio(today.value.carts, today.value.clicks)), pct(ratio(today.value.carts, today.value.clicks), ratio(yesterday.value.carts, yesterday.value.clicks)), "positive"),
]);

const overallRows = computed(() => {
  const t = today.value, p = yesterday.value;
  return [
    row("总花费", money(t.cost), money(p.cost), pct(t.cost, p.cost), "cost"),
    row("总成交金额（GMV）", money(t.totalSales), money(p.totalSales), pct(t.totalSales, p.totalSales), "positive"),
    row("直接 ROI", ratio(t.directSales, t.cost).toFixed(2), ratio(p.directSales, p.cost).toFixed(2), pct(ratio(t.directSales, t.cost), ratio(p.directSales, p.cost)), "positive", true),
    row("总 ROI", ratio(t.totalSales, t.cost).toFixed(2), ratio(p.totalSales, p.cost).toFixed(2), pct(ratio(t.totalSales, t.cost), ratio(p.totalSales, p.cost)), "positive", true),
    row("平均点击花费 CPC", money(ratio(t.cost, t.clicks), 2), money(ratio(p.cost, p.clicks), 2), pct(ratio(t.cost, t.clicks), ratio(p.cost, p.clicks)), "cost"),
    row("点击率 CTR", percent(ratio(t.clicks, t.impressions)), percent(ratio(p.clicks, p.impressions)), pct(ratio(t.clicks, t.impressions), ratio(p.clicks, p.impressions)), "positive"),
    row("点击转化率 CVR", percent(ratio(t.orders, t.clicks)), percent(ratio(p.orders, p.clicks)), pct(ratio(t.orders, t.clicks), ratio(p.orders, p.clicks)), "positive"),
    row("加购率", percent(ratio(t.carts, t.clicks)), percent(ratio(p.carts, p.clicks)), pct(ratio(t.carts, t.clicks), ratio(p.carts, p.clicks)), "positive"),
  ];
});
const scenarioRows = computed(() => currentScenario.value.map(item => tableRow(item.name, item, false)));
const subCategoryRows = computed(() => currentSubCategory.value.map(item => [...tableRow(item.name, item, false).slice(0, 7), number(item.current.orders), ratio(item.current.totalSales, item.current.cost).toFixed(2), ratio(item.previous.totalSales, item.previous.cost).toFixed(2)]));
const planRows = computed(() => comparePlans().sort((a, b) => b.current.totalSales - a.current.totalSales).slice(0, 24).map(item => {
  const costChange = pct(item.current.cost, item.previous.cost); const roiNow = ratio(item.current.totalSales, item.current.cost); const roiPrev = ratio(item.previous.totalSales, item.previous.cost);
  return [{ value: item.name, badge: action(costChange), class: "daily-name-cell" }, money(item.current.cost), money(item.previous.cost), changeCell(costChange, "cost"), money(item.current.totalSales), money(item.previous.totalSales), changeCell(pct(item.current.totalSales, item.previous.totalSales), "positive"), roiNow.toFixed(2), roiPrev.toFixed(2), changeCell(roiNow - roiPrev, "positive", true)];
}));
const productRows = computed(() => {
  const sorted = compareProducts().sort((a, b) => b.current.totalSales - a.current.totalSales);
  const visible = category.value === "DT" ? sorted.slice(0, 10) : sorted;
  return visible.map(item => [{ value: item.name, class: "daily-name-cell" }, money(item.current.totalSales), money(item.current.cost), ratio(item.current.totalSales, item.current.cost).toFixed(2), number(item.current.orders)]);
});
const platformRows = computed(() => {
  const t = today.value, p = yesterday.value;
  const labels = [["自然流量转化", "naturalSales"], ["平台助推成交", "platformSales"], ["补贴引导成交", "subsidySales"]];
  const rows = labels.map(([label, key]) => [label, money(t[key]), money(p[key]), changeCell(pct(t[key], p[key]), "positive"), percent(ratio(t[key], t.totalSales))]);
  const totalNow = t.naturalSales + t.platformSales + t.subsidySales, totalPrev = p.naturalSales + p.platformSales + p.subsidySales;
  rows.push([{ value: "三项合计", class: "daily-total-cell" }, { value: money(totalNow), class: "daily-total-cell" }, { value: money(totalPrev), class: "daily-total-cell" }, changeCell(pct(totalNow, totalPrev), "positive", false, "daily-total-cell"), { value: percent(ratio(totalNow, t.totalSales)), class: "daily-total-cell" }]);
  return rows;
});
const insightLines = computed(() => {
  const t = today.value, p = yesterday.value, gmv = pct(t.totalSales, p.totalSales), roiChange = pct(ratio(t.totalSales, t.cost), ratio(p.totalSales, p.cost));
  const topScene = currentScenario.value[0], activeScenes = currentScenario.value.filter(item => item.current.cost > 0 || item.previous.cost > 0);
  const bestSub = [...currentSubCategory.value].filter(item => item.current.cost > 0).sort((a, b) => ratio(b.current.totalSales, b.current.cost) - ratio(a.current.totalSales, a.current.cost))[0];
  const topSub = currentSubCategory.value[0];
  const allPlans = comparePlans();
  const newPlans = allPlans.filter(item => item.current.cost > 0 && item.previous.cost === 0);
  const investmentMoves = allPlans.filter(item => item.current.cost > 0 && item.previous.cost > 0).reduce((counts, item) => { const change = pct(item.current.cost, item.previous.cost); counts[change >= .15 ? "up" : change <= -.15 ? "down" : "flat"] += 1; return counts; }, { up: 0, down: 0, flat: 0 });
  const leverage = t.naturalSales + t.platformSales + t.subsidySales;
  const tailSub = currentSubCategory.value.find(item => item.current.totalSales <= 1 && item.current.cost > 0);
  const gmvDirection = gmv >= 0 ? "升" : "降";
  const roiDirection = roiChange >= 0 ? "升" : "降";
  const overallDescription = gmv >= 0 && roiChange >= 0 ? "双升，效率提升" : gmv < 0 && roiChange < 0 ? "双降，效率承压" : gmv >= 0 ? "量增价跌" : "量减效升";
  const wateringDirection = pct(t.favCart, p.favCart) >= 0 && pct(t.carts, p.carts) >= 0 ? "整体向好" : "仍有承压";
  const newPlanNames = newPlans.slice(0, 2).map(item => item.name).join("、");
  return [
    `整体：GMV${gmvDirection}、ROI${roiDirection}（${overallDescription}）。总花费 ${money(t.cost)}（${formatChange(pct(t.cost, p.cost))}）、GMV ${money(t.totalSales)}（${formatChange(gmv)}）、总ROI ${ratio(p.totalSales, p.cost).toFixed(2)}→${ratio(t.totalSales, t.cost).toFixed(2)}（${formatChange(roiChange)}）、成交成本 ${money(ratio(t.cost, t.orders))}（${formatChange(pct(ratio(t.cost, t.orders), ratio(p.cost, p.orders)))}）。`,
    topScene ? `场景结构：${activeScenes.map(item => `${item.name}（${action(pct(item.current.cost, item.previous.cost))}，花费 ${formatChange(pct(item.current.cost, item.previous.cost))}，GMV ${formatChange(pct(item.current.totalSales, item.previous.totalSales))}，ROI ${ratio(item.previous.totalSales, item.previous.cost).toFixed(2)}→${ratio(item.current.totalSales, item.current.cost).toFixed(2)}）`).join("；")}。其中 ${topScene.name} 为今日 GMV 主力来源（GMV ${money(topScene.current.totalSales)}，占品类 ${percent(ratio(topScene.current.totalSales, t.totalSales))}）。` : "场景结构：暂无可用场景数据。",
    `计划加减法：今日在投 ${allPlans.length} 个计划。新增 ${newPlans.length} 个${newPlanNames ? `（${newPlanNames}）` : ""}；加投 ${investmentMoves.up} / 减投 ${investmentMoves.down} / 持平/微动 ${investmentMoves.flat}，结构调整${investmentMoves.up || investmentMoves.down ? "明显" : "平稳"}。`,
    bestSub && topSub ? `细类格局：${topSub.name} 是绝对主力（GMV ${money(topSub.current.totalSales)}，占品类 ${percent(ratio(topSub.current.totalSales, t.totalSales))}）；${bestSub.name} ROI 最高（${ratio(bestSub.current.totalSales, bestSub.current.cost).toFixed(2)}），性价比突出${tailSub ? `；${tailSub.name} 今日近 0 成交，属于长尾/测试` : ""}。` : "细类格局：暂无可用细类数据。",
    `平台撬动：自然流量+平台助推+补贴合计贡献今日 GMV 的 ${percent(ratio(leverage, t.totalSales))}（合计 ${money(leverage)}）。自然流量转化 ${money(t.naturalSales)}（${formatChange(pct(t.naturalSales, p.naturalSales))}）、平台助推成交 ${money(t.platformSales)}（${formatChange(pct(t.platformSales, p.platformSales))}）、补贴引导成交 ${money(t.subsidySales)}（${formatChange(pct(t.subsidySales, p.subsidySales))}）——三项均为 GMV 内部组成。`,
    `蓄水指标：总收藏 ${number(t.favorites)}（${formatChange(pct(t.favorites, p.favorites))}）、总购物车 ${number(t.carts)}（${formatChange(pct(t.carts, p.carts))}）、加购率 ${percent(ratio(t.carts, t.clicks))}（${formatChange(pct(ratio(t.carts, t.clicks), ratio(p.carts, p.clicks)))}）、收藏加购合计 ${number(t.favCart)}（${formatChange(pct(t.favCart, p.favCart))}）——蓄水侧${wateringDirection}。`,
  ];
});
const emphasizedInsightLines = computed(() => insightLines.value.map(text => ({ parts: emphasize(text), tone: insightTone(text) })));

const ReportTable = defineComponent({
  props: { title: String, subtitle: String, headers: Array, rows: Array, loading: Boolean },
  setup(tableProps) {
    return () => {
      const bodyRows = tableProps.loading
        ? [h("tr", [h("td", { class: "empty", colspan: tableProps.headers.length }, "正在加载计划明细...")])]
        : tableProps.rows?.length
          ? tableProps.rows.map((cells, index) => h("tr", { key: index }, cells.map((cell, position) => {
              const item = typeof cell === "object" ? cell : { value: cell };
              return h("td", { class: [position ? "num" : "", item.class] }, [item.value, item.badge ? h("span", { class: ["daily-action-tag", `action-${item.badge}`] }, item.badge) : null]);
            })))
          : [h("tr", [h("td", { class: "empty", colspan: tableProps.headers.length }, "当前条件下暂无数据")])];
      return h("section", { class: "daily-section daily-table-section" }, [
        h("div", { class: "daily-heading-row" }, [h("h3", tableProps.title), tableProps.subtitle ? h("span", tableProps.subtitle) : null]),
        h("div", { class: "table-wrap daily-table-wrap" }, [
          h("table", [
            h("thead", [h("tr", tableProps.headers.map((header, index) => h("th", { class: index ? "num" : "" }, header)))]),
            h("tbody", bodyRows),
          ]),
        ]),
      ]);
    };
  },
});

onMounted(loadPlanRecords);
function filterByDay(records, date) { return records.filter(item => item.category === category.value && item.date === date); }
function aggregate(records) { return records.reduce((sum, item) => { for (const key of ["cost", "totalSales", "directSales", "orders", "clicks", "impressions", "carts", "favorites", "favCart", "naturalSales", "platformSales", "subsidySales"]) sum[key] += Number(item[key] || 0); return sum; }, { cost: 0, totalSales: 0, directSales: 0, orders: 0, clicks: 0, impressions: 0, carts: 0, favorites: 0, favCart: 0, naturalSales: 0, platformSales: 0, subsidySales: 0 }); }
function aggregateDimension(records, key, date) { const map = new Map(); for (const item of records) { if (item.category !== category.value || item.date !== date) continue; const name = item[key] || "未分类"; const entry = map.get(name) || { name, records: [] }; entry.records.push(item); map.set(name, entry); } return [...map.values()].map(item => ({ name: item.name, metrics: aggregate(item.records) })); }
function compareRows(current, previous) { const previousMap = new Map(previous.map(item => [item.name, item.metrics])); const all = new Map(current.map(item => [item.name, item.metrics])); for (const item of previous) if (!all.has(item.name)) all.set(item.name, aggregate([])); return [...all.entries()].map(([name, metrics]) => ({ name, current: metrics, previous: previousMap.get(name) || aggregate([]) })).sort((a, b) => b.current.totalSales - a.current.totalSales); }
function comparePlans() { const map = new Map(); for (const item of planRecords.value) { const subject = subjectById.value.get(String(item.subjectId)); if (!subject || subject.category !== category.value || ![reportDate.value, previousDate.value].includes(item.date)) continue; const key = `${item.planId}|${item.planName}`; const row = map.get(key) || { name: item.planName || "未关联计划", current: [], previous: [] }; row[item.date === reportDate.value ? "current" : "previous"].push(item); map.set(key, row); } return [...map.values()].map(item => ({ name: item.name, current: aggregate(item.current), previous: aggregate(item.previous) })); }
function compareProducts() { const map = new Map(); for (const item of props.payload.subjectDateRecords || []) { const subject = subjectById.value.get(String(item.subjectId)); if (!subject || subject.category !== category.value || ![reportDate.value, previousDate.value].includes(item.date)) continue; const row = map.get(item.subjectId) || { name: subject.subjectName || "未命名商品", current: [], previous: [] }; row[item.date === reportDate.value ? "current" : "previous"].push(item); map.set(item.subjectId, row); } return [...map.values()].map(item => ({ name: item.name, current: aggregate(item.current), previous: aggregate(item.previous) })); }
function card(label, value, change, direction, point = false) { return { label, value: typeof value === "number" ? value.toFixed(2) : value, change: point ? change : change, direction }; }
function row(label, current, previous, change, direction, point = false) { return [{ value: label }, current, previous, changeCell(change, direction, point)]; }
function tableRow(name, item) { const c = item.current, p = item.previous; return [{ value: item.name || name, class: "daily-name-cell" }, money(c.cost), money(p.cost), changeCell(pct(c.cost, p.cost), "cost"), money(c.totalSales), money(p.totalSales), changeCell(pct(c.totalSales, p.totalSales), "positive"), ratio(c.totalSales, c.cost).toFixed(2), ratio(p.totalSales, p.cost).toFixed(2)]; }
function changeCell(value, direction, point = false, extraClass = "") { return { value: point ? `${value > 0 ? "+" : ""}${Number(value || 0).toFixed(2)}` : formatChange(value), class: `${changeTone(value, direction)} ${extraClass}` }; }
function action(change) { if (change == null) return "新增"; if (change >= 0.15) return "加投"; if (change <= -0.15) return "减投"; return "持平/微动"; }
function pct(current, previous) { return previous ? (current - previous) / Math.abs(previous) : current ? null : 0; }
function ratio(numerator, denominator) { return denominator ? numerator / denominator : 0; }
function money(value, digits = 0) { return `¥${Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`; }
function number(value) { return Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 0 }); }
function percent(value) { return `${(Number(value || 0) * 100).toFixed(2)}%`; }
function formatChange(value) { if (value == null) return "新增"; return `${value >= 0 ? "↑" : "↓"}${Math.abs(value * 100).toFixed(1)}%`; }
function insightTone(text) {
  if (/(双升|效率提升|整体向好|性价比突出|ROI 最高)/.test(text)) return "green";
  if (/(双降|效率承压|仍有承压|低效|减投|近 0 成交|近0成交|下降)/.test(text)) return "red";
  return "yellow";
}
function emphasize(text) {
  const pattern = /(整体|场景结构|计划加减法|细类格局|平台撬动|蓄水指标|GMV[^，；。]*|ROI[^，；。]*|加购率[^，；。]*|新增\s+\d+\s+个|加投\s+\d+\s*\/\s*减投\s+\d+)/g;
  const parts = [];
  let lastIndex = 0;
  for (const match of text.matchAll(pattern)) {
    if (match.index > lastIndex) parts.push({ text: text.slice(lastIndex, match.index) });
    const value = match[0];
    const label = /^(整体|场景结构|计划加减法|细类格局|平台撬动|蓄水指标)$/.test(value);
    parts.push({ text: value, tone: label ? "label" : "metric" });
    lastIndex = match.index + value.length;
  }
  if (lastIndex < text.length) parts.push({ text: text.slice(lastIndex) });
  return parts;
}
function changeTone(value, direction) { if (value == null || Math.abs(value) < 0.00001) return "daily-flat"; const good = direction === "cost" ? value < 0 : value > 0; return good ? "daily-good" : "daily-bad"; }
function addDays(date, days) { const [year, month, day] = date.split("-").map(Number); const result = new Date(Date.UTC(year, month - 1, day + days)); return result.toISOString().slice(0, 10); }
function base64Bytes(value) { return Uint8Array.from(atob(value), char => char.charCodeAt(0)); }
async function loadPlanRecords() { planLoading.value = true; try { const response = await fetch(`${import.meta.env.BASE_URL}data/product-details.enc.json`, { cache: "no-store" }); if (!response.ok) throw new Error("no data"); const envelope = await response.json(); const decoded = await crypto.subtle.decrypt({ name: "AES-GCM", iv: base64Bytes(envelope.iv) }, props.cryptoKey, base64Bytes(envelope.ciphertext)); const bytes = envelope.compression === "gzip" ? await new Response(new Blob([decoded]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer() : decoded; planRecords.value = JSON.parse(new TextDecoder().decode(bytes)).subjectPlanRecords || []; } finally { planLoading.value = false; } }
</script>
