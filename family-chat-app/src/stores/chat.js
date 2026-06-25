/**
 * 聊天状态管理
 */
import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import * as api from '../utils/api'
import ws from '../utils/ws'
import { getCachedMessages, setCachedMessages, getUnreadCount, setUnreadCount, clearUnreadCount } from '../utils/storage'

export const useChatStore = defineStore('chat', () => {
  const groups = ref([])
  const currentGroupId = ref(null)
  const messagesMap = reactive({})  // groupId -> messages[]
  const unreadMap = reactive({})    // groupId -> count
  const typingMap = reactive({})    // groupId -> { name, timer }

  /** 加载群列表 */
  async function loadGroups() {
    try {
      const res = await api.getGroups()
      groups.value = Array.isArray(res) ? res : (res.groups || [])
      // 加载未读数
      groups.value.forEach(g => {
        unreadMap[g.id] = getUnreadCount(g.id) || 0
      })
      return groups.value
    } catch (e) {
      console.error('加载群列表失败:', e)
      return []
    }
  }

  /** 加载消息 */
  async function loadMessages(groupId, limit = 100) {
    try {
      const res = await api.getMessages(groupId, limit)
      const messages = Array.isArray(res) ? res : (res.messages || [])
      messagesMap[groupId] = messages
      setCachedMessages(groupId, messages)
      return messages
    } catch (e) {
      console.error('加载消息失败:', e)
      // 从缓存读取
      messagesMap[groupId] = getCachedMessages(groupId)
      return messagesMap[groupId]
    }
  }

  /** 发送消息 */
  async function sendMessage(data) {
    try {
      const res = await api.sendMessage(data)
      return res
    } catch (e) {
      console.error('发送消息失败:', e)
      throw e
    }
  }

  /** 添加消息到列表 */
  function addMessage(groupId, message) {
    if (!messagesMap[groupId]) {
      messagesMap[groupId] = []
    }
    // 去重
    const exists = messagesMap[groupId].some(m => m.id === message.id)
    if (!exists) {
      messagesMap[groupId].push(message)
      setCachedMessages(groupId, messagesMap[groupId])
    }
  }

  /** 撤回消息 */
  function handleRecall(messageId) {
    for (const gid in messagesMap) {
      const idx = messagesMap[gid].findIndex(m => m.id === messageId)
      if (idx > -1) {
        messagesMap[gid][idx].recalled = true
        messagesMap[gid][idx].content = '你撤回了一条消息'
        break
      }
    }
  }

  /** 处理表情反应 */
  function handleReaction(messageId, emoji, userId) {
    for (const gid in messagesMap) {
      const msg = messagesMap[gid].find(m => m.id === messageId)
      if (msg) {
        if (!msg.reactions) msg.reactions = {}
        if (!msg.reactions[emoji]) msg.reactions[emoji] = []
        if (!msg.reactions[emoji].includes(userId)) {
          msg.reactions[emoji].push(userId)
        }
        break
      }
    }
  }

  /** 增加未读 */
  function incrementUnread(groupId) {
    if (groupId === currentGroupId.value) return
    unreadMap[groupId] = (unreadMap[groupId] || 0) + 1
    setUnreadCount(groupId, unreadMap[groupId])
  }

  /** 清除未读 */
  function clearUnread(groupId) {
    unreadMap[groupId] = 0
    clearUnreadCount(groupId)
  }

  /** 设置正在输入 */
  function setTyping(groupId, name) {
    if (typingMap[groupId]?.timer) {
      clearTimeout(typingMap[groupId].timer)
    }
    typingMap[groupId] = {
      name,
      timer: setTimeout(() => {
        delete typingMap[groupId]
      }, 3000)
    }
  }

  /** 撤回消息 API */
  async function recallMsg(messageId) {
    try {
      await api.recallMessage(messageId)
      handleRecall(messageId)
    } catch (e) {
      throw e
    }
  }

  /** 转发消息 */
  async function forwardMsg(messageId, targetGroupId) {
    return api.forwardMessage(messageId, targetGroupId)
  }

  /** 表情反应 */
  async function reactMsg(messageId, emoji) {
    return api.addReaction(messageId, emoji)
  }

  /** 置顶消息 */
  async function pinMsg(messageId) {
    return api.pinMessage(messageId)
  }

  /** 创建群 */
  async function createGroup(data) {
    const res = await api.createGroup(data)
    await loadGroups()
    return res
  }

  return {
    groups,
    currentGroupId,
    messagesMap,
    unreadMap,
    typingMap,
    loadGroups,
    loadMessages,
    sendMessage,
    addMessage,
    handleRecall,
    handleReaction,
    incrementUnread,
    clearUnread,
    setTyping,
    recallMsg,
    forwardMsg,
    reactMsg,
    pinMsg,
    createGroup
  }
})
