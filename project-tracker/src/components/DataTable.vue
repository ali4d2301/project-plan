<template>
  <section class="api-table">
    

    <p v-if="loading" class="api-table__info">Chargement…</p>
    <p v-else-if="error" class="api-table__error">{{ error }}</p>
    <p v-else-if="!rows.length" class="api-table__info">Aucune donnée.</p>

    <div v-else class="api-table__wrap">
      <table class="api-table__table">
        <colgroup>
          <col
            v-for="(c, i) in effectiveColumns"
            :key="c.key"
            :style="{ width: columnWidths[c.key] ? columnWidths[c.key] + 'px' : 'auto' }"
          />
        </colgroup>
        <thead>
          <tr>
            <th v-for="c in effectiveColumns" :key="c.key">
              <span class="th-label">{{ c.label }}</span>
              <span class="col-resizer" @mousedown="startResize($event, c.key)"></span>
            </th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="(r, i) in filteredRows" :key="r[idKey] ?? i">
            <td v-for="c in effectiveColumns" :key="c.key">
              {{ formatCell(r, c.key) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue"

const props = defineProps({
  title: { type: String, default: "" },

  // Comme tu fais d’habitude
  endpoint: { type: String, required: true },
  autoLoad: { type: Boolean, default: true },

  // clé unique (si ton API renvoie id)
  idKey: { type: String, default: "id" },

  // Colonnes optionnelles: [{ key:'entite', label:'Entité' }, ...]
  // Si vide -> on auto-déduit à partir de la 1ère ligne
  columns: { type: Array, default: () => [] },

  // ✅ filtres front (multi-select)
  entites: { type: Array, default: () => ["ALL"] },
  statuts: { type: Array, default: () => ["ALL"] },

  // ✅ noms des colonnes à filtrer dans la table (au cas où ça diffère)
  entiteKey: { type: String, default: "entites" },
  statutKey: { type: String, default: "statut" },

  // ✅ filtres période (backend)
  start: { type: String, default: "" },
  end: { type: String, default: "" },
})

function apiBase() {
  return import.meta.env.VITE_API_BASE || ""
}
const url = computed(() => {
  const base = `${apiBase()}${props.endpoint}`
  const params = new URLSearchParams()
  if (props.start) params.set("start", props.start)
  if (props.end) params.set("end", props.end)
  const qs = params.toString()
  if (!qs) return base
  return base.includes("?") ? `${base}&${qs}` : `${base}?${qs}`
})

const rows = ref([])
const loading = ref(false)
const error = ref("")
const columnWidths = ref({})

async function load() {
  loading.value = true
  error.value = ""
  try {
    const res = await fetch(url.value)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()

    // On supporte: soit une liste, soit { items: [...] }
    const arr = Array.isArray(data) ? data : (data?.items ?? [])
    rows.value = arr
  } catch (e) {
    error.value = e?.message || "Erreur lors du chargement"
    rows.value = []
  } finally {
    loading.value = false
  }
}

const effectiveColumns = computed(() => {
  if (props.columns?.length) return props.columns
  const first = rows.value?.[0]
  if (!first || typeof first !== "object") return []
  return Object.keys(first).map((k) => ({
    key: k,
    label: k,
  }))
})

function ensureColumnWidths() {
  const cols = effectiveColumns.value || []
  cols.forEach((c) => {
    if (!columnWidths.value[c.key]) {
      const k = String(c.key || "").toLowerCase()
      let w = 160
      if (k === "id") w = 70
      else if (k === "taches" || k === "tache" || k === "email") w = 360
      else if (k === "observations") w = 240
      else if (k === "dependance") w = 200
      else if (k === "acteurs") w = 180
      else if (k === "entites" || k === "entite") w = 180
      else if (k === "statut" || k === "status") w = 140
      else if (k === "mois") w = 110
      else if (k === "date_debut" || k === "date_fin") w = 130
      columnWidths.value[c.key] = w
    }
  })
}

function startResize(e, key) {
  e.preventDefault()
  const startX = e.clientX
  const th = e.target?.closest("th")
  const startW = columnWidths.value[key] || th?.offsetWidth || 160

  function onMove(ev) {
    const w = Math.max(90, startW + (ev.clientX - startX))
    columnWidths.value = { ...columnWidths.value, [key]: w }
  }

  function onUp() {
    document.removeEventListener("mousemove", onMove)
    document.removeEventListener("mouseup", onUp)
  }

  document.addEventListener("mousemove", onMove)
  document.addEventListener("mouseup", onUp)
}

function formatDateString(v) {
  if (typeof v !== "string") return null
  const m = v.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return null
  const [, y, mm, dd] = m
  return `${dd}/${mm}/${y}`
}

const filteredRows = computed(() => {
  let out = rows.value || []

  // 1) ✅ Filtre Entités (front)
  const entSel = props.entites || ["ALL"]
  if (!entSel.includes("ALL")) {
    out = out.filter(r => entSel.includes(String(r?.[props.entiteKey] ?? "")))
  }

  // 2) ✅ Filtre Statuts (front)
  const staSel = props.statuts || ["ALL"]
  if (!staSel.includes("ALL")) {
    out = out.filter(r => staSel.includes(String(r?.[props.statutKey] ?? "")))
  }

  return out
})

function toCsvValue(v) {
  const s = v === null || v === undefined ? "" : String(v)
  const escaped = s.replace(/"/g, '""')
  return `"${escaped}"`
}

function exportToCsv(filenameBase = "export") {
  const cols = effectiveColumns.value || []
  const data = filteredRows.value || []
  const sep = ";"
  const header = cols.map(c => toCsvValue(c.label ?? c.key)).join(sep)
  const lines = data.map((r) =>
    cols.map((c) => toCsvValue(formatCell(r, c.key))).join(sep)
  )
  const csv = "\ufeff" + [header, ...lines].join("\r\n")

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  const stamp = new Date().toISOString().slice(0, 10)
  a.href = url
  a.download = `${filenameBase}-${stamp}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

defineExpose({ exportToCsv })


function formatCell(row, key) {
  const v = row?.[key]
  if (v === null || v === undefined) return ""
  const formattedDate = formatDateString(v)
  if (formattedDate) return formattedDate
  if (typeof v === "object") return JSON.stringify(v)
  return String(v)
}

onMounted(() => {
  if (props.autoLoad) load()
  ensureColumnWidths()
})

// si endpoint change -> recharge auto
watch(url, () => {
  if (props.autoLoad) load()
})

watch(effectiveColumns, () => {
  ensureColumnWidths()
})
</script>

<style scoped>
.api-table {
  background: #fff;
  border: 1px solid #e9e9ef;
  border-radius: 12px;
  padding: 12px;
}

.api-table__wrap {
  overflow: auto;
  border-radius: 10px;
  border: 1px solid #eee;
  max-height: 460px;
}

.api-table__table {
  width: 100%;
  border-collapse: collapse;
  min-width: 700px;
  table-layout: fixed;
}

.api-table__table th,
.api-table__table td {
  padding: 10px 12px;
  border-bottom: 1px solid #f0f0f6;
  text-align: left;
  white-space: normal;
  word-break: break-word;
  vertical-align: top;
}

.api-table__table thead th {
  position: sticky;
  top: 0;
  background: #fafafe;
  z-index: 1;
  font-weight: 700;
  padding-right: 18px;
}

.th-label {
  display: block;
  padding-right: 6px;
}

.api-table__table th {
  position: relative;
}

.col-resizer {
  position: absolute;
  top: 0;
  right: 0;
  width: 8px;
  height: 100%;
  cursor: col-resize;
  user-select: none;
}
.col-resizer:hover {
  background: rgba(100, 116, 139, 0.2);
}

.api-table__info {
  margin: 8px 0 0;
  color: #666;
}
.api-table__error {
  margin: 8px 0 0;
  color: #b00020;
}
</style>
