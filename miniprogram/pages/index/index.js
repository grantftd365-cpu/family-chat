/**
 * 消息列表页
 */
const app = getApp();
const { formatTime, formatLastMessage } = require('../../utils/util');
const ws = require('../../utils/ws');

Page({
  data: {
    isLoggedIn: false,
    loading: true,
    refreshing: false,
    groups: [],
  },

  onLoad() {
    this.checkLogin();
  },

  onShow() {
    if (this.data.isLoggedIn) {
      this.loadGroups();
    }
  },

  checkLogin() {
    if (app.globalData.token) {
      this.setData({ isLoggedIn: true, loading: false });
      this.loadGroups();
      this.connectWs();
    } else {
      this.setData({ isLoggedIn: false, loading: false });
    }
  },

  goLogin() {
    wx.navigateTo({ url: '/pages/login/login' });
  },

  loadGroups() {
    app.request({ url: '/api/groups' }).then(groups => {
      const list = groups.map(g => ({
        ...g,
        timeStr: formatTime(g.last_time),
        last_message: formatLastMessage(g.last_message),
      }));
      this.setData({ groups: list, loading: false, refreshing: false });
    }).catch(() => {
      this.setData({ loading: false, refreshing: false });
    });
  },

  onRefresh() {
    this.setData({ refreshing: true });
    this.loadGroups();
  },

  connectWs() {
    ws.connect(app.globalData.token);
    ws.on('message', () => this.loadGroups());
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
