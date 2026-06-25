/**
 * WebSocket 封装
 * 支持自动重连、心跳检测、消息队列
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
    this.maxReconnectAttempts = 10
    this.reconnectDelay = 3000
    this.heartbeatInterval = 30000
    this.messageQueue = []
    this.isManualClose = false
  }

  /**
   * 获取 WebSocket 地址
   */
  getUrl() {
    const token = getToken()
    // #ifdef H5
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${location.host}/ws?token=${token}`
    // #endif
    // #ifndef H5
    return `ws://localhost:8000/ws?token=${token}`
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

    try {
      this.socket = uni.connectSocket({
        url: this.getUrl(),
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
      case 'pong':
        // 心跳回复，忽略
        break
      default:
        this.emit(type, data)
    }
  }

  /**
   * 发送消息
   */
  send(data) {
    const msg = typeof data === 'string' ? data : JSON.stringify(data)
    if (this.state === STATE.CONNECTED && this.socket) {
      this.socket.send({ data: msg })
    } else {
      this.messageQueue.push(msg)
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
    while (this.messageQueue.length > 0) {
      const msg = this.messageQueue.shift()
      if (this.socket && this.state === STATE.CONNECTED) {
        this.socket.send({ data: msg })
      }
    }
  }

  /**
   * 开始心跳检测
   */
  startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.state === STATE.CONNECTED) {
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

    const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts)
    console.log(`${delay}ms 后尝试第 ${this.reconnectAttempts + 1} 次重连`)
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
      this.socket.close({})
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
}

/** 全局单例 */
const ws = new WsClient()

export default ws
export { WsClient }
