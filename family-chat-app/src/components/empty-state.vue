<template>
  <view class="empty-state" :class="{ 'empty-state-compact': compact }">
    <view v-if="icon || preset" class="empty-icon" :class="iconAnimation">
      <text v-if="preset">{{ presetIcon }}</text>
      <text v-else>{{ icon }}</text>
    </view>
    <text v-if="title || presetTitle" class="empty-title">{{ title || presetTitle }}</text>
    <text v-if="description || presetDesc" class="empty-desc">{{ description || presetDesc }}</text>
    <view v-if="actionText" class="empty-action" @tap="$emit('action')">
      <text>{{ actionText }}</text>
    </view>
    <slot></slot>
  </view>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'

const props = defineProps({
  icon: { type: String, default: '' },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  actionText: { type: String, default: '' },
  compact: { type: Boolean, default: false },
  preset: { type: String, default: '' } // chat/contacts/moments/search/favorites
})

defineEmits(['action'])

const iconAnimation = ref('')

onMounted(() => {
  // 触发淡入动画
  setTimeout(() => {
    iconAnimation.value = 'icon-animate'
  }, 50)
})

const presets = {
  chat: { icon: '💬', title: '暂无聊天', description: '点击右上角创建群聊开始吧' },
  contacts: { icon: '👤', title: '暂无联系人', description: '点击右上角添加好友' },
  moments: { icon: '📷', title: '暂无动态', description: '快去发布第一条朋友圈吧' },
  search: { icon: '🔍', title: '无搜索结果', description: '换个关键词试试' },
  favorites: { icon: '⭐', title: '暂无收藏', description: '长按消息可以收藏' }
}

const presetIcon = computed(() => {
  if (props.preset && presets[props.preset]) return presets[props.preset].icon
  return ''
})

const presetTitle = computed(() => {
  if (props.preset && presets[props.preset]) return presets[props.preset].title
  return ''
})

const presetDesc = computed(() => {
  if (props.preset && presets[props.preset]) return presets[props.preset].description
  return ''
})
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
  opacity: 0;
  transform: translateY(20rpx) scale(0.8);
  transition: opacity 0.5s ease, transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);

  &.icon-animate {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.empty-title {
  font-size: $font-lg;
  font-weight: 500;
  color: var(--text-primary, $text-primary);
  margin-bottom: $space-xs;
  opacity: 0;
  animation: fadeInUp 0.4s ease 0.15s forwards;
}

.empty-desc {
  font-size: $font-sm;
  color: var(--text-secondary, $text-secondary);
  text-align: center;
  line-height: $line-height-base;
  max-width: 480rpx;
  margin-bottom: $space-lg;
  opacity: 0;
  animation: fadeInUp 0.4s ease 0.25s forwards;
}

.empty-action {
  padding: $space-sm $space-xl;
  background: $primary-color;
  border-radius: $radius-pill;
  transition: opacity $transition-fast;
  opacity: 0;
  animation: fadeInUp 0.4s ease 0.35s forwards;

  &:active {
    opacity: 0.8;
  }

  text {
    font-size: $font-base;
    color: $text-inverse;
    font-weight: 500;
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16rpx); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
