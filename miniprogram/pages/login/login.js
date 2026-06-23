/**
 * 登录页 - 三步引导流程
 * 1. 微信登录（获取 openid）
 * 2. 设置头像昵称（用户授权）
 * 3. 加入/创建家庭群
 */
const app = getApp();

Page({
  data: {
    step: 1,
    nickname: '',
    avatarUrl: '',
    avatarTempPath: '',
    codeChars: ['', '', '', '', '', ''],
    codeFocus: 0,
    codeStr: '',
    joining: false,
  },

  // ========== 步骤1: 微信登录 ==========

  onWxLogin() {
    wx.showLoading({ title: '登录中...', mask: true });
    app.wxLogin().then(user => {
      wx.hideLoading();
      if (user.is_new) {
        // 新用户 → 步骤2 设置资料
        this.setData({ step: 2 });
      } else {
        // 老用户 → 直接进入主页
        this._goMain();
      }
    }).catch(err => {
      wx.hideLoading();
      wx.showToast({ title: err.message || '登录失败', icon: 'none' });
    });
  },

  // ========== 步骤2: 设置资料 ==========

  onChooseAvatar(e) {
    const tempPath = e.detail.avatarUrl;
    this.setData({ avatarTempPath: tempPath, avatarUrl: tempPath });
  },

  onNicknameInput(e) {
    this.setData({ nickname: e.detail.value });
  },

  onConfirmProfile() {
    const { nickname, avatarTempPath } = this.data;
    if (!nickname.trim()) {
      wx.showToast({ title: '请输入昵称', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '保存中...', mask: true });

    // 如果有头像，先上传
    const saveProfile = avatarTempPath
      ? app.uploadFile(avatarTempPath, 'image').then(res => app.updateProfile(nickname, res.url))
      : app.updateProfile(nickname, '');

    saveProfile.then(() => {
      wx.hideLoading();
      // 更新本地缓存
      const user = app.globalData.user;
      if (user) {
        user.nickname = nickname;
        wx.setStorageSync('user', user);
      }
      this.setData({ step: 3 });
    }).catch(() => {
      wx.hideLoading();
      // 即使保存失败也继续
      this.setData({ step: 3 });
    });
  },

  // ========== 步骤3: 加入/创建家庭 ==========

  onCodeInput(e) {
    const index = e.currentTarget.dataset.index;
    const value = e.detail.value.toUpperCase();
    const chars = [...this.data.codeChars];
    chars[index] = value;

    const codeStr = chars.join('');
    let nextFocus = this.data.codeFocus;
    if (value && index < 5) {
      nextFocus = index + 1;
    }

    this.setData({
      codeChars: chars,
      codeStr,
      codeFocus: nextFocus,
    });
  },

  onJoinFamily() {
    const code = this.data.codeStr;
    if (code.length !== 6) return;

    this.setData({ joining: true });
    app.request({
      url: '/api/family/join',
      method: 'POST',
      params: { code },
    }).then(res => {
      this.setData({ joining: false });
      if (res.already_joined) {
        wx.showToast({ title: '你已在该家庭中', icon: 'none' });
      } else {
        wx.showToast({ title: '加入成功！', icon: 'success' });
      }
      setTimeout(() => this._goMain(), 1000);
    }).catch(err => {
      this.setData({ joining: false });
      wx.showToast({ title: err.message || '邀请码无效', icon: 'none' });
    });
  },

  onCreateFamily() {
    wx.showModal({
      title: '创建家庭',
      editable: true,
      placeholderText: '给家庭起个名字，如：温馨小家',
      success: (res) => {
        if (res.confirm && res.content) {
          wx.showLoading({ title: '创建中...', mask: true });
          app.request({
            url: '/api/groups',
            method: 'POST',
            data: { name: res.content.trim() },
          }).then(group => {
            wx.hideLoading();
            wx.showToast({ title: '创建成功！', icon: 'success' });
            setTimeout(() => this._goMain(), 1000);
          }).catch(err => {
            wx.hideLoading();
            wx.showToast({ title: err.message || '创建失败', icon: 'none' });
          });
        }
      },
    });
  },

  // ========== 工具 ==========

  _goMain() {
    wx.switchTab({ url: '/pages/index/index' });
  },
});
