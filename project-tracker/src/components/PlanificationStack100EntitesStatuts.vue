<template>
  <div class="card" ref="cardRef" :class="{ 'is-fullscreen': fullscreen }">
    <div class="top">
      <h3>Répartition des statuts par entité</h3>
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
  // "ALL" ou "YYYY-MM" (filtre global)
  period: { type: String, default: "ALL" }
})

const chartEl = ref(null)
const cardRef = ref(null)
let chart = null

const error = ref("")
const raw = ref([])
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

const STATUS_COLORS = {
  "non demarree": "#2196F3",
  "realisee": "#4CAF50",
  "en cours": "#9E9E9E",
  "non realisee": "#F44336"
}

function normalizeText(value) {
  return String(value ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
}

function statusColor(name) {
  return STATUS_COLORS[normalizeText(name)] || "#7b8ba6"
}

function tintColor(hex, amount = 0.25) {
  const value = String(hex || "").replace("#", "")
  if (value.length !== 6) return hex
  const num = parseInt(value, 16)
  const r = (num >> 16) & 255
  const g = (num >> 8) & 255
  const b = num & 255
  const mix = (c) => Math.round(c + (255 - c) * amount)
  const toHex = (c) => c.toString(16).padStart(2, "0")
  return `#${toHex(mix(r))}${toHex(mix(g))}${toHex(mix(b))}`
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
  const [ys, ms] = String(p).split("-")
  const year = Number(ys)
  const month = Number(ms)
  if (!year || !month) return null
  return { year, month }
}

async function load() {
  error.value = ""
  const base = import.meta.env.VITE_API_BASE || ""
  const p = parsePeriod(props.period)

  const url = p
    ? `${base}/api/planification/stack100-entites-statuts?year=${p.year}&month=${p.month}`
    : `${base}/api/planification/stack100-entites-statuts`

  try {
    const res = await fetch(url)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    raw.value = await res.json()
    render()
  } catch (e) {
    error.value = `Erreur de chargement: ${e.message || e}`
  }
}

function render() {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)

  // 1) construire la liste des entités et statuts
  const entites = Array.from(new Set(raw.value.map(r => r.entite)))
  const statuts = Array.from(new Set(raw.value.map(r => r.statut)))

  // 2) matrice nb[statut][entite]
  const map = new Map()
  for (const r of raw.value) {
    map.set(`${r.statut}||${r.entite}`, Number(r.nb) || 0)
  }

  const totals = entites.map(e =>
    statuts.reduce((sum, st) => sum + (map.get(`${st}||${e}`) || 0), 0)
  )
  const totalByEntite = new Map(entites.map((e, i) => [e, totals[i]]))
  const sortedEntites = [...entites]
    .map(e => ({ entite: e, total: totalByEntite.get(e) || 0 }))
    .sort((a, b) => {
      const diff = b.total - a.total
      if (diff !== 0) return diff
      return String(a.entite || "").localeCompare(String(b.entite || ""), "fr", { sensitivity: "base" })
    })
    .map(item => item.entite)

  // 3) séries empilées à 100% via stack + formatter %
  const series = statuts.map(st => ({
    name: st,
    type: "bar",
    stack: "total",
    emphasis: { focus: "series" },
    data: sortedEntites.map(e => map.get(`${st}||${e}`) || 0),
    itemStyle: { color: tintColor(statusColor(st), 0.2) },
  }))

  chart.setOption({
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (items) => {
        // items = toutes les barres empilées pour une entité
        const total = items.reduce((s, it) => s + (it.value || 0), 0)
        const title = items[0]?.axisValue ?? ""
        const lines = [`<b>${title}</b>`]
        for (const it of items) {
          const v = it.value || 0
          const pct = total ? ((v / total) * 100).toFixed(0) : 0
          lines.push(`${it.marker} ${it.seriesName}: ${pct}% (${v})`)
        }
        return lines.join("<br/>")
      }
    },
    legend: {
      top: 0,
      data: statuts.map((st) => ({ name: st, itemStyle: { color: statusColor(st) } }))
    },
    grid: { left: 40, right: 20, top: 46, bottom: 52, containLabel: true },
    xAxis: {
      type: "category",
      data: sortedEntites,
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
      max: 100,
      axisLabel: { show: false },
      axisTick: { show: false },
      axisLine: { show: false },
      splitLine: { show: false }
    },
    // ✅ magie 100%: transformer l'affichage via dataset? (alternative)
    // Ici on calcule les % côté series via "stackStrategy: 'all'" n'existe pas partout.
    // Donc: on convertit nous-mêmes en % juste avant (voir ci-dessous)
    series: toPercent(series, sortedEntites.length)
  })
}

// Convertit les séries (valeurs absolues) en % par entité (colonne)
function toPercent(series, nEntites) {
  // totaux par entité
  const totals = Array(nEntites).fill(0)
  for (const s of series) {
    s.data.forEach((v, i) => totals[i] += (v || 0))
  }
  // remplacer data par %
  return series.map(s => ({
    ...s,
    data: s.data.map((v, i) => {
      const t = totals[i] || 0
      return t ? Number(((v / t) * 100).toFixed(2)) : 0
    }),
    label: { show: false }
  }))
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
.chart { height: 340px; width: 100%; }
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
