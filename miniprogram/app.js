/**
 * FamilyChat 小程序 - 入口 v2.0
 * 高端家庭聊天体验
 */

// 服务器地址（发布时改为正式地址）
const BASE_URL = 'https://your-domain.com';

App({
  globalData: {
    baseUrl: BASE_URL,
    token: '',
    user: null,
    wsConnected: false,
    theme: 'light', // light | dark
    statusBarHeight: 0,
    systemInfo: null,
  },

  onLaunch() {
    // 获取系统信息
    const sys = wx.getSystemInfoSync();
    this.globalData.systemInfo = sys;
    this.globalData.statusBarHeight = sys.statusBarHeight || 20;

    // 恢复登录态
    const token = wx.getStorageSync('token');
    const user = wx.getStorageSync('user');
    if (token && user) {
      this.globalData.token = token;
      this.globalData.user = user;
    }

    // 恢复主题
    const theme = wx.getStorageSync('theme') || 'light';
    this.globalData.theme = theme;
  },

  /**
   * 微信登录（静默获取 openid）
   */
  wxLogin() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (loginRes) => {
          if (!loginRes.code) {
            reject(new Error('wx.login 失败'));
            return;
          }
          wx.request({
            url: `${this.globalData.baseUrl}/api/wx-login`,
            method: 'POST',
            data: { code: loginRes.code },
            success: (res) => {
              if (res.statusCode === 200) {
                const { token, user } = res.data;
                this.globalData.token = token;
                this.globalData.user = user;
                wx.setStorageSync('token', token);
                wx.setStorageSync('user', user);
                resolve(user);
              } else {
                reject(new Error(res.data?.detail || '登录失败'));
              }
            },
            fail: () => reject(new Error('网络错误')),
          });
        },
        fail: () => reject(new Error('wx.login 失败')),
      });
    });
  },

  /**
   * 更新用户资料（头像+昵称）
   */
  updateProfile(nickname, avatarUrl) {
    return this.request({
      url: '/api/me',
      method: 'PUT',
      data: { nickname, avatar: avatarUrl || '' },
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
            this.globalData.token = '';
            this.globalData.user = null;
            wx.removeStorageSync('token');
            wx.removeStorageSync('user');
            wx.redirectTo({ url: '/pages/login/login' });
            reject(new Error('登录过期'));
          } else if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(res.data);
          } else {
            reject(new Error(res.data?.detail || '请求失败'));
          }
        },
        fail: () => reject(new Error('网络错误')),
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
        header: { Authorization: `Bearer ${this.globalData.token}` },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(JSON.parse(res.data));
          } else {
            reject(new Error('上传失败'));
          }
        },
        fail: () => reject(new Error('上传失败')),
      });
    });
  },

  /**
   * 切换主题
   */
  setTheme(theme) {
    this.globalData.theme = theme;
    wx.setStorageSync('theme', theme);
  },
});
