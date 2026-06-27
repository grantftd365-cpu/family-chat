/**
 * WebSocket 封装 - 优化版
 * 支持自动重连、心跳检测、消息队列、断线缓存
 */
import { getToken } from './storage'

/** 连接状态 */
const STATE = {
  DISCONNECTED: 0,
  CONNECTING: 1,
  CONNECTED: 2
}

class WsClient {
  constructor() {
    this.socket = null
    this.state = STATE.DISCONNECTED
    this.listeners = new Map()
    this.reconnectTimer = null
    this.heartbeatTimer = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 15
    this.reconnectDelay = 2000
    this.heartbeatInterval = 25000
    this.messageQueue = []
    this.isManualClose = false
    this._lastPong = 0
    this._connectionId = 0
  }

  /**
   * 获取 WebSocket 地址
   */
  getUrl() {
    const token = getToken()
    if (!token) return ''
    // #ifdef H5
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${location.host}/ws?token=${token}`
    // #endif
    // #ifndef H5
    // 从存储或编译时常量读取服务器地址
    let serverUrl = 'http://localhost:8000'
    try {
      const stored = uni.getStorageSync('server_url')
      if (stored) serverUrl = stored
    } catch (e) {}
    if (typeof __SERVER_URL__ !== 'undefined' && __SERVER_URL__) serverUrl = __SERVER_URL__
    // 将 http(s) 转为 ws(s)
    const wsUrl = serverUrl.replace(/^https?:\/\//, (m) => m === 'https://' ? 'wss://' : 'ws://')
    return `${wsUrl}/ws?token=${token}`
    // #endif
  }

  /**
   * 连接 WebSocket
   */
  connect() {
    if (this.state === STATE.CONNECTING || this.state === STATE.CONNECTED) {
      return
    }
    const token = getToken()
    if (!token) return

    this.isManualClose = false
    this.state = STATE.CONNECTING
    this._connectionId++

    const url = this.getUrl()
    if (!url) return

    try {
      this.socket = uni.connectSocket({
        url,
        success: () => {},
        fail: (err) => {
          console.error('WebSocket 连接失败:', err)
          this.state = STATE.DISCONNECTED
          this.scheduleReconnect()
        }
      })

      this.socket.onOpen(() => {
        console.log('WebSocket 已连接')
        this.state = STATE.CONNECTED
        this.reconnectAttempts = 0
        this._lastPong = Date.now()
        this.startHeartbeat()
        this.flushQueue()
        this.emit('connected')
      })

      this.socket.onMessage((res) => {
        try {
          const data = JSON.parse(res.data)
          this.handleMessage(data)
        } catch (e) {
          console.error('WebSocket 消息解析失败:', e)
        }
      })

      this.socket.onClose((res) => {
        console.log('WebSocket 已断开:', res.code, res.reason)
        this.state = STATE.DISCONNECTED
        this.stopHeartbeat()
        this.emit('disconnected')
        if (!this.isManualClose) {
          this.scheduleReconnect()
        }
      })

      this.socket.onError((err) => {
        console.error('WebSocket 错误:', err)
        this.state = STATE.DISCONNECTED
        this.emit('error', err)
      })
    } catch (e) {
      console.error('WebSocket 创建异常:', e)
      this.state = STATE.DISCONNECTED
      this.scheduleReconnect()
    }
  }

  /**
   * 处理收到的消息
   */
  handleMessage(data) {
    const { type } = data
    switch (type) {
      case 'message':
        this.emit('message', data.data || data)
        break
      case 'typing':
        this.emit('typing', data)
        break
      case 'recall':
        this.emit('recall', data)
        break
      case 'reaction':
        this.emit('reaction', data)
        break
      case 'reaction_v2':
        this.emit('reaction_v2', data)
        break
      case 'read':
        this.emit('read', data)
        break
      case 'sync_complete':
        this.emit('sync_complete', data)
        break
      case 'pong':
        this._lastPong = Date.now()
        break
      default:
        this.emit(type, data)
    }
  }

  /**
   * 确认收到消息（ACK）
   */
  sendAck(messageIds) {
    if (!messageIds || !messageIds.length) return
    this.send({
      type: 'ack',
      message_ids: messageIds
    })
  }

  /**
   * 标记群聊消息已读
   */
  sendRead(groupId, beforeTimestamp) {
    this.send({
      type: 'read',
      group_id: groupId,
      before: beforeTimestamp || Date.now() / 1000
    })
  }

  /**
   * 标记单条消息已读
   */
  sendReadSingle(messageId) {
    this.send({
      type: 'read_single',
      message_id: messageId
    })
  }

  /**
   * 发送表情回应
   */
  sendReaction(messageId, emoji, groupId, action = 'add') {
    this.send({
      type: 'reaction',
      message_id: messageId,
      emoji: emoji,
      group_id: groupId,
      action: action
    })
  }

  /**
   * 发送消息
   */
  send(data) {
    const msg = typeof data === 'string' ? data : JSON.stringify(data)
    if (this.state === STATE.CONNECTED && this.socket) {
      try {
        this.socket.send({ data: msg })
      } catch (e) {
        console.error('WebSocket 发送失败:', e)
        this.messageQueue.push(msg)
      }
    } else {
      this.messageQueue.push(msg)
      // 如果断开连接，尝试重连
      if (this.state === STATE.DISCONNECTED) {
        this.connect()
      }
    }
  }

  /**
   * 发送正在输入状态
   */
  sendTyping(groupId, name) {
    this.send({
      type: 'typing',
      group_id: groupId,
      name
    })
  }

  /**
   * 刷新消息队列
   */
  flushQueue() {
    const maxFlush = 50 // 防止队列过大
    let count = 0
    while (this.messageQueue.length > 0 && count < maxFlush) {
      const msg = this.messageQueue.shift()
      if (this.socket && this.state === STATE.CONNECTED) {
        try {
          this.socket.send({ data: msg })
        } catch (e) {
          this.messageQueue.unshift(msg)
          break
        }
      }
      count++
    }
  }

  /**
   * 开始心跳检测
   */
  startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.state === STATE.CONNECTED) {
        // 检查上次 pong 时间
        const now = Date.now()
        if (now - this._lastPong > this.heartbeatInterval * 2) {
          // 超时，主动断开重连
          console.log('心跳超时，重新连接')
          this.disconnect()
          this.isManualClose = false
          this.scheduleReconnect()
          return
        }
        this.send({ type: 'ping' })
      }
    }, this.heartbeatInterval)
  }

  /**
   * 停止心跳
   */
  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 安排重连
   */
  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('达到最大重连次数，停止重连')
      this.emit('reconnect_failed')
      return
    }
    if (this.reconnectTimer) return

    // 指数退避 + 抖动
    const baseDelay = this.reconnectDelay * Math.pow(1.3, this.reconnectAttempts)
    const jitter = Math.random() * 1000
    const delay = Math.min(baseDelay + jitter, 30000)

    console.log(`${Math.round(delay)}ms 后尝试第 ${this.reconnectAttempts + 1} 次重连`)
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.reconnectAttempts++
      this.connect()
    }, delay)
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.isManualClose = true
    this.stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.socket) {
      try {
        this.socket.close({})
      } catch (e) {}
      this.socket = null
    }
    this.state = STATE.DISCONNECTED
  }

  /**
   * 注册事件监听
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  /**
   * 移除事件监听
   */
  off(event, callback) {
    if (!this.listeners.has(event)) return
    if (!callback) {
      this.listeners.delete(event)
      return
    }
    const cbs = this.listeners.get(event)
    const idx = cbs.indexOf(callback)
    if (idx > -1) cbs.splice(idx, 1)
  }

  /**
   * 触发事件
   */
  emit(event, data) {
    const cbs = this.listeners.get(event)
    if (cbs) {
      cbs.forEach(cb => {
        try { cb(data) } catch (e) { console.error('事件处理错误:', event, e) }
      })
    }
  }

  /**
   * 获取连接状态
   */
  isConnected() {
    return this.state === STATE.CONNECTED
  }

  /**
   * 获取连接信息
   */
  getInfo() {
    return {
      state: this.state,
      reconnectAttempts: this.reconnectAttempts,
      queueLength: this.messageQueue.length,
      lastPong: this._lastPong,
    }
  }
}

/** 全局单例 */
const ws = new WsClient()

export default ws
export { WsClient }
