<template>
  <main class="page">
    <header class="topbar">
      <div>
        <h1>万相台投放数据看板</h1>
        <p>{{ dataRangeLabel }} · 更新 {{ generatedAtLabel }}</p>
      </div>
      <div class="topbar-right">
        <nav class="tab-nav">
          <button :class="{ active: tab === 'dashboard' }" @click="tab = 'dashboard'">品类看板</button>
          <button :class="{ active: tab === 'product' }" @click="tab = 'product'">商品主体</button>
        </nav>
        <div class="status-pill">{{ filtered.length }} 条记录</div>
      </div>
    </header>

    <section class="toolbar">
      <label>
        <span>开始</span>
        <input v-model="startDate" type="date" :min="payload.dateMin" :max="payload.dateMax" />
      </label>
      <label>
        <span>结束</span>
        <input v-model="endDate" type="date" :min="payload.dateMin" :max="payload.dateMax" />
      </label>
      <label>
        <span>品类</span>
        <select v-model="category">
          <option value="all">全部品类</option>
          <option v-for="item in payload.categories" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <div class="quick-actions">
        <button :class="{ active: quickDays === 1 }" @click="setQuickRange(1)">今天</button>
        <button :class="{ active: quickDays === 7 }" @click="setQuickRange(7)">近7天</button>
        <button :class="{ active: quickDays === 30 }" @click="setQuickRange(30)">近30天</button>
        <button :class="{ active: quickDays === 0 }" @click="setQuickRange(0)">全部</button>
      </div>
    </section>

    <DashboardPage v-if="tab === 'dashboard'" :filtered="filtered" />
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

const dataRangeLabel = computed(() => {
  if (!payload.dateMin || !payload.dateMax) return "暂无数据";
  return `数据范围 ${payload.dateMin} 至 ${payload.dateMax}`;
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
