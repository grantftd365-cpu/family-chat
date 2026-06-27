<template>
  <view class="empty-state" :class="{ 'empty-state-compact': compact }">
    <view v-if="icon" class="empty-icon">
      <text>{{ icon }}</text>
    </view>
    <text v-if="title" class="empty-title">{{ title }}</text>
    <text v-if="description" class="empty-desc">{{ description }}</text>
    <view v-if="actionText" class="empty-action" @tap="$emit('action')">
      <text>{{ actionText }}</text>
    </view>
    <slot></slot>
  </view>
</template>

<script setup>
defineProps({
  icon: { type: String, default: '' },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  actionText: { type: String, default: '' },
  compact: { type: Boolean, default: false }
})

defineEmits(['action'])
</script>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $space-xxxl $space-lg;
  animation: fadeIn 0.3s ease;
}

.empty-state-compact {
  padding: $space-xl $space-base;
}

.empty-icon {
  font-size: 120rpx;
  margin-bottom: $space-base;
}

.empty-title {
  font-size: $font-lg;
  font-weight: 500;
  color: $text-primary;
  margin-bottom: $space-xs;
}

.empty-desc {
  font-size: $font-sm;
  color: $text-secondary;
  text-align: center;
  line-height: $line-height-base;
  max-width: 480rpx;
  margin-bottom: $space-lg;
}

.empty-action {
  padding: $space-sm $space-xl;
  background: $primary-color;
  border-radius: $radius-pill;
  transition: opacity $transition-fast;

  &:active {
    opacity: 0.8;
  }

  text {
    font-size: $font-base;
    color: $text-inverse;
    font-weight: 500;
  }
}
</style>
