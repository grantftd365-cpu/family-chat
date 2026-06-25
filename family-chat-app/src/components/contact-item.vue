<template>
  <view class="contact-item" @tap="$emit('tap')">
    <view class="item-avatar" :class="{ 'agent-avatar': isAgent }">
      <text>{{ avatarText }}</text>
    </view>
    <view class="item-body">
      <view class="item-name-row">
        <text class="item-name">{{ name }}</text>
        <view v-if="isAgent" class="agent-badge"><text>AI</text></view>
        <text v-if="online" class="online-dot">🟢</text>
      </view>
      <text v-if="signature" class="item-sig">{{ signature }}</text>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, default: '' },
  avatar: { type: String, default: '' },
  signature: { type: String, default: '' },
  isAgent: { type: Boolean, default: false },
  online: { type: Boolean, default: false }
})
defineEmits(['tap'])

const avatarText = computed(() => {
  if (props.avatar && props.avatar.length <= 2) return props.avatar
  return (props.name || '?')[0]
})
</script>

<style lang="scss" scoped>
.contact-item {
  display: flex; align-items: center; padding: 24rpx 30rpx;
  background: var(--card-bg); border-bottom: 1rpx solid var(--border-color);
  &:active { background: var(--bg-color); }
}
.item-avatar {
  width: 80rpx; height: 80rpx; border-radius: $radius-base;
  background: #4A90D9; display: flex; align-items: center; justify-content: center;
  font-size: 36rpx; font-weight: bold; color: #fff; margin-right: 24rpx; flex-shrink: 0;
}
.agent-avatar { background: $primary-color; }
.item-body { flex: 1; min-width: 0; }
.item-name-row { display: flex; align-items: center; gap: 12rpx; }
.item-name { font-size: $font-base; color: var(--text-primary); }
.agent-badge {
  font-size: 18rpx; background: $primary-color; color: #fff;
  padding: 2rpx 12rpx; border-radius: 4rpx;
}
.online-dot { font-size: 20rpx; }
.item-sig { font-size: $font-sm; color: var(--text-secondary); margin-top: 6rpx; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
