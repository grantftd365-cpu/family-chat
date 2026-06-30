<template>
  <view class="profile-page">
    <!-- 导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-content">
        <text class="nav-title">我</text>
      </view>
    </view>

    <!-- 用户信息卡片 -->
    <view class="user-card" @tap="goEditProfile">
      <view class="user-avatar">
        <image
          v-if="userInfo?.avatar_url"
          :src="api.toAbsoluteMediaUrl(userInfo.avatar_url)"
          class="avatar-img"
          mode="aspectFill"
        />
        <view v-else class="avatar-placeholder">
          <text>{{ userInfo?.avatar || (userInfo?.nickname || '?')[0] }}</text>
        </view>
      </view>
      <view class="user-info">
        <text class="user-name">{{ userInfo?.nickname || userInfo?.username || '未设置昵称' }}</text>
        <text class="user-id">微信号：{{ userInfo?.username || '未设置' }}</text>
        <text v-if="userInfo?.signature" class="user-sign">{{ userInfo.signature }}</text>
      </view>
      <text class="card-arrow">›</text>
    </view>

    <!-- 功能列表 -->
    <view class="section">
      <view class="section-item" @tap="goMoments">
        <view class="item-icon">📷</view>
        <text class="item-label">朋友圈</text>
        <text class="item-arrow">›</text>
      </view>
      <view class="section-item" @tap="goRefine">
        <view class="item-icon">🧪</view>
        <text class="item-label">炼化数字人</text>
        <text class="item-arrow">›</text>
      </view>
      <view class="section-item" @tap="goVoiceProfiles">
        <view class="item-icon">🎤</view>
        <text class="item-label">语音音色</text>
        <text class="item-arrow">›</text>
      </view>
    </view>

    <view class="section">
      <view class="section-item" @tap="goFavorites">
        <view class="item-icon">⭐</view>
        <text class="item-label">收藏</text>
        <text class="item-arrow">›</text>
      </view>
      <view class="section-item" @tap="goCards">
        <view class="item-icon">💳</view>
        <text class="item-label">卡包</text>
        <text class="item-arrow">›</text>
      </view>
      <view class="section-item" @tap="goEmoji">
        <view class="item-icon">😊</view>
        <text class="item-label">表情</text>
        <text class="item-arrow">›</text>
      </view>
    </view>

    <view class="section">
      <view class="section-item" @tap="goSettings">
        <view class="item-icon">⚙️</view>
        <text class="item-label">设置</text>
        <text class="item-arrow">›</text>
      </view>
    </view>

    <!-- Agent 炼化入口 -->
    <view class="section">
      <view class="section-item" @tap="goAgentRefine">
        <view class="item-icon">🧪</view>
        <text class="item-label">数字人炼化</text>
        <text class="item-arrow">›</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useUserStore } from '../../stores/user'
import { useThemeStore } from '../../stores/theme'
import * as api from '../../utils/api'

const userStore = useUserStore()
const themeStore = useThemeStore()

const statusBarHeight = ref(44)
const userInfo = computed(() => userStore.userInfo)

onShow(() => {
  if (!userStore.checkLogin()) return
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  themeStore.applyTheme()
  userStore.refreshUserInfo()
})

function goEditProfile() {
  uni.navigateTo({ url: '/pages/settings/settings' })
}

function goMoments() {
  uni.navigateTo({ url: '/pages/moments/moments' })
}

function goFavorites() {
  uni.navigateTo({ url: '/pages/favorites/favorites' })
}

function goRefine() {
  uni.navigateTo({ url: '/pages/refine/refine' })
}

function goVoiceProfiles() {
  uni.navigateTo({ url: '/pages/voice-profiles/voice-profiles' })
}

function goCards() {
  uni.navigateTo({ url: '/pages/favorites/favorites' })
}

function goEmoji() {
  uni.showModal({
    title: '表情',
    content: '表情面板已经集成在聊天输入框，进入任意聊天点击 😊 即可使用。',
    confirmText: '去聊天',
    success: (res) => {
      if (res.confirm) uni.switchTab({ url: '/pages/index/index' })
    }
  })
}

function goSettings() {
  uni.navigateTo({ url: '/pages/settings/settings' })
}

function goAgentRefine() {
  uni.navigateTo({ url: '/pages/refine/refine' })
}
</script>

<style lang="scss" scoped>
.profile-page {
  min-height: 100vh;
  background: var(--bg-color);
}

.nav-bar {
  background: $primary-color;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-content {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 88rpx;
  padding: 0 30rpx;
}

.nav-title {
  font-size: $font-lg;
  font-weight: bold;
  color: #ffffff;
}

.user-card {
  display: flex;
  align-items: center;
  padding: 40rpx 30rpx;
  background: var(--card-bg);
  margin-bottom: 20rpx;
  transition: background 0.2s;

  &:active {
    background: var(--bg-color);
  }
}

.user-avatar {
  margin-right: 28rpx;
  flex-shrink: 0;
}

.avatar-img {
  width: 120rpx;
  height: 120rpx;
  border-radius: $radius-base;
}

.avatar-placeholder {
  width: 120rpx;
  height: 120rpx;
  border-radius: $radius-base;
  background: $primary-color;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 52rpx;
  font-weight: bold;
  color: #ffffff;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: $font-lg;
  font-weight: bold;
  color: var(--text-primary);
  margin-bottom: 8rpx;
}

.user-id {
  font-size: $font-sm;
  color: var(--text-secondary);
  margin-bottom: 6rpx;
}

.user-sign {
  font-size: $font-sm;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-arrow {
  font-size: $font-xl;
  color: var(--text-placeholder);
  flex-shrink: 0;
}

.section {
  background: var(--card-bg);
  margin-bottom: 20rpx;
}

.section-item {
  display: flex;
  align-items: center;
  padding: 28rpx 30rpx;
  border-bottom: 1rpx solid var(--border-color);
  transition: background 0.2s;

  &:last-child {
    border-bottom: none;
  }

  &:active {
    background: var(--bg-color);
  }
}

.item-icon {
  font-size: 40rpx;
  margin-right: 24rpx;
}

.item-label {
  flex: 1;
  font-size: $font-base;
  color: var(--text-primary);
}

.item-arrow {
  font-size: $font-lg;
  color: var(--text-placeholder);
}
</style>
