<template>
  <view class="red-envelope-card" @tap="$emit('open')">
    <view class="envelope-top">
      <text class="envelope-icon">🧧</text>
      <view class="envelope-info">
        <text class="envelope-title">红包</text>
        <text class="envelope-greeting">{{ greeting || '恭喜发财' }}</text>
      </view>
    </view>
    <view class="envelope-footer">
      <text>查看红包</text>
    </view>
  </view>
</template>

<script setup>
defineProps({
  greeting: { type: String, default: '恭喜发财' },
  amount: { type: [Number, String], default: '' },
  opened: { type: Boolean, default: false }
})
defineEmits(['open'])
</script>

<style lang="scss" scoped>
.red-envelope-card {
  background: linear-gradient(135deg, #FA9D3B, #E8652B);
  border-radius: 16rpx; padding: 24rpx; min-width: 360rpx;
  &:active { opacity: 0.9; }
}
.envelope-top { display: flex; align-items: center; gap: 16rpx; margin-bottom: 16rpx; }
.envelope-icon { font-size: 48rpx; }
.envelope-info { flex: 1; }
.envelope-title { font-size: $font-base; font-weight: 500; color: #fff; display: block; }
.envelope-greeting { font-size: $font-sm; color: rgba(255,255,255,0.8); display: block; margin-top: 4rpx; }
.envelope-footer {
  text-align: center; padding-top: 12rpx; border-top: 1rpx solid rgba(255,255,255,0.2);
  font-size: $font-sm; color: rgba(255,255,255,0.7);
}
</style>
