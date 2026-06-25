<template>
  <view class="emoji-panel">
    <view class="emoji-grid">
      <view
        v-for="emoji in emojis"
        :key="emoji"
        class="emoji-item"
        @tap="$emit('select', emoji)"
      >
        <text>{{ emoji }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
defineEmits(['select'])

const emojis = [
  '😀', '😂', '🤣', '😊', '😍', '🥰', '😘', '😋', '🤔', '😅',
  '😢', '😭', '😡', '🥺', '😴', '🙏', '👍', '👎', '❤️', '💔',
  '🎉', '🎊', '💪', '👏', '🤝', '✌️', '💐', '🌹', '🎂', '🍰',
  '🍜', '🍲', '🎣', '♟️', '📰', '💊', '🧧', '👨', '👩', '👵',
  '🏠', '🔥', '✨', '💯', '🎯', '👀', '🤗', '😎', '🤫', '🤐'
]
</script>

<style lang="scss" scoped>
.emoji-panel {
  background: var(--card-bg);
  border-top: 1rpx solid var(--border-color);
  padding: 16rpx;
  max-height: 360rpx;
  overflow-y: auto;
}
.emoji-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4rpx;
}
.emoji-item {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  border-radius: 8rpx;
  &:active { background: var(--bg-color); }
}
</style>
