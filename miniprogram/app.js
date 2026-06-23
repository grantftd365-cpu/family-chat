/**
 * FamilyChat 小程序 - 入口
 */

// 服务器地址配置（发布时改为正式地址）
const BASE_URL = 'https://your-domain.com';  // TODO: 改为正式服务器地址
// 本地开发时可临时改为:
// const BASE_URL = 'http://localhost:8000';

App({
  globalData: {
    baseUrl: BASE_URL,
    token: '',
    user: null,
    wsConnected: false,
  },

  onLaunch() {
    // 从本地缓存恢复登录态
    const token = wx.getStorageSync('token');
    const user = wx.getStorageSync('user');
    if (token && user) {
      this.globalData.token = token;
      this.globalData.user = user;
    }
  },

  /**
   * 微信登录
   */
  wxLogin() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (loginRes) => {
          if (!loginRes.code) {
            reject(new Error('wx.login 失败'));
            return;
          }
          wx.showLoading({ title: '登录中...', mask: true });
          wx.request({
            url: `${this.globalData.baseUrl}/api/wx-login`,
            method: 'POST',
            data: { code: loginRes.code },
            success: (res) => {
              wx.hideLoading();
              if (res.statusCode === 200) {
                const { token, user } = res.data;
                this.globalData.token = token;
                this.globalData.user = user;
                wx.setStorageSync('token', token);
                wx.setStorageSync('user', user);
                resolve(user);
              } else {
                const msg = res.data?.detail || '登录失败';
                wx.showToast({ title: msg, icon: 'none' });
                reject(new Error(msg));
              }
            },
            fail: (err) => {
              wx.hideLoading();
              wx.showToast({ title: '网络错误，请检查服务器地址', icon: 'none' });
              reject(err);
            },
          });
        },
        fail: (err) => {
          wx.showToast({ title: '微信登录失败', icon: 'none' });
          reject(err);
        },
      });
    });
  },

  /**
   * 通用请求封装
   */
  request(options) {
    return new Promise((resolve, reject) => {
      const { url, method = 'GET', data, header = {} } = options;
      if (this.globalData.token) {
        header['Authorization'] = `Bearer ${this.globalData.token}`;
      }
      wx.request({
        url: `${this.globalData.baseUrl}${url}`,
        method,
        data,
        header,
        success: (res) => {
          if (res.statusCode === 401) {
            // Token 过期，重新登录
            this.globalData.token = '';
            this.globalData.user = null;
            wx.removeStorageSync('token');
            wx.removeStorageSync('user');
            wx.reLaunch({ url: '/pages/profile/profile' });
            reject(new Error('登录过期'));
          } else if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(res.data);
          } else {
            reject(new Error(res.data.detail || '请求失败'));
          }
        },
        fail: reject,
      });
    });
  },

  /**
   * 上传文件
   */
  uploadFile(filePath, type = 'image') {
    return new Promise((resolve, reject) => {
      const url = type === 'image' ? '/api/upload/image' : '/api/upload/file';
      wx.uploadFile({
        url: `${this.globalData.baseUrl}${url}`,
        filePath,
        name: 'file',
        header: {
          Authorization: `Bearer ${this.globalData.token}`,
        },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(JSON.parse(res.data));
          } else {
            reject(new Error('上传失败'));
          }
        },
        fail: reject,
      });
    });
  },
});
