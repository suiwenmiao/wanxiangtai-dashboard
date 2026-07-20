<template>
  <div class="creative-access">
    <section v-if="locked" class="creative-login" aria-labelledby="creative-login-title">
      <div class="creative-login-mark">素材看板</div>
      <h2 id="creative-login-title">解锁私有投放数据</h2>
      <p>输入访问密码后，数据仅在当前浏览器中本地解密。</p>
      <form @submit.prevent="unlock">
        <label for="creative-password">访问密码</label>
        <input id="creative-password" v-model="password" type="password" autocomplete="current-password" :disabled="unlocking" autofocus />
        <p v-if="authError" class="creative-login-error">{{ authError }}</p>
        <button type="submit" :disabled="unlocking || !password">{{ unlocking ? "正在解锁..." : "进入素材看板" }}</button>
      </form>
    </section>
    <div v-else class="creative-page">
    <div class="creative-toolbar">
      <div>
        <div class="creative-title">素材表现</div>
        <div class="creative-subtitle">{{ loading ? "正在加载品类素材数据..." : loadError || `${dataRange} · ${matrixRows.length} 条图片素材记录 · 显示 ${matrixMaterials.length}/${matrixMaterialTotal} 张图片 · ${textMaterialCount} 条标题/文字素材` }}</div>
      </div>
      <div class="creative-filters">
        <div class="filter-group">
          <label>开始日期</label>
          <input v-model="selectedStartDate" type="date" :min="creative.dateStart" :max="creative.dateEnd" />
        </div>
        <div class="filter-group">
          <label>结束日期</label>
          <input v-model="selectedEndDate" type="date" :min="creative.dateStart" :max="creative.dateEnd" />
        </div>
        <div class="filter-group">
          <label>展示方式</label>
          <div class="display-mode" role="group" aria-label="素材展示方式">
            <button :class="{ active: displayMode === 'main' }" type="button" @click="displayMode = 'main'">商品主图</button>
            <button :class="{ active: displayMode === 'variant' }" type="button" @click="displayMode = 'variant'">创意变体</button>
          </div>
        </div>
        <div class="filter-group">
          <label>商品 ID</label>
          <details ref="productPicker" class="multi-picker">
            <summary>{{ selectedProductIds.length ? `已选 ${selectedProductIds.length} 个商品` : "全部商品" }}</summary>
            <div class="multi-picker-menu">
              <label v-for="product in products" :key="product.id" class="multi-option">
                <input v-model="selectedProductIds" type="checkbox" :value="product.id" />
                <span>{{ product.label }}</span>
              </label>
              <button class="picker-done" type="button" @click="closePicker(productPicker)">完成</button>
            </div>
          </details>
        </div>
        <div class="filter-group">
          <label>计划</label>
          <details ref="planPicker" class="multi-picker">
            <summary>{{ selectedPlans.length ? `已选 ${selectedPlans.length} 个计划` : "全部计划" }}</summary>
            <div class="multi-picker-menu">
              <label v-for="plan in plans" :key="plan" class="multi-option">
                <input v-model="selectedPlans" type="checkbox" :value="plan" />
                <span>{{ plan }}</span>
              </label>
              <button class="picker-done" type="button" @click="closePicker(planPicker)">完成</button>
            </div>
          </details>
        </div>
        <div class="filter-group">
          <label>推广场景</label>
          <details ref="scenarioPicker" class="multi-picker">
            <summary>{{ selectedScenarios.length ? `已选 ${selectedScenarios.length} 个场景` : "全部场景" }}</summary>
            <div class="multi-picker-menu">
              <label v-for="scenario in scenarios" :key="scenario.id" class="multi-option">
                <input v-model="selectedScenarios" type="checkbox" :value="scenario.id" />
                <span>{{ scenario.label }}</span>
              </label>
              <button class="picker-done" type="button" @click="closePicker(scenarioPicker)">完成</button>
            </div>
          </details>
        </div>
        <div class="filter-group">
          <label>品类</label>
          <details ref="categoryPicker" class="multi-picker">
            <summary>{{ selectedCategories.length ? `已选 ${selectedCategories.length} 个品类` : "全部品类" }}</summary>
            <div class="multi-picker-menu">
              <label v-for="category in categories" :key="category" class="multi-option">
                <input v-model="selectedCategories" type="checkbox" :value="category" />
                <span>{{ category }}</span>
              </label>
              <button class="picker-done" type="button" @click="closePicker(categoryPicker)">完成</button>
            </div>
          </details>
        </div>
        <button class="filter-apply" type="button" @click="applyFilters">筛选</button>
      </div>
    </div>

    <div class="kpi-row creative-kpis">
      <div class="kpi-card click"><div class="kpi-label">点击量</div><div class="kpi-value">{{ totals.clicks.toLocaleString() }}</div></div>
      <div class="kpi-card ctr"><div class="kpi-label">点击率</div><div class="kpi-value">{{ formatPercent(totals.ctr) }}</div></div>
      <div class="kpi-card cvr"><div class="kpi-label">点击转化率</div><div class="kpi-value">{{ formatPercent(totals.cvr) }}</div></div>
      <div class="kpi-card sales"><div class="kpi-label">总成交金额</div><div class="kpi-value">¥{{ formatMoney(totals.totalSales) }}</div></div>
      <div class="kpi-card troi"><div class="kpi-label">ROI</div><div class="kpi-value">{{ totals.totalRoi.toFixed(2) }}</div></div>
      <div class="kpi-card cost"><div class="kpi-label">高点击素材</div><div class="kpi-value">{{ highClickMaterialCount }}</div></div>
    </div>

    <section v-if="!loading && !loadError" class="creative-insights">
      <div class="insights-heading">
        <div class="chart-title">素材分析与建议</div>
        <div class="insights-range">基于当前筛选条件</div>
      </div>
      <div class="insights-grid">
        <div class="insight-item">
          <div class="insight-label">高点击素材特征</div>
          <p>{{ materialInsights.highClick }}</p>
        </div>
        <div class="insight-item">
          <div class="insight-label">需要关注的素材</div>
          <p>{{ materialInsights.underperforming }}</p>
        </div>
        <div class="insight-item">
          <div class="insight-label">下一步优化方向</div>
          <p>{{ materialInsights.recommendation }}</p>
        </div>
      </div>
    </section>

    <section v-if="planTopMaterials.length" class="quality-materials">
      <div class="quality-heading">
        <div>
          <div class="chart-title">计划优质素材 TOP 3 矩阵</div>
          <div class="matrix-note">每个计划独立排序，优先成交笔数，再比较转化率、点击率和点击量。</div>
        </div>
      </div>
      <div class="quality-matrix-wrap">
        <table class="quality-matrix">
          <thead>
            <tr><th class="quality-plan-head">计划</th><th>TOP 1</th><th>TOP 2</th><th>TOP 3</th></tr>
          </thead>
          <tbody>
            <tr v-for="plan in planTopMaterials" :key="plan.id">
              <th class="quality-plan-name" :title="plan.name">{{ plan.name }}</th>
              <td v-for="rank in 3" :key="rank" class="quality-matrix-cell">
                <div v-if="plan.materials[rank - 1]" :class="['quality-material', { 'top-rank': rank === 1 }]">
                  <div class="quality-rank">{{ rank }}</div>
                  <div class="quality-thumb image-thumb"><img v-if="plan.materials[rank - 1].imageUrl" :src="plan.materials[rank - 1].imageUrl" :alt="plan.materials[rank - 1].name" /><span v-else>{{ thumbText(plan.materials[rank - 1].name) }}</span></div>
                  <div class="quality-copy">
                    <div class="quality-material-name" :title="plan.materials[rank - 1].name">{{ plan.materials[rank - 1].name }}</div>
                    <div>{{ plan.materials[rank - 1].orders }} 成交 · CTR {{ formatPercent(plan.materials[rank - 1].ctr) }}</div>
                    <div>CVR {{ formatPercent(plan.materials[rank - 1].cvr) }}</div>
                  </div>
                </div>
                <span v-else class="matrix-empty">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel-table matrix-panel">
      <div class="matrix-heading">
        <div>
          <div class="chart-title">计划 × 素材点击率矩阵</div>
          <div class="matrix-note">{{ displayMode === 'main' ? '同一商品仅展示一张代表主图，所有创意变体数据合并计算；列为素材，行为计划。' : '按严格视觉去重展示创意变体；列为素材，行为计划。' }}</div>
        </div>
        <div class="matrix-legend"><span class="legend-low"></span>低 CTR <span class="legend-high"></span>高 CTR</div>
      </div>
      <div class="matrix-wrap">
        <table class="ctr-matrix">
          <thead>
            <tr>
              <th class="matrix-plan-head">计划</th>
              <th v-for="material in matrixMaterials" :key="material.key" class="matrix-material-head">
                <div class="matrix-thumb">
                  <img v-if="material.imageUrl" :src="material.imageUrl" :alt="material.name" />
                  <span v-else>{{ thumbText(material.name) }}</span>
                </div>
                <div class="matrix-material-name" :title="material.name">{{ material.name }}</div>
                <div class="matrix-material-id">{{ material.id ? `素材 ${material.id}` : '文字素材' }}</div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="plan in matrixPlans" :key="plan">
              <th class="matrix-plan-name" :title="plan">{{ plan }}</th>
              <td v-for="material in matrixMaterials" :key="`${plan}-${material.key}`" class="matrix-cell">
                <template v-if="matrixCell(plan, material.key)">
                  <div class="ctr-cell" :class="{ hot: matrixCell(plan, material.key).high }" :style="{ '--heat': heat(matrixCell(plan, material.key).ctr) }">
                    <span v-if="matrixCell(plan, material.key).high" class="matrix-hot">高点击</span>
                    <strong>{{ formatPercent(matrixCell(plan, material.key).ctr) }}</strong>
                    <small>{{ matrixCell(plan, material.key).clicks }} 点击</small>
                    <small>CVR {{ formatPercent(matrixCell(plan, material.key).cvr) }}</small>
                  </div>
                </template>
                <span v-else class="matrix-empty">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel-table">
      <div class="chart-title">素材投放明细 <span class="table-count">按视觉素材全局合并 · 显示 {{ detailRows.length }}/{{ sortedRows.length }} 条</span></div>
      <div class="table-wrap">
        <table class="creative-table">
          <thead><tr><th>素材</th><th>计划</th><th>品类</th><th>商品 ID</th><th class="num">展现</th><th class="num">点击</th><th class="num">点击率</th><th class="num">转化率</th><th class="num">花费</th><th class="num">成交</th><th class="num">ROI</th></tr></thead>
          <tbody>
            <tr v-for="row in detailRows" :key="rowKey(row)" :class="{ 'row-good': row.isHighClick, 'row-danger': row.clicks >= 20 && row.cvr === 0 }">
              <td><div class="creative-cell"><div class="mini-thumb image-thumb"><img v-if="row.imageUrl" :src="row.imageUrl" :alt="row.materialName" /><span v-else>{{ thumbText(row.materialName) }}</span></div><div><strong>{{ row.materialName }}</strong><div class="creative-id">{{ row.variantCount > 1 ? `${row.variantCount} 个创意变体` : row.materialId ? `素材 ID ${row.materialId}` : `创意 ID ${row.creativeId}` }}</div></div></div></td>
              <td :title="row.planNames.join('、')">{{ row.planNames.length }} 个计划</td><td>{{ row.category }}</td><td>{{ row.subjectId }}</td><td class="num">{{ row.impressions.toLocaleString() }}</td><td class="num">{{ row.clicks.toLocaleString() }}</td>
              <td :class="['num', row.isHighClick ? 'roi-good' : '']">{{ formatPercent(row.ctr) }}</td><td :class="['num', row.isHighConvert ? 'roi-good' : row.clicks >= 20 && row.cvr === 0 ? 'roi-risk' : '']">{{ formatPercent(row.cvr) }}</td><td class="num">¥{{ formatMoney(row.cost) }}</td><td class="num">¥{{ formatMoney(row.totalSales) }}</td><td :class="['num', row.roi >= 3 ? 'roi-good' : row.roi < 1 ? 'roi-risk' : '']">{{ row.roi.toFixed(2) }}</td>
            </tr>
            <tr v-if="sortedRows.length === 0"><td colspan="11" class="empty">没有匹配的素材记录</td></tr>
          </tbody>
        </table>
      </div>
    </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { formatMoney, formatPercent, sumMetrics } from "../utils/metrics";

const creative = ref({ records: [], dateStart: "", dateEnd: "" });
const publicDataUrl = filename => `${import.meta.env.BASE_URL}data/${filename}`;
const locked = ref(true);
const password = ref("");
const unlocking = ref(false);
const authError = ref("");
const indexCategories = ref([]);
const loading = ref(false);
const loadError = ref("");
const selectedPlans = ref([]);
const selectedProductIds = ref([]);
const selectedScenarios = ref([]);
const selectedCategories = ref(["手机"]);
const displayMode = ref("main");
const selectedStartDate = ref("");
const selectedEndDate = ref("");
const appliedPlans = ref([]);
const appliedProductIds = ref([]);
const appliedScenarios = ref([]);
const appliedCategories = ref(["手机"]);
const appliedStartDate = ref("");
const appliedEndDate = ref("");
const productPicker = ref(null);
const planPicker = ref(null);
const scenarioPicker = ref(null);
const categoryPicker = ref(null);
const materialKey = row => (displayMode.value === "main" ? row.mainVisualKey : row.visualKey) || row.imageUrl || row.materialId || row.materialName;
const rowKey = row => `${row.planId}|${row.creativeId}|${materialKey(row)}`;
const products = computed(() => {
  const names = new Map();
  for (const row of creative.value.records) {
    if (!names.has(row.subjectId)) names.set(row.subjectId, row.subjectName || row.productName || "未命名商品");
  }
  return [...names.entries()]
    .map(([id, name]) => ({ id, label: `${id} · ${name}` }))
    .sort((a, b) => a.label.localeCompare(b.label, "zh-CN"));
});
const plans = computed(() => [...new Set(creative.value.records.map(row => row.planName))].sort((a, b) => a.localeCompare(b, "zh-CN")));
const scenarios = computed(() => {
  const names = new Map();
  for (const row of creative.value.records) {
    const id = String(row.scenarioId || row.scenarioName || "未命名场景");
    if (!names.has(id)) names.set(id, row.scenarioName || "未命名场景");
  }
  return [...names.entries()]
    .map(([id, name]) => ({ id, label: `${name} · ${id}` }))
    .sort((a, b) => a.label.localeCompare(b.label, "zh-CN"));
});
const categories = computed(() => indexCategories.value);
const dataRange = computed(() => creative.value.dateStart && creative.value.dateEnd
  ? `${creative.value.dateStart} 至 ${creative.value.dateEnd}`
  : "暂无数据");

const filteredRows = computed(() => creative.value.records.filter(row =>
  (!appliedStartDate.value || row.date >= appliedStartDate.value)
  && (!appliedEndDate.value || row.date <= appliedEndDate.value)
  && (appliedPlans.value.length === 0 || appliedPlans.value.includes(row.planName))
  && (appliedProductIds.value.length === 0 || appliedProductIds.value.includes(String(row.subjectId)))
  && (appliedScenarios.value.length === 0 || appliedScenarios.value.includes(String(row.scenarioId || row.scenarioName || "未命名场景")))
  && (appliedCategories.value.length === 0 || appliedCategories.value.includes(row.category))
));
const consolidatedRows = computed(() => {
  const map = new Map();
  for (const row of filteredRows.value) {
    const key = materialKey(row);
    const entry = map.get(key) || {
      ...row,
      impressions: 0,
      clicks: 0,
      cost: 0,
      totalSales: 0,
      directSales: 0,
      orders: 0,
      carts: 0,
      favorites: 0,
      favCart: 0,
      isHighClick: false,
      isHighConvert: false,
      bestRowClicks: -1,
      planNames: new Set(),
      variantKeys: new Set(),
    };
    entry.impressions += row.impressions;
    entry.clicks += row.clicks;
    entry.cost += row.cost;
    entry.totalSales += row.totalSales;
    entry.directSales += row.directSales;
    entry.orders += row.orders;
    entry.carts += row.carts;
    entry.favorites += row.favorites;
    entry.favCart += row.favCart;
    entry.isHighClick ||= row.isHighClick;
    entry.isHighConvert ||= row.isHighConvert;
    entry.planNames.add(row.planName);
    entry.variantKeys.add(row.visualKey || row.imageUrl || row.materialId);
    if (row.clicks > entry.bestRowClicks) {
      entry.creativeId = row.creativeId;
      entry.materialId = row.materialId;
      entry.materialName = row.materialName;
      entry.imageUrl = row.imageUrl;
      entry.bestRowClicks = row.clicks;
    }
    map.set(key, entry);
  }
  return [...map.values()].map(row => ({
    ...row,
    cost: Math.round(row.cost * 100) / 100,
    totalSales: Math.round(row.totalSales * 100) / 100,
    directSales: Math.round(row.directSales * 100) / 100,
    planNames: [...row.planNames].sort((a, b) => a.localeCompare(b, "zh-CN")),
    variantCount: row.variantKeys.size,
    ctr: row.impressions ? row.clicks / row.impressions : 0,
    cvr: row.clicks ? row.orders / row.clicks : 0,
    roi: row.cost ? row.totalSales / row.cost : 0,
  }));
});
const sortedRows = computed(() => [...consolidatedRows.value].sort((a, b) => b.clicks - a.clicks || b.ctr - a.ctr));
const detailRows = computed(() => sortedRows.value.slice(0, 500));
const totals = computed(() => sumMetrics(filteredRows.value));
const matrixRows = computed(() => filteredRows.value.filter(row => row.isImage));
const textMaterialCount = computed(() => filteredRows.value.length - matrixRows.value.length);

const visualMaterials = computed(() => {
  const map = new Map();
  for (const row of matrixRows.value) {
    const key = materialKey(row);
    const material = map.get(key) || {
      key,
      name: row.materialName,
      category: row.category,
      size: row.materialSize || "未标注尺寸",
      imageUrl: row.imageUrl,
      impressions: 0,
      clicks: 0,
      orders: 0,
      high: false,
      bestRowClicks: -1,
      plans: new Set(),
    };
    material.impressions += row.impressions;
    material.clicks += row.clicks;
    material.orders += row.orders;
    material.high ||= row.isHighClick;
    material.plans.add(row.planName);
    if (row.clicks > material.bestRowClicks) {
      material.name = row.materialName;
      material.category = row.category;
      material.size = row.materialSize || "未标注尺寸";
      material.imageUrl = row.imageUrl;
      material.bestRowClicks = row.clicks;
    }
    map.set(key, material);
  }
  return [...map.values()].map(material => ({
    ...material,
    ctr: material.impressions ? material.clicks / material.impressions : 0,
    cvr: material.clicks ? material.orders / material.clicks : 0,
    planCount: material.plans.size,
  }));
});
const highClickMaterials = computed(() => visualMaterials.value.filter(material => material.high));
const highClickMaterialCount = computed(() => highClickMaterials.value.length);
const materialInsights = computed(() => {
  if (!visualMaterials.value.length) {
    return {
      highClick: "当前筛选条件下暂无图片素材。",
      underperforming: "暂无可判断的低效素材。",
      recommendation: "调整筛选条件后即可生成素材建议。",
    };
  }
  const countBy = (items, key) => {
    const counts = new Map();
    for (const item of items) counts.set(item[key], (counts.get(item[key]) || 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
  };
  const topCategory = countBy(highClickMaterials.value, "category");
  const topSize = countBy(highClickMaterials.value, "size");
  const avgPlanCoverage = highClickMaterials.value.length
    ? highClickMaterials.value.reduce((sum, material) => sum + material.planCount, 0) / highClickMaterials.value.length
    : 0;
  const weakMaterials = visualMaterials.value
    .filter(material => material.clicks >= 20 && material.orders === 0)
    .sort((a, b) => b.clicks - a.clicks)
    .slice(0, 3);
  const weakNames = weakMaterials.map(material => material.name || "未命名素材").join("、");

  return {
    highClick: highClickMaterials.value.length
      ? `${highClickMaterials.value.length} 张高点击素材主要来自 ${topCategory?.[0] || "当前品类"}，以 ${topSize?.[0] || "未标注尺寸"} 为主，平均投放在 ${avgPlanCoverage.toFixed(1)} 个计划。`
      : "当前没有达到高点击标准的图片素材，可先积累更多展现与点击后再判断。",
    underperforming: weakMaterials.length
      ? `${weakMaterials.length} 张素材累计点击不少于 20 次但尚未成交：${weakNames}。这说明画面能带来兴趣，但转化承接偏弱。`
      : "当前未发现累计点击不少于 20 次但无成交的图片素材，优先继续观察高点击素材的转化稳定性。",
    recommendation: weakMaterials.length
      ? "保留高点击画面的核心卖点与构图，优先校验标题、价格权益和落地页是否与素材承诺一致；对无成交素材先缩量，再替换利益点或人群测试。"
      : highClickMaterials.value.length
        ? "围绕高点击素材的主尺寸和表达方向制作 3 至 5 个变体，分别测试主卖点、价格权益和首屏商品信息，再按转化率筛选放量。"
        : "先补充不同卖点、场景和尺寸的素材，再用点击率与转化率共同判断保留方向。",
  };
});
const planTopMaterials = computed(() => {
  const planMap = new Map();
  for (const row of matrixRows.value) {
    const plan = planMap.get(row.planId) || { id: row.planId, name: row.planName, materials: new Map() };
    const key = materialKey(row);
    const material = plan.materials.get(key) || {
      key,
      name: row.materialName,
      imageUrl: row.imageUrl,
      impressions: 0,
      clicks: 0,
      orders: 0,
      bestRowClicks: -1,
    };
    material.impressions += row.impressions;
    material.clicks += row.clicks;
    material.orders += row.orders;
    if (row.clicks > material.bestRowClicks) {
      material.name = row.materialName;
      material.imageUrl = row.imageUrl;
      material.bestRowClicks = row.clicks;
    }
    plan.materials.set(key, material);
    planMap.set(row.planId, plan);
  }
  return [...planMap.values()]
    .map(plan => ({
      ...plan,
      materials: [...plan.materials.values()]
        .map(material => ({
          ...material,
          ctr: material.impressions ? material.clicks / material.impressions : 0,
          cvr: material.clicks ? material.orders / material.clicks : 0,
        }))
        .sort((a, b) => b.orders - a.orders || b.cvr - a.cvr || b.ctr - a.ctr || b.clicks - a.clicks)
        .slice(0, 3),
    }))
    .sort((a, b) => a.name.localeCompare(b.name, "zh-CN"));
});

const allMatrixMaterials = computed(() => {
  const map = new Map();
  for (const row of matrixRows.value) {
    const key = materialKey(row);
    const prior = map.get(key);
    if (!prior || row.clicks > prior.clicks) map.set(key, { key, id: row.materialId, name: row.materialName, imageUrl: row.imageUrl, clicks: row.clicks });
  }
  return [...map.values()].sort((a, b) => b.clicks - a.clicks);
});
const matrixMaterialTotal = computed(() => allMatrixMaterials.value.length);
const matrixMaterials = computed(() => allMatrixMaterials.value.slice(0, 60));
const matrixPlans = computed(() => [...new Set(matrixRows.value.map(row => row.planName))].sort());
const matrix = computed(() => {
  const map = new Map();
  for (const row of matrixRows.value) {
    const key = `${row.planName}::${materialKey(row)}`;
    const cell = map.get(key) || { impressions: 0, clicks: 0, orders: 0, high: false };
    cell.impressions += row.impressions;
    cell.clicks += row.clicks;
    cell.orders += row.orders;
    cell.high ||= row.isHighClick;
    map.set(key, cell);
  }
  for (const cell of map.values()) {
    cell.ctr = cell.impressions ? cell.clicks / cell.impressions : 0;
    cell.cvr = cell.clicks ? cell.orders / cell.clicks : 0;
  }
  return map;
});
function matrixCell(plan, key) { return matrix.value.get(`${plan}::${key}`); }
function thumbText(value) { return String(value || "素材").slice(0, 2); }
function heat(ctr) { return Math.min(1, ctr / 0.12).toFixed(2); }
function closePicker(picker) { if (picker) picker.open = false; }
function closeAllPickers() {
  closePicker(productPicker.value);
  closePicker(planPicker.value);
  closePicker(scenarioPicker.value);
  closePicker(categoryPicker.value);
}
function applyFilters() {
  if (selectedStartDate.value && selectedEndDate.value && selectedStartDate.value > selectedEndDate.value) {
    loadError.value = "开始日期不能晚于结束日期";
    return;
  }
  appliedPlans.value = [...selectedPlans.value];
  appliedProductIds.value = [...selectedProductIds.value];
  appliedScenarios.value = [...selectedScenarios.value];
  appliedCategories.value = [...selectedCategories.value];
  appliedStartDate.value = selectedStartDate.value;
  appliedEndDate.value = selectedEndDate.value;
  closeAllPickers();
}
function closePickersOnOutsideClick(event) {
  if (!event.target.closest(".multi-picker")) closeAllPickers();
}
function base64Bytes(value) {
  const binary = atob(value);
  return Uint8Array.from(binary, char => char.charCodeAt(0));
}
async function unlock() {
  unlocking.value = true;
  authError.value = "";
  try {
    const response = await fetch(publicDataUrl("creative-data.enc.json"), { cache: "no-store" });
    if (!response.ok) throw new Error("未找到加密素材数据，请稍后重试。");
    const envelope = await response.json();
    const encoder = new TextEncoder();
    const passwordKey = await crypto.subtle.importKey("raw", encoder.encode(password.value), "PBKDF2", false, ["deriveKey"]);
    const key = await crypto.subtle.deriveKey(
      { name: "PBKDF2", salt: base64Bytes(envelope.kdf.salt), iterations: envelope.kdf.iterations, hash: envelope.kdf.hash },
      passwordKey,
      { name: "AES-GCM", length: 256 },
      false,
      ["decrypt"],
    );
    const decrypted = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: base64Bytes(envelope.iv) },
      key,
      base64Bytes(envelope.ciphertext),
    );
    const payload = JSON.parse(new TextDecoder().decode(decrypted));
    const index = payload.index || {};
    const categoryPayloads = Object.values(payload.categories || {});
    if (!categoryPayloads.length) throw new Error("加密素材数据为空。");
    indexCategories.value = index.categories || [];
    creative.value = {
      dateStart: index.dateStart || categoryPayloads[0].dateStart || "",
      dateEnd: index.dateEnd || categoryPayloads[0].dateEnd || "",
      records: categoryPayloads.flatMap(item => item.records || []),
    };
    selectedStartDate.value = creative.value.dateStart;
    selectedEndDate.value = creative.value.dateEnd;
    appliedStartDate.value = creative.value.dateStart;
    appliedEndDate.value = creative.value.dateEnd;
    locked.value = false;
    password.value = "";
  } catch (error) {
    authError.value = "密码不正确，或加密数据暂不可用。";
  } finally {
    unlocking.value = false;
  }
}
onMounted(() => {
  document.addEventListener("pointerdown", closePickersOnOutsideClick);
});
onBeforeUnmount(() => document.removeEventListener("pointerdown", closePickersOnOutsideClick));
</script>
