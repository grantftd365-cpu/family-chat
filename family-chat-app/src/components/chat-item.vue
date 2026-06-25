<template>
  <view class="chat-item" @tap="$emit('tap')">
    <view class="item-avatar">
      <image v-if="group.avatar" :src="group.avatar" class="avatar-img" mode="aspectFill" />
      <view v-else class="avatar-default"><text>{{ (group.name || '?')[0] }}</text></view>
      <view v-if="unread" class="badge"><text>{{ unread > 99 ? '99+' : unread }}</text></view>
    </view>
    <view class="item-body">
      <view class="item-top">
        <text class="item-name">{{ group.name || '未命名' }}</text>
        <text class="item-time">{{ formatTime(group.last_message_time || group.updated_at) }}</text>
      </view>
      <view class="item-bottom">
        <text class="item-preview">{{ group.last_message || group.description || '暂无消息' }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
defineProps({
  group: { type: Object, required: true },
  unread: { type: Number, default: 0 }
})
defineEmits(['tap'])

function formatTime(time) {
  if (!time) return ''
  const d = new Date(time)
  const now = new Date()
  const diff = now - d
  if (diff < 86400000) return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
  if (diff < 172800000) return '昨天'
  return `${d.getMonth()+1}/${d.getDate()}`
}
</script>

<style lang="scss" scoped>
.chat-item {
  display: flex; align-items: center; padding: 24rpx 30rpx;
  background: var(--card-bg); border-bottom: 1rpx solid var(--border-color);
  &:active { background: var(--bg-color); }
}
.item-avatar { position: relative; margin-right: 24rpx; flex-shrink: 0; }
.avatar-img { width: 96rpx; height: 96rpx; border-radius: $radius-base; }
.avatar-default {
  width: 96rpx; height: 96rpx; border-radius: $radius-base;
  background: $primary-color; display: flex; align-items: center; justify-content: center;
  font-size: 40rpx; font-weight: bold; color: #fff;
}
.badge {
  position: absolute; top: -8rpx; right: -8rpx; min-width: 36rpx; height: 36rpx;
  padding: 0 10rpx; background: $danger-color; border-radius: 18rpx;
  display: flex; align-items: center; justify-content: center;
  font-size: $font-xs; color: #fff; border: 3rpx solid var(--card-bg);
}
.item-body { flex: 1; min-width: 0; }
.item-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8rpx; }
.item-name { font-size: $font-base; font-weight: 500; color: var(--text-primary); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-right: 16rpx; }
.item-time { font-size: $font-xs; color: var(--text-secondary); flex-shrink: 0; }
.item-bottom { display: flex; }
.item-preview { font-size: $font-sm; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
