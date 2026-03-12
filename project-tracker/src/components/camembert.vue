<template>
  <div class="card" ref="cardRef" :class="{ 'is-fullscreen': fullscreen }">
    <div class="top">
      <h3 class="title">{{ title }}</h3>
      <div class="top-actions">
        <span v-if="loading" class="hint">Chargement…</span>
        <span v-else-if="error" class="error">{{ error }}</span>
        <button class="fullscreen-btn" type="button" @click="toggleFullscreen">
          {{ fullscreen ? "Réduire" : "Plein écran" }}
        </button>
      </div>
    </div>

    <div ref="chartEl" class="chart"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from "vue"
import * as echarts from "echarts"
import { fetchWithRetry, getFetchErrorMessage } from "../utils/http"

const props = defineProps({
  title: { type: String, default: "Répartition des niveaux d'exécution des tâches" },
  endpoint: { type: String, default: "/api/planification/pie-by-thera" }, 
})

const chartEl = ref(null)
const cardRef = ref(null)
let chart = null
let resizeObserver = null

const loading = ref(false)
const error = ref("")
const rows = ref([])
const fullscreen = ref(false)

async function toggleFullscreen() {
  const el = cardRef.value
  if (!el) return
  if (!(document.fullscreenEnabled && el?.requestFullscreen)) {
    fullscreen.value = !fullscreen.value
    document.body.classList.toggle("fs-lock", fullscreen.value)
    resizeChartSoon(true)
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
  resizeChartSoon(true)
}

function apiBase() {
  // En prod (Netlify), tu as déjà VITE_API_BASE
  // En dev, ex: http://localhost:8000
  return import.meta.env.VITE_API_BASE || ""
}

async function load() {
  loading.value = true
  error.value = ""
  try {
    const url = `${apiBase()}${props.endpoint}`
    const res = await fetchWithRetry(url)
    rows.value = await res.json()
  } catch (e) {
    error.value = getFetchErrorMessage(e, "la repartition des niveaux d'execution des taches")
    rows.value = []
  } finally {
    loading.value = false
  }
}

function render() {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  const isFs = fullscreen.value
  const width = chartEl.value.clientWidth || 800
  const height = chartEl.value.clientHeight || 300
  const base = Math.max(280, Math.min(width, height))
  const fsBoost = isFs ? 1.22 : 1
  const legendSize = clamp(Math.round(base * 0.042 * fsBoost), 12, 30)
  const ringLabelSize = clamp(Math.round(base * 0.05 * fsBoost), 12, 38)
  const totalSize = clamp(Math.round(base * 0.16 * fsBoost), 42, 110)
  const totalLabelSize = clamp(Math.round(base * 0.07 * fsBoost), 18, 48)
  const centerValueOffsetY = Math.round(-totalSize * 0.25)
  const centerLabelOffsetY = Math.round(totalSize * 0.58)
  const labelLineLength = clamp(Math.round(base * 0.045), 14, 34)
  const labelLineLength2 = clamp(Math.round(base * 0.04), 12, 30)

  const data = (rows.value || []).map(r => ({
    name: r.label,
    value: Number(r.value) || 0,
  }))
  const total = data.reduce((sum, item) => sum + (item.value || 0), 0)
  const totalLabel = total === 1 ? "Tâche" : "Tâches"

  chart.setOption({
    color: ['#2196F3', '#4CAF50', '#9E9E9E', '#F44336'],
    tooltip: { 
        trigger: "item",
        formatter: "{b} : {c} tâches ({d}%)"
    },
    legend: {
      top: 10,
      left: "center",
      textStyle: {
        fontSize: legendSize,
        fontWeight: isFs ? 600 : 500,
      },
      itemWidth: isFs ? 34 : 24,
      itemHeight: isFs ? 20 : 14,
      itemGap: isFs ? 18 : 10,
    },
    graphic: [
        {
            type: "group",
            left: "50%",
            top: "58%",
            z: 10,
            bounding: "raw",
            children: [
                {
                    type: "text",
                    x: 0,
                    y: centerValueOffsetY,
                    style: {
                        text: `${total}`,
                        font: `700 ${totalSize}px "Space Grotesk", "Segoe UI", Tahoma, sans-serif`,
                        fill: "#111827",
                        textAlign: "center",
                        textVerticalAlign: "middle"
                    }
                },
                {
                    type: "text",
                    x: 0,
                    y: centerLabelOffsetY,
                    style: {
                        text: `${totalLabel}`,
                        font: `500 ${totalLabelSize}px "Space Grotesk", "Segoe UI", Tahoma, sans-serif`,
                        fill: "#6b7280",
                        textAlign: "center",
                        textVerticalAlign: "middle"
                    }
                }
            ]
        }
    ],
    series: [
        {
            type: "pie",
            radius: ["52%", "78%"],
            center: ["50%", "58%"],
            data,
            avoidLabelOverlap: true,
            labelLayout: { hideOverlap: true },
            labelLine: { length: labelLineLength, length2: labelLineLength2 },
            label: {
                //show: false, // 👈 Cacher les étiquettes
                position: "outside", // 👈 Déplacer le texte à l’extérieur
                formatter: "{b}\n{d}%",
                fontSize: ringLabelSize,
                lineHeight: Math.round(ringLabelSize * 1.35),
                fontWeight: isFs ? 600 : 500
                //formatter: "{b}\n{c} tâches ({d}%)"
            }
        }
    ],
  })
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function onResize() {
  resizeChartSoon(true)
}

async function resizeChartSoon(reRender = false) {
  await nextTick()
  requestAnimationFrame(() => {
    if (!chart || !chartEl.value) return
    chart.resize({
      width: chartEl.value.clientWidth,
      height: chartEl.value.clientHeight,
    })
    if (reRender) {
      requestAnimationFrame(() => {
        render()
      })
    }
  })
}

onMounted(async () => {
  await load()
  render()
  window.addEventListener("resize", onResize)
  document.addEventListener("fullscreenchange", syncFullscreen)
  if (typeof ResizeObserver !== "undefined" && chartEl.value) {
    resizeObserver = new ResizeObserver(() => resizeChartSoon(true))
    resizeObserver.observe(chartEl.value)
  }
  syncFullscreen()
})

watch(() => props.endpoint, async () => {
  await load()
  render()
})

watch(fullscreen, () => {
  resizeChartSoon(true)
})

onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize)
  document.removeEventListener("fullscreenchange", syncFullscreen)
  resizeObserver?.disconnect()
  resizeObserver = null
  document.body.classList.remove("fs-lock")
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.card { background:#fff; border-radius:12px; padding:12px; }
.card.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  height: 100vh;
  width: 100vw;
  border-radius: 0;
  padding: 16px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  background: #fff;
}
.card.is-fullscreen .chart {
  flex: 1;
  height: calc(100vh - 140px);
  min-height: 420px;
}
.top { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.top-actions { display:flex; align-items:center; gap:8px; }
.title { margin:0; font-weight:700; }
.card.is-fullscreen .title { font-size: 42px; line-height: 1.1; }
.hint { opacity:.7; }
.error { color:#b00020; }
.chart { width:100%; height:300px; }
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
.card.is-fullscreen .fullscreen-btn {
  font-size: 18px;
  padding: 10px 16px;
}

@media (max-width: 720px) {
  .top { flex-direction: column; align-items: flex-start; }
  .chart { height: 240px; }
}
</style>
