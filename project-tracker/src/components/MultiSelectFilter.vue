<template>
  <div class="ms">
    <label v-if="label" class="ms__label">{{ label }}</label>

    <!-- Champ (chips + caret) -->
    <div
      class="ms__control"
      :class="{ 'is-open': open, 'is-disabled': disabled || loading }"
      @click="toggleOpen"
      ref="controlEl"
    >
      <div class="ms__chips">
        <!-- Chips sélectionnés -->
        <template v-if="displaySelected.length">
            <span v-for="opt in visibleChips" :key="opt.value" class="chip" @click.stop>
                <span class="chip__text">{{ opt.label }}</span>
                <button class="chip__x" type="button" @click.stop="remove(opt.value)">×</button>
            </span>

            <button
                v-if="moreCount"
                type="button"
                class="chip chip--more"
                @click.stop="open = true"
                :title="`${moreCount} sélection(s) en plus`"
            >
                {{ moreLabelPrefix }}{{ moreCount }}
            </button>
        </template>

        <!-- Placeholder -->
        <span v-else class="ms__placeholder">{{ placeholder }}</span>
      </div>

      <div class="ms__right">
        <span v-if="loading" class="ms__spinner" aria-hidden="true"></span>
        <span class="ms__caret" aria-hidden="true">▾</span>
      </div>
    </div>

    <!-- Dropdown -->
    <div v-if="open" class="ms__dropdown" ref="dropdownEl" @click.stop>
      <div class="ms__panel">
        <!-- Recherche -->
        <div class="ms__search">
          <input
            class="ms__searchInput"
            v-model.trim="q"
            type="text"
            :placeholder="searchPlaceholder"
            :disabled="disabled || loading"
            @keydown.escape.prevent="close"
          />
        </div>

        <!-- Liste -->
        <div class="ms__list">
          <button
            v-for="opt in filteredOptions"
            :key="opt.value"
            type="button"
            class="ms__item"
            :class="{ 'is-selected': isSelected(opt.value) }"
            @click="toggle(opt.value)"
          >
            <span class="ms__check">{{ isSelected(opt.value) ? "✓" : "" }}</span>
            <span class="ms__text">{{ opt.label }}</span>
          </button>

          <div v-if="!filteredOptions.length" class="ms__empty">
            Aucun résultat
          </div>
        </div>
      </div>
    </div>

    <small v-if="error" class="ms__error">{{ error }}</small>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onBeforeUnmount } from "vue"

const ALL = "ALL"

const props = defineProps({
  modelValue: { type: Array, default: () => [ALL] },

  endpoint: { type: String, required: true },

  label: { type: String, default: "" },
  placeholder: { type: String, default: "Sélectionner…" },

  withAll: { type: Boolean, default: true },
  allLabel: { type: String, default: "Tout" },

  disabled: { type: Boolean, default: false },

  searchable: { type: Boolean, default: true },
  searchPlaceholder: { type: String, default: "Rechercher…" },

  maxChips: { type: Number, default: 2 },
  moreLabelPrefix: { type: String, default: "+" },

  // mapping si ton API renvoie déjà {value,label} c'est bon
  valueKey: { type: String, default: "value" },
  labelKey: { type: String, default: "label" },
})

const emit = defineEmits(["update:modelValue", "change"])

function apiBase() {
  return import.meta.env.VITE_API_BASE || ""
}
const url = computed(() => `${apiBase()}${props.endpoint}`)

const open = ref(false)
const loading = ref(false)
const error = ref("")
const q = ref("")

const options = ref([]) // [{value,label}]
const selected = ref(Array.isArray(props.modelValue) ? [...props.modelValue] : [ALL])

watch(
  () => props.modelValue,
  (v) => {
    selected.value = Array.isArray(v) ? [...v] : [ALL]
  }
)

const mergedOptions = computed(() => {
  const base = options.value || []
  if (!props.withAll) return base
  return [{ value: ALL, label: props.allLabel }, ...base]
})

const filteredOptions = computed(() => {
  const base = mergedOptions.value
  if (!props.searchable) return base

  const qq = (q.value || "").toLowerCase()
  if (!qq) return base
  return base.filter(o => String(o.label || "").toLowerCase().includes(qq))
})

const displaySelected = computed(() => {
  const map = new Map(mergedOptions.value.map(o => [String(o.value), o]))
  return (selected.value || [])
    .map(v => map.get(String(v)))
    .filter(Boolean)
})

const visibleChips = computed(() => displaySelected.value.slice(0, props.maxChips))

const moreCount = computed(() => {
  const n = displaySelected.value.length - props.maxChips
  return n > 0 ? n : 0
})

function isSelected(v) {
  return (selected.value || []).includes(v)
}

function normalize(sel) {
  if (!props.withAll) return sel.filter(Boolean)

  const hasAll = sel.includes(ALL)
  if (hasAll && sel.length > 1) return [ALL]
  if (!sel.length) return [ALL]
  return sel
}

function commit(next) {
  const normalized = normalize(next)
  selected.value = normalized
  emit("update:modelValue", normalized)
  emit("change", normalized)
}

function toggle(v) {
  const cur = [...(selected.value || [])]

  // si click sur ALL
  if (props.withAll && v === ALL) {
    commit([ALL])
    return
  }

  // sinon: si ALL était là, on l'enlève d'abord
  let next = cur.filter(x => x !== ALL)

  if (next.includes(v)) next = next.filter(x => x !== v)
  else next.push(v)

  commit(next)
}

function remove(v) {
  let next = (selected.value || []).filter(x => x !== v)
  commit(next)
}

function toggleOpen() {
  if (props.disabled || loading.value) return
  open.value = !open.value
  if (open.value) {
    // reset recherche à l’ouverture (optionnel)
    q.value = ""
  }
}
function close() {
  open.value = false
}

const controlEl = ref(null)
const dropdownEl = ref(null)

function onClickOutside(e) {
  if (!open.value) return
  const c = controlEl.value
  const d = dropdownEl.value
  if (!c || !d) return
  if (c.contains(e.target) || d.contains(e.target)) return
  close()
}

async function load() {
  loading.value = true
  error.value = ""
  try {
    const res = await fetch(url.value)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()

    // Supporte:
    // - [{value,label}]
    // - ["A","B"]
    // - [{entites:"X"}] via valueKey/labelKey
    if (Array.isArray(data) && data.length && typeof data[0] === "object") {
      options.value = data
        .map(r => ({
          value: r[props.valueKey] ?? r.value ?? r.id ?? r.name,
          label: r[props.labelKey] ?? r.label ?? r.name ?? String(r[props.valueKey] ?? ""),
        }))
        .filter(o => o.value != null)
    } else if (Array.isArray(data)) {
      options.value = data.map(x => ({ value: x, label: String(x) }))
    } else {
      options.value = []
    }
  } catch (e) {
    error.value = "Impossible de charger la liste."
    options.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  document.addEventListener("mousedown", onClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener("mousedown", onClickOutside)
})
</script>

<style scoped>
.ms { display: grid; gap: 6px; position: relative; width: 100%; height: auto; }
.ms__label { font-weight: 600; font-size: 13px; opacity: 0.9; }

.ms__control {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px; 
  font-weight: 600;
  min-height: 42px;
  padding: 6px 10px;
  border: 1px solid #d0d7de;
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  transition: box-shadow .15s, border-color .15s;
  width: 100%;
  box-sizing: border-box;
}
.ms__control:hover { border-color: #b6c0cb; }
.ms__control.is-open {
  border-color: #7aa7ff;
  box-shadow: 0 0 0 3px rgba(122,167,255,.25);
}
.ms__control.is-disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ms__chips { display: flex; flex-wrap: wrap; gap: 3px; flex: 1; min-width: 0; }
.ms__placeholder { opacity: .6; font-size: 14px; padding-left: 2px; }

.ms__right { display: flex; align-items: center; gap: 10px; padding-left: 10px; }
.ms__caret { opacity: .7; font-size: 20px; }

.ms__spinner{
  width: 14px; height: 14px; border-radius: 50%;
  border: 2px solid rgba(0,0,0,.15);
  border-top-color: rgba(0,0,0,.45);
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  background: rgba(122,167,255,.12);      /* ↓ moins “bleu” */
  border: 1px solid rgba(122,167,255,.35);
  color: #1f2a37;                          /* texte */
  padding: 0px 8px; 
  border-radius: 9px;
  font-size: 13px;
}
.chip__text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 300px; }
.chip__x {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  opacity: .75;
}
.chip__x:hover { opacity: 1; }

.ms__dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  box-shadow: 0 10px 24px rgba(0,0,0,.12);
  overflow: hidden;
  z-index: 2000;
  max-height: 280px;
}

.ms__panel {
  padding: 6px;
  display: grid;
  gap: 6px;
  background: #fff;
}

.ms__search {
  border-bottom: 1px solid #f0f2f4;
  padding-bottom: 6px;
}
.ms__searchInput {
  width: 100%;
  height: 30px;
  padding: 0 8px;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  outline: none;
  font-size: 12px;
  box-sizing: border-box;
  max-width: 100%;
  display: block;
}
.ms__searchInput:focus {
  border-color: #7aa7ff;
  box-shadow: none;
}

.ms__list { max-height: 190px; overflow: auto; padding: 2px; }
.ms__item {
  width: 100%;
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 8px;
  align-items: center;
  padding: 6px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 10px;
  text-align: left;
}
.chip--more{
  background: rgba(0,0,0,.06);
  border: 1px dashed rgba(0,0,0,.18);
  cursor: pointer;
}
.chip--more:hover{
  background: rgba(0,0,0,.09);
}

.ms__item:hover { background: rgba(0,0,0,.04); }
.ms__item.is-selected { background: rgba(122,167,255,.16); }
.ms__check { font-weight: 700; opacity: .8; }
.ms__text { font-size: 12px; }

.ms__empty { padding: 12px; opacity: .6; font-size: 13px; }
.ms__error { color: #c62828; font-size: 12px; margin-top: 2px; }

@media (max-width: 640px) {
  .chip__text { max-width: 220px; }
  .ms__dropdown { max-height: 60vh; }
  .ms__control { padding: 8px 10px; }
}
</style>
