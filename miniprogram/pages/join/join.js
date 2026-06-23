/**
 * 加入家庭页 - 邀请码输入
 */
const app = getApp();

Page({
  data: {
    codeChars: ['', '', '', '', '', ''],
    codeFocus: 0,
    codeStr: '',
    groupInfo: null,
    loading: false,
  },

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

    this.setData({ codeChars: chars, codeStr, codeFocus: nextFocus });

    // 6位输入完自动检查
    if (codeStr.length === 6) {
      this._checkCode(codeStr);
    } else {
      this.setData({ groupInfo: null });
    }
  },

  _checkCode(code) {
    app.request({
      url: '/api/family/check-code',
      data: { code },
    }).then(info => {
      this.setData({ groupInfo: info });
    }).catch(() => {
      this.setData({ groupInfo: null });
    });
  },

  onJoin() {
    const code = this.data.codeStr;
    if (code.length !== 6) return;

    this.setData({ loading: true });
    app.request({
      url: '/api/family/join',
      method: 'POST',
      params: { code },
    }).then(res => {
      this.setData({ loading: false });
      if (res.already_joined) {
        wx.showToast({ title: '你已在该家庭中', icon: 'none' });
      } else {
        wx.showToast({ title: '加入成功！', icon: 'success' });
      }
      setTimeout(() => {
        wx.switchTab({ url: '/pages/index/index' });
      }, 1200);
    }).catch(err => {
      this.setData({ loading: false });
      wx.showToast({ title: err.message || '邀请码无效', icon: 'none' });
    });
  },
});
