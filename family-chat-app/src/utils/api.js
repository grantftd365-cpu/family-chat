/**
 * API 请求封装
 * 支持 H5 / 小程序 / APP 多端
 * 包含 token 自动注入、错误处理、请求拦截
 */
import { getToken, removeToken, removeUserInfo } from './storage'

/** 基础配置 */
const CONFIG = {
  // H5模式下使用相对路径（同域代理），其他模式配置完整地址
  baseUrl: (() => {
    // #ifdef H5
    return ''
    // #endif
    // #ifndef H5
    return 'http://localhost:8000'
    // #endif
  })(),
  timeout: 15000,
  header: {
    'Content-Type': 'application/json'
  }
}

/**
 * 核心请求方法
 * @param {object} options 请求配置
 * @returns {Promise}
 */
function request(options) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    const header = { ...CONFIG.header, ...options.header }
    if (token) {
      header['Authorization'] = `Bearer ${token}`
    }

    uni.request({
      url: CONFIG.baseUrl + options.url,
      method: options.method || 'GET',
      data: options.data,
      header,
      timeout: options.timeout || CONFIG.timeout,
      success: (res) => {
        if (res.statusCode === 200 || res.statusCode === 201) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          // Token 过期，清除登录态并跳转
          removeToken()
          removeUserInfo()
          uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
          setTimeout(() => {
            uni.reLaunch({ url: '/pages/login/login' })
          }, 1500)
          reject(new Error('未授权'))
        } else if (res.statusCode === 403) {
          uni.showToast({ title: '没有权限', icon: 'none' })
          reject(new Error('没有权限'))
        } else if (res.statusCode === 404) {
          reject(new Error('资源不存在'))
        } else if (res.statusCode === 422) {
          const msg = res.data?.detail?.[0]?.msg || res.data?.detail || '参数错误'
          uni.showToast({ title: msg, icon: 'none' })
          reject(new Error(msg))
        } else {
          const msg = res.data?.detail || res.data?.message || `请求失败(${res.statusCode})`
          uni.showToast({ title: msg, icon: 'none' })
          reject(new Error(msg))
        }
      },
      fail: (err) => {
        uni.showToast({ title: '网络连接失败', icon: 'none' })
        reject(new Error(err.errMsg || '网络错误'))
      }
    })
  })
}

/** GET 请求 */
function get(url, data = {}) {
  return request({ url, method: 'GET', data })
}

/** POST 请求 */
function post(url, data = {}) {
  return request({ url, method: 'POST', data })
}

/** PUT 请求 */
function put(url, data = {}) {
  return request({ url, method: 'PUT', data })
}

/** DELETE 请求 */
function del(url, data = {}) {
  return request({ url, method: 'DELETE', data })
}

/* ========== 用户相关 ========== */

/** 注册 */
export function register(data) {
  return post('/api/register', data)
}

/** 登录 */
export function login(data) {
  return post('/api/login', data)
}

/** 微信登录 */
export function wxLogin(code) {
  return post('/api/wx-login', { code })
}

/** 获取当前用户信息 */
export function getMe() {
  return get('/api/me')
}

/** 更新个人资料 */
export function updateMe(data) {
  return put('/api/me', data)
}

/** 上传头像 */
export function uploadAvatar(filePath) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    uni.uploadFile({
      url: CONFIG.baseUrl + '/api/me/avatar',
      filePath,
      name: 'file',
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(JSON.parse(res.data))
        } else {
          reject(new Error('上传失败'))
        }
      },
      fail: (err) => reject(new Error(err.errMsg || '上传失败'))
    })
  })
}

/* ========== 群组相关 ========== */

/** 获取群列表 */
export function getGroups() {
  return get('/api/groups')
}

/** 创建群 */
export function createGroup(data) {
  return post('/api/groups', data)
}

/** 获取群成员 */
export function getGroupMembers(groupId) {
  return get(`/api/groups/${groupId}/members`)
}

/* ========== 消息相关 ========== */

/** 获取消息列表 */
export function getMessages(groupId, limit = 100) {
  return get(`/api/messages/${groupId}`, { limit })
}

/** 发送消息 */
export function sendMessage(data) {
  return post('/api/messages', data)
}

/** 撤回消息 */
export function recallMessage(messageId) {
  return post('/api/messages/recall', { message_id: messageId })
}

/** 转发消息 */
export function forwardMessage(messageId, targetGroupId) {
  return post('/api/messages/forward', { message_id: messageId, target_group_id: targetGroupId })
}

/** 置顶消息 */
export function pinMessage(messageId) {
  return post(`/api/messages/${messageId}/pin`)
}

/** 表情反应 */
export function addReaction(messageId, emoji) {
  return post(`/api/messages/${messageId}/reactions`, { emoji })
}

/* ========== 数字人相关 ========== */

/** 获取数字人列表 */
export function getAgents() {
  return get('/api/agents')
}

/** 炼化文本 */
export function refineText(data) {
  return post('/api/agents/refine/text', data)
}

/* ========== 好友相关 ========== */

/** 获取好友列表 */
export function getFriends() {
  return get('/api/friends')
}

/** 获取好友请求 */
export function getFriendRequests() {
  return get('/api/friends/requests')
}

/** 处理好友请求 */
export function handleFriendRequest(data) {
  return post('/api/friends/requests/handle', data)
}

/* ========== 朋友圈相关 ========== */

/** 获取朋友圈动态 */
export function getMoments() {
  return get('/api/moments')
}

/** 发布朋友圈 */
export function postMoment(data) {
  return post('/api/moments', data)
}

/** 点赞 */
export function likeMoment(momentId) {
  return post(`/api/moments/${momentId}/like`)
}

/** 评论 */
export function commentMoment(momentId, content) {
  return post(`/api/moments/${momentId}/comment`, { content })
}

/** 上传朋友圈图片 */
export function uploadMomentImage(filePath) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    uni.uploadFile({
      url: CONFIG.baseUrl + '/api/moments/upload',
      filePath,
      name: 'file',
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(JSON.parse(res.data))
        } else {
          reject(new Error('上传失败'))
        }
      },
      fail: (err) => reject(new Error(err.errMsg || '上传失败'))
    })
  })
}

/* ========== 收藏相关 ========== */

/** 获取收藏列表 */
export function getFavorites() {
  return get('/api/favorites')
}

/** 添加收藏 */
export function addFavorite(data) {
  return post('/api/favorites', data)
}

/* ========== 搜索 ========== */

/** 全局搜索 */
export function search(q) {
  return get('/api/search', { q })
}

/* ========== 配置 ========== */

/** 获取 LLM 配置 */
export function getLLMConfig() {
  return get('/api/config/llm')
}

/** 更新 LLM 配置 */
export function updateLLMConfig(data) {
  return post('/api/config/llm', data)
}

/* ========== 语音 ========== */

/** TTS 语音合成 */
export function textToSpeech(text) {
  return post(`/api/tts?text=${encodeURIComponent(text)}`)
}

/** 上传语音 */
export function uploadVoice(filePath) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    uni.uploadFile({
      url: CONFIG.baseUrl + '/api/voice/upload',
      filePath,
      name: 'file',
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(JSON.parse(res.data))
        } else {
          reject(new Error('上传失败'))
        }
      },
      fail: (err) => reject(new Error(err.errMsg || '上传失败'))
    })
  })
}

export default {
  register,
  login,
  wxLogin,
  getMe,
  updateMe,
  uploadAvatar,
  getGroups,
  createGroup,
  getGroupMembers,
  getMessages,
  sendMessage,
  recallMessage,
  forwardMessage,
  pinMessage,
  addReaction,
  getAgents,
  refineText,
  getFriends,
  getFriendRequests,
  handleFriendRequest,
  getMoments,
  postMoment,
  likeMoment,
  commentMoment,
  uploadMomentImage,
  getFavorites,
  addFavorite,
  search,
  getLLMConfig,
  updateLLMConfig,
  textToSpeech,
  uploadVoice
}
