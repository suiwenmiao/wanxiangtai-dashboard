<template>
  <section v-if="!payload" class="dashboard-login" aria-labelledby="dashboard-login-title">
    <div class="dashboard-login-mark">万相台投放数据看板</div>
    <h1 id="dashboard-login-title">解锁投放看板</h1>
    <p>输入访问密码后，三类看板数据仅在当前浏览器中本地解密。</p>
    <form @submit.prevent="unlock">
      <label for="dashboard-password">访问密码</label>
      <input id="dashboard-password" v-model="password" type="password" autocomplete="current-password" :disabled="unlocking" autofocus />
      <p v-if="authError" class="dashboard-login-error">{{ authError }}</p>
      <button type="submit" :disabled="unlocking || !password">{{ unlocking ? "正在解锁..." : "进入看板" }}</button>
    </form>
  </section>
  <main v-else class="page">
    <div class="header">
      <div>
        <h1>万相台投放数据看板</h1>
        <div class="update-time">数据范围: {{ dataRangeLabel }} · 更新 {{ generatedAtLabel }}</div>
      </div>
      <div class="header-right">
        <nav class="tab-nav">
          <button :class="{ active: tab === 'dashboard' || tab === 'product' }" @click="selectTab('dashboard')">投放分析</button>
          <button :class="{ active: tab === 'daily' }" @click="selectTab('daily')">投放日报</button>
          <button :class="{ active: tab === 'weekly' }" @click="selectTab('weekly')">投放周报</button>
          <button :class="{ active: tab === 'monthly' }" @click="selectTab('monthly')">投放月报</button>
          <button :class="{ active: tab === 'creative' }" @click="selectTab('creative')">素材看板</button>
        </nav>
        <div class="status-pill">{{ filtered.length }} 条记录</div>
      </div>
    </div>

    <div v-if="tab !== 'creative' && tab !== 'daily' && tab !== 'weekly' && tab !== 'monthly'" class="filter-bar">
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
        <details ref="categoryPicker" class="multi-picker">
          <summary>{{ selectedCategories.length ? `已选 ${selectedCategories.length} 个品类` : "全部品类" }}</summary>
          <div class="multi-picker-menu">
            <label v-for="item in payload.categories" :key="item" class="multi-option">
              <input v-model="selectedCategories" type="checkbox" :value="item" />
              <span>{{ item }}</span>
            </label>
            <button class="picker-done" type="button" @click="closeCategoryPicker">完成</button>
          </div>
        </details>
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

    <DashboardPage v-if="tab === 'dashboard' || tab === 'product'" :payload="payload" :filtered="filtered" :prevFiltered="prevFiltered" :category="selectedCategories" :allSubCats="subCategoryFiltered" :crypto-key="cryptoKey" :initial-view="tab === 'product' ? 'subject' : 'overview'" />
    <DailyReportPage v-if="tab === 'daily'" :payload="payload" :crypto-key="cryptoKey" />
    <WeeklyReportPage v-if="tab === 'weekly'" key="weekly" :payload="payload" :crypto-key="cryptoKey" />
    <WeeklyReportPage v-if="tab === 'monthly'" key="monthly" :payload="payload" :crypto-key="cryptoKey" period="month" />
    <CreativePage  v-if="tab === 'creative'" :crypto-key="cryptoKey" />
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from "vue";
import DashboardPage from "./components/DashboardPage.vue";
import DailyReportPage from "./components/DailyReportPage.vue";
import WeeklyReportPage from "./components/WeeklyReportPage.vue";
import CreativePage from "./components/CreativePage.vue";
const payload = ref(null);
const cryptoKey = shallowRef(null);
const password = ref("");
const unlocking = ref(false);
const authError = ref("");
const tab = ref(tabFromHash());
const startDate = ref("");
const endDate = ref("");
const selectedCategories = ref([]);
const categoryPicker = ref(null);
const quickDays = ref(1);

const filtered = computed(() =>
  (payload.value?.records || []).filter(r => {
    if (startDate.value && r.date < startDate.value) return false;
    if (endDate.value && r.date > endDate.value) return false;
    if (selectedCategories.value.length && !selectedCategories.value.includes(r.category)) return false;
    return true;
  })
);

const subCategoryFiltered = computed(() =>
  (payload.value?.subCategoryRecords || []).filter(r => {
    if (startDate.value && r.date < startDate.value) return false;
    if (endDate.value && r.date > endDate.value) return false;
    if (selectedCategories.value.length && !selectedCategories.value.includes(r.category)) return false;
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
  return (payload.value?.records || []).filter(r => {
    if (r.date < prevStart.value) return false;
    if (r.date > prevEnd.value) return false;
    if (selectedCategories.value.length && !selectedCategories.value.includes(r.category)) return false;
    return true;
  });
});

const dataRangeLabel = computed(() => {
  if (!payload.value?.dateMin || !payload.value?.dateMax) return "暂无数据";
  return `${payload.value.dateMin} ~ ${payload.value.dateMax}`;
});
const generatedAtLabel = computed(() => {
  if (!payload.value?.generatedAt) return "未生成";
  return payload.value.generatedAt.replace("T", " ");
});

function setQuickRange(days) {
  quickDays.value = days;
  if (!payload.value?.dateMax) return;
  const end = new Date(payload.value.dateMax);
  const start = days === 0 ? new Date(payload.value.dateMin)
    : (() => { const s = new Date(end); s.setDate(s.getDate() - days + 1); return s; })();
  startDate.value = start.toISOString().slice(0, 10);
  endDate.value = end.toISOString().slice(0, 10);
}

function selectTab(nextTab) {
  tab.value = nextTab;
  const hashMap = { creative: "#/creative", product: "#/product", daily: "#/daily", weekly: "#/weekly", monthly: "#/monthly", dashboard: "#/" };
  history.replaceState(null, "", hashMap[nextTab] || "#/");
}
function syncTabFromHash() {
  tab.value = tabFromHash();
}
function tabFromHash() {
  if (location.hash === "#/creative") return "creative";
  if (location.hash === "#/product") return "product";
  if (location.hash === "#/daily") return "daily";
  if (location.hash === "#/weekly") return "weekly";
  if (location.hash === "#/monthly") return "monthly";
  return "dashboard";
}
function closeCategoryPicker() {
  if (categoryPicker.value) categoryPicker.value.open = false;
}
function closeCategoryPickerOnOutside(event) {
  if (categoryPicker.value && !categoryPicker.value.contains(event.target)) closeCategoryPicker();
}
function base64Bytes(value) {
  const binary = atob(value);
  return Uint8Array.from(binary, char => char.charCodeAt(0));
}
async function decodePayload(envelope, decrypted) {
  if (envelope.compression !== "gzip") return JSON.parse(new TextDecoder().decode(decrypted));
  const stream = new Blob([decrypted]).stream().pipeThrough(new DecompressionStream("gzip"));
  return JSON.parse(new TextDecoder().decode(await new Response(stream).arrayBuffer()));
}
async function unlock() {
  unlocking.value = true;
  authError.value = "";
  try {
    const response = await fetch(`${import.meta.env.BASE_URL}data/dashboard-data.enc.json`, { cache: "no-store" });
    if (!response.ok) throw new Error("未找到加密看板数据");
    const envelope = await response.json();
    const passwordKey = await crypto.subtle.importKey("raw", new TextEncoder().encode(password.value), "PBKDF2", false, ["deriveKey"]);
    const key = await crypto.subtle.deriveKey(
      { name: "PBKDF2", salt: base64Bytes(envelope.kdf.salt), iterations: envelope.kdf.iterations, hash: envelope.kdf.hash },
      passwordKey,
      { name: "AES-GCM", length: 256 }, false, ["decrypt"],
    );
    const decrypted = await crypto.subtle.decrypt({ name: "AES-GCM", iv: base64Bytes(envelope.iv) }, key, base64Bytes(envelope.ciphertext));
    payload.value = await decodePayload(envelope, decrypted);
    cryptoKey.value = key;
    startDate.value = payload.value.dateMax || "";
    endDate.value = payload.value.dateMax || "";
    password.value = "";
  } catch (error) {
    authError.value = "密码不正确，或加密数据暂不可用。";
  } finally {
    unlocking.value = false;
  }
}
onMounted(() => {
  window.addEventListener("hashchange", syncTabFromHash);
  window.addEventListener("click", closeCategoryPickerOnOutside);
});
onBeforeUnmount(() => {
  window.removeEventListener("hashchange", syncTabFromHash);
  window.removeEventListener("click", closeCategoryPickerOnOutside);
});
</script>
<style scoped>
.huanbi-label { font-size: 12px; color: #888; white-space: nowrap; padding: 6px 10px; background: #f0f2f5; border-radius: 4px; }
</style>
