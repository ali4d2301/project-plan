<template>
  <div class="card" ref="cardRef" :class="{ 'is-fullscreen': fullscreen }">
    <div class="top">
      <div class="title-block">
        <h3>Synthese des tâches par entite</h3>
        <p class="subtitle">Vue consolidee des statuts par structure</p>
      </div>
      <div class="top-right">
        <div class="inline-filter">
          <MonthFilter v-model="localPeriod" label="Mois :" />
        </div>
        <button class="fullscreen-btn" type="button" @click="toggleFullscreen">
          {{ fullscreen ? "Reduire" : "Plein ecran" }}
        </button>
      </div>
    </div>

    <p v-if="error" class="msg msg--error">{{ error }}</p>
    <p v-else-if="loading" class="msg">Chargement...</p>
    <p v-else-if="!rows.length" class="msg">Aucune donnee.</p>

    <div v-else class="table-wrap">
      <table class="summary-table">
        <thead>
          <tr>
            <th>Entite</th>
            <th>Tâches</th>
            <th>Completion</th>
            <th>Realisées</th>
            <th>En cours</th>
            <th>Non dem.</th>
            <th>Retard</th>
            <th>Risque</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.entite">
            <td class="entity-cell">
              <div class="entity-name">{{ row.entite }}</div>
              <div v-if="row.description" class="entity-desc">{{ row.description }}</div>
            </td>
            <td class="num">{{ row.taches }}</td>
            <td class="num">{{ row.completion }}%</td>
            <td class="num num--done">{{ row.realisees }}</td>
            <td class="num num--progress">{{ row.en_cours }}</td>
            <td class="num num--pending">{{ row.non_dem }}</td>
            <td class="num num--late">{{ row.retard > 0 ? row.retard : "-" }}</td>
            <td>
              <span class="risk-badge" :class="`risk-${row.risque_level}`">
                {{ row.risque }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, computed } from "vue"
import MonthFilter from "./MonthFilter.vue"
import { fetchWithRetry, getFetchErrorMessage } from "../utils/http"

const props = defineProps({
  period: { type: String, default: "ALL" },
})
const emit = defineEmits(["update:period"])

const localPeriod = computed({
  get: () => props.period,
  set: (v) => emit("update:period", v),
})

const cardRef = ref(null)
const fullscreen = ref(false)
const loading = ref(false)
const error = ref("")
const rows = ref([])

function parsePeriod(period) {
  if (!period || period === "ALL") return null
  const [ys, ms] = String(period).split("-")
  const year = Number(ys)
  const month = Number(ms)
  if (!year || !month) return null
  return { year, month }
}

function endpointUrl() {
  const base = import.meta.env.VITE_API_BASE || ""
  const period = parsePeriod(props.period)
  if (!period) return `${base}/api/planification/entites-summary`
  return `${base}/api/planification/entites-summary?year=${period.year}&month=${period.month}`
}

async function load() {
  loading.value = true
  error.value = ""
  try {
    const res = await fetchWithRetry(endpointUrl())
    rows.value = await res.json()
  } catch (e) {
    error.value = getFetchErrorMessage(e, "le tableau de synthese par entite")
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function toggleFullscreen() {
  const el = cardRef.value
  if (!el) return
  if (!(document.fullscreenEnabled && el?.requestFullscreen)) {
    fullscreen.value = !fullscreen.value
    document.body.classList.toggle("fs-lock", fullscreen.value)
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
}

onMounted(() => {
  load()
  document.addEventListener("fullscreenchange", syncFullscreen)
  syncFullscreen()
})

onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", syncFullscreen)
  document.body.classList.remove("fs-lock")
})

watch(() => props.period, () => load())
</script>

<style scoped>
.card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 14px;
}

.card.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  width: 100%;
  height: 100%;
  border-radius: 0;
  border: none;
  padding: 16px;
  box-sizing: border-box;
  background: #ffffff;
  display: flex;
  flex-direction: column;
}

.top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.top-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.top h3 {
  margin: 0;
  font-size: 34px;
  line-height: 1.08;
  letter-spacing: -0.3px;
}

.title-block {
  position: relative;
  padding-left: 14px;
}

.title-block::before {
  content: "";
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 4px;
  border-radius: 999px;
  background: linear-gradient(180deg, #1d4ed8, #0f2946);
}

.subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: #64748b;
}

.inline-filter :deep(.month-filter) {
  gap: 8px;
  align-items: center;
}

.inline-filter :deep(.label) {
  font-size: 14px;
  font-weight: 700;
}

.inline-filter :deep(.control) {
  height: 34px;
  width: 220px;
  font-size: 16px;
  padding: 0 12px;
  border-radius: 10px;
}

.msg {
  margin: 8px 0 12px;
  color: #64748b;
}

.msg--error {
  color: #b00020;
}

.fullscreen-btn {
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #64748b;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  cursor: pointer;
}

.table-wrap {
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  max-height: 520px;
}

.card.is-fullscreen .table-wrap {
  flex: 1;
  max-height: none;
}

.summary-table {
  width: 100%;
  min-width: 900px;
  border-collapse: collapse;
}

.summary-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #0f2946;
  color: #f8fafc;
  padding: 12px 14px;
  font-weight: 700;
  text-align: center;
  border-right: 1px solid rgba(248, 250, 252, 0.25);
}

.summary-table thead th:first-child {
  text-align: left;
}

.summary-table td {
  border-top: 1px solid #dce2ea;
  border-right: 1px solid #dce2ea;
  padding: 12px 14px;
  background: #f8fafc;
}

.summary-table tbody tr:nth-child(even) td {
  background: #f2f6fb;
}

.entity-cell {
  min-width: 280px;
}

.entity-name {
  font-weight: 700;
  color: #0f172a;
}

.entity-desc {
  margin-top: 3px;
  font-size: 12px;
  color: #64748b;
}

.num {
  text-align: center;
  font-weight: 700;
  color: #0f172a;
}

.num--done {
  color: #16a34a;
}

.num--progress {
  color: #d97706;
}

.num--pending {
  color: #2563eb;
}

.num--late {
  color: #dc2626;
}

.risk-badge {
  display: inline-flex;
  min-width: 92px;
  justify-content: center;
  padding: 6px 10px;
  border-radius: 2px;
  font-weight: 700;
}

.risk-high {
  background: #fee2e2;
  color: #dc2626;
}

.risk-medium {
  background: #fef3c7;
  color: #d97706;
}

.risk-normal {
  background: #dcfce7;
  color: #16a34a;
}

.risk-waiting {
  background: #dbeafe;
  color: #2563eb;
}

@media (max-width: 720px) {
  .top {
    flex-direction: column;
    align-items: flex-start;
  }
  .top-right {
    width: 100%;
    margin-left: 0;
    justify-content: space-between;
  }
  .top h3 {
    font-size: 26px;
  }
  .subtitle { font-size: 12px; }
  .inline-filter :deep(.label) {
    font-size: 13px;
  }
  .inline-filter :deep(.control) {
    width: 170px;
    font-size: 14px;
    height: 32px;
  }
}
</style>
