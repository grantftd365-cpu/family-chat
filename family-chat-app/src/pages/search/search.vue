<template>
  <view class="search-page">
    <!-- 搜索栏 -->
    <view class="search-header" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="search-bar">
        <text class="search-icon">🔍</text>
        <input
          v-model="keyword"
          class="search-input"
          placeholder="搜索联系人、群组、聊天记录"
          focus
          confirm-type="search"
          @confirm="doSearch"
          @input="onInput"
        />
        <view v-if="keyword" class="clear-btn" @tap="clearKeyword">
          <text>✕</text>
        </view>
      </view>
      <view class="cancel-btn" @tap="goBack">
        <text>取消</text>
      </view>
    </view>

    <!-- 搜索结果 -->
    <scroll-view scroll-y class="result-list">
      <!-- 联系人 -->
      <view v-if="results.contacts && results.contacts.length" class="result-group">
        <text class="group-title">联系人</text>
        <view
          v-for="item in results.contacts"
          :key="item.id"
          class="result-item"
          @tap="goContact(item)"
        >
          <view class="item-avatar">
            <image v-if="item.avatar_url" :src="api.toAbsoluteMediaUrl(item.avatar_url)" class="avatar-img" mode="aspectFill" />
            <text v-else>{{ item.avatar || (item.nickname || '?')[0] }}</text>
          </view>
          <view class="item-info">
            <text class="item-name">{{ item.nickname }}</text>
            <text class="item-desc">{{ item.signature || '' }}</text>
          </view>
        </view>
      </view>

      <!-- 群组 -->
      <view v-if="results.groups && results.groups.length" class="result-group">
        <text class="group-title">群组</text>
        <view
          v-for="item in results.groups"
          :key="item.id"
          class="result-item"
          @tap="goGroup(item)"
        >
          <view class="item-avatar group-avatar">
            <text>{{ (item.name || '?')[0] }}</text>
          </view>
          <view class="item-info">
            <text class="item-name">{{ item.name }}</text>
          </view>
        </view>
      </view>

      <!-- 聊天记录 -->
      <view v-if="results.messages && results.messages.length" class="result-group">
        <text class="group-title">聊天记录</text>
        <view
          v-for="item in results.messages"
          :key="item.id"
          class="result-item"
          @tap="goMessage(item)"
        >
          <view class="item-avatar msg-avatar">
            <text>💬</text>
          </view>
          <view class="item-info">
            <text class="item-name">{{ item.sender_name }} · {{ item.group_name }}</text>
            <text class="item-desc">{{ item.content }}</text>
          </view>
        </view>
      </view>

      <!-- 空状态 -->
      <view v-if="keyword && searched && !hasResults" class="empty-state">
        <text class="empty-icon">🔍</text>
        <text class="empty-text">未找到相关结果</text>
      </view>

      <!-- 初始状态 -->
      <view v-if="!keyword" class="initial-state">
        <text class="initial-hint">输入关键词开始搜索</text>
      </view>
    </scroll-view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import * as api from '../../utils/api'

const statusBarHeight = ref(44)
const keyword = ref('')
const searched = ref(false)
const results = ref({ contacts: [], groups: [], messages: [] })
let searchTimer = null

const hasResults = computed(() => {
  const r = results.value
  return (r.contacts?.length || 0) + (r.groups?.length || 0) + (r.messages?.length || 0) > 0
})

onLoad((options = {}) => {
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  if (options.q) {
    keyword.value = decodeURIComponent(options.q)
    doSearch()
  }
})

function clearKeyword() {
  keyword.value = ''
  results.value = { contacts: [], groups: [], messages: [] }
  searched.value = false
}

function onInput() {
  clearTimeout(searchTimer)
  if (!keyword.value.trim()) {
    results.value = { contacts: [], groups: [], messages: [] }
    searched.value = false
    return
  }
  searchTimer = setTimeout(() => doSearch(), 300)
}

async function doSearch() {
  const q = keyword.value.trim()
  if (!q) return
  searched.value = true
  try {
    const res = await api.search(q)
    results.value = res
  } catch (e) {
    console.error('搜索失败:', e)
  }
}

function goContact(item) {
  uni.showActionSheet({
    itemList: ['发消息', '添加好友'],
    success: async (res) => {
      if (res.tapIndex === 0) {
        await openDirectChat(item)
      } else if (res.tapIndex === 1) {
        await addFriend(item)
      }
    }
  })
}

async function openDirectChat(item) {
  uni.showLoading({ title: '正在打开聊天...' })
  try {
    const group = await api.getOrCreateDirectGroup(item.id)
    uni.hideLoading()
    uni.navigateTo({
      url: `/pages/chat/chat?groupId=${group.id}&name=${encodeURIComponent(item.nickname || '私聊')}`
    })
  } catch (e) {
    uni.hideLoading()
    uni.showModal({
      title: '还不是好友',
      content: '需要先添加好友，是否现在发送好友申请？',
      success: async (r) => {
        if (r.confirm) await addFriend(item)
      }
    })
  }
}

async function addFriend(item) {
  try {
    await api.sendFriendRequest(item.id, '你好，我想添加你为好友')
    uni.showToast({ title: '好友申请已发送', icon: 'success' })
  } catch (e) {
    uni.showToast({ title: e.message || '发送失败', icon: 'none' })
  }
}

function goGroup(item) {
  uni.navigateTo({
    url: `/pages/chat/chat?groupId=${item.id}&name=${encodeURIComponent(item.name)}`
  })
}

function goMessage(item) {
  uni.navigateTo({
    url: `/pages/chat/chat?groupId=${item.group_id}&name=${encodeURIComponent(item.group_name || '聊天')}`
  })
}

function goBack() {
  uni.navigateBack()
}
</script>

<style lang="scss" scoped>
.search-page {
  min-height: 100vh;
  background: var(--bg-color);
}

.search-header {
  display: flex;
  align-items: center;
  padding: 16rpx 24rpx;
  background: $primary-color;
  gap: 16rpx;
}

.search-bar {
  flex: 1;
  display: flex;
  align-items: center;
  height: 72rpx;
  background: rgba(255, 255, 255, 0.2);
  border-radius: $radius-base;
  padding: 0 20rpx;
}

.search-icon {
  font-size: 28rpx;
  margin-right: 12rpx;
}

.search-input {
  flex: 1;
  font-size: $font-base;
  color: #ffffff;
}

.clear-btn {
  padding: 8rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.7);
}

.cancel-btn {
  font-size: $font-base;
  color: #ffffff;
  padding: 8rpx 0;
}

.result-list {
  height: calc(100vh - 120rpx);
}

.result-group {
  margin-bottom: 16rpx;
}

.group-title {
  display: block;
  padding: 20rpx 30rpx 12rpx;
  font-size: $font-sm;
  color: var(--text-secondary);
}

.result-item {
  display: flex;
  align-items: center;
  padding: 24rpx 30rpx;
  background: var(--card-bg);
  border-bottom: 1rpx solid var(--border-color);

  &:active {
    background: var(--bg-color);
  }
}

.item-avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: $radius-base;
  background: $primary-color;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36rpx;
  font-weight: bold;
  color: #ffffff;
  margin-right: 24rpx;
  flex-shrink: 0;
}

.group-avatar {
  background: #4A90D9;
}

.msg-avatar {
  background: #F5A623;
}


.avatar-img {
  width: 80rpx;
  height: 80rpx;
  border-radius: $radius-base;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: $font-base;
  color: var(--text-primary);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-desc {
  font-size: $font-sm;
  color: var(--text-secondary);
  display: block;
  margin-top: 4rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-state, .initial-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 200rpx 0;
}

.empty-icon {
  font-size: 100rpx;
  margin-bottom: 24rpx;
}

.empty-text {
  font-size: $font-base;
  color: var(--text-secondary);
}

.initial-hint {
  font-size: $font-base;
  color: var(--text-placeholder);
}
</style>
