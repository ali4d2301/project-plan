<template>
  <div class="card" ref="cardRef" :class="{ 'is-fullscreen': fullscreen }">
    <div class="top">
      <h3>Nombre de tâches par entité</h3>
      <div class="top-actions">
        <span class="msg" v-if="error">{{ error }}</span>
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
  // "ALL" ou "YYYY-MM"
  period: { type: String, default: "ALL" }
})

const chartEl = ref(null)
const cardRef = ref(null)
let chart = null

const error = ref("")
const rows = ref([])
const fullscreen = ref(false)

async function toggleFullscreen() {
  const el = cardRef.value
  if (!el) return
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
  fullscreen.value = document.fullscreenElement === cardRef.value
  setTimeout(() => chart?.resize(), 50)
}

function wrapLabel(value, max = 12) {
  const text = String(value ?? "")
  if (text.length <= max) return text
  const cleaned = text.replace(/\s*\/\s*/g, " / ")
  const parts = cleaned.split(" ")
  const lines = []
  let line = ""

  for (const part of parts) {
    const next = line ? `${line} ${part}` : part
    if (next.length > max && line) {
      lines.push(line)
      line = part
      continue
    }
    if (next.length > max) {
      const chunks = part.match(new RegExp(`.{1,${max}}`, "g")) || [part]
      lines.push(...chunks.slice(0, -1))
      line = chunks[chunks.length - 1]
      continue
    }
    line = next
  }
  if (line) lines.push(line)
  return lines.join("\n")
}

function parsePeriod(p) {
  if (!p || p === "ALL") return null
  const [y, m] = p.split("-").map(Number)
  return { year: y, month: m }
}

async function load() {
  error.value = ""

  const base = import.meta.env.VITE_API_BASE || ""
  const p = parsePeriod(props.period)

  // ✅ endpoint: si ALL -> pas de year/month
  const url = p
    ? `${base}/api/planification/histogram-entites?year=${p.year}&month=${p.month}`
    : `${base}/api/planification/histogram-entites`

  try {
    const res = await fetch(url)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    rows.value = await res.json()
    render()
  } catch (e) {
    error.value = `Erreur de chargement: ${e.message || e}`
  }
}

function render() {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)

  const orderedRows = [...(rows.value || [])].sort((a, b) => {
    const diff = (Number(b.nb) || 0) - (Number(a.nb) || 0)
    if (diff !== 0) return diff
    return String(a.entite || "").localeCompare(String(b.entite || ""), "fr", { sensitivity: "base" })
  })

  const labels = orderedRows.map(r => r.entite)
  const values = orderedRows.map(r => Number(r.nb) || 0)

  chart.setOption({
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 20, top: 30, bottom: 52, containLabel: true },
    xAxis: {
      type: "category",
      data: labels,
      axisLabel: {
        interval: 0,
        rotate: 0,
        lineHeight: 14,
        margin: 12,
        formatter: (value) => wrapLabel(value, 12)
      }
    },
    yAxis: {
      type: "value",
      axisLabel: { show: false },
      axisTick: { show: false },
      axisLine: { show: false },
      splitLine: { show: false }
    },
    series: [
      {
        type: "bar",
        data: values,
        barMaxWidth: 40,
        itemStyle: { color: "#f59e0b" },
        label: {
          show: true,
          position: "top",
          distance: 6,
          color: "#1f2937",
          fontWeight: 600,
          formatter: (params) => (params.value ? params.value : "")
        }
      }
    ]
  })
}

function handleResize() { chart?.resize() }

onMounted(() => {
  load()
  window.addEventListener("resize", handleResize)
  document.addEventListener("fullscreenchange", syncFullscreen)
  syncFullscreen()
})

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize)
  document.removeEventListener("fullscreenchange", syncFullscreen)
  chart?.dispose()
  chart = null
})

// ✅ recharge auto quand le filtre global change
watch(() => props.period, () => load())
</script>

<style scoped>
.card { background:#fff; border:1px solid #eee; border-radius:12px; padding:14px; }
.card.is-fullscreen {
  height: 100%;
  width: 100%;
  border-radius: 0;
  border: none;
  padding: 16px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}
.card.is-fullscreen .chart {
  flex: 1;
  height: auto;
  min-height: 0;
}
.top { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:10px; }
.top-actions { display:flex; align-items:center; gap:8px; }
.chart { height:330px; width:100%; }
.msg { color:#b00020; font-size:13px; }
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
</style>
