/**
 * 聊天列表页
 */
const app = getApp();
const { formatTime, formatLastMessage } = require('../../utils/util');
const ws = require('../../utils/ws');

Page({
  data: {
    isLoggedIn: false,
    loading: true,
    groups: [],
  },

  onLoad() {
    this.checkLogin();
  },

  onShow() {
    if (this.data.isLoggedIn) {
      this.loadGroups();
      this.connectWs();
    }
  },

  onPullDownRefresh() {
    this.loadGroups().then(() => wx.stopPullDownRefresh());
  },

  checkLogin() {
    const token = app.globalData.token;
    if (token) {
      this.setData({ isLoggedIn: true, loading: false });
      this.loadGroups();
    } else {
      // 尝试自动登录
      app.wxLogin().then(() => {
        this.setData({ isLoggedIn: true, loading: false });
        this.loadGroups();
      }).catch(() => {
        this.setData({ isLoggedIn: false, loading: false });
      });
    }
  },

  doLogin() {
    app.wxLogin().then(() => {
      this.setData({ isLoggedIn: true });
      this.loadGroups();
      this.connectWs();
    }).catch((err) => {
      wx.showToast({ title: err.message || '登录失败', icon: 'none' });
    });
  },

  loadGroups() {
    return app.request({ url: '/api/groups' }).then(groups => {
      const list = groups.map(g => ({
        ...g,
        timeStr: formatTime(g.last_time),
        last_message: formatLastMessage(g.last_message, g.last_type),
      }));
      this.setData({ groups: list });
    }).catch(err => {
      console.error('加载群组失败:', err);
    });
  },

  connectWs() {
    ws.connect(app.globalData.token);
    ws.on('message', (data) => {
      // 收到新消息，刷新列表
      this.loadGroups();
    });
  },

  goChat(e) {
    const { id, name } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/chat/chat?id=${id}&name=${encodeURIComponent(name)}`,
    });
  },

  goSearch() {
    wx.showToast({ title: '搜索功能开发中', icon: 'none' });
  },
});
