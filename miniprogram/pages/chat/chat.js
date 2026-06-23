/**
 * 聊天室页
 */
const app = getApp();
const { formatTime } = require('../../utils/util');
const ws = require('../../utils/ws');

Page({
  data: {
    groupId: '',
    groupName: '',
    messages: [],
    inputText: '',
    scrollToId: '',
    typingAgent: '',
    myId: '',
  },

  onLoad(options) {
    const groupId = options.id || 'family_default';
    const groupName = decodeURIComponent(options.name || '家庭群');
    this.setData({
      groupId,
      groupName,
      myId: app.globalData.user?.id || '',
    });
    wx.setNavigationBarTitle({ title: groupName });
    this.loadMessages();
    this.setupWsListeners();
  },

  onUnload() {
    // 清理 WS 监听
    ws.off('message', this._onMessage);
    ws.off('typing', this._onTyping);
  },

  loadMessages() {
    app.request({
      url: `/api/messages/${this.data.groupId}`,
      data: { limit: 50 },
    }).then(messages => {
      const list = messages.map(m => ({
        ...m,
        isMine: m.sender_id === this.data.myId,
        timeStr: formatTime(m.created_at),
      }));
      this.setData({ messages: list });
      this.scrollToBottom();
    }).catch(err => {
      console.error('加载消息失败:', err);
    });
  },

  setupWsListeners() {
    this._onMessage = (data) => {
      if (data.group_id !== this.data.groupId) return;
      const msg = {
        ...data,
        isMine: data.sender_id === this.data.myId,
        timeStr: formatTime(data.created_at),
      };
      this.setData({
        messages: [...this.data.messages, msg],
        typingAgent: '',
      });
      this.scrollToBottom();
    };

    this._onTyping = (data) => {
      if (data.group_id !== this.data.groupId) return;
      if (data.user_id === this.data.myId) return;
      this.setData({ typingAgent: data.user_name || '对方' });
      clearTimeout(this._typingTimer);
      this._typingTimer = setTimeout(() => {
        this.setData({ typingAgent: '' });
      }, 3000);
    };

    ws.on('message', this._onMessage);
    ws.on('typing', this._onTyping);
  },

  sendMessage() {
    const content = this.data.inputText.trim();
    if (!content) return;

    // 先本地显示
    const tempMsg = {
      id: 'temp_' + Date.now(),
      group_id: this.data.groupId,
      sender_id: this.data.myId,
      sender_name: app.globalData.user?.nickname || '我',
      sender_avatar: app.globalData.user?.avatar || '😀',
      content,
      msg_type: 'text',
      isMine: true,
      timeStr: formatTime(Date.now() / 1000),
      reactions: [],
      created_at: Date.now() / 1000,
    };
    this.setData({
      messages: [...this.data.messages, tempMsg],
      inputText: '',
    });
    this.scrollToBottom();

    // 发送到服务器
    app.request({
      url: '/api/messages',
      method: 'POST',
      data: {
        group_id: this.data.groupId,
        content,
        msg_type: 'text',
      },
    }).then(res => {
      // 替换临时消息为真实消息
      const messages = this.data.messages.map(m => {
        if (m.id === tempMsg.id) {
          return { ...m, id: res.id, created_at: res.created_at };
        }
        return m;
      });
      this.setData({ messages });
    }).catch(err => {
      wx.showToast({ title: '发送失败', icon: 'none' });
      console.error('发送失败:', err);
    });
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value });
    // 发送 typing 事件
    ws.send({
      type: 'typing',
      group_id: this.data.groupId,
      name: app.globalData.user?.nickname || '我',
    });
  },

  scrollToBottom() {
    const msgs = this.data.messages;
    if (msgs.length > 0) {
      setTimeout(() => {
        this.setData({ scrollToId: `msg-${msgs[msgs.length - 1].id}` });
      }, 100);
    }
  },

  chooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      success: (res) => {
        const tempPath = res.tempFiles[0].tempFilePath;
        app.uploadFile(tempPath, 'image').then(uploadRes => {
          app.request({
            url: '/api/messages',
            method: 'POST',
            data: {
              group_id: this.data.groupId,
              content: uploadRes.url,
              msg_type: 'image',
              media_url: uploadRes.url,
            },
          });
        }).catch(() => {
          wx.showToast({ title: '上传失败', icon: 'none' });
        });
      },
    });
  },

  previewImage(e) {
    const url = app.globalData.baseUrl + e.currentTarget.dataset.url;
    wx.previewImage({ urls: [url] });
  },

  onLongPress(e) {
    const { id, sender } = e.currentTarget.dataset;
    const actions = ['复制', '回复'];
    if (sender === this.data.myId) {
      actions.push('撤回');
    }
    wx.showActionSheet({
      itemList: actions,
      success: (res) => {
        if (res.tapIndex === 0) {
          // 复制
          const msg = this.data.messages.find(m => m.id === id);
          if (msg) {
            wx.setClipboardData({ data: msg.content });
          }
        } else if (res.tapIndex === 1) {
          // 回复 (TODO: 实现回复 UI)
          wx.showToast({ title: '回复功能开发中', icon: 'none' });
        } else if (res.tapIndex === 2) {
          // 撤回
          app.request({
            url: '/api/messages/recall',
            method: 'POST',
            data: { message_id: id },
          }).then(() => {
            this.loadMessages();
          });
        }
      },
    });
  },

  openRedEnvelope(e) {
    wx.showToast({ title: '红包功能开发中', icon: 'none' });
  },

  playVoice(e) {
    wx.showToast({ title: '语音播放开发中', icon: 'none' });
  },

  toggleEmoji() {
    wx.showToast({ title: '表情面板开发中', icon: 'none' });
  },
});
