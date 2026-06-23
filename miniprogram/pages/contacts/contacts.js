/**
 * 通讯录页 v2.0
 */
const app = getApp();

Page({
  data: {
    agents: [],
    friends: [],
    pendingRequests: 0,
  },

  onShow() {
    this.loadData();
  },

  loadData() {
    app.request({ url: '/api/agents' }).then(agents => {
      this.setData({ agents });
    }).catch(() => {});

    app.request({ url: '/api/friends' }).then(friends => {
      this.setData({ friends });
    }).catch(() => {});

    app.request({ url: '/api/friends/requests' }).then(reqs => {
      this.setData({ pendingRequests: reqs.length });
    }).catch(() => {});
  },

  goSearch() {
    wx.showToast({ title: '搜索功能开发中', icon: 'none' });
  },

  goJoin() {
    wx.navigateTo({ url: '/pages/join/join' });
  },

  goFriendRequests() {
    wx.showToast({ title: '好友请求页面开发中', icon: 'none' });
  },

  goAgentChat(e) {
    const { id, name } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/chat/chat?id=family_default&name=${encodeURIComponent('家庭群')}`,
    });
  },

  goFriendChat(e) {
    wx.showToast({ title: '私聊功能开发中', icon: 'none' });
  },
});
