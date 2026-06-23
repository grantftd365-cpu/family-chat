/**
 * 聊天室页 v2.0
 */
const app = getApp();
const { formatTime } = require('../../utils/util');
const ws = require('../../utils/ws');

Page({
  data: {
    statusBarHeight: 20,
    groupId: '',
    groupName: '',
    messages: [],
    inputText: '',
    scrollToId: '',
    typingAgent: '',
    myId: '',
    myAvatar: '😀',
    refreshing: false,
    showMore: false,
    showEmoji: false,
  },

  onLoad(options) {
    this.setData({
      groupId: options.id || 'family_default',
      groupName: decodeURIComponent(options.name || '家庭群'),
      statusBarHeight: app.globalData.statusBarHeight,
      myId: app.globalData.user?.id || '',
      myAvatar: app.globalData.user?.avatar || '😀',
    });
    wx.setNavigationBarTitle({ title: this.data.groupName });
    this.loadMessages();
    this.setupWs();
  },

  onUnload() {
    ws.off('message', this._onMsg);
    ws.off('typing', this._onTyping);
  },

  // ========== 消息加载 ==========

  loadMessages() {
    app.request({
      url: `/api/messages/${this.data.groupId}`,
      data: { limit: 50 },
    }).then(msgs => {
      const list = msgs.map(m => ({
        ...m,
        isMine: m.sender_id === this.data.myId,
        timeStr: formatTime(m.created_at),
      }));
      this.setData({ messages: list });
      this.scrollToBottom();
    }).catch(() => {});
  },

  onRefresh() {
    this.setData({ refreshing: true });
    this.loadMessages();
  },

  // ========== WebSocket ==========

  setupWs() {
    this._onMsg = (data) => {
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
      if (data.group_id !== this.data.groupId || data.user_id === this.data.myId) return;
      this.setData({ typingAgent: data.user_name || '对方' });
      clearTimeout(this._typingTimer);
      this._typingTimer = setTimeout(() => this.setData({ typingAgent: '' }), 3000);
    };

    ws.on('message', this._onMsg);
    ws.on('typing', this._onTyping);
  },

  // ========== 发送消息 ==========

  sendMessage() {
    const content = this.data.inputText.trim();
    if (!content) return;

    const tempMsg = {
      id: 'tmp_' + Date.now(),
      group_id: this.data.groupId,
      sender_id: this.data.myId,
      sender_name: app.globalData.user?.nickname || '我',
      sender_avatar: this.data.myAvatar,
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
      showMore: false,
      showEmoji: false,
    });
    this.scrollToBottom();

    app.request({
      url: '/api/messages',
      method: 'POST',
      data: { group_id: this.data.groupId, content, msg_type: 'text' },
    }).then(res => {
      const messages = this.data.messages.map(m =>
        m.id === tempMsg.id ? { ...m, id: res.id } : m
      );
      this.setData({ messages });
    }).catch(() => {
      wx.showToast({ title: '发送失败', icon: 'none' });
    });
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value });
    ws.send({ type: 'typing', group_id: this.data.groupId, name: app.globalData.user?.nickname || '我' });
  },

  // ========== 更多操作 ==========

  toggleMore() {
    this.setData({ showMore: !this.data.showMore, showEmoji: false });
  },

  toggleEmoji() {
    this.setData({ showEmoji: !this.data.showEmoji, showMore: false });
  },

  chooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      success: (res) => {
        const path = res.tempFiles[0].tempFilePath;
        wx.showLoading({ title: '上传中...' });
        app.uploadFile(path, 'image').then(uploadRes => {
          wx.hideLoading();
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
          wx.hideLoading();
          wx.showToast({ title: '上传失败', icon: 'none' });
        });
      },
    });
  },

  takePhoto() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['camera'],
      success: (res) => {
        const path = res.tempFiles[0].tempFilePath;
        wx.showLoading({ title: '上传中...' });
        app.uploadFile(path, 'image').then(uploadRes => {
          wx.hideLoading();
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
          wx.hideLoading();
          wx.showToast({ title: '上传失败', icon: 'none' });
        });
      },
    });
  },

  sendRedEnvelope() {
    wx.showToast({ title: '红包功能开发中', icon: 'none' });
  },

  inviteMember() {
    app.request({
      url: `/api/groups/${this.data.groupId}/invite-code`,
      method: 'POST',
    }).then(res => {
      wx.showModal({
        title: '邀请家人',
        content: `邀请码: ${res.code}\n\n分享给家人，让他们在 FamilyChat 中输入此码加入`,
        confirmText: '复制',
        success: (modalRes) => {
          if (modalRes.confirm) {
            wx.setClipboardData({ data: res.code });
          }
        },
      });
    }).catch(() => {
      wx.showToast({ title: '获取邀请码失败', icon: 'none' });
    });
  },

  // ========== 消息操作 ==========

  onLongPress(e) {
    const { id, sender, content } = e.currentTarget.dataset;
    const actions = ['复制'];
    if (sender === this.data.myId) actions.push('撤回');

    wx.showActionSheet({
      itemList: actions,
      success: (res) => {
        if (res.tapIndex === 0) {
          wx.setClipboardData({ data: content });
        } else if (res.tapIndex === 1 && sender === this.data.myId) {
          app.request({
            url: '/api/messages/recall',
            method: 'POST',
            data: { message_id: id },
          }).then(() => this.loadMessages());
        }
      },
    });
  },

  previewImage(e) {
    const url = e.currentTarget.dataset.url;
    wx.previewImage({ urls: [app.globalData.baseUrl + url] });
  },

  // ========== 工具 ==========

  scrollToBottom() {
    const msgs = this.data.messages;
    if (msgs.length > 0) {
      setTimeout(() => {
        this.setData({ scrollToId: `msg-${msgs[msgs.length - 1].id}` });
      }, 100);
    }
  },
});
