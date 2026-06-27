/**
 * API 请求封装 - 优化版
 * 支持 H5 / 小程序 / APP 多端
 * 包含 token 自动注入、错误处理、自动重试、请求队列
 */
import { getToken, removeToken, removeUserInfo } from './storage'

/** 基础配置 */
// 服务器地址：H5 模式使用相对路径，非 H5 从 manifest 配置或环境变量读取
const _getServerUrl = () => {
  // #ifdef H5
  return ''
  // #endif
  // #ifndef H5
  // 优先从 uni-app 的 manifest 配置读取
  try {
    const manifest = uni.getStorageSync('server_url')
    if (manifest) return manifest
  } catch (e) {}
  // 从编译时常量读取（在 vite.config.js 中定义）
  if (typeof __SERVER_URL__ !== 'undefined' && __SERVER_URL__) return __SERVER_URL__
  // 开发环境默认值
  return 'http://localhost:8000'
  // #endif
}

const CONFIG = {
  baseUrl: _getServerUrl(),
  timeout: 15000,
  maxRetries: 2,
  retryDelay: 1000,
  header: {
    'Content-Type': 'application/json'
  }
}

/** 请求计数器（用于取消重复请求） */
let _requestId = 0

/**
 * 核心请求方法（支持自动重试）
 * @param {object} options 请求配置
 * @param {number} retryCount 当前重试次数
 * @returns {Promise}
 */
function request(options, retryCount = 0) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    const header = { ...CONFIG.header, ...options.header }
    if (token) {
      header['Authorization'] = `Bearer ${token}`
    }

    const requestId = ++_requestId
    const timeout = options.timeout || CONFIG.timeout

    const timer = setTimeout(() => {
      reject(new Error('请求超时'))
    }, timeout + 1000)

    uni.request({
      url: CONFIG.baseUrl + options.url,
      method: options.method || 'GET',
      data: options.data,
      header,
      timeout,
      success: (res) => {
        clearTimeout(timer)
        if (res.statusCode === 200 || res.statusCode === 201) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          removeToken()
          removeUserInfo()
          uni.showToast({ title: '登录已过期', icon: 'none' })
          setTimeout(() => {
            uni.reLaunch({ url: '/pages/login/login' })
          }, 1500)
          reject(new Error('未授权'))
        } else if (res.statusCode === 403) {
          reject(new Error('没有权限'))
        } else if (res.statusCode === 404) {
          reject(new Error('资源不存在'))
        } else if (res.statusCode === 429) {
          // 被限流，重试
          if (retryCount < CONFIG.maxRetries) {
            setTimeout(() => {
              request(options, retryCount + 1).then(resolve).catch(reject)
            }, CONFIG.retryDelay * (retryCount + 1))
            return
          }
          reject(new Error('请求过于频繁'))
        } else if (res.statusCode >= 500) {
          // 服务器错误，重试
          if (retryCount < CONFIG.maxRetries) {
            setTimeout(() => {
              request(options, retryCount + 1).then(resolve).catch(reject)
            }, CONFIG.retryDelay * (retryCount + 1))
            return
          }
          const msg = res.data?.detail || `服务器错误(${res.statusCode})`
          reject(new Error(msg))
        } else {
          const msg = res.data?.detail || res.data?.message || `请求失败(${res.statusCode})`
          uni.showToast({ title: msg, icon: 'none' })
          reject(new Error(msg))
        }
      },
      fail: (err) => {
        clearTimeout(timer)
        // 网络错误自动重试
        if (retryCount < CONFIG.maxRetries) {
          setTimeout(() => {
            request(options, retryCount + 1).then(resolve).catch(reject)
          }, CONFIG.retryDelay * (retryCount + 1))
          return
        }
        uni.showToast({ title: '网络连接失败', icon: 'none', duration: 2000 })
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

/* ========== 消息必达 + 已读回执 + 表情回应 ========== */

/** 批量确认收到消息 (ACK) */
export function ackMessages(messageIds) {
  return post('/api/messages/ack', { message_ids: messageIds })
}

/** 批量标记已读 — 打开群聊时调用 */
export function markGroupRead(groupId, beforeTimestamp) {
  return post('/api/messages/read', { group_id: groupId, before_timestamp: beforeTimestamp || 0 })
}

/** 标记单条消息已读 */
export function markMessageRead(messageId) {
  return post(`/api/messages/${messageId}/read`)
}

/** 获取已读某消息的用户列表 */
export function getReadUsers(messageId) {
  return get(`/api/messages/${messageId}/read-users`)
}

/** 获取所有群的未读消息数 */
export function getAllUnread() {
  return get('/api/unread')
}

/** 获取断线期间未送达消息 */
export function getUndelivered() {
  return get('/api/undelivered')
}

/** 添加表情回应 (飞书风格) */
export function addReactionV2(messageId, emoji) {
  return post(`/api/messages/${messageId}/reactions/v2`, { emoji })
}

/** 移除表情回应 */
export function removeReactionV2(messageId, emoji) {
  return del(`/api/messages/${messageId}/reactions/v2/${emoji}`)
}

/** 获取消息的表情回应 */
export function getReactionsV2(messageId) {
  return get(`/api/messages/${messageId}/reactions/v2`)
}

/* ========== 搜索 ========== */

/** 在群聊中搜索消息 */
export function searchGroupMessages(groupId, q, limit = 20) {
  return get(`/api/messages/${groupId}/search`, { q, limit })
}

/* ========== 群公告 + 置顶 ========== */

/** 获取群公告 */
export function getGroupAnnouncement(groupId) {
  return get(`/api/groups/${groupId}/announcement`)
}

/** 更新群公告 */
export function updateGroupAnnouncement(groupId, data) {
  return put(`/api/groups/${groupId}/announcement`, data)
}

/** 置顶消息到群 */
export function pinMessageToGroup(groupId, messageId) {
  return post(`/api/groups/${groupId}/pin/${messageId}`)
}

/** 获取群置顶消息 */
export function getGroupPinned(groupId) {
  return get(`/api/groups/${groupId}/pinned`)
}

/* ========== 消息管理 ========== */

/** 删除消息（仅自己可见） */
export function deleteMessage(messageId) {
  return del(`/api/messages/${messageId}`)
}

/* ========== 用户状态 ========== */

/** 查询用户在线状态 */
export function getUserOnline(userId) {
  return get(`/api/users/${userId}/online`)
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

/* ========== 语音音色管理 ========== */

/** 获取音色配置列表 */
export function getVoiceProfiles() {
  return get('/api/voice-profiles')
}

/** 获取可用 edge-tts 声音 */
export function getAvailableVoices() {
  return get('/api/voice-profiles/available')
}

/** 创建音色配置 */
export function createVoiceProfile(name, edgeVoiceId, gender = '') {
  return post('/api/voice-profiles', { name, edge_voice_id: edgeVoiceId, gender })
}

/** 上传音频创建音色配置 */
export function uploadVoiceProfile(name, filePath, gender = '') {
  return new Promise((resolve, reject) => {
    const token = getToken()
    uni.uploadFile({
      url: CONFIG.baseUrl + '/api/voice-profiles/upload',
      filePath,
      name: 'file',
      formData: { name, gender },
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) resolve(JSON.parse(res.data))
        else reject(new Error('上传失败'))
      },
      fail: (err) => reject(new Error(err.errMsg || '上传失败'))
    })
  })
}

/** 删除音色配置 */
export function deleteVoiceProfile(profileId) {
  return del(`/api/voice-profiles/${profileId}`)
}

/** 分配音色给数字人 */
export function assignVoiceToAgent(agentId, profileId) {
  return post('/api/voice-profiles/assign', { agent_id: agentId, profile_id: profileId })
}

/** 获取数字人音色配置 */
export function getAgentVoice(agentId) {
  return get(`/api/voice-profiles/agent/${agentId}`)
}

/** 预览音色合成 */
export function synthesizeVoicePreview(text, edgeVoiceId = '', profileId = '') {
  return new Promise((resolve, reject) => {
    const token = getToken()
    uni.uploadFile({
      url: CONFIG.baseUrl + '/api/voice-profiles/synthesize',
      filePath: '',
      name: 'file',
      formData: { text, edge_voice_id: edgeVoiceId, profile_id: profileId },
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) {
          const audio = uni.createInnerAudioContext()
          audio.src = 'data:audio/mp3;base64,' + res.data
          audio.play()
          audio.onEnded(() => { audio.destroy(); resolve() })
          audio.onError(() => { audio.destroy(); reject(new Error('播放失败')) })
        } else reject(new Error('合成失败'))
      },
      fail: (err) => reject(new Error(err.errMsg || '合成失败'))
    })
  })
}

/* ========== 多模态炼化 ========== */

/** 从文本炼化 */
export function refineFromText(data) {
  return post('/api/agents/refine/text', data)
}

/** 从语音炼化 */
export function refineFromVoice(agentId, filePath) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    uni.uploadFile({
      url: CONFIG.baseUrl + '/api/agents/refine/voice',
      filePath,
      name: 'file',
      formData: { agent_id: agentId },
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) resolve(JSON.parse(res.data))
        else reject(new Error('炼化失败'))
      },
      fail: (err) => reject(new Error(err.errMsg || '炼化失败'))
    })
  })
}

/** 从视频炼化 */
export function refineFromVideo(agentId, filePath) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    uni.uploadFile({
      url: CONFIG.baseUrl + '/api/agents/refine/video',
      filePath,
      name: 'file',
      formData: { agent_id: agentId },
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) resolve(JSON.parse(res.data))
        else reject(new Error('炼化失败'))
      },
      fail: (err) => reject(new Error(err.errMsg || '炼化失败'))
    })
  })
}

/** 从文档炼化 */
export function refineFromDocument(agentId, filePath) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    uni.uploadFile({
      url: CONFIG.baseUrl + '/api/agents/refine/document',
      filePath,
      name: 'file',
      formData: { agent_id: agentId },
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) resolve(JSON.parse(res.data))
        else reject(new Error('炼化失败'))
      },
      fail: (err) => reject(new Error(err.errMsg || '炼化失败'))
    })
  })
}

/** 从聊天记录炼化 */
export function refineFromChatHistory(data) {
  return post('/api/agents/refine/chat-history', data)
}

/** 从自我描述炼化 — 最深层数据源 */
export function refineFromSelfDescription(agentId, answers) {
  return post('/api/agents/refine/self-description', { agent_id: agentId, answers })
}

/** 获取炼化问卷模板 */
export function getRefinementQuestionnaire() {
  return get('/api/agents/refine/questionnaire')
}

/** 获取数字人七层本质 */
export function getAgentEssence(agentId) {
  return get(`/api/agents/refine/essence/${agentId}`)
}

/** 获取炼化完成度 */
export function getRefinementCompleteness(agentId) {
  return get(`/api/agents/refine/completeness/${agentId}`)
}

/** 获取炼化历史 */
export function getRefinementHistory(agentId, limit = 20) {
  return get(`/api/agents/refine/history/${agentId}`, { limit })
}

/* ========== 微信 OAuth ========== */

/** 获取微信 OAuth 授权 URL */
export function getWxOAuthUrl(redirectUri) {
  return get('/api/wx/oauth/url', { redirect_uri: redirectUri })
}

/** 微信 OAuth 登录 */
export function wxOAuthLogin(code) {
  return post('/api/wx/oauth/login', { code })
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
  ackMessages,
  markGroupRead,
  markMessageRead,
  getReadUsers,
  getAllUnread,
  getUndelivered,
  addReactionV2,
  removeReactionV2,
  getReactionsV2,
  searchGroupMessages,
  getGroupAnnouncement,
  updateGroupAnnouncement,
  pinMessageToGroup,
  getGroupPinned,
  deleteMessage,
  getUserOnline,
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
  uploadVoice,
  getVoiceProfiles,
  getAvailableVoices,
  createVoiceProfile,
  uploadVoiceProfile,
  deleteVoiceProfile,
  assignVoiceToAgent,
  getAgentVoice,
  synthesizeVoicePreview,
  refineFromText,
  refineFromVoice,
  refineFromVideo,
  refineFromDocument,
  refineFromChatHistory,
  refineFromSelfDescription,
  getRefinementQuestionnaire,
  getAgentEssence,
  getRefinementCompleteness,
  getRefinementHistory,
  getWxOAuthUrl,
  wxOAuthLogin
}
