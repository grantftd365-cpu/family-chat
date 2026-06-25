/**
 * 本地存储封装
 * 统一管理 token、用户信息、聊天记录等本地数据
 */

const STORAGE_PREFIX = 'family_chat_'

/**
 * 设置存储
 * @param {string} key 键名
 * @param {*} value 值
 * @param {number} expire 过期时间（秒），0表示永不过期
 */
export function setStorage(key, value, expire = 0) {
  const data = {
    value,
    timestamp: Date.now(),
    expire: expire > 0 ? expire * 1000 : 0
  }
  try {
    uni.setStorageSync(STORAGE_PREFIX + key, JSON.stringify(data))
  } catch (e) {
    console.error('存储写入失败:', key, e)
  }
}

/**
 * 读取存储
 * @param {string} key 键名
 * @param {*} defaultValue 默认值
 * @returns {*}
 */
export function getStorage(key, defaultValue = null) {
  try {
    const raw = uni.getStorageSync(STORAGE_PREFIX + key)
    if (!raw) return defaultValue
    const data = JSON.parse(raw)
    if (data.expire > 0 && Date.now() - data.timestamp > data.expire) {
      uni.removeStorageSync(STORAGE_PREFIX + key)
      return defaultValue
    }
    return data.value
  } catch (e) {
    return defaultValue
  }
}

/**
 * 删除存储
 * @param {string} key 键名
 */
export function removeStorage(key) {
  try {
    uni.removeStorageSync(STORAGE_PREFIX + key)
  } catch (e) {
    console.error('存储删除失败:', key, e)
  }
}

/**
 * 清空所有应用存储
 */
export function clearStorage() {
  try {
    const res = uni.getStorageInfoSync()
    res.keys.forEach(k => {
      if (k.startsWith(STORAGE_PREFIX)) {
        uni.removeStorageSync(k)
      }
    })
  } catch (e) {
    console.error('存储清空失败:', e)
  }
}

/* === 便捷方法 === */

/** Token 管理 */
export function getToken() {
  return getStorage('token', '')
}

export function setToken(token) {
  setStorage('token', token, 86400 * 7) // 7天有效
}

export function removeToken() {
  removeStorage('token')
}

/** 用户信息 */
export function getUserInfo() {
  return getStorage('userInfo', null)
}

export function setUserInfo(info) {
  setStorage('userInfo', info)
}

export function removeUserInfo() {
  removeStorage('userInfo')
}

/** 草稿箱 */
export function getDraft(groupId) {
  return getStorage(`draft_${groupId}`, '')
}

export function setDraft(groupId, text) {
  if (text) {
    setStorage(`draft_${groupId}`, text)
  } else {
    removeStorage(`draft_${groupId}`)
  }
}

/** 聊天记录本地缓存 */
export function getCachedMessages(groupId) {
  return getStorage(`messages_${groupId}`, [])
}

export function setCachedMessages(groupId, messages) {
  setStorage(`messages_${groupId}`, messages)
}

/** 主题设置 */
export function getTheme() {
  return getStorage('theme', 'light')
}

export function setTheme(theme) {
  setStorage('theme', theme)
}

/** 未读数 */
export function getUnreadCount(groupId) {
  return getStorage(`unread_${groupId}`, 0)
}

export function setUnreadCount(groupId, count) {
  setStorage(`unread_${groupId}`, count)
}

export function clearUnreadCount(groupId) {
  removeStorage(`unread_${groupId}`)
}
