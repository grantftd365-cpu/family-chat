<template>
  <view class="moments-page">
    <!-- 导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-content">
        <view class="nav-back" @tap="goBack">
          <text>‹</text>
        </view>
        <text class="nav-title">朋友圈</text>
        <view class="nav-action" @tap="showCompose = true">
          <text>📷</text>
        </view>
      </view>
    </view>

    <!-- 动态列表 -->
    <scroll-view
      scroll-y
      class="moments-list"
      refresher-enabled
      :refresher-triggered="refreshing"
      @refresherrefresh="onRefresh"
    >
      <!-- 发布入口 -->
      <view class="compose-bar" @tap="showCompose = true">
        <view class="compose-avatar">
          <text>{{ userAvatar }}</text>
        </view>
        <text class="compose-hint">分享新鲜事...</text>
      </view>

      <view v-if="moments.length === 0 && !loading" class="empty-state">
        <text class="empty-icon">📷</text>
        <text class="empty-text">暂无动态</text>
      </view>

      <!-- 动态卡片 -->
      <view v-for="moment in moments" :key="moment.id" class="moment-card">
        <view class="moment-header" @tap="viewUser(moment)">
          <view class="moment-avatar">
            <text>{{ (moment.nickname || '?')[0] }}</text>
          </view>
          <view class="moment-user">
            <text class="moment-name">{{ moment.nickname }}</text>
            <text class="moment-time">{{ formatTime(moment.created_at) }}</text>
          </view>
        </view>

        <text class="moment-content">{{ moment.content }}</text>

        <!-- 图片 -->
        <view v-if="moment.images && moment.images.length" class="moment-images" :class="'img-count-' + Math.min(moment.images.length, 9)">
          <image
            v-for="(img, idx) in moment.images"
            :key="idx"
            :src="img"
            class="moment-img"
            mode="aspectFill"
            @tap="previewImage(moment.images, idx)"
          />
        </view>

        <!-- 操作栏 -->
        <view class="moment-actions">
          <view class="action-left">
            <text class="action-time">{{ formatTime(moment.created_at) }}</text>
          </view>
          <view class="action-right">
            <view class="action-btn" @tap="handleLike(moment)">
              <text>{{ moment.my_like ? '❤️' : '🤍' }}</text>
              <text v-if="moment.like_count" class="action-count">{{ moment.like_count }}</text>
            </view>
            <view class="action-btn" @tap="handleComment(moment)">
              <text>💬</text>
              <text v-if="moment.comment_count" class="action-count">{{ moment.comment_count }}</text>
            </view>
          </view>
        </view>

        <!-- 点赞列表 -->
        <view v-if="moment.likes && moment.likes.length" class="likes-bar">
          <text class="likes-icon">❤️</text>
          <text class="likes-names">{{ moment.likes.map(l => l.user_name).join('、') }}</text>
        </view>

        <!-- 评论列表 -->
        <view v-if="moment.comments && moment.comments.length" class="comments-bar">
          <view v-for="comment in moment.comments" :key="comment.id" class="comment-item">
            <text class="comment-name">{{ comment.user_name }}</text>
            <text class="comment-text">：{{ comment.content }}</text>
          </view>
        </view>
      </view>
    </scroll-view>

    <!-- 发布弹窗 -->
    <view v-if="showCompose" class="modal-mask" @tap="showCompose = false">
      <view class="compose-modal" @tap.stop>
        <view class="compose-header">
          <text class="compose-cancel" @tap="showCompose = false">取消</text>
          <text class="compose-title">发表动态</text>
          <text class="compose-submit" :class="{ disabled: !composeText.trim() && !composeImages.length }" @tap="publishMoment">发表</text>
        </view>
        <textarea
          v-model="composeText"
          class="compose-textarea"
          placeholder="分享新鲜事..."
          :maxlength="500"
        />
        <view class="compose-images">
          <view v-for="(img, idx) in composeImages" :key="idx" class="compose-img-wrap">
            <image :src="img" class="compose-img" mode="aspectFill" />
            <view class="compose-img-del" @tap="removeImage(idx)">
              <text>✕</text>
            </view>
          </view>
          <view v-if="composeImages.length < 9" class="compose-add-img" @tap="chooseImage">
            <text class="add-icon">+</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useUserStore } from '../../stores/user'
import * as api from '../../utils/api'

const userStore = useUserStore()
const statusBarHeight = ref(44)
const refreshing = ref(false)
const loading = ref(false)
const moments = ref([])
const showCompose = ref(false)
const composeText = ref('')
const composeImages = ref([])

const userAvatar = computed(() => {
  const u = userStore.userInfo
  return u?.nickname?.[0] || '😀'
})

onLoad(() => {
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  loadMoments()
})

async function loadMoments() {
  loading.value = true
  try {
    const res = await api.getMoments()
    moments.value = Array.isArray(res) ? res : (res.moments || [])
  } catch (e) {
    console.error('加载朋友圈失败:', e)
  } finally {
    loading.value = false
  }
}

async function onRefresh() {
  refreshing.value = true
  await loadMoments()
  refreshing.value = false
}

async function handleLike(moment) {
  try {
    await api.likeMoment(moment.id)
    moment.my_like = !moment.my_like
    moment.like_count = (moment.like_count || 0) + (moment.my_like ? 1 : -1)
  } catch (e) {
    console.error('点赞失败:', e)
  }
}

function handleComment(moment) {
  uni.showModal({
    title: '评论',
    editable: true,
    placeholderText: '写评论...',
    success: async (res) => {
      if (res.confirm && res.content?.trim()) {
        try {
          await api.commentMoment(moment.id, res.content.trim())
          await loadMoments()
        } catch (e) {
          console.error('评论失败:', e)
        }
      }
    }
  })
}

function chooseImage() {
  uni.chooseImage({
    count: 9 - composeImages.value.length,
    sizeType: ['compressed'],
    sourceType: ['album', 'camera'],
    success: (res) => {
      composeImages.value.push(...res.tempFilePaths)
    }
  })
}

function removeImage(idx) {
  composeImages.value.splice(idx, 1)
}

async function publishMoment() {
  if (!composeText.value.trim() && !composeImages.value.length) return
  uni.showLoading({ title: '发表中...' })
  try {
    const uploadedUrls = []
    for (const filePath of composeImages.value) {
      const res = await api.uploadMomentImage(filePath)
      uploadedUrls.push(res.url)
    }
    await api.postMoment({
      content: composeText.value.trim(),
      images: uploadedUrls
    })
    showCompose.value = false
    composeText.value = ''
    composeImages.value = []
    uni.showToast({ title: '已发表', icon: 'success' })
    await loadMoments()
  } catch (e) {
    uni.showToast({ title: '发表失败', icon: 'none' })
  } finally {
    uni.hideLoading()
  }
}

function previewImage(images, idx) {
  uni.previewImage({ urls: images, current: idx })
}

function viewUser(moment) {
  // 查看用户详情
}

function formatTime(time) {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diffMs = now - date
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 7) return `${diffDay}天前`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function goBack() {
  uni.navigateBack()
}
</script>

<style lang="scss" scoped>
.moments-page {
  min-height: 100vh;
  background: var(--bg-color);
}

.nav-bar {
  background: $primary-color;
}

.nav-content {
  display: flex;
  align-items: center;
  height: 88rpx;
  padding: 0 30rpx;
}

.nav-back {
  font-size: 48rpx;
  color: #ffffff;
  padding: 0 16rpx 0 0;
}

.nav-title {
  flex: 1;
  text-align: center;
  font-size: $font-lg;
  font-weight: bold;
  color: #ffffff;
}

.nav-action {
  font-size: 36rpx;
  padding: 8rpx;
}

.moments-list {
  height: calc(100vh - 88rpx);
}

.compose-bar {
  display: flex;
  align-items: center;
  padding: 24rpx 30rpx;
  background: var(--card-bg);
  margin-bottom: 16rpx;
}

.compose-avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: $radius-base;
  background: $primary-color;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36rpx;
  color: #ffffff;
  font-weight: bold;
  margin-right: 24rpx;
}

.compose-hint {
  font-size: $font-base;
  color: var(--text-placeholder);
}

.moment-card {
  background: var(--card-bg);
  margin-bottom: 16rpx;
  padding: 24rpx 30rpx;
}

.moment-header {
  display: flex;
  align-items: center;
  margin-bottom: 20rpx;
}

.moment-avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: $radius-base;
  background: #4A90D9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36rpx;
  font-weight: bold;
  color: #ffffff;
  margin-right: 20rpx;
}

.moment-user {
  flex: 1;
}

.moment-name {
  font-size: $font-base;
  font-weight: 500;
  color: #576B95;
  display: block;
}

.moment-time {
  font-size: $font-xs;
  color: var(--text-secondary);
  display: block;
  margin-top: 4rpx;
}

.moment-content {
  font-size: $font-base;
  color: var(--text-primary);
  line-height: 1.6;
  margin-bottom: 16rpx;
}

.moment-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
  margin-bottom: 16rpx;
}

.moment-img {
  width: 210rpx;
  height: 210rpx;
  border-radius: 8rpx;
}

.img-count-1 .moment-img { width: 400rpx; height: 400rpx; }

.moment-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16rpx;
  border-top: 1rpx solid var(--border-color);
}

.action-time {
  font-size: $font-xs;
  color: var(--text-secondary);
}

.action-right {
  display: flex;
  gap: 24rpx;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6rpx;
  font-size: 28rpx;
}

.action-count {
  font-size: $font-xs;
  color: var(--text-secondary);
}

.likes-bar {
  display: flex;
  align-items: flex-start;
  padding: 16rpx 20rpx;
  background: var(--bg-color);
  border-radius: 8rpx;
  margin-top: 16rpx;
}

.likes-icon {
  margin-right: 8rpx;
  flex-shrink: 0;
}

.likes-names {
  font-size: $font-sm;
  color: #576B95;
  line-height: 1.5;
}

.comments-bar {
  margin-top: 12rpx;
}

.comment-item {
  padding: 8rpx 0;
  font-size: $font-sm;
}

.comment-name {
  color: #576B95;
}

.comment-text {
  color: var(--text-primary);
}

/* 发布弹窗 */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
}

.compose-modal {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--card-bg);
  border-radius: 24rpx 24rpx 0 0;
  max-height: 80vh;
  overflow-y: auto;
}

.compose-header {
  display: flex;
  align-items: center;
  padding: 24rpx 30rpx;
  border-bottom: 1rpx solid var(--border-color);
}

.compose-cancel {
  font-size: $font-base;
  color: var(--text-secondary);
}

.compose-title {
  flex: 1;
  text-align: center;
  font-size: $font-lg;
  font-weight: bold;
  color: var(--text-primary);
}

.compose-submit {
  font-size: $font-base;
  color: $primary-color;
  font-weight: 500;

  &.disabled {
    opacity: 0.5;
  }
}

.compose-textarea {
  width: 100%;
  min-height: 200rpx;
  padding: 24rpx 30rpx;
  font-size: $font-base;
  color: var(--text-primary);
}

.compose-images {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
  padding: 0 30rpx 30rpx;
}

.compose-img-wrap {
  position: relative;
  width: 200rpx;
  height: 200rpx;
}

.compose-img {
  width: 100%;
  height: 100%;
  border-radius: 8rpx;
}

.compose-img-del {
  position: absolute;
  top: -12rpx;
  right: -12rpx;
  width: 40rpx;
  height: 40rpx;
  background: $danger-color;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20rpx;
  color: #ffffff;
}

.compose-add-img {
  width: 200rpx;
  height: 200rpx;
  border: 2rpx dashed var(--border-color);
  border-radius: 8rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-icon {
  font-size: 60rpx;
  color: var(--text-placeholder);
}
</style>
