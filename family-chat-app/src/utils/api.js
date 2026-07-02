/**
 * API 请求封装 - 优化版
 * 支持 H5 / 小程序 / APP 多端
 * 包含 token 自动注入、错误处理、自动重试、请求队列
 */
import { getToken, removeToken, removeUserInfo } from './storage'
import { getServerUrl } from './server-config'

/** 基础配置 */
const CONFIG = {
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
      url: getServerUrl() + options.url,
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
          const msg = res.data?.detail || res.data?.message || '没有权限'
          reject(new Error(msg))
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

function parseResponseData(data) {
  if (typeof data !== 'string') return data
  try { return JSON.parse(data) } catch (e) { return data }
}

function getResponseErrorMessage(res, fallback = '请求失败') {
  const data = parseResponseData(res.data)
  return data?.detail || data?.message || data?.error || `${fallback}(${res.statusCode})`
}

export function toAbsoluteMediaUrl(url) {
  if (!url) return ''
  if (/^(https?:|file:|data:|blob:)/i.test(url)) return url
  const base = getServerUrl()
  if (base) return base + url
  // #ifdef H5
  if (typeof window !== 'undefined' && window.location?.pathname?.startsWith('/family-chat')) {
    return '/family-chat' + url
  }
  // #endif
  return url
}

function formEncode(data) {
  return Object.entries(data)
    .filter(([, value]) => value !== undefined && value !== null)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&')
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
export function wxLogin(code, profile = {}) {
  return post('/api/wx-login', { code, ...profile })
}

/** 获取当前用户信息 */
export function getMe() {
  return get('/api/me')
}

/** 更新个人资料 */
export function updateMe(data) {
  return put('/api/me', data)
}


function uploadFileToEndpoint(endpoint, fileOrPath, fallbackName = 'file') {
  return new Promise((resolve, reject) => {
    const token = getToken()
    // #ifdef H5
    if (typeof File !== 'undefined' && fileOrPath instanceof File) {
      const form = new FormData()
      form.append('file', fileOrPath, fileOrPath.name || fallbackName)
      const xhr = new XMLHttpRequest()
      xhr.open('POST', getServerUrl() + endpoint)
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      xhr.onload = () => {
        const data = parseResponseData(xhr.responseText)
        if (xhr.status === 200 || xhr.status === 201) resolve(data)
        else reject(new Error(data?.detail || data?.message || '上传失败'))
      }
      xhr.onerror = () => reject(new Error('上传失败'))
      xhr.send(form)
      return
    }
    // #endif
    uni.uploadFile({
      url: getServerUrl() + endpoint,
      filePath: fileOrPath,
      name: 'file',
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200 || res.statusCode === 201) resolve(parseResponseData(res.data))
        else reject(new Error(getResponseErrorMessage(res, '上传失败')))
      },
      fail: (err) => reject(new Error(err.errMsg || '上传失败'))
    })
  })
}

/** 上传头像 */
export function uploadAvatar(filePath) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    uni.uploadFile({
      url: getServerUrl() + '/api/me/avatar',
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

export function getOrCreateDirectGroup(friendId) {
  return post(`/api/groups/direct/${friendId}`)
}

/** 获取群成员 */
export function getGroupMembers(groupId) {
  return get(`/api/groups/${groupId}/members`)
}

export function addGroupMember(groupId, userId, role = 'member') {
  return post(`/api/groups/${groupId}/members`, { user_id: userId, role })
}

export function generateFamilyInviteCode(groupId) {
  return post(`/api/groups/${groupId}/invite-code`)
}

export function joinFamilyByCode(code) {
  return post(`/api/family/join?code=${encodeURIComponent(code)}`)
}

export function checkFamilyInviteCode(code) {
  return get('/api/family/check-code', { code })
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
export function getAgents(params = {}) {
  return get('/api/agents', params)
}

/** 获取单个数字人 */
export function getAgent(agentId) {
  return get(`/api/agents/${agentId}`)
}

/** 更新数字人 */
export function updateAgent(agentId, data) {
  return put(`/api/agents/${agentId}`, data)
}

/** 删除数字人 */
export function deleteAgent(agentId) {
  return del(`/api/agents/${agentId}`)
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

export function sendFriendRequest(toUserId, message = '') {
  return post('/api/friends/request', { to_user_id: toUserId, message })
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
  return uploadFileToEndpoint('/api/moments/upload', filePath)
}

export function uploadChatImage(filePath) {
  return uploadFileToEndpoint('/api/upload/image', filePath)
}

export function uploadChatFile(fileOrPath) {
  return uploadFileToEndpoint('/api/upload/file', fileOrPath)
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
export function createRedEnvelope(data) {
  return post('/api/red-envelopes', data)
}

export function claimRedEnvelope(envelopeId) {
  return post(`/api/red-envelopes/${envelopeId}/claim`)
}

export function getRedEnvelope(envelopeId) {
  return get(`/api/red-envelopes/${envelopeId}`)
}

export function uploadVoice(filePath) {
  return new Promise((resolve, reject) => {
    const token = getToken()
    uni.uploadFile({
      url: getServerUrl() + '/api/voice/upload',
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

/** 获取语音能力诊断 */
export function getVoiceDiagnostics() {
  return get('/api/voice-profiles/diagnostics')
}

/** 创建音色配置 */
export function createVoiceProfile(name, edgeVoiceId, gender = '') {
  return post('/api/voice-profiles', { name, edge_voice_id: edgeVoiceId, gender })
}

/** 上传音频创建音色配置 */
export function uploadVoiceProfile(name, filePath, gender = '', voiceEngine = 'edge-tts') {
  return new Promise((resolve, reject) => {
    const token = getToken()
    uni.uploadFile({
      url: getServerUrl() + '/api/voice-profiles/upload',
      filePath,
      name: 'file',
      formData: { name, gender, voice_engine: voiceEngine },
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) resolve(parseResponseData(res.data))
        else reject(new Error(getResponseErrorMessage(res, '上传失败')))
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
    uni.request({
      url: getServerUrl() + '/api/voice-profiles/synthesize',
      method: 'POST',
      data: formEncode({ text, edge_voice_id: edgeVoiceId, profile_id: profileId, as_url: true }),
      header: {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      success: (res) => {
        if (res.statusCode === 200) {
          const data = parseResponseData(res.data)
          const src = toAbsoluteMediaUrl(data?.url)
          if (!src) {
            reject(new Error('预览地址为空'))
            return
          }
          const audio = uni.createInnerAudioContext()
          let settled = false
          const settle = (ok, err) => {
            if (settled) return
            settled = true
            ok ? resolve(audio) : reject(err || new Error('播放失败'))
          }
          audio.src = src
          audio.onCanplay(() => settle(true))
          audio.onEnded(() => audio.destroy())
          audio.onError(() => { audio.destroy(); settle(false, new Error('播放失败')) })
          audio.play()
          setTimeout(() => settle(true), 800)
        } else reject(new Error(getResponseErrorMessage(res, '合成失败')))
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
      url: getServerUrl() + '/api/agents/refine/voice',
      filePath,
      name: 'file',
      formData: { agent_id: agentId },
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) resolve(parseResponseData(res.data))
        else reject(new Error(getResponseErrorMessage(res, '炼化失败')))
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
      url: getServerUrl() + '/api/agents/refine/video',
      filePath,
      name: 'file',
      formData: { agent_id: agentId },
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) resolve(parseResponseData(res.data))
        else reject(new Error(getResponseErrorMessage(res, '炼化失败')))
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
      url: getServerUrl() + '/api/agents/refine/document',
      filePath,
      name: 'file',
      formData: { agent_id: agentId },
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) resolve(parseResponseData(res.data))
        else reject(new Error(getResponseErrorMessage(res, '炼化失败')))
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
  toAbsoluteMediaUrl,
  uploadAvatar,
  getGroups,
  getOrCreateDirectGroup,
  createGroup,
  getGroupMembers,
  addGroupMember,
  generateFamilyInviteCode,
  joinFamilyByCode,
  checkFamilyInviteCode,
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
  getAgent,
  updateAgent,
  deleteAgent,
  refineText,
  getFriends,
  sendFriendRequest,
  getFriendRequests,
  handleFriendRequest,
  getMoments,
  postMoment,
  likeMoment,
  commentMoment,
  uploadMomentImage,
  uploadChatFile,
  uploadChatImage,
  getFavorites,
  addFavorite,
  search,
  getLLMConfig,
  updateLLMConfig,
  textToSpeech,
  uploadVoice,
  getRedEnvelope,
  claimRedEnvelope,
  createRedEnvelope,
  getVoiceProfiles,
  getAvailableVoices,
  getVoiceDiagnostics,
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
