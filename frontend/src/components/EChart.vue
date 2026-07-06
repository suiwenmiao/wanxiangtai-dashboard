<template>
  <div ref="chartEl" class="echart" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  option: {
    type: Object,
    required: true
  }
});

const chartEl = ref(null);
let chart;
let observer;

function render() {
  if (!chart && chartEl.value) {
    chart = echarts.init(chartEl.value);
  }
  if (chart) chart.setOption(props.option, true);
}

function resize() {
  if (chart) chart.resize();
}

watch(() => props.option, render, { deep: true });

onMounted(() => {
  render();
  window.addEventListener("resize", resize);
  if (window.ResizeObserver) {
    observer = new ResizeObserver(() => resize());
    if (chartEl.value) observer.observe(chartEl.value);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resize);
  if (observer) observer.disconnect();
  if (chart) chart.dispose();
});
</script>
