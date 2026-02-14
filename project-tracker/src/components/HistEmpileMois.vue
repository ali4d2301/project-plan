<template>
  <div class="card" ref="cardRef" :class="{ 'is-fullscreen': fullscreen }">
    <div class="top">
      <h3 class="title">{{ title }}</h3>
      <div class="top-actions">
        <button class="fullscreen-btn" type="button" @click="toggleFullscreen">
          {{ fullscreen ? "Réduire" : "Plein écran" }}
        </button>
      </div>
    </div>

    <div ref="chartEl" class="chart"></div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-else-if="!loading && !rows.length" class="hint">
      Aucune donnée disponible
    </p>
  </div>
</template>

<script setup>
import * as echarts from "echarts"
import { ref, onMounted, onBeforeUnmount, watch } from "vue"

/* =======================
   Props & config API
======================= */
const props = defineProps({
    title: { type: String, default: "Répartition des tâches par mois" },
    endpoint: { type: String, default: "/api/planification/status-by-month" },
})

function apiBase() {        
  return import.meta.env.VITE_API_BASE || ""
}

/* =======================
   State
======================= */
const chartEl = ref(null)
const cardRef = ref(null)
let chart = null

const rows = ref([]) // [{ mois, statut, n }]
const loading = ref(false)
const error = ref("")
const fullscreen = ref(false)

async function toggleFullscreen() {
  const el = cardRef.value
  if (!el) return
  if (!(document.fullscreenEnabled && el?.requestFullscreen)) {
    fullscreen.value = !fullscreen.value
    document.body.classList.toggle("fs-lock", fullscreen.value)
    setTimeout(() => chart?.resize(), 50)
    return
  }
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
    } else {
      await el.requestFullscreen()
    }
  } catch {
    // no-op
  }
}

function syncFullscreen() {
  const isFs = document.fullscreenElement === cardRef.value
  fullscreen.value = isFs
  if (isFs) document.body.classList.add("fs-lock")
  else document.body.classList.remove("fs-lock")
  setTimeout(() => chart?.resize(), 50)
}

/* =======================
   Chart builder
======================= */
function buildOption(data) {
  const months = Array.from(new Set(data.map(r => r.mois)))
  const statuses = Array.from(new Set(data.map(r => r.statut)))

  const colorMap = {
    'Non demarrée': '#2196F3',
    'Réalisée': '#4CAF50',
    'En cours': '#9E9E9E',
    'Non réalisée': '#F44336'
  }

  const map = new Map()
  data.forEach(r => {
    map.set(`${r.mois}||${r.statut}`, Number(r.n) || 0)
  })

  const totals = months.map(m =>
    statuses.reduce((sum, statut) => sum + (map.get(`${m}||${statut}`) ?? 0), 0)
  )
  const maxValue = Math.max(0, ...totals)
  const step =
    maxValue <= 10 ? 2 :
    maxValue <= 20 ? 3 :
    maxValue <= 40 ? 5 :
    maxValue <= 80 ? 10 : 20
  const maxRounded = maxValue === 0 ? step : Math.ceil(maxValue / step) * step

  const series = statuses.map((statut, index) => ({
    name: statut,
    type: "bar",
    stack: "total",
    emphasis: { focus: "series" },
    data: months.map(m => map.get(`${m}||${statut}`) ?? 0),
    itemStyle: { color: colorMap[statut] || "#999" },
    ...(index === statuses.length - 1
      ? {
          label: {
            show: true,
            position: "top",
            distance: 6,
            color: "#1f2937",
            fontWeight: 600,
            formatter: (params) => {
              const value = totals[params.dataIndex] || 0
              return value ? value : ""
            }
          }
        }
      : {})
  }))

  return {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    legend: { top: 10 },
    grid: {
      left: 40,
      right: 20,
      top: 46,
      bottom: 36,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: months,
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: maxRounded,
      interval: step,
      axisLabel: { show: false },
      axisTick: { show: false },
      axisLine: { show: false },
      splitLine: { show: false },
    },
    series,
  }
}

/* =======================
   Render
======================= */
function render() {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  chart.setOption(buildOption(rows.value), { notMerge: true })
}

/* =======================
   Load data
======================= */
async function load() {
  loading.value = true
  error.value = ""

  try {
    const url = `${apiBase()}${props.endpoint}`
    const res = await fetch(url)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const json = await res.json()
    rows.value = json.data || []
  } catch (e) {
    rows.value = []
    error.value = e?.message || "Erreur de chargement"
  } finally {
    loading.value = false
  }
}

/* =======================
   Lifecycle
======================= */
function onResize() {
  if (chart) chart.resize()
}

onMounted(async () => {
  await load()
  render()
  window.addEventListener("resize", onResize)
  document.addEventListener("fullscreenchange", syncFullscreen)
  syncFullscreen()
})

watch(rows, render)

onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize)
  document.removeEventListener("fullscreenchange", syncFullscreen)
  document.body.classList.remove("fs-lock")
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.card {
  padding: 12px;
  border: 1px solid #e9e9e9;
  border-radius: 10px;
}
.card.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  height: 100%;
  width: 100%;
  border-radius: 0;
  border: none;
  padding: 16px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  background: #fff;
}
.card.is-fullscreen .chart {
  flex: 1;
  height: auto;
  min-height: 0;
}
.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.top-actions { display: flex; align-items: center; gap: 8px; }
.title { 
  margin:0; 
  font-weight:700; 
}
.chart {
  height: 330px;
  width: 100%;
}
.error {
  margin-top: 8px;
  color: #b00020;
}
.hint {
  margin-top: 8px;
  color: #666;
}
.fullscreen-btn {
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #64748b;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.fullscreen-btn:hover {
  background: #f8fafc;
  color: #111827;
  border-color: #cbd5f5;
}
.fullscreen-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
}

@media (max-width: 720px) {
  .top { flex-direction: column; align-items: flex-start; }
  .chart { height: 240px; }
}
</style>
