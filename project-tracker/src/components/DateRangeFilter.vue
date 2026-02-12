<template>
  <div class="field">
    <label class="label">{{ label }}</label>

    <div class="row"> 
      <div>  <!-- Insérer class="field" pour avoir le "Du" au dessus-->
        <label>Du </label>
        <input
          class="control"
          type="date"
          v-model="start"
          :min="minDate"
          :max="end || maxDate"
          :disabled="loading || disabled"
        />
      </div>

      <!-- <span class="sep">→</span> -->
      <span class="sep">→</span>

      <div> <!-- Insérer class="field" pour avoir le "Du" au dessus-->
        <label>Au </label>
        <input
          class="control"
          type="date"
          v-model="end"
          :min="start || minDate"
          :max="maxDate"
          :disabled="loading || disabled"
        />
      </div>
      

    </div>

    <small v-if="error" class="error">{{ error }}</small>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from "vue"

const props = defineProps({
  // ✅ valeurs par défaut configurables
  defaultStart: { type: String, default: "" }, // "2026-01-01"
  defaultEnd: { type: String, default: "" },   // "2026-12-31"

  endpoint: { type: String, default: "" }, // optionnel (bornes API)

  label: { type: String, default: "Période" },
  disabled: { type: Boolean, default: false },

  // ✅ v-model: { start, end }
  modelValue: {
    type: Object,
    default: () => ({ start: "", end: "" }),
  },
})

const emit = defineEmits(["change", "update:modelValue"])

function apiBase() {
  return import.meta.env.VITE_API_BASE || ""
}

const start = ref(props.modelValue?.start || props.defaultStart)
const end = ref(props.modelValue?.end || props.defaultEnd)

const minDate = ref("")
const maxDate = ref("")

const loading = ref(false)
const error = ref("")

/* 🔁 émet automatiquement quand ça change */
watch([start, end], () => {
  if (start.value && end.value && start.value > end.value) {
    end.value = start.value
  }

  emit("update:modelValue", {
    start: start.value,
    end: end.value,
  })

  emit("change", {
    start: start.value,
    end: end.value,
  })
})

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    if (typeof v.start === "string") start.value = v.start
    if (typeof v.end === "string") end.value = v.end
  },
  { deep: true }
)

async function loadBounds() {
  if (!props.endpoint) return

  loading.value = true
  error.value = ""

  try {
    const url = `${apiBase()}${props.endpoint}`
    const res = await fetch(url)
    if (!res.ok) throw new Error()

    const data = await res.json()

    minDate.value = data?.min || ""
    maxDate.value = data?.max || ""
  } catch {
    error.value = "Erreur chargement dates"
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadBounds()

  // ✅ émettre les valeurs par défaut au démarrage
  emit("update:modelValue", {
    start: start.value,
    end: end.value,
  })
  emit("change", {
    start: start.value,
    end: end.value,
  })
})
</script>

<style scoped>
.field { display: grid; gap: 6px; align-items: center;}
.label { font-weight: 600; }
label { font-size: 14px; color: #555; } /* Différent de .label*/
.row { display: flex; align-items: center; gap: 10px; }
.control {
  height: 36px;
  padding: 0 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
}

/* Harmoniser le texte dans les <input type="date"> (Chrome/Windows) */
.row input[type="date"]{
  font-family: sans-serif,'Segoe UI', Tahoma, Geneva, Verdana; /* police système Windows */
  font-size: 12px;          /* ajuste si tu veux */
  font-weight: 700;
  letter-spacing: 0;
  font-variant-numeric: normal;
  -webkit-font-smoothing: antialiased;
}

.sep { opacity: 0.7; }
.error { color: #b00020; }
</style>
