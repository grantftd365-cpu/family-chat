<template>
  <view class="index-page">
    <!-- 自定义导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-content">
        <text class="nav-title">消息</text>
        <view class="nav-right">
          <view class="nav-btn" @tap="goSearch">
            <text>🔍</text>
          </view>
          <view class="nav-btn" @tap="showCreateGroup = true">
            <text>➕</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 搜索栏 -->
    <view class="search-bar" @tap="goSearch">
      <view class="search-inner">
        <text class="search-icon">🔍</text>
        <text class="search-placeholder">搜索</text>
      </view>
    </view>

    <!-- 群列表 -->
    <scroll-view
      scroll-y
      class="chat-list"
      :style="{ height: scrollHeight + 'px' }"
      refresher-enabled
      :refresher-triggered="refreshing"
      @refresherrefresh="onRefresh"
    >
      <!-- 加载骨架屏 -->
      <skeleton v-if="loading" mode="list" :count="8" />

      <!-- 空状态 -->
      <empty-state
        v-else-if="groups.length === 0"
        icon="💬"
        title="暂无聊天"
        description="点击右上角创建群聊开始吧"
      />

      <view
        v-for="group in groups"
        :key="group.id"
        class="chat-item"
        @tap="goChat(group)"
        @longpress="onLongPress(group)"
      >
        <view class="avatar-wrap">
          <image
            v-if="group.avatar"
            :src="group.avatar"
            class="avatar"
            mode="aspectFill"
          />
          <view v-else class="avatar avatar-default">
            <text>{{ (group.name || '?')[0] }}</text>
          </view>
          <view v-if="unreadMap[group.id]" class="badge">
            <text>{{ unreadMap[group.id] > 99 ? '99+' : unreadMap[group.id] }}</text>
          </view>
        </view>
        <view class="chat-info">
          <view class="chat-top">
            <text class="chat-name">{{ group.name || '未命名群组' }}</text>
            <text class="chat-time">{{ formatTime(group.last_message_time || group.updated_at) }}</text>
          </view>
          <view class="chat-bottom">
            <text class="chat-preview">{{ group.last_message || group.description || '暂无消息' }}</text>
          </view>
          <view v-if="typingMap[group.id]" class="typing-indicator">
            <text class="typing-dot">●</text>
            <text class="typing-dot">●</text>
            <text class="typing-dot">●</text>
            <text class="typing-text">{{ typingMap[group.id].name }} 正在输入...</text>
          </view>
        </view>
      </view>
    </scroll-view>

    <!-- 创建群弹窗 -->
    <view v-if="showCreateGroup" class="modal-mask" @tap="showCreateGroup = false">
      <view class="modal-content" @tap.stop>
        <text class="modal-title">创建群聊</text>
        <view class="modal-input-wrap">
          <input
            v-model="newGroupName"
            placeholder="请输入群名称"
            class="modal-input"
            :maxlength="20"
          />
        </view>
        <view class="modal-input-wrap">
          <input
            v-model="newGroupDesc"
            placeholder="群描述（选填）"
            class="modal-input"
            :maxlength="100"
          />
        </view>
        <view class="modal-btns">
          <view class="modal-btn cancel" @tap="showCreateGroup = false">
            <text>取消</text>
          </view>
          <view class="modal-btn confirm" @tap="handleCreateGroup">
            <text>创建</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { onShow, onUnload } from '@dcloudio/uni-app'
import { useUserStore } from '../../stores/user'
import { useChatStore } from '../../stores/chat'
import { useThemeStore } from '../../stores/theme'
import Skeleton from '../../components/skeleton.vue'
import EmptyState from '../../components/empty-state.vue'

const userStore = useUserStore()
const chatStore = useChatStore()
const themeStore = useThemeStore()

const statusBarHeight = ref(44)
const scrollHeight = ref(600)
const refreshing = ref(false)
const loading = ref(false)
const showCreateGroup = ref(false)
const newGroupName = ref('')
const newGroupDesc = ref('')

const groups = computed(() => chatStore.groups)
const unreadMap = computed(() => chatStore.unreadMap)
const typingMap = computed(() => chatStore.typingMap)

onShow(() => {
  if (!userStore.checkLogin()) return
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  // 导航栏 + 搜索栏高度
  const navHeight = statusBarHeight.value + 44 + 50
  scrollHeight.value = sysInfo.windowHeight - navHeight - 50
  themeStore.applyTheme()
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    await chatStore.loadGroups()
  } finally {
    loading.value = false
  }
}

async function onRefresh() {
  refreshing.value = true
  await loadData()
  refreshing.value = false
}

function goChat(group) {
  chatStore.currentGroupId = group.id
  chatStore.clearUnread(group.id)
  uni.navigateTo({
    url: `/pages/chat/chat?groupId=${group.id}&name=${encodeURIComponent(group.name || '聊天')}`
  })
}

function goSearch() {
  uni.navigateTo({ url: '/pages/search/search' })
}

function onLongPress(group) {
  uni.showActionSheet({
    itemList: ['置顶聊天', '删除聊天', '群信息'],
    success: (res) => {
      if (res.tapIndex === 0) {
        uni.showToast({ title: '已置顶', icon: 'success' })
      } else if (res.tapIndex === 1) {
        uni.showModal({
          title: '提示',
          content: '确定删除该聊天？',
          success: (r) => {
            if (r.confirm) {
              uni.showToast({ title: '已删除', icon: 'success' })
            }
          }
        })
      } else if (res.tapIndex === 2) {
        uni.showToast({ title: '群信息功能开发中', icon: 'none' })
      }
    }
  })
}

async function handleCreateGroup() {
  if (!newGroupName.value.trim()) {
    uni.showToast({ title: '请输入群名称', icon: 'none' })
    return
  }
  try {
    await chatStore.createGroup({
      name: newGroupName.value.trim(),
      description: newGroupDesc.value.trim()
    })
    showCreateGroup.value = false
    newGroupName.value = ''
    newGroupDesc.value = ''
    uni.showToast({ title: '创建成功', icon: 'success' })
  } catch (e) {
    console.error('创建群失败:', e)
  }
}

function formatTime(time) {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diffMs = now - date
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffDays === 0) {
    const h = date.getHours().toString().padStart(2, '0')
    const m = date.getMinutes().toString().padStart(2, '0')
    return `${h}:${m}`
  } else if (diffDays === 1) {
    return '昨天'
  } else if (diffDays < 7) {
    const days = ['日', '一', '二', '三', '四', '五', '六']
    return `星期${days[date.getDay()]}`
  } else {
    return `${date.getMonth() + 1}/${date.getDate()}`
  }
}
</script>

<style lang="scss" scoped>
.index-page {
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
  justify-content: space-between;
  height: 88rpx;
  padding: 0 30rpx;
}

.nav-title {
  font-size: $font-lg;
  font-weight: bold;
  color: #ffffff;
}

.nav-right {
  display: flex;
  gap: 20rpx;
}

.nav-btn {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $radius-round;
  font-size: 36rpx;

  &:active {
    background: rgba(255, 255, 255, 0.2);
  }
}

.search-bar {
  padding: 16rpx 30rpx;
  background: $primary-color;
}

.search-inner {
  display: flex;
  align-items: center;
  height: 72rpx;
  background: rgba(255, 255, 255, 0.2);
  border-radius: $radius-base;
  padding: 0 24rpx;
}

.search-icon {
  font-size: 28rpx;
  margin-right: 12rpx;
}

.search-placeholder {
  font-size: $font-base;
  color: rgba(255, 255, 255, 0.7);
}

.chat-list {
  background: var(--bg-color);
}



.chat-item {
  display: flex;
  align-items: center;
  padding: 24rpx 30rpx;
  background: var(--card-bg);
  border-bottom: 1rpx solid var(--border-color);
  transition: background 0.2s;

  &:active {
    background: var(--bg-color);
  }
}

.avatar-wrap {
  position: relative;
  margin-right: 24rpx;
  flex-shrink: 0;
}

.avatar {
  width: 96rpx;
  height: 96rpx;
  border-radius: $radius-base;
}

.avatar-default {
  display: flex;
  align-items: center;
  justify-content: center;
  background: $primary-color;
  font-size: 40rpx;
  font-weight: bold;
  color: #ffffff;
}

.badge {
  position: absolute;
  top: -8rpx;
  right: -8rpx;
  min-width: 36rpx;
  height: 36rpx;
  padding: 0 10rpx;
  background: $danger-color;
  border-radius: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: $font-xs;
  color: #ffffff;
  border: 3rpx solid var(--card-bg);
}

.chat-info {
  flex: 1;
  min-width: 0;
}

.chat-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8rpx;
}

.chat-name {
  font-size: $font-base;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: 16rpx;
}

.chat-time {
  font-size: $font-xs;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.chat-bottom {
  display: flex;
  align-items: center;
}

.chat-preview {
  font-size: $font-sm;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4rpx;
  margin-top: 6rpx;
}

.typing-dot {
  font-size: 16rpx;
  color: $primary-color;
  animation: typingBounce 1.4s infinite ease-in-out;

  &:nth-child(2) { animation-delay: 0.2s; }
  &:nth-child(3) { animation-delay: 0.4s; }
}

@keyframes typingBounce {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}

.typing-text {
  font-size: $font-xs;
  color: $primary-color;
  margin-left: 8rpx;
}

/* 弹窗 */
.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

.modal-content {
  width: 600rpx;
  background: var(--card-bg);
  border-radius: $radius-lg;
  padding: 48rpx 40rpx;
}

.modal-title {
  font-size: $font-lg;
  font-weight: bold;
  color: var(--text-primary);
  text-align: center;
  margin-bottom: 40rpx;
}

.modal-input-wrap {
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

.modal-btns {
  display: flex;
  gap: 24rpx;
  margin-top: 40rpx;
}

.modal-btn {
  flex: 1;
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $radius-base;
  font-size: $font-base;
  font-weight: 500;
  transition: opacity 0.2s;

  &:active {
    opacity: 0.8;
  }

  &.cancel {
    background: var(--bg-color);
    color: var(--text-secondary);
  }

  &.confirm {
    background: $primary-color;
    color: #ffffff;
  }
}
</style>
