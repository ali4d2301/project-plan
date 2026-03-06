const rawTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS)
const rawRetryCount = Number(import.meta.env.VITE_API_RETRY_COUNT)
const rawRetryDelayMs = Number(import.meta.env.VITE_API_RETRY_DELAY_MS)

export const DEFAULT_FETCH_TIMEOUT_MS =
  Number.isFinite(rawTimeout) && rawTimeout > 0 ? rawTimeout : 10000
export const DEFAULT_FETCH_RETRY_COUNT =
  Number.isFinite(rawRetryCount) && rawRetryCount >= 0 ? Math.floor(rawRetryCount) : 2
export const DEFAULT_FETCH_RETRY_DELAY_MS =
  Number.isFinite(rawRetryDelayMs) && rawRetryDelayMs > 0 ? rawRetryDelayMs : 400

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function toRequestMeta(url, options = {}) {
  const method = String(options?.method || "GET").toUpperCase()
  const requestUrl =
    typeof url === "string"
      ? url
      : typeof url?.url === "string"
        ? url.url
        : String(url)
  return { method, url: requestUrl }
}

function nowIso() {
  return new Date().toISOString()
}

function createHttpError(response) {
  const status = response?.status ?? 0
  const error = new Error(`HTTP ${status}`)
  error.code = "HTTP"
  error.status = status
  return error
}

function shouldRetry(error) {
  if (!error) return false
  if (error.code === "TIMEOUT" || error.code === "NETWORK") return true
  if (error.code === "HTTP") {
    const status = Number(error.status)
    return status === 408 || status === 425 || status === 429 || status >= 500
  }
  return false
}

function normalizeErrorForLog(error) {
  return {
    code: error?.code || "UNKNOWN",
    status: Number.isFinite(Number(error?.status)) ? Number(error.status) : null,
    message: String(error?.message || "Unknown error"),
    timeoutMs: Number.isFinite(Number(error?.timeoutMs)) ? Number(error.timeoutMs) : null,
  }
}

function attachApiMeta(error, meta) {
  if (!error || typeof error !== "object") return
  const current = error.apiMeta && typeof error.apiMeta === "object" ? error.apiMeta : {}
  error.apiMeta = { ...current, ...meta }
}

function logApiFailure({ request, attempt, maxAttempts, retryDelayMs, error }) {
  const info = normalizeErrorForLog(error)
  const payload = {
    timestamp: nowIso(),
    method: request.method,
    url: request.url,
    attempt,
    maxAttempts,
    code: info.code,
    status: info.status,
    message: info.message,
    timeoutMs: info.timeoutMs,
  }

  if (retryDelayMs > 0) {
    console.warn("[API_RETRY]", { ...payload, nextRetryInMs: retryDelayMs })
    return
  }

  console.error("[API_ERROR]", payload)
}

export async function fetchWithTimeout(url, options = {}) {
  const { timeoutMs = DEFAULT_FETCH_TIMEOUT_MS, ...fetchOptions } = options
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  try {
    return await fetch(url, { ...fetchOptions, signal: controller.signal })
  } catch (error) {
    if (error?.name === "AbortError") {
      const timeoutError = new Error(`Request timed out after ${timeoutMs}ms`)
      timeoutError.code = "TIMEOUT"
      timeoutError.timeoutMs = timeoutMs
      throw timeoutError
    }

    if (error instanceof TypeError) {
      const networkError = new Error(error.message || "Network request failed")
      networkError.code = "NETWORK"
      throw networkError
    }

    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function fetchWithRetry(url, options = {}) {
  const {
    retries = DEFAULT_FETCH_RETRY_COUNT,
    retryDelayMs = DEFAULT_FETCH_RETRY_DELAY_MS,
    retryBackoff = 1.5,
    ...fetchOptions
  } = options
  const maxAttempts = Math.max(1, Number(retries) + 1)
  const request = toRequestMeta(url, fetchOptions)

  let lastError = null

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await fetchWithTimeout(url, fetchOptions)
      if (!response?.ok) throw createHttpError(response)
      return response
    } catch (error) {
      lastError = error
      const canRetry = attempt < maxAttempts && shouldRetry(error)

      const safeBaseDelay = Math.max(0, Number(retryDelayMs) || 0)
      const safeBackoff = Math.max(1, Number(retryBackoff) || 1)
      const delay = canRetry
        ? Math.round(safeBaseDelay * Math.pow(safeBackoff, attempt - 1))
        : 0
      attachApiMeta(error, {
        ...request,
        attempt,
        maxAttempts,
        timestamp: nowIso(),
      })
      logApiFailure({
        request,
        attempt,
        maxAttempts,
        retryDelayMs: delay,
        error,
      })

      if (!canRetry) throw error
      if (delay > 0) await wait(delay)
    }
  }

  throw lastError
}

export function assertOk(response) {
  if (response?.ok) return
  throw createHttpError(response)
}

function toSeconds(ms) {
  const value = Number(ms)
  if (!Number.isFinite(value) || value <= 0) return 10
  return Math.max(1, Math.round(value / 1000))
}

export function getFetchErrorMessage(error, resourceLabel = "les donnees") {
  if (error?.code === "TIMEOUT") {
    const seconds = toSeconds(error.timeoutMs || DEFAULT_FETCH_TIMEOUT_MS)
    return `Le serveur met trop de temps a repondre (${seconds}s) pour ${resourceLabel}. Reessayez.`
  }

  if (error?.code === "NETWORK") {
    return `Impossible de joindre le serveur pour ${resourceLabel}. Verifiez le reseau puis reessayez.`
  }

  if (error?.code === "HTTP") {
    return `Le serveur a renvoye une erreur (${error.status}) pour ${resourceLabel}.`
  }

  return `Echec du chargement de ${resourceLabel}. Reessayez.`
}
