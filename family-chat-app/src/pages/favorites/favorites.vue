<template>
  <view class="favorites-page">
    <!-- 导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-content">
        <view class="nav-back" @tap="goBack"><text>‹</text></view>
        <text class="nav-title">我的收藏</text>
        <view class="nav-placeholder"></view>
      </view>
    </view>

    <scroll-view scroll-y class="fav-list" refresher-enabled :refresher-triggered="refreshing" @refresherrefresh="onRefresh">
      <view v-if="favorites.length === 0 && !loading" class="empty-state">
        <text class="empty-icon">⭐</text>
        <text class="empty-text">暂无收藏</text>
        <text class="empty-hint">长按消息可添加收藏</text>
      </view>

      <view v-for="fav in favorites" :key="fav.id" class="fav-item" @tap="onTap(fav)">
        <view class="fav-header">
          <text class="fav-source">{{ fav.source_name || '未知来源' }}</text>
          <text class="fav-time">{{ formatTime(fav.created_at) }}</text>
        </view>
        <!-- 图片类型 -->
        <image v-if="fav.msg_type === 'image'" :src="fav.media_url" class="fav-image" mode="aspectFill" />
        <!-- 文件类型 -->
        <view v-else-if="fav.msg_type === 'file'" class="fav-file">
          <text class="file-icon">📄</text>
          <text class="file-name">{{ fav.content || '文件' }}</text>
        </view>
        <!-- 文本类型 -->
        <text v-else class="fav-content">{{ fav.content }}</text>
      </view>
    </scroll-view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import * as api from '../../utils/api'

const statusBarHeight = ref(44)
const refreshing = ref(false)
const loading = ref(false)
const favorites = ref([])

onLoad(() => {
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  loadFavorites()
})

async function loadFavorites() {
  loading.value = true
  try {
    const res = await api.getFavorites()
    favorites.value = Array.isArray(res) ? res : (res.favorites || [])
  } catch (e) {
    console.error('加载收藏失败:', e)
  } finally {
    loading.value = false
  }
}

async function onRefresh() {
  refreshing.value = true
  await loadFavorites()
  refreshing.value = false
}

function onTap(fav) {
  if (fav.msg_type === 'image' && fav.media_url) {
    uni.previewImage({ urls: [fav.media_url] })
  }
}

function formatTime(time) {
  if (!time) return ''
  const d = new Date(time)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function goBack() { uni.navigateBack() }
</script>

<style lang="scss" scoped>
.favorites-page { min-height: 100vh; background: var(--bg-color); }
.nav-bar { background: $primary-color; }
.nav-content { display: flex; align-items: center; height: 88rpx; padding: 0 30rpx; }
.nav-back { font-size: 48rpx; color: #fff; padding-right: 16rpx; }
.nav-title { flex: 1; text-align: center; font-size: $font-lg; font-weight: bold; color: #fff; }
.nav-placeholder { width: 64rpx; }
.fav-list { height: calc(100vh - 88rpx); }
.empty-state { display: flex; flex-direction: column; align-items: center; padding: 200rpx 0; }
.empty-icon { font-size: 120rpx; margin-bottom: 24rpx; }
.empty-text { font-size: $font-lg; color: var(--text-secondary); margin-bottom: 12rpx; }
.empty-hint { font-size: $font-sm; color: var(--text-placeholder); }
.fav-item { background: var(--card-bg); margin-bottom: 2rpx; padding: 24rpx 30rpx; &:active { background: var(--bg-color); } }
.fav-header { display: flex; justify-content: space-between; margin-bottom: 12rpx; }
.fav-source { font-size: $font-sm; color: $primary-color; }
.fav-time { font-size: $font-xs; color: var(--text-secondary); }
.fav-content { font-size: $font-base; color: var(--text-primary); line-height: 1.6; }
.fav-image { width: 300rpx; height: 300rpx; border-radius: 8rpx; }
.fav-file { display: flex; align-items: center; gap: 12rpx; }
.file-icon { font-size: 40rpx; }
.file-name { font-size: $font-base; color: var(--text-primary); }
</style>
