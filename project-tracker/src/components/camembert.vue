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
import { ref, onMounted, onBeforeUnmount, watch } from "vue"
import * as echarts from "echarts"

const props = defineProps({
  title: { type: String, default: "Répartition des niveaux d'exécution des tâches" },
  endpoint: { type: String, default: "/api/planification/pie-by-thera" }, 
})

const chartEl = ref(null)
const cardRef = ref(null)
let chart = null

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
    const res = await fetch(url)
    if (!res.ok) throw new Error(`API error: ${res.status}`)
    rows.value = await res.json()
  } catch (e) {
    error.value = e?.message || "Erreur inconnue"
    rows.value = []
  } finally {
    loading.value = false
  }
}

function render() {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)

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
    legend: { top: 10, left: "center" },
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
                    y: -10,
                    style: {
                        text: `${total}`,
                        font: "700 42px sans-serif",
                        fill: "#111827",
                        textAlign: "center",
                        textVerticalAlign: "middle"
                    }
                },
                {
                    type: "text",
                    x: 0,
                    y: 22,
                    style: {
                        text: `${totalLabel}`,
                        font: "500 18px sans-serif",
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
            labelLine: { length: 14, length2: 12 },
            label: {
                //show: false, // 👈 Cacher les étiquettes
                position: "outside", // 👈 Déplacer le texte à l’extérieur
                formatter: "{b}\n{d}%",
                fontSize: 12,
                lineHeight: 16
                //formatter: "{b}\n{c} tâches ({d}%)"
            }
        }
    ],
  })
}

function onResize() {
  chart?.resize()
}

onMounted(async () => {
  await load()
  render()
  window.addEventListener("resize", onResize)
  document.addEventListener("fullscreenchange", syncFullscreen)
  syncFullscreen()
})

watch(() => props.endpoint, async () => {
  await load()
  render()
})

onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize)
  document.removeEventListener("fullscreenchange", syncFullscreen)
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
  height: 100%;
  width: 100%;
  border-radius: 0;
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
.top { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.top-actions { display:flex; align-items:center; gap:8px; }
.title { margin:0; font-weight:700; }
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

@media (max-width: 720px) {
  .top { flex-direction: column; align-items: flex-start; }
  .chart { height: 240px; }
}
</style>
