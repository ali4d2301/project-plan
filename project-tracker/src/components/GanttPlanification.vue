<template>
  <section
    ref="ganttRootRef"
    class="gantt"
    :class="{ 'is-fullscreen': ganttFullscreen }"
  >
    <div class="gantt__filters">
      <DateRangeFilter
        label="Periode (date fin)"
        v-model="period"
      />
      <MultiSelectDropdown
        v-model="entites"
        label="Entites"
        endpoint="/api/planification/entites"
      />
      <MultiSelectDropdown
        v-model="statuts"
        label="Statuts"
        endpoint="/api/planification/statuts"
        :maxChips="3"
      />
    </div>

    <div class="gantt__card">
      <div class="gantt__legend-bar">
        <div class="gantt__legend">
          <div class="gantt__legend-item">
            <span class="gantt__legend-dot dot--not-started"></span>
            Non demarree
          </div>
          <div class="gantt__legend-item">
            <span class="gantt__legend-dot dot--in-progress"></span>
            En cours
          </div>
          <div class="gantt__legend-item">
            <span class="gantt__legend-dot dot--done"></span>
            Realisee
          </div>
          <div class="gantt__legend-item">
            <span class="gantt__legend-dot dot--not-done"></span>
            Non realisee
          </div>
        </div>
        <button
          class="gantt__fullscreen"
          type="button"
          @click="toggleGanttFullscreen"
        >
          {{ ganttFullscreen ? "Quitter" : "Plein écran" }}
        </button>
      </div>
      <p v-if="loading" class="gantt__info">Chargement...</p>
      <p v-else-if="error" class="gantt__error">{{ error }}</p>
      <p v-else-if="!filteredTasks.length" class="gantt__info">Aucune donnee.</p>

      <div
        v-else
        class="gantt__board"
        :style="{
          '--gantt-left': leftWidth + 'px',
          '--gantt-timeline': timelineWidth + 'px'
        }"
      >
        <div class="gantt__header">
          <div class="gantt__h-left">
            Taches
            <span class="gantt__col-resizer" @mousedown="startResize"></span>
          </div>
          <div class="gantt__h-right">
            <div class="gantt__ticks">
              <div
                v-for="t in ticks"
                :key="t.key"
                class="gantt__tick"
                :style="{ left: t.left + '%' }"
              >
                {{ t.label }}
              </div>
            </div>
          </div>
        </div>

        <div class="gantt__rows">
          <div v-for="task in filteredTasks" :key="task.id" class="gantt__row">
            <div class="gantt__task">
              <div class="gantt__task-title">{{ task.taches }}</div>
              <div class="gantt__task-meta">
                {{ task.entites || "-" }} - {{ task.statut || "-" }}
              </div>
            </div>
            <div class="gantt__bar-area">
              <div class="gantt__bar-track">
                <div
                  class="gantt__bar"
                  :class="statusClass(task)"
                  :style="barStyle(task)"
                  @mouseenter="showTooltip(task, $event)"
                  @mousemove="moveTooltip($event)"
                  @mouseleave="hideTooltip"
                >
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <teleport to="body">
    <div
      v-if="tooltip.show"
      class="gantt__tooltip-layer"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >
      <div class="gantt__tooltip">
        <div class="gantt__tip-title">{{ tooltipTask.taches || "Tache" }}</div>
        <div class="gantt__tip-row">
          <span class="gantt__tip-label">Entite</span>
          <span class="gantt__tip-value">{{ tooltipTask.entites || "-" }}</span>
        </div>
        <div class="gantt__tip-row">
          <span class="gantt__tip-label">Statut</span>
          <span class="gantt__tip-value">{{ tooltipTask.statut || "-" }}</span>
        </div>
        <div class="gantt__tip-row">
          <span class="gantt__tip-label">Debut</span>
          <span class="gantt__tip-value">{{ formatDateFr(tooltipTask.date_debut) }}</span>
        </div>
        <div class="gantt__tip-row">
          <span class="gantt__tip-label">Fin</span>
          <span class="gantt__tip-value">{{ formatDateFr(tooltipTask.date_fin) }}</span>
        </div>
        <div class="gantt__tip-row">
          <span class="gantt__tip-label">Duree</span>
          <span class="gantt__tip-value">{{ durationDays(tooltipTask) }} j</span>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue"
import DateRangeFilter from "./DateRangeFilter.vue"
import MultiSelectDropdown from "./MultiSelectFilter.vue"

const period = ref({ start: "2025-10-15", end: "2026-02-28" })
const entites = ref(["ALL"])
const statuts = ref(["ALL"])
const leftWidth = ref(420)
const ganttRootRef = ref(null)
const ganttFullscreen = ref(false)

const tasks = ref([])
const loading = ref(false)
const error = ref("")
const tooltip = ref({ show: false, x: 0, y: 0, task: null })

function apiBase() {
  return import.meta.env.VITE_API_BASE || ""
}

function pickSingle(sel) {
  if (!Array.isArray(sel)) return "ALL"
  if (sel.includes("ALL") || sel.length !== 1) return "ALL"
  return sel[0]
}

const url = computed(() => {
  const base = `${apiBase()}/api/planification/gantt`
  const params = new URLSearchParams()
  if (period.value?.start) params.set("start", period.value.start)
  if (period.value?.end) params.set("end", period.value.end)
  const ent = pickSingle(entites.value)
  const sta = pickSingle(statuts.value)
  if (ent !== "ALL") params.set("entites", ent)
  if (sta !== "ALL") params.set("statut", sta)
  const qs = params.toString()
  return qs ? `${base}?${qs}` : base
})

async function load() {
  loading.value = true
  error.value = ""
  try {
    const res = await fetch(url.value)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    tasks.value = Array.isArray(data) ? data : (data?.data ?? [])
  } catch (e) {
    error.value = "Erreur lors du chargement."
    tasks.value = []
  } finally {
    loading.value = false
  }
}

watch(url, () => {
  load()
}, { immediate: true })

async function toggleGanttFullscreen() {
  const el = ganttRootRef.value
  if (!el) return
  if (!(document.fullscreenEnabled && el?.requestFullscreen)) {
    ganttFullscreen.value = !ganttFullscreen.value
    document.body.classList.toggle("fs-lock", ganttFullscreen.value)
    return
  }
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
    } else {
      await el.requestFullscreen()
    }
  } catch {
    // no-op: fullscreen might be blocked by browser policy
  }
}

function syncGanttFullscreen() {
  const el = ganttRootRef.value
  const isFs = !!document.fullscreenElement && document.fullscreenElement === el
  ganttFullscreen.value = isFs
  if (isFs) document.body.classList.add("fs-lock")
  else document.body.classList.remove("fs-lock")
}

onMounted(() => {
  document.addEventListener("fullscreenchange", syncGanttFullscreen)
  syncGanttFullscreen()
})

onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", syncGanttFullscreen)
  document.body.classList.remove("fs-lock")
})

function parseDate(s) {
  if (!s || typeof s !== "string") return null
  return new Date(`${s}T00:00:00`)
}

function daysBetween(a, b) {
  const ms = b - a
  return Math.round(ms / (1000 * 60 * 60 * 24))
}

function durationDays(task) {
  const s = parseDate(task?.date_debut)
  const e = parseDate(task?.date_fin)
  if (!s || !e) return 0
  return Math.max(1, daysBetween(s, e) + 1)
}

function normalizeStatus(s) {
  const v = String(s || "").trim().toLowerCase()
  return v.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
}

function statusClass(task) {
  const s = normalizeStatus(task?.statut)
  if (!s) return "bar--unknown"
  if (s.includes("non demar")) return "bar--not-started"
  if (s.includes("en cours")) return "bar--in-progress"
  if (s.includes("non realise")) return "bar--not-done"
  if (s.includes("realise")) return "bar--done"
  return "bar--unknown"
}

const filteredTasks = computed(() => {
  let out = tasks.value || []

  // Filtre entites
  const entSel = entites.value || ["ALL"]
  if (!entSel.includes("ALL")) {
    out = out.filter(t => entSel.includes(String(t?.entites ?? "")))
  }

  // Filtre statut
  const staSel = statuts.value || ["ALL"]
  if (!staSel.includes("ALL")) {
    out = out.filter(t => staSel.includes(String(t?.statut ?? "")))
  }

  // Filtre periode sur date_fin
  if (period.value?.start) {
    out = out.filter(t => String(t?.date_fin || "") >= period.value.start)
  }
  if (period.value?.end) {
    out = out.filter(t => String(t?.date_fin || "") <= period.value.end)
  }

  return out.sort((a, b) => {
    const da = String(a?.date_debut || "")
    const db = String(b?.date_debut || "")
    if (da === db) return String(a?.date_fin || "").localeCompare(String(b?.date_fin || ""))
    return da.localeCompare(db)
  })
})

const tooltipTask = computed(() => tooltip.value.task || {})

const rangeStart = computed(() => {
  const s = parseDate(period.value?.start)
  if (s) return s
  let min = null
  for (const t of filteredTasks.value) {
    const d = parseDate(t?.date_debut) || parseDate(t?.date_fin)
    if (d && (!min || d < min)) min = d
  }
  return min
})

const rangeEnd = computed(() => {
  const e = parseDate(period.value?.end)
  if (e) return e
  let max = null
  for (const t of filteredTasks.value) {
    const d = parseDate(t?.date_fin) || parseDate(t?.date_debut)
    if (d && (!max || d > max)) max = d
  }
  return max
})

const totalDays = computed(() => {
  if (!rangeStart.value || !rangeEnd.value) return 0
  return Math.max(1, daysBetween(rangeStart.value, rangeEnd.value) + 1)
})

const pxPerDay = 6

const timelineWidth = computed(() => {
  const days = totalDays.value || 0
  const w = days * pxPerDay
  return Math.max(320, w)
})

function barStyle(task) {
  const s = parseDate(task?.date_debut)
  const e = parseDate(task?.date_fin)
  if (!s || !e || !rangeStart.value || !rangeEnd.value || !totalDays.value) return {}

  const start = s < rangeStart.value ? rangeStart.value : s
  const end = e > rangeEnd.value ? rangeEnd.value : e

  const leftDays = Math.max(0, daysBetween(rangeStart.value, start))
  const widthDays = Math.max(1, daysBetween(start, end) + 1)

  return {
    left: `${(leftDays / totalDays.value) * 100}%`,
    width: `${(widthDays / totalDays.value) * 100}%`,
  }
}

function formatDateFr(s) {
  const d = parseDate(s)
  if (!d) return ""
  const dd = String(d.getDate()).padStart(2, "0")
  const mm = String(d.getMonth() + 1).padStart(2, "0")
  const yyyy = d.getFullYear()
  return `${dd}/${mm}/${yyyy}`
}

function formatTickLabel(d) {
  const day = d.getDate()
  const months = ["janv", "fev", "mars", "avr", "mai", "juin", "juil", "aout", "sept", "oct", "nov", "dec"]
  return `${day} ${months[d.getMonth()]}`
}

const ticks = computed(() => {
  if (!rangeStart.value || !rangeEnd.value || !totalDays.value) return []
  const out = []
  const step = 7
  const d = new Date(rangeStart.value)
  d.setDate(15)
  while (d < rangeStart.value) {
    d.setDate(d.getDate() + step)
  }
  while (d <= rangeEnd.value) {
    const left = ((daysBetween(rangeStart.value, d) + 1) / totalDays.value) * 100
    if (left >= 0 && left <= 100) {
      out.push({
        key: `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`,
        left,
        label: formatTickLabel(d),
      })
    }
    d.setDate(d.getDate() + step)
  }
  return out
})

function startResize(e) {
  e.preventDefault()
  const startX = e.clientX
  const startW = leftWidth.value

  function onMove(ev) {
    const w = Math.min(520, Math.max(220, startW + (ev.clientX - startX)))
    leftWidth.value = w
  }

  function onUp() {
    document.removeEventListener("mousemove", onMove)
    document.removeEventListener("mouseup", onUp)
  }

  document.addEventListener("mousemove", onMove)
  document.addEventListener("mouseup", onUp)
}

function positionTooltip(e) {
  const pad = 12
  const width = 260
  const height = 170
  let x = e.clientX + 14
  let y = e.clientY + 14

  if (x + width + pad > window.innerWidth) x = e.clientX - width - 14
  if (y + height + pad > window.innerHeight) y = e.clientY - height - 14

  tooltip.value.x = Math.max(pad, x)
  tooltip.value.y = Math.max(pad, y)
}

function showTooltip(task, e) {
  tooltip.value.show = true
  tooltip.value.task = task
  positionTooltip(e)
}

function moveTooltip(e) {
  if (!tooltip.value.show) return
  positionTooltip(e)
}

function hideTooltip() {
  tooltip.value.show = false
  tooltip.value.task = null
}
</script>

<style scoped>
.gantt {
  display: grid;
  gap: 12px;
  --gantt-left: 320px;
  max-width: 100%;
  overflow-x: hidden;
  overflow-y: visible;
}
.gantt.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  height: 100%;
  width: 100%;
  padding: 12px;
  box-sizing: border-box;
  background: #f6f7fb;
  grid-template-rows: auto 1fr;
}

.gantt__filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.gantt__filters > * { min-width: 0; }

.gantt__legend-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 6px 4px 10px;
  border-bottom: 1px solid #eef2f7;
  margin-bottom: 10px;
}
.gantt__legend {
  display: flex;
  gap: 18px;
  align-items: center;
  flex-wrap: wrap;
  flex: 1;
}
.gantt__legend-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}
.gantt__legend-dot {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  display: inline-block;
}
.dot--not-started { background: #2563eb; }
.dot--in-progress { background: #6b7280; }
.dot--done { background: #16a34a; }
.dot--not-done { background: #dc2626; }

.gantt__card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 12px;
  width: 100%;
  box-sizing: border-box;
  overflow-x: hidden;
  overflow-y: visible;
}
.gantt.is-fullscreen .gantt__card {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.gantt__info {
  margin: 8px 0 0;
  color: #64748b;
}

.gantt__error {
  margin: 8px 0 0;
  color: #b00020;
}

.gantt__board {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow-x: auto;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  touch-action: pan-x pan-y;
  overscroll-behavior: contain;
  max-height: 65vh;
  --gantt-timeline: 600px;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}
.gantt.is-fullscreen .gantt__board {
  flex: 1;
  max-height: none;
  min-height: 0;
}

.gantt__fullscreen {
  height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid #d0d7de;
  background: #f8fafc;
  color: #1f2937;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}
.gantt__fullscreen:hover {
  background: #eef2f7;
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.12);
  transform: translateY(-1px);
}
.gantt__fullscreen:active {
  transform: translateY(0);
}
.gantt__fullscreen:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(148, 163, 184, 0.4);
}

.gantt__header {
  display: grid;
  grid-template-columns: var(--gantt-left) var(--gantt-timeline);
  background: #f8fafc;
  border-bottom: 1px solid #e5e7eb;
  position: sticky;
  top: 0;
  z-index: 10;
  min-width: calc(var(--gantt-left) + var(--gantt-timeline));
  box-sizing: border-box;
}

.gantt__h-left,
.gantt__h-right {
  padding: 10px 12px;
  font-weight: 700;
}

.gantt__h-left {
  border-right: 1px solid #e5e7eb;
  position: sticky;
  left: 0;
  background: #f8fafc;
  z-index: 11;
  display: flex;
  align-items: center;
}

.gantt__col-resizer {
  position: absolute;
  top: 0;
  right: 0;
  width: 8px;
  height: 100%;
  cursor: col-resize;
  user-select: none;
}
.gantt__col-resizer:hover {
  background: rgba(100, 116, 139, 0.2);
}

.gantt__ticks {
  position: relative;
  height: 18px;
  width: 100%;
}

.gantt__tick {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  font-size: 10px;
  color: #64748b;
  white-space: nowrap;
}

.gantt__rows {
  display: grid;
  min-width: calc(var(--gantt-left) + var(--gantt-timeline));
  box-sizing: border-box;
}

.gantt__row {
  display: grid;
  grid-template-columns: var(--gantt-left) var(--gantt-timeline);
  border-top: 1px solid #f0f2f4;
  min-height: 44px;
}

.gantt__task {
  padding: 8px 12px;
  border-right: 1px solid #f0f2f4;
  position: sticky;
  left: 0;
  background: #fff;
  z-index: 4;
  box-shadow: 6px 0 8px -6px rgba(0,0,0,.15);
}

.gantt__task-title {
  font-weight: 600;
}

.gantt__task-meta {
  font-size: 12px;
  color: #64748b;
}

.gantt__bar-area {
  padding: 8px 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
}

.gantt__bar-track {
  position: relative;
  height: 32px;
  border-radius: 8px;
  background: repeating-linear-gradient(
    to right,
    #f8fafc 0,
    #f8fafc 40px,
    #ffffff 40px,
    #ffffff 80px
  );
  border: 1px solid #eef2f7;
  width: 100%;
  overflow: hidden;
}

.gantt__bar {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  height: 24px;
  border-radius: 6px;
  background: #94a3b8;
  min-width: 2px;
  cursor: pointer;
  overflow: visible;
  z-index: 1;
}
.gantt__bar.bar--not-started { background: #2563eb; }
.gantt__bar.bar--in-progress { background: #6b7280; }
.gantt__bar.bar--done { background: #16a34a; }
.gantt__bar.bar--not-done { background: #dc2626; }
.gantt__bar.bar--unknown { background: #9ca3af; }

.gantt__tooltip-layer {
  position: fixed;
  z-index: 99999;
  pointer-events: none;
}
.gantt__tooltip {
  width: 260px;
  background: #0f172a;
  color: #fff;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.25;
  box-shadow: 0 10px 20px rgba(0,0,0,.25);
}
.gantt__tip-title {
  font-weight: 700;
  margin-bottom: 6px;
}
.gantt__tip-row {
  display: grid;
  grid-template-columns: 60px 1fr;
  gap: 6px;
}
.gantt__tip-label {
  opacity: 0.7;
}
.gantt__tip-value {
  text-align: right;
}

@media (max-width: 900px) {
  .gantt__filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 720px) {
  .gantt__filters {
    grid-template-columns: 1fr;
    gap: 8px;
    align-items: stretch;
  }
  .gantt {
    --gantt-left: 220px;
  }
  .gantt__legend-bar { gap: 8px; }
  .gantt__legend { gap: 10px; }
  .gantt__legend-item { font-size: 12px; }
  .gantt__board { max-height: 60vh; height: 60vh; }
  .gantt__task-title { font-size: 13px; }
  .gantt__task-meta { font-size: 11px; }
}
</style>
