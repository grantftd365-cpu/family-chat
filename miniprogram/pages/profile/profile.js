/**
 * 个人中心页
 */
const app = getApp();

Page({
  data: {
    user: null,
  },

  onShow() {
    this.setData({ user: app.globalData.user });
  },

  doLogin() {
    app.wxLogin().then(user => {
      this.setData({ user });
    }).catch(err => {
      wx.showToast({ title: err.message || '登录失败', icon: 'none' });
    });
  },

  goMyAgent() {
    wx.showToast({ title: '数字人页面开发中', icon: 'none' });
  },

  goFavorites() {
    wx.showToast({ title: '收藏页面开发中', icon: 'none' });
  },

  goMoments() {
    wx.showToast({ title: '朋友圈开发中', icon: 'none' });
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
