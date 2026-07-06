<template>
  <main class="page">
    <div class="header">
      <div>
        <h1>万相台投放数据看板</h1>
        <div class="update-time">数据范围: {{ dataRangeLabel }} · 更新 {{ generatedAtLabel }}</div>
      </div>
      <div class="header-right">
        <nav class="tab-nav">
          <button :class="{ active: tab === 'dashboard' }" @click="tab = 'dashboard'">品类看板</button>
          <button :class="{ active: tab === 'product' }" @click="tab = 'product'">商品主体</button>
        </nav>
        <div class="status-pill">{{ filtered.length }} 条记录</div>
      </div>
    </div>

    <div class="filter-bar">
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
        <button class="btn" @click="tab = 'dashboard'">查询</button>
        <button class="btn-quick" :class="{ active: quickDays === 7 }" @click="setQuickRange(7)">近7天</button>
        <button class="btn-quick" :class="{ active: quickDays === 1 }" @click="setQuickRange(1)">今天</button>
        <button class="btn-quick" :class="{ active: quickDays === 30 }" @click="setQuickRange(30)">近30天</button>
        <button class="btn-quick" :class="{ active: quickDays === 90 }" @click="setQuickRange(90)">近90天</button>
        <button class="btn-quick" :class="{ active: quickDays === 0 }" @click="setQuickRange(0)">全部</button>
      </div>
    </div>

    <DashboardPage v-if="tab === 'dashboard'" :filtered="filtered" :category="category" :allSubCats="subCategoryFiltered" />
    <ProductPage   v-if="tab === 'product'"   :filtered="filtered" />
  </main>
</template>

<script setup>
import { computed, ref } from "vue";
import DashboardPage from "./components/DashboardPage.vue";
import ProductPage from "./components/ProductPage.vue";
import payload from "./data/dashboard-data.json";

const tab = ref("dashboard");
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

const subCategoryFiltered = computed(() =>
  payload.subCategoryRecords.filter((row) => {
    if (startDate.value && row.date < startDate.value) return false;
    if (endDate.value && row.date > endDate.value) return false;
    if (category.value !== "all" && row.category !== category.value) return false;
    return true;
  })
);

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
  const start = days === 0
    ? new Date(payload.dateMin)
    : (() => { const s = new Date(end); s.setDate(s.getDate() - days + 1); return s; })();
  startDate.value = start.toISOString().slice(0, 10);
  endDate.value = end.toISOString().slice(0, 10);
}
</script>
