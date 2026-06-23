/**
 * 个人中心页 v2.0
 */
const app = getApp();

Page({
  data: {
    user: null,
  },

  onShow() {
    this.setData({ user: app.globalData.user });
  },

  goLogin() {
    wx.navigateTo({ url: '/pages/login/login' });
  },

  goMyAgent() {
    wx.showToast({ title: '数字人页面开发中', icon: 'none' });
  },

  goMoments() {
    wx.showToast({ title: '朋友圈开发中', icon: 'none' });
  },

  goFavorites() {
    wx.showToast({ title: '收藏页面开发中', icon: 'none' });
  },

  goInvite() {
    // 获取用户所在的第一个群的邀请码
    app.request({ url: '/api/groups' }).then(groups => {
      if (groups.length === 0) {
        wx.showToast({ title: '请先创建家庭群', icon: 'none' });
        return;
      }
      const groupId = groups[0].id;
      app.request({
        url: `/api/groups/${groupId}/invite-code`,
        method: 'POST',
      }).then(res => {
        wx.showModal({
          title: '邀请家人',
          content: `邀请码: ${res.code}\n\n分享给家人，让他们输入此码加入`,
          confirmText: '复制',
          success: (modalRes) => {
            if (modalRes.confirm) {
              wx.setClipboardData({ data: res.code });
            }
          },
        });
      });
    });
  },

  goSettings() {
    wx.showActionSheet({
      itemList: ['退出登录'],
      success: (res) => {
        if (res.tapIndex === 0) {
          app.globalData.token = '';
          app.globalData.user = null;
          wx.removeStorageSync('token');
          wx.removeStorageSync('user');
          this.setData({ user: null });
          wx.showToast({ title: '已退出', icon: 'success' });
        }
      },
    });
  },
});
