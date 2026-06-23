/**
 * 通讯录页
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
    // 加载 Agent
    app.request({ url: '/api/agents' }).then(agents => {
      this.setData({ agents });
    }).catch(() => {});

    // 加载好友
    app.request({ url: '/api/friends' }).then(friends => {
      this.setData({ friends });
    }).catch(() => {});

    // 好友请求数
    app.request({ url: '/api/friends/requests' }).then(reqs => {
      this.setData({ pendingRequests: reqs.length });
    }).catch(() => {});
  },

  goSearch() {
    wx.showToast({ title: '搜索功能开发中', icon: 'none' });
  },

  goFriendRequests() {
    wx.showToast({ title: '好友请求页面开发中', icon: 'none' });
  },

  goAgent(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/chat/chat?id=family_default&name=${encodeURIComponent('家庭群')}` });
  },

  goFriend(e) {
    const id = e.currentTarget.dataset.id;
    wx.showToast({ title: '私聊功能开发中', icon: 'none' });
  },
});
