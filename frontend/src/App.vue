<template>
  <main class="page">
    <div class="header">
      <div>
        <h1>万相台投放数据看板</h1>
        <div class="update-time">数据范围: {{ dataRangeLabel }} · 更新 {{ generatedAtLabel }}</div>
      </div>
      <div class="header-right">
        <nav class="tab-nav">
          <button :class="{ active: tab === 'dashboard' }" @click="selectTab('dashboard')">品类看板</button>
          <button :class="{ active: tab === 'product' }" @click="selectTab('product')">商品主体</button>
          <button :class="{ active: tab === 'creative' }" @click="selectTab('creative')">素材看板</button>
        </nav>
        <div class="status-pill">{{ filtered.length }} 条记录</div>
      </div>
    </div>

    <div v-if="tab !== 'creative'" class="filter-bar">
      <div class="filter-group">
        <label>开始日期</label>
        <input v-model="startDate" type="date" :min="payload.dateMin" :max="payload.dateMax" />
      </div>
      <div class="filter-group">
        <label>结束日期</label>
        <input v-model="endDate" type="date" :min="payload.dateMin" :max="payload.dateMax" />
      </div>
      <div class="filter-group">
        <label>品类</label>
        <select v-model="category">
          <option value="all">全部品类</option>
          <option v-for="item in payload.categories" :key="item" :value="item">{{ item }}</option>
        </select>
      </div>
      <div style="display:flex;gap:8px;margin-left:auto;flex-wrap:wrap;">
        <button class="btn-quick" :class="{ active: quickDays === 1 }" @click="setQuickRange(1)">今天</button>
        <button class="btn-quick" :class="{ active: quickDays === 7 }" @click="setQuickRange(7)">近7天</button>
        <button class="btn-quick" :class="{ active: quickDays === 30 }" @click="setQuickRange(30)">近30天</button>
        <button class="btn-quick" :class="{ active: quickDays === 90 }" @click="setQuickRange(90)">近90天</button>
        <button class="btn-quick" :class="{ active: quickDays === 0 }" @click="setQuickRange(0)">全部</button>
      </div>
      <div v-if="prevLabel" class="huanbi-label">{{ prevLabel }}</div>
    </div>

    <DashboardPage v-if="tab === 'dashboard'" :filtered="filtered" :prevFiltered="prevFiltered" :category="category" :allSubCats="subCategoryFiltered" />
    <ProductPage   v-if="tab === 'product'"   :filtered="filtered" :prevFiltered="prevFiltered" />
    <CreativePage  v-if="tab === 'creative'" />
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import DashboardPage from "./components/DashboardPage.vue";
import ProductPage from "./components/ProductPage.vue";
import CreativePage from "./components/CreativePage.vue";
import payload from "./data/dashboard-data.json";

const tab = ref(location.hash === "#/creative" ? "creative" : "dashboard");
const startDate = ref(payload.dateMax || "");
const endDate = ref(payload.dateMax || "");
const category = ref("all");
const quickDays = ref(1);

const filtered = computed(() =>
  payload.records.filter(r => {
    if (startDate.value && r.date < startDate.value) return false;
    if (endDate.value && r.date > endDate.value) return false;
    if (category.value !== "all" && r.category !== category.value) return false;
    return true;
  })
);

const subCategoryFiltered = computed(() =>
  payload.subCategoryRecords.filter(r => {
    if (startDate.value && r.date < startDate.value) return false;
    if (endDate.value && r.date > endDate.value) return false;
    if (category.value !== "all" && r.category !== category.value) return false;
    return true;
  })
);

// ─── 环比（同期对比） ───
const periodDays = computed(() => {
  if (!startDate.value || !endDate.value) return 0;
  return Math.ceil((new Date(endDate.value) - new Date(startDate.value)) / 86400000) + 1;
});
const prevStart = computed(() => {
  if (!startDate.value) return null;
  const d = new Date(startDate.value); d.setDate(d.getDate() - periodDays.value);
  return d.toISOString().slice(0, 10);
});
const prevEnd = computed(() => {
  if (!startDate.value) return null;
  const d = new Date(startDate.value); d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
});
const prevLabel = computed(() => {
  if (!prevStart.value || !prevEnd.value) return '';
  return `环比: ${prevStart.value} ~ ${prevEnd.value}`;
});
const prevFiltered = computed(() => {
  if (!prevStart.value || !prevEnd.value) return [];
  return payload.records.filter(r => {
    if (r.date < prevStart.value) return false;
    if (r.date > prevEnd.value) return false;
    if (category.value !== "all" && r.category !== category.value) return false;
    return true;
  });
});

const dataRangeLabel = computed(() => {
  if (!payload.dateMin || !payload.dateMax) return "暂无数据";
  return `${payload.dateMin} ~ ${payload.dateMax}`;
});
const generatedAtLabel = computed(() => {
  if (!payload.generatedAt) return "未生成";
  return payload.generatedAt.replace("T", " ");
});

function setQuickRange(days) {
  quickDays.value = days;
  if (!payload.dateMax) return;
  const end = new Date(payload.dateMax);
  const start = days === 0 ? new Date(payload.dateMin)
    : (() => { const s = new Date(end); s.setDate(s.getDate() - days + 1); return s; })();
  startDate.value = start.toISOString().slice(0, 10);
  endDate.value = end.toISOString().slice(0, 10);
}

function selectTab(nextTab) {
  tab.value = nextTab;
  history.replaceState(null, "", nextTab === "creative" ? "#/creative" : "#/");
}
function syncTabFromHash() {
  tab.value = location.hash === "#/creative" ? "creative" : "dashboard";
}
onMounted(() => window.addEventListener("hashchange", syncTabFromHash));
onBeforeUnmount(() => window.removeEventListener("hashchange", syncTabFromHash));
</script>
<style scoped>
.huanbi-label { font-size: 12px; color: #888; white-space: nowrap; padding: 6px 10px; background: #f0f2f5; border-radius: 4px; }
</style>
