const SERVER_URL_KEY = 'server_url'
const DEFAULT_DEV_SERVER_URL = 'http://localhost:8000'

function normalizeServerUrl(value) {
  const url = String(value || '').trim().replace(/\/+$/, '')
  if (!url) return ''
  if (!/^https?:\/\//i.test(url)) return `https://${url}`
  return url
}

function getStoredServerUrl() {
  try {
    return normalizeServerUrl(uni.getStorageSync(SERVER_URL_KEY))
  } catch (e) {
    return ''
  }
}

function getCompiledServerUrl() {
  try {
    if (typeof __SERVER_URL__ !== 'undefined') {
      return normalizeServerUrl(__SERVER_URL__)
    }
  } catch (e) {}
  return ''
}

export function getServerUrl() {
  // #ifdef H5
  return ''
  // #endif
  // #ifndef H5
  return getStoredServerUrl() || getCompiledServerUrl() || DEFAULT_DEV_SERVER_URL
  // #endif
}

export function getDisplayServerUrl() {
  return getStoredServerUrl() || getCompiledServerUrl()
}

export function saveServerUrl(value) {
  const url = normalizeServerUrl(value)
  if (!url) {
    uni.removeStorageSync(SERVER_URL_KEY)
    return ''
  }
  uni.setStorageSync(SERVER_URL_KEY, url)
  return url
}

export function clearServerUrl() {
  uni.removeStorageSync(SERVER_URL_KEY)
}

export function toWebSocketUrl(serverUrl) {
  return normalizeServerUrl(serverUrl).replace(/^https?:\/\//, (matched) => {
    return matched.toLowerCase() === 'https://' ? 'wss://' : 'ws://'
  })
}

export function isLocalServerUrl(serverUrl) {
  return /^(https?:\/\/)?(localhost|127\.0\.0\.1)(:|\/|$)/i.test(String(serverUrl || ''))
}

