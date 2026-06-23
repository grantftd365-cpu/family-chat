/**
 * WebSocket 管理器
 */
class WsManager {
  constructor() {
    this.socket = null;
    this.listeners = {};
    this.reconnectTimer = null;
    this.reconnectCount = 0;
    this.maxReconnect = 5;
  }

  connect(token) {
    if (this.socket) return;

    const app = getApp();
    const url = `${app.globalData.baseUrl.replace('http', 'ws')}/ws?token=${token}`;

    this.socket = wx.connectSocket({ url });

    this.socket.onOpen(() => {
      console.log('[WS] 已连接');
      this.reconnectCount = 0;
      app.globalData.wsConnected = true;
      this._emit('open');
      // 心跳
      this._startHeartbeat();
    });

    this.socket.onMessage((res) => {
      try {
        const msg = JSON.parse(res.data);
        this._emit(msg.type, msg.data);
      } catch (e) {
        console.error('[WS] 解析失败:', e);
      }
    });

    this.socket.onClose(() => {
      console.log('[WS] 已断开');
      this.socket = null;
      app.globalData.wsConnected = false;
      this._stopHeartbeat();
      this._emit('close');
      this._reconnect(token);
    });

    this.socket.onError((err) => {
      console.error('[WS] 错误:', err);
    });
  }

  disconnect() {
    this._stopHeartbeat();
    clearTimeout(this.reconnectTimer);
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  send(data) {
    if (this.socket) {
      this.socket.send({ data: JSON.stringify(data) });
    }
  }

  on(event, callback) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(callback);
  }

  off(event, callback) {
    if (!this.listeners[event]) return;
    this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
  }

  _emit(event, data) {
    (this.listeners[event] || []).forEach(cb => cb(data));
  }

  _startHeartbeat() {
    this._stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping' });
    }, 30000);
  }

  _stopHeartbeat() {
    clearInterval(this.heartbeatTimer);
  }

  _reconnect(token) {
    if (this.reconnectCount >= this.maxReconnect) return;
    this.reconnectCount++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectCount), 30000);
    console.log(`[WS] ${delay}ms 后重连 (${this.reconnectCount}/${this.maxReconnect})`);
    this.reconnectTimer = setTimeout(() => {
      this.connect(token);
    }, delay);
  }
}

module.exports = new WsManager();
