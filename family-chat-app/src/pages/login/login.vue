<template>
  <view class="login-page">
    <!-- 状态栏占位 -->
    <view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>

    <!-- Logo 区域 -->
    <view class="logo-section fade-in">
      <view class="logo-icon">👨‍👩‍👧‍👦</view>
      <text class="logo-title">家庭聊天</text>
      <text class="logo-subtitle">连接家人，温暖每一天</text>
    </view>

    <!-- 表单区域 -->
    <view class="form-section">
      <!-- Tab 切换 -->
      <view class="tab-bar">
        <view
          class="tab-item"
          :class="{ active: currentTab === 'login' }"
          @tap="currentTab = 'login'"
        >
          <text>登录</text>
        </view>
        <view
          class="tab-item"
          :class="{ active: currentTab === 'register' }"
          @tap="currentTab = 'register'"
        >
          <text>注册</text>
        </view>
      </view>

      <!-- 登录表单 -->
      <view v-if="currentTab === 'login'" class="form-content fade-in">
        <view class="input-group">
          <view class="input-wrapper">
            <text class="input-icon">📧</text>
            <input
              v-model="loginForm.email"
              type="text"
              placeholder="请输入邮箱"
              class="input-field"
              @confirm="handleLogin"
            />
          </view>
        </view>
        <view class="input-group">
          <view class="input-wrapper">
            <text class="input-icon">🔒</text>
            <input
              v-model="loginForm.password"
              type="password"
              :password="!showPassword"
              placeholder="请输入密码"
              class="input-field"
              @confirm="handleLogin"
            />
            <view class="eye-btn" @tap="showPassword = !showPassword">
              <text>{{ showPassword ? '👁️' : '👁️‍🗨️' }}</text>
            </view>
          </view>
        </view>

        <view class="btn-primary" :class="{ disabled: loginLoading }" @tap="handleLogin">
          <text v-if="loginLoading" class="btn-loading">⏳</text>
          <text>{{ loginLoading ? '登录中...' : '登 录' }}</text>
        </view>

        <!-- 微信登录 -->
        <!-- #ifdef MP-WEIXIN -->
        <view class="divider">
          <view class="divider-line"></view>
          <text class="divider-text">其他登录方式</text>
          <view class="divider-line"></view>
        </view>
        <view class="wx-login-btn" @tap="handleWxLogin">
          <text class="wx-icon">💬</text>
          <text>微信一键登录</text>
        </view>
        <!-- #endif -->
      </view>

      <!-- 注册表单 -->
      <view v-if="currentTab === 'register'" class="form-content fade-in">
        <view class="input-group">
          <view class="input-wrapper">
            <text class="input-icon">📧</text>
            <input
              v-model="registerForm.email"
              type="text"
              placeholder="请输入邮箱"
              class="input-field"
            />
          </view>
        </view>
        <view class="input-group">
          <view class="input-wrapper">
            <text class="input-icon">👤</text>
            <input
              v-model="registerForm.username"
              type="text"
              placeholder="请输入用户名"
              class="input-field"
            />
          </view>
        </view>
        <view class="input-group">
          <view class="input-wrapper">
            <text class="input-icon">😊</text>
            <input
              v-model="registerForm.nickname"
              type="text"
              placeholder="请输入昵称"
              class="input-field"
            />
          </view>
        </view>
        <view class="input-group">
          <view class="input-wrapper">
            <text class="input-icon">🔒</text>
            <input
              v-model="registerForm.password"
              type="password"
              :password="!showPassword"
              placeholder="请输入密码（至少6位）"
              class="input-field"
            />
          </view>
        </view>
        <view class="input-group">
          <view class="input-wrapper">
            <text class="input-icon">👨‍👩‍👧</text>
            <input
              v-model="registerForm.role_in_family"
              type="text"
              placeholder="家庭角色（如：爸爸/妈妈/孩子）"
              class="input-field"
            />
          </view>
        </view>

        <view class="btn-primary" :class="{ disabled: registerLoading }" @tap="handleRegister">
          <text v-if="registerLoading" class="btn-loading">⏳</text>
          <text>{{ registerLoading ? '注册中...' : '注 册' }}</text>
        </view>
      </view>
    </view>

    <!-- 底部 -->
    <view class="footer">
      <text class="footer-text">登录即表示同意</text>
      <text class="footer-link">《用户协议》</text>
      <text class="footer-text">和</text>
      <text class="footer-link">《隐私政策》</text>
      <view class="server-config-link" @tap="showServerConfig">
        <text>服务器：{{ serverUrlLabel }}</text>
      </view>
    </view>

    <view v-if="showServerModal" class="modal-mask" @tap="showServerModal = false">
      <view class="modal-box" @tap.stop>
        <text class="modal-title">服务器地址</text>
        <text class="modal-desc">测试阿里云时填写 HTTPS 域名或公网 IP，例如 https://chat.example.com</text>
        <input v-model="serverForm.url" class="modal-input" placeholder="https://你的域名" />
        <view class="modal-actions">
          <view class="modal-btn cancel" @tap="resetServerUrl"><text>恢复默认</text></view>
          <view class="modal-btn confirm" @tap="saveServerUrlForm"><text>保存</text></view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useUserStore } from '../../stores/user'
import { clearServerUrl, getDisplayServerUrl, isLocalServerUrl, saveServerUrl } from '../../utils/server-config'

const userStore = useUserStore()

const statusBarHeight = ref(44)
const currentTab = ref('login')
const showPassword = ref(false)
const loginLoading = ref(false)
const registerLoading = ref(false)
const showServerModal = ref(false)
const serverUrlLabel = ref('默认')
const serverForm = reactive({ url: '' })

const loginForm = reactive({
  email: '',
  password: ''
})

const registerForm = reactive({
  email: '',
  username: '',
  nickname: '',
  password: '',
  role_in_family: ''
})

onLoad(() => {
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  refreshServerUrlLabel()
  // 已登录则跳转
  if (userStore.isLoggedIn) {
    uni.switchTab({ url: '/pages/index/index' })
  }
})

function refreshServerUrlLabel() {
  const url = getDisplayServerUrl()
  serverForm.url = url
  serverUrlLabel.value = url || 'H5 同域 / APP 默认本机'
}

function showServerConfig() {
  refreshServerUrlLabel()
  showServerModal.value = true
}

function saveServerUrlForm() {
  const url = saveServerUrl(serverForm.url)
  showServerModal.value = false
  refreshServerUrlLabel()
  uni.showToast({ title: url ? '服务器已保存' : '已使用默认地址', icon: 'success' })
  if (url && isLocalServerUrl(url)) {
    uni.showToast({ title: '模拟器测试阿里云请使用公网地址', icon: 'none', duration: 2500 })
  }
}

function resetServerUrl() {
  clearServerUrl()
  showServerModal.value = false
  refreshServerUrlLabel()
  uni.showToast({ title: '已恢复默认', icon: 'success' })
}

async function handleLogin() {
  if (loginLoading.value) return
  if (!loginForm.email.trim()) {
    uni.showToast({ title: '请输入邮箱', icon: 'none' })
    return
  }
  if (!loginForm.password) {
    uni.showToast({ title: '请输入密码', icon: 'none' })
    return
  }
  loginLoading.value = true
  try {
    await userStore.login(loginForm.email.trim(), loginForm.password)
    uni.showToast({ title: '登录成功', icon: 'success' })
    setTimeout(() => {
      uni.switchTab({ url: '/pages/index/index' })
    }, 500)
  } catch (e) {
    console.error('登录失败:', e)
  } finally {
    loginLoading.value = false
  }
}

async function handleRegister() {
  if (registerLoading.value) return
  const { email, username, nickname, password, role_in_family } = registerForm
  if (!email.trim()) return uni.showToast({ title: '请输入邮箱', icon: 'none' })
  if (!username.trim()) return uni.showToast({ title: '请输入用户名', icon: 'none' })
  if (!nickname.trim()) return uni.showToast({ title: '请输入昵称', icon: 'none' })
  if (password.length < 6) return uni.showToast({ title: '密码至少6位', icon: 'none' })

  registerLoading.value = true
  try {
    await userStore.register({
      email: email.trim(),
      username: username.trim(),
      nickname: nickname.trim(),
      password,
      role_in_family: role_in_family.trim() || '成员'
    })
    uni.showToast({ title: '注册成功', icon: 'success' })
    setTimeout(() => {
      uni.switchTab({ url: '/pages/index/index' })
    }, 500)
  } catch (e) {
    console.error('注册失败:', e)
  } finally {
    registerLoading.value = false
  }
}

function handleWxLogin() {
  // #ifdef MP-WEIXIN
  uni.login({
    provider: 'weixin',
    success: async (loginRes) => {
      try {
        await userStore.wxLogin(loginRes.code)
        uni.showToast({ title: '登录成功', icon: 'success' })
        setTimeout(() => {
          uni.switchTab({ url: '/pages/index/index' })
        }, 500)
      } catch (e) {
        console.error('微信登录失败:', e)
      }
    },
    fail: (err) => {
      uni.showToast({ title: '微信登录失败', icon: 'none' })
      console.error('wx login fail:', err)
    }
  })
  // #endif
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #07C160 0%, #06AD56 40%, var(--bg-color) 100%);
  display: flex;
  flex-direction: column;
}

.status-bar {
  width: 100%;
}

.logo-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60rpx 0 80rpx;
}

.logo-icon {
  font-size: 120rpx;
  margin-bottom: 20rpx;
}

.logo-title {
  font-size: 52rpx;
  font-weight: bold;
  color: #ffffff;
  margin-bottom: 12rpx;
}

.logo-subtitle {
  font-size: $font-sm;
  color: rgba(255, 255, 255, 0.8);
}

.form-section {
  flex: 1;
  background: var(--card-bg);
  margin: 0 30rpx;
  border-radius: $radius-lg $radius-lg 0 0;
  padding: 0 40rpx;
  box-shadow: $shadow-lg;
}

.tab-bar {
  display: flex;
  justify-content: center;
  padding: 40rpx 0 30rpx;
  gap: 60rpx;
}

.tab-item {
  font-size: $font-lg;
  color: var(--text-secondary);
  padding-bottom: 16rpx;
  position: relative;
  transition: all 0.3s;

  &.active {
    color: $primary-color;
    font-weight: bold;

    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 48rpx;
      height: 6rpx;
      background: $primary-color;
      border-radius: 3rpx;
    }
  }
}

.form-content {
  padding-top: 10rpx;
}

.input-group {
  margin-bottom: 28rpx;
}

.input-wrapper {
  display: flex;
  align-items: center;
  background: var(--bg-color);
  border-radius: $radius-base;
  padding: 0 24rpx;
  height: 96rpx;
  border: 2rpx solid transparent;
  transition: border-color 0.3s;

  &:focus-within {
    border-color: $primary-color;
  }
}

.input-icon {
  font-size: 36rpx;
  margin-right: 16rpx;
  flex-shrink: 0;
}

.input-field {
  flex: 1;
  height: 96rpx;
  font-size: $font-base;
  color: var(--text-primary);
  background: transparent;
}

.eye-btn {
  padding: 10rpx;
  flex-shrink: 0;
  font-size: 32rpx;
}

.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 96rpx;
  background: $primary-color;
  border-radius: $radius-base;
  color: #ffffff;
  font-size: $font-lg;
  font-weight: bold;
  margin-top: 40rpx;
  transition: opacity 0.3s;

  &:active {
    opacity: 0.8;
  }

  &.disabled {
    opacity: 0.6;
    pointer-events: none;
  }
}

.btn-loading {
  margin-right: 12rpx;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.divider {
  display: flex;
  align-items: center;
  margin: 48rpx 0 36rpx;
}

.divider-line {
  flex: 1;
  height: 1rpx;
  background: var(--border-color);
}

.divider-text {
  padding: 0 24rpx;
  font-size: $font-sm;
  color: var(--text-secondary);
}

.wx-login-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 96rpx;
  border: 2rpx solid $primary-color;
  border-radius: $radius-base;
  color: $primary-color;
  font-size: $font-base;
  gap: 12rpx;

  &:active {
    background: rgba(7, 193, 96, 0.05);
  }
}

.wx-icon {
  font-size: 40rpx;
}

.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx 0;
  flex-wrap: wrap;
}

.server-config-link {
  width: 100%;
  text-align: center;
  margin-top: 16rpx;
  font-size: $font-xs;
  color: $primary-color;
}

.footer-text {
  font-size: $font-xs;
  color: var(--text-secondary);
}

.footer-link {
  font-size: $font-xs;
  color: $primary-color;
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  width: 640rpx;
  background: var(--card-bg);
  border-radius: $radius-lg;
  padding: 40rpx;
}

.modal-title {
  display: block;
  text-align: center;
  font-size: $font-lg;
  font-weight: bold;
  color: var(--text-primary);
  margin-bottom: 16rpx;
}

.modal-desc {
  display: block;
  font-size: $font-sm;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 24rpx;
}

.modal-input {
  height: 88rpx;
  background: var(--bg-color);
  border-radius: $radius-base;
  padding: 0 24rpx;
  font-size: $font-base;
  color: var(--text-primary);
}

.modal-actions {
  display: flex;
  gap: 24rpx;
  margin-top: 28rpx;
}

.modal-btn {
  flex: 1;
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $radius-base;
  font-size: $font-base;

  &.cancel { background: var(--bg-color); color: var(--text-secondary); }
  &.confirm { background: $primary-color; color: #fff; }
}
</style>
