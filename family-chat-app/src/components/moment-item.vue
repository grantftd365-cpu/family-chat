<template>
  <view class="moment-card">
    <view class="moment-header" @tap="$emit('user')">
      <view class="moment-avatar">
        <text>{{ (moment.nickname || '?')[0] }}</text>
      </view>
      <view class="moment-user">
        <text class="moment-name">{{ moment.nickname }}</text>
        <text class="moment-time">{{ formatTime(moment.created_at) }}</text>
      </view>
    </view>

    <text class="moment-content">{{ moment.content }}</text>

    <view v-if="moment.images && moment.images.length" class="moment-images" :class="'img-' + Math.min(moment.images.length, 9)">
      <image v-for="(img, idx) in moment.images" :key="idx" :src="img" class="moment-img" mode="aspectFill" @tap="$emit('preview', moment.images, idx)" />
    </view>

    <view class="moment-actions">
      <text class="action-time">{{ formatTime(moment.created_at) }}</text>
      <view class="action-btns">
        <view class="action-btn" @tap="$emit('like')">
          <text>{{ moment.my_like ? '❤️' : '🤍' }}</text>
          <text v-if="moment.like_count" class="action-count">{{ moment.like_count }}</text>
        </view>
        <view class="action-btn" @tap="$emit('comment')">
          <text>💬</text>
          <text v-if="moment.comment_count" class="action-count">{{ moment.comment_count }}</text>
        </view>
      </view>
    </view>

    <view v-if="moment.likes && moment.likes.length" class="likes-bar">
      <text class="likes-icon">❤️</text>
      <text class="likes-names">{{ moment.likes.map(l => l.user_name).join('、') }}</text>
    </view>

    <view v-if="moment.comments && moment.comments.length" class="comments-bar">
      <view v-for="c in moment.comments" :key="c.id" class="comment-item">
        <text class="comment-name">{{ c.user_name }}</text>
        <text class="comment-text">：{{ c.content }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
defineProps({ moment: { type: Object, required: true } })
defineEmits(['user', 'preview', 'like', 'comment'])

function formatTime(time) {
  if (!time) return ''
  const d = new Date(time)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff/60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff/3600000)}小时前`
  return `${d.getMonth()+1}月${d.getDate()}日`
}
</script>

<style lang="scss" scoped>
.moment-card { background: var(--card-bg); margin-bottom: 16rpx; padding: 24rpx 30rpx; }
.moment-header { display: flex; align-items: center; margin-bottom: 20rpx; }
.moment-avatar {
  width: 80rpx; height: 80rpx; border-radius: $radius-base; background: #4A90D9;
  display: flex; align-items: center; justify-content: center;
  font-size: 36rpx; font-weight: bold; color: #fff; margin-right: 20rpx;
}
.moment-user { flex: 1; }
.moment-name { font-size: $font-base; font-weight: 500; color: #576B95; display: block; }
.moment-time { font-size: $font-xs; color: var(--text-secondary); display: block; margin-top: 4rpx; }
.moment-content { font-size: $font-base; color: var(--text-primary); line-height: 1.6; margin-bottom: 16rpx; }
.moment-images { display: flex; flex-wrap: wrap; gap: 8rpx; margin-bottom: 16rpx; }
.moment-img { width: 210rpx; height: 210rpx; border-radius: 8rpx; }
.img-1 .moment-img { width: 400rpx; height: 400rpx; }
.moment-actions {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 16rpx; border-top: 1rpx solid var(--border-color);
}
.action-time { font-size: $font-xs; color: var(--text-secondary); }
.action-btns { display: flex; gap: 24rpx; }
.action-btn { display: flex; align-items: center; gap: 6rpx; font-size: 28rpx; }
.action-count { font-size: $font-xs; color: var(--text-secondary); }
.likes-bar {
  display: flex; align-items: flex-start; padding: 16rpx 20rpx;
  background: var(--bg-color); border-radius: 8rpx; margin-top: 16rpx;
}
.likes-icon { margin-right: 8rpx; }
.likes-names { font-size: $font-sm; color: #576B95; }
.comments-bar { margin-top: 12rpx; }
.comment-item { padding: 8rpx 0; font-size: $font-sm; }
.comment-name { color: #576B95; }
.comment-text { color: var(--text-primary); }
</style>
