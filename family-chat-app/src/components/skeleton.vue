<template>
  <view class="skeleton" :class="'skeleton-' + mode">
    <!-- list 模式：聊天列表骨架 -->
    <view v-if="mode === 'list'" class="skeleton-list">
      <view v-for="i in count" :key="i" class="skeleton-list-item">
        <view class="skel-avatar shimmer"></view>
        <view class="skeleton-list-body">
          <view class="skel-line skel-line-title shimmer"></view>
          <view class="skel-line skel-line-sub shimmer"></view>
        </view>
      </view>
    </view>

    <!-- chat 模式：聊天消息骨架 -->
    <view v-else-if="mode === 'chat'" class="skeleton-chat">
      <view v-for="i in count" :key="i" class="skeleton-chat-row" :class="i % 3 === 0 ? 'skel-row-right' : ''">
        <view class="skel-avatar-sm shimmer"></view>
        <view class="skel-bubble shimmer" :class="i % 3 === 0 ? 'skel-bubble-self' : ''" :style="{ width: bubbleWidth(i) }"></view>
      </view>
    </view>

    <!-- card 模式：卡片骨架 -->
    <view v-else-if="mode === 'card'" class="skeleton-card">
      <view v-for="i in count" :key="i" class="skeleton-card-item">
        <view class="skel-card-img shimmer"></view>
        <view class="skel-card-body">
          <view class="skel-line skel-line-title shimmer"></view>
          <view class="skel-line skel-line-md shimmer"></view>
          <view class="skel-line skel-line-sub shimmer"></view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
const props = defineProps({
  mode: {
    type: String,
    default: 'list',
    validator: (v) => ['list', 'chat', 'card'].includes(v)
  },
  count: {
    type: Number,
    default: 6
  }
})

function bubbleWidth(index) {
  const widths = ['60%', '45%', '70%', '50%', '55%', '65%']
  return widths[(index - 1) % widths.length]
}
</script>

<style lang="scss" scoped>
.shimmer {
  background: linear-gradient(
    90deg,
    var(--bg-color, #EDEDED) 25%,
    var(--bg-color-secondary, #F7F7F7) 37%,
    var(--bg-color, #EDEDED) 63%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: $radius-sm;
}

/* ---- list 模式 ---- */
.skeleton-list-item {
  display: flex;
  align-items: center;
  padding: $space-base $space-lg;
  border-bottom: 1rpx solid $border-color;
}

.skel-avatar {
  width: $avatar-lg;
  height: $avatar-lg;
  border-radius: $radius-base;
  flex-shrink: 0;
  margin-right: $space-base;
}

.skeleton-list-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: $space-sm;
}

.skel-line {
  height: 24rpx;
  border-radius: $radius-xs;
}

.skel-line-title {
  width: 40%;
}

.skel-line-md {
  width: 70%;
}

.skel-line-sub {
  width: 60%;
}

/* ---- chat 模式 ---- */
.skeleton-chat-row {
  display: flex;
  align-items: flex-start;
  padding: $space-sm $space-base;
  gap: $space-md;

  &.skel-row-right {
    flex-direction: row-reverse;
  }
}

.skel-avatar-sm {
  width: $avatar-base;
  height: $avatar-base;
  border-radius: $radius-base;
  flex-shrink: 0;
}

.skel-bubble {
  height: 72rpx;
  border-radius: $radius-base;

  &.skel-bubble-self {
    border-top-right-radius: $radius-xs;
  }
}

/* ---- card 模式 ---- */
.skeleton-card-item {
  background: $card-bg;
  border-radius: $radius-base;
  overflow: hidden;
  margin-bottom: $space-md;
  box-shadow: $shadow-xs;
}

.skel-card-img {
  width: 100%;
  height: 300rpx;
}

.skel-card-body {
  padding: $space-base;
  display: flex;
  flex-direction: column;
  gap: $space-sm;
}
</style>
