<template>
  <div class="month-filter">
    <label class="label">{{ label }}</label>

    <select class="control" v-model="model" :disabled="loading || disabled">
      <option value="ALL">Tout</option>

      <option v-for="m in months" :key="m.value" :value="m.value">
        {{ m.label }}
      </option>
    </select>
  </div>

  <small v-if="error" class="error">{{ error }}</small>
</template>

<script setup>
import { ref, onMounted, computed } from "vue"

const props = defineProps({
  modelValue: { type: String, default: "ALL" },
  endpoint: { type: String, default: "/api/planification/months" },
  label: { type: String, default: "Mois selectionné :" },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(["update:modelValue"])

// ✅ v-model “direct” sans localValue / watch
const model = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
})

function apiBase() {
  return import.meta.env.VITE_API_BASE || ""
}

const months = ref([])
const loading = ref(false)
const error = ref("")

async function loadMonths() {
  loading.value = true
  error.value = ""
  try {
    const url = `${apiBase()}${props.endpoint}`
    const res = await fetch(url)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    months.value = await res.json()
  } catch (e) {
    error.value = "Erreur de chargement des mois"
    months.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadMonths)
</script>

<style scoped>
.month-filter {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.label { font-weight: 600; }
.control {
  height: 36px;
  width: 320px;
  max-width: 100%;
  padding: 0 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-sizing: border-box;
}
.error { color: #b00020; display: block; margin-top: 6px; }

@media (max-width: 640px) {
  .month-filter {
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
  }
  .control { width: 100%; }
}
</style>
