<template>
  <div class="page">
    
    <div class="dashboard-header">
      <div class="header-bar">
        <img class="title-logo" src="/logos/mshpcmu.png" alt="MSHPCMU" />
        <h1 class="title">Projet d'interopérabilité CNAM/MSHPCMU</h1>
        <img class="title-logo" src="/logos/disd.png" alt="DISD" />
      </div>

      <div class="tabs">
        <button class="tab" :class="{ active: activeTab === 'overview' }" @click="changeTab('overview')">
          Dashboard - Macro-planning
        </button>
        <button class="tab" :class="{ active: activeTab === 'diagramme' }" @click="changeTab('diagramme')">
          Diagramme de gantt - Tâches
        </button>
        <button class="tab" :class="{ active: activeTab === 'micro' }" @click="changeTab('micro')">
          Micro-planning
        </button>
      </div>

      <div class="divider"></div>
    </div>

    <!-- DASHBOARD -->
    <div v-if="activeTab === 'overview'" class="stack">
         <section class="grid-2">
            <camembert/>
            <hist-empile-mois/>
         </section>

         <div class="filter">
             <MonthFilter v-model="period" />
         </div>

         <section class="grid-2">
            <planification-histogram-entites :period="period"/>
            <PlanificationStack100EntitesStatuts :period="period" />
         </section>
         
    </div>

    <!-- MACRO-->
    <div v-else-if="activeTab === 'diagramme'" class="card pad">
      <GanttPlanification />
    </div>

    <!-- MICRO -->
    <div v-else class="card pad micro">
      <section class="grid-3 micro__filters">
        <DateRangeFilter
          label="Période"
          defaultStart="2025-10-01"
          defaultEnd="2026-02-28"
          v-model="microPeriod"
        />
        <MultiSelectDropdown
          v-model="entites"
          label="Entités"
          endpoint="/api/planification/entites"
        />
        <MultiSelectDropdown
          v-model="statuts"
          label="Statuts"
          endpoint="/api/planification/statuts"
          :maxChips="3"
        />
        <button class="micro__export" type="button" @click="exportMicro">
          Exporter Excel
        </button>
        <button class="micro__fullscreen" type="button" @click="toggleMicroFullscreen">
          {{ microFullscreen ? "Réduire" : "Plein écran" }}
        </button>
      </section>

      <section
        ref="microTableSectionRef"
        class="micro__table"
        :class="{ 'is-fullscreen': microFullscreen }"
      >
        <button
          v-if="microFullscreen"
          class="micro__fullscreen-close"
          type="button"
          @click="toggleMicroFullscreen"
        >
          Réduire
        </button>
        <DataTable
          ref="microTableRef"
          title="Mes données"
          endpoint="/api/planification/micro"
          :start="microPeriod.start"
          :end="microPeriod.end"
          :entites="entites"
          :statuts="statuts"
          :columns="[
            { key: 'id', label: 'ID' },
            { key: 'entites', label: 'Entités' },
            { key: 'taches', label: 'Tâches' },
            { key: 'date_debut', label: 'Date de début' },
            { key: 'date_fin', label: 'Date de fin' }, 
            { key: 'mois', label: 'Mois' },
            { key: 'statut', label: 'Statut' },
            { key: 'acteurs', label: 'Acteurs' },
            { key: 'dependance', label: 'Dépendance' },
            { key: 'observations', label: 'Observations' }
          ]"
        />
      </section>

    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";

const router = useRouter();
const route = useRoute();

const allowedTabs = ["overview", "diagramme", "micro"];

const activeTab = ref(route.params.tab && allowedTabs.includes(route.params.tab) ? route.params.tab : 'overview');

// Normaliser l'URL si le paramètre est vide ou invalide
if (!route.params.tab || !allowedTabs.includes(route.params.tab)) {
  router.replace({ name: 'dashboard', params: { tab: activeTab.value }});
}

watch(() => route.params.tab, (newTab) => {
  if (allowedTabs.includes(newTab)) {
    activeTab.value = newTab;
  } else {
    router.replace({ name: 'dashboard', params: { tab: 'overview' }});
  }
});

function changeTab(tab) {
  if (tab === activeTab.value) return;
  router.push({ name: 'dashboard', params: { tab }});
}

import Camembert from "../components/camembert.vue";
import HistEmpileMois from "../components/HistEmpileMois.vue";
import MonthFilter from "../components/MonthFilter.vue";
import PlanificationHistogramEntites from "../components/PlanificationHistogramEntites.vue"
import PlanificationStack100EntitesStatuts from "../components/PlanificationStack100EntitesStatuts.vue";
  const period = ref("ALL")
  watch(period, v => console.log("PARENT period =", v))

import GanttPlanification from "../components/GanttPlanification.vue";
import DateRangeFilter from "../components/DateRangeFilter.vue";
import MultiSelectDropdown from "../components/MultiSelectFilter.vue";
  const entites = ref(["ALL"])
  const statuts = ref(["ALL"])
  const microPeriod = ref({ start: "2025-10-01", end: "2026-02-28" })

import DataTable from '../components/DataTable.vue'
  const microTableRef = ref(null)
  const microTableSectionRef = ref(null)
  const microFullscreen = ref(false)

  function canUseNativeFullscreen(el) {
    return !!(document.fullscreenEnabled && el?.requestFullscreen)
  }

  function exportMicro() {
    microTableRef.value?.exportToCsv?.("micro-planning")
  }

  async function toggleMicroFullscreen() {
    const el = microTableSectionRef.value
    if (!el) return
    if (!canUseNativeFullscreen(el)) {
      microFullscreen.value = !microFullscreen.value
      document.body.classList.toggle("fs-lock", microFullscreen.value)
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

  function syncFullscreenState() {
    const el = microTableSectionRef.value
    const isFs = !!document.fullscreenElement && document.fullscreenElement === el
    microFullscreen.value = isFs
    if (isFs) document.body.classList.add("fs-lock")
    else document.body.classList.remove("fs-lock")
  }

  onMounted(() => {
    document.addEventListener("fullscreenchange", syncFullscreenState)
    syncFullscreenState()
  })

  onBeforeUnmount(() => {
    document.removeEventListener("fullscreenchange", syncFullscreenState)
    document.body.classList.remove("fs-lock")
  })

</script>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap");
.page{
  /* occupe toute la largeur du navigateur pour réduire les marges latérales */
  width: 100%;
  max-width: none;         /* plus de limite de largeur */
  margin:-6px 0;           /* réduit l'espace en haut et en bas */
  padding:4px 16px 10px;   /* réduit l'espace en haut */
  background:#f6f7fb;
  min-height:calc(100vh - 12px);
  box-sizing:border-box;
}

.title{
  margin:2px 0 6px;       /* réduit l'espace au-dessus/au-dessous du titre */
  font-size:36px;
  letter-spacing:-0.6px;
  line-height:1.02;
  font-family: 'arial black', sans-serif;
  text-align:center;
}
.header-bar{
  display:flex;
  align-items:center;
  justify-content:center;
  gap:16px;
  flex-wrap:wrap;
}
.title-logo{
  height:46px;
  width:auto;
  object-fit:contain;
}
@media (max-width: 720px) {
  .title-logo{ height:36px; }
  .title{ font-size:28px; }
}
.tabs{
  display:flex;
  gap:28px;
  align-items:flex-end;
  padding-bottom:6px;
  overflow-x:auto;
  -webkit-overflow-scrolling:touch;
  scrollbar-width: thin;
}
.tab{
  background:transparent;
  border:none;
  cursor:pointer;
  padding:10px 2px;
  color:#64748b;
  border-bottom:3px solid transparent;
  font-size:18px;
  white-space: nowrap;
}
.tab.active{
  color:#2563eb;
  border-bottom-color:#2563eb;
  font-weight:700;
}
/* Supprimer l'encadré de focus au clic et retirer l'effet par défaut sur Firefox */
.tab:focus{
  outline: none;
  box-shadow: none;
}
.tab::-moz-focus-inner { /* Firefox */
  border: 0;
}
.divider{ height:1px; background:#e5e7eb; }
/* Header figé */
.page .dashboard-header {
  position: sticky;
  top: 0;
  background: #f6f8fb; /* ou blanc selon ton thème */
  z-index: 100;
  padding-top: 2px;
  padding-bottom: 6px;
}

.stack{ display:flex; flex-direction:column; gap:16px; margin-top:10px; }

.grid-2{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap:16px;
}
.grid-2 > * { min-width: 0; }
.grid-3{
  display:grid;
  grid-template-columns: repeat(3, 1fr);
  gap:16px;
}
.grid-3 > * { min-width: 0; }

.card{
  background:#fff;
  border:1px solid #e5e7eb;
  border-radius:14px;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05);
  min-width: 0;
}
.pad{ padding:16px; margin-top:10px; }

.filter {
  display: flex;
  justify-content: center;
  align-items: center;
}

/* Micro planning polish */
.micro {
  --micro-accent: #2563eb;
  --micro-accent-2: #60a5fa;
  --micro-ink: #0f172a;
  --micro-muted: #5b6b7a;
  --micro-surface: #ffffff;
  --micro-border: #dbe5f5;
  --micro-shadow: 0 18px 40px rgba(30, 64, 175, 0.18);
  position: relative;
  isolation: isolate;
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid var(--micro-border);
  background: var(--micro-surface);
  box-shadow: var(--micro-shadow);
  font-family: "Space Grotesk", "Segoe UI", Tahoma, sans-serif;
  color: var(--micro-ink);
}
.micro.pad { padding: 18px; }
.micro::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(640px 260px at 10% 0%, rgba(96, 165, 250, 0.18), transparent 60%),
    radial-gradient(520px 240px at 95% 10%, rgba(37, 99, 235, 0.14), transparent 55%);
  opacity: 0.7;
  z-index: 0;
  pointer-events: none;
}
.micro::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(59, 130, 246, 0.04));
  opacity: 0.5;
  z-index: 0;
  pointer-events: none;
}
.micro > * { position: relative; }

.micro__filters {
  position: relative;
  z-index: 2;
  grid-template-columns: 1.15fr 1fr 1fr auto auto;
  align-items: end;
  gap: 18px;
  padding: 14px;
  border: 1px solid rgba(37, 99, 235, 0.14);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(96, 165, 250, 0.12), rgba(255, 255, 255, 0.88));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  animation: micro-fade-up 420ms ease both;
}
.micro__table {
  position: relative;
  z-index: 1;
  margin-top: 14px;
  animation: micro-fade-up 420ms ease both;
  animation-delay: 80ms;
}

@keyframes micro-fade-up {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
@media (prefers-reduced-motion: reduce) {
  .micro__filters,
  .micro__table {
    animation: none;
  }
}

@media (max-width: 900px) {
  .micro__filters { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .grid-2 { grid-template-columns: 1fr; }
  .grid-3 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .micro__filters {
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 10px;
    align-items: stretch;
  }
  .grid-3 { grid-template-columns: 1fr; }
  .filter { align-items: stretch; }
  .micro__export,
  .micro__fullscreen {
    width: 100%;
    justify-self: stretch;
  }
  .tabs { gap: 8px; padding-bottom: 2px; }
  .tab { font-size: 13px; padding: 6px 2px; border-bottom-width: 2px; }
  .page { padding: 6px 8px 12px; margin: 0; }
  .page .dashboard-header {
    position: static;
    top: auto;
    padding-top: 0;
    padding-bottom: 4px;
  }
  .micro__table.is-fullscreen { padding: 12px; }
}

@media (max-width: 520px) {
  .title-logo { height: 32px; }
  .title { font-size: 22px; }
  .tab { font-size: 13px; }
}

@media (max-height: 520px) and (orientation: landscape) {
  .page .dashboard-header {
    position: static;
    top: auto;
  }
}

.micro__export {
  height: 44px;
  padding: 0 16px;
  border-radius: 12px;
  border: 1px solid rgba(37, 99, 235, 0.35);
  background: linear-gradient(135deg, #2563eb, #60a5fa);
  color: #f8fafc;
  font-weight: 700;
  letter-spacing: 0.01em;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.25);
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}
.micro__export:hover {
  filter: brightness(1.02);
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.3);
  transform: translateY(-1px);
}
.micro__export:active {
  transform: translateY(0);
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.25);
}
.micro__export:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.3), 0 8px 18px rgba(37, 99, 235, 0.25);
}

.micro__fullscreen {
  height: 44px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(37, 99, 235, 0.35);
  background: #f8fbff;
  color: #1e3a8a;
  font-weight: 700;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}
.micro__fullscreen:hover {
  background: #eef3ff;
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.18);
  transform: translateY(-1px);
}
.micro__fullscreen:active {
  transform: translateY(0);
}
.micro__fullscreen:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.25);
}

.micro__table.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  width: 100%;
  height: 100%;
  background: #ffffff;
  border-radius: 0;
  padding: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin-top: 0;
}
.micro__fullscreen-close {
  align-self: flex-end;
  margin-bottom: 10px;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.2);
  background: #111827;
  color: #f9fafb;
  font-weight: 700;
  cursor: pointer;
}
.micro__table.is-fullscreen :deep(.api-table) {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.micro__table.is-fullscreen :deep(.api-table__wrap) {
  flex: 1;
  height: 100%;
  min-height: 0;
  max-height: none;
}

/* Date range */
.micro :deep(.field) { gap: 8px; }
.micro :deep(.field .label) {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--micro-muted);
}
.micro :deep(.field .row label) {
  font-size: 12px;
  color: var(--micro-muted);
  font-weight: 600;
}
.micro :deep(.field .control) {
  height: 40px;
  border-radius: 12px;
  border: 1px solid var(--micro-border);
  background: #fff;
  font-weight: 600;
  color: var(--micro-ink);
}
.micro :deep(.field .control:focus) {
  outline: none;
  border-color: var(--micro-accent);
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.25);
}
.micro :deep(.row input[type="date"]) {
  font-family: "Space Grotesk", "Segoe UI", Tahoma, sans-serif;
  font-size: 12px;
}

/* Multi select */
.micro :deep(.ms__label) {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--micro-muted);
}
.micro :deep(.ms__control) {
  min-height: 44px;
  border-radius: 14px;
  border: 1px solid var(--micro-border);
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.05);
}
.micro :deep(.ms__control:hover) { border-color: rgba(37, 99, 235, 0.55); }
.micro :deep(.ms__control.is-open) {
  border-color: var(--micro-accent);
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.25);
}
.micro :deep(.ms__placeholder) { color: var(--micro-muted); }
.micro :deep(.chip) {
  background: rgba(96, 165, 250, 0.16);
  border: 1px solid rgba(37, 99, 235, 0.3);
  color: #1e3a8a;
}
.micro :deep(.chip--more) {
  background: rgba(37, 99, 235, 0.08);
  border: 1px dashed rgba(37, 99, 235, 0.35);
}
.micro :deep(.ms__dropdown) {
  border-radius: 16px;
  border: 1px solid rgba(37, 99, 235, 0.24);
  box-shadow: 0 18px 36px rgba(30, 64, 175, 0.22);
}
.micro :deep(.ms__item.is-selected) { background: rgba(96, 165, 250, 0.2); }
.micro :deep(.ms__item:hover) { background: rgba(37, 99, 235, 0.1); }
.micro :deep(.ms__searchInput:focus) {
  border-color: var(--micro-accent);
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.2);
}
.micro :deep(.ms__searchInput) { font-size: 13px; }
.micro :deep(.ms__item) { font-size: 13px; }
.micro :deep(.ms__text) { font-size: 13px; }

/* Data table */
.micro :deep(.api-table) {
  border-radius: 16px;
  border: 1px solid rgba(37, 99, 235, 0.18);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
  background: #fff;
}
.micro :deep(.api-table__wrap) {
  border-radius: 12px;
  border: 1px solid rgba(37, 99, 235, 0.14);
}
.micro :deep(.api-table__table) { font-size: 13px; }
.micro :deep(.api-table__table thead th) {
  background: linear-gradient(180deg, #3b4047, #2d3138);
  color: #f8fafc;
}
.micro :deep(.api-table__table tbody tr:nth-child(even)) { background: rgba(59, 130, 246, 0.04); }
.micro :deep(.api-table__table tbody tr:hover) { background: rgba(96, 165, 250, 0.12); }
.micro :deep(.api-table__table th),
.micro :deep(.api-table__table td) {
  border-bottom: 1px solid rgba(37, 99, 235, 0.1);
}
.micro :deep(.api-table__wrap::-webkit-scrollbar) { height: 10px; width: 10px; }
.micro :deep(.api-table__wrap::-webkit-scrollbar-thumb) {
  background: rgba(37, 99, 235, 0.4);
  border-radius: 999px;
}
.micro :deep(.api-table__wrap::-webkit-scrollbar-track) {
  background: rgba(37, 99, 235, 0.12);
  border-radius: 999px;
}

</style>
