<template>
  <view class="emoji-panel">
    <!-- 内容区域 -->
    <scroll-view scroll-y class="emoji-scroll">
      <!-- 最近使用 -->
      <view v-if="activeTab === 'recent'">
        <view v-if="recentEmojis.length" class="emoji-section">
          <text class="section-title">最近使用</text>
          <view class="emoji-grid">
            <view
              v-for="emoji in recentEmojis"
              :key="'r-' + emoji"
              class="emoji-item"
              @tap="onSelect(emoji)"
            >
              <text>{{ emoji }}</text>
            </view>
          </view>
        </view>
        <view v-else class="empty-hint">
          <text>暂无最近使用的表情</text>
        </view>
      </view>

      <!-- 表情符号 -->
      <view v-if="activeTab === 'emoji'">
        <view v-for="(group, gi) in emojiGroups" :key="gi" class="emoji-section">
          <text class="section-title">{{ group.name }}</text>
          <view class="emoji-grid">
            <view
              v-for="emoji in group.items"
              :key="emoji"
              class="emoji-item"
              @tap="onSelect(emoji)"
            >
              <text>{{ emoji }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 自定义表情包 -->
      <view v-if="activeTab === 'custom'">
        <view v-if="customPacks.length" class="emoji-section">
          <view v-for="pack in customPacks" :key="pack.id" class="custom-pack">
            <text class="section-title">{{ pack.name }}</text>
            <view class="emoji-grid custom-grid">
              <view
                v-for="item in pack.items"
                :key="item.id"
                class="custom-item"
                @tap="onSelectCustom(item)"
              >
                <image :src="item.url" class="custom-img" mode="aspectFill" />
              </view>
            </view>
          </view>
        </view>
        <view v-else class="empty-hint">
          <text>暂无自定义表情包</text>
        </view>
      </view>
    </scroll-view>

    <!-- 底部 Tab 栏 -->
    <view class="emoji-tabs">
      <view
        class="tab-item"
        :class="{ active: activeTab === 'recent' }"
        @tap="activeTab = 'recent'"
      >
        <text class="tab-icon">🕐</text>
        <text class="tab-label">最近</text>
      </view>
      <view
        class="tab-item"
        :class="{ active: activeTab === 'emoji' }"
        @tap="activeTab = 'emoji'"
      >
        <text class="tab-icon">😊</text>
        <text class="tab-label">表情</text>
      </view>
      <view
        class="tab-item"
        :class="{ active: activeTab === 'custom' }"
        @tap="activeTab = 'custom'"
      >
        <text class="tab-icon">🐱</text>
        <text class="tab-label">表情包</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['select'])

const activeTab = ref('emoji')
const recentEmojis = ref([])

const emojiGroups = [
  {
    name: '常用表情',
    items: ['😀', '😂', '🤣', '😊', '😍', '🥰', '😘', '😋', '🤔', '😅', '😢', '😭', '😡', '🥺', '😴']
  },
  {
    name: '手势',
    items: ['🙏', '👍', '👎', '👏', '🤝', '✌️', '🤟', '👋', '💪', '🤞', '☝️', '👆', '👇', '👈', '👉']
  },
  {
    name: '爱心',
    items: ['❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '💕', '💞', '💓', '💗', '💖']
  },
  {
    name: '庆祝',
    items: ['🎉', '🎊', '🎂', '🍰', '🎁', '🎈', '🎆', '🎇', '✨', '💯', '🎯', '🏆', '🥇', '🎀', '💐']
  },
  {
    name: '自然',
    items: ['🌹', '🌸', '🌺', '🌻', '🌷', '🍀', '🌈', '☀️', '🌙', '⭐', '🔥', '💧', '🌊', '❄️', '🍀']
  },
  {
    name: '食物',
    items: ['🍜', '🍲', '🍕', '🍔', '🍟', '🍚', '🍙', '🍣', '🍰', '🧧', '☕', '🍵', '🥤', '🍺', '🥂']
  },
  {
    name: '其他',
    items: ['🎣', '♟️', '📰', '💊', '👨', '👩', '👵', '🏠', '👀', '🤗', '😎', '🤫', '🤐', '🤩', '😏']
  }
]

const customPacks = ref([])

onMounted(() => {
  loadRecent()
  loadCustomPacks()
})

function loadRecent() {
  try {
    const stored = uni.getStorageSync('emoji_recent')
    if (stored) {
      recentEmojis.value = JSON.parse(stored)
    }
  } catch (e) {
    recentEmojis.value = []
  }
}

function saveRecent(emoji) {
  let list = recentEmojis.value.filter(e => e !== emoji)
  list.unshift(emoji)
  if (list.length > 30) list = list.slice(0, 30)
  recentEmojis.value = list
  try {
    uni.setStorageSync('emoji_recent', JSON.stringify(list))
  } catch (e) {}
}

function loadCustomPacks() {
  try {
    const stored = uni.getStorageSync('emoji_custom_packs')
    if (stored) {
      customPacks.value = JSON.parse(stored)
    }
  } catch (e) {
    customPacks.value = []
  }
}

function onSelect(emoji) {
  saveRecent(emoji)
  emit('select', emoji)
}

function onSelectCustom(item) {
  emit('select', item.url || item.id)
}
</script>

<style lang="scss" scoped>
.emoji-panel {
  background: var(--card-bg);
  border-top: 1rpx solid var(--border-color);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.emoji-scroll {
  flex: 1;
  padding: 16rpx;
  overflow-y: auto;
}

.emoji-section {
  margin-bottom: 20rpx;
}

.section-title {
  font-size: $font-xs;
  color: var(--text-secondary);
  padding: 8rpx 4rpx;
  display: block;
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
  transition: background 0.15s;

  &:active {
    background: var(--bg-color);
  }
}

.empty-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80rpx 0;

  text {
    font-size: $font-sm;
    color: var(--text-placeholder);
  }
}

.custom-pack {
  margin-bottom: 24rpx;
}

.custom-grid {
  gap: 12rpx;
}

.custom-item {
  width: 120rpx;
  height: 120rpx;
  border-radius: 8rpx;
  overflow: hidden;
  transition: opacity 0.15s;

  &:active {
    opacity: 0.7;
  }
}

.custom-img {
  width: 100%;
  height: 100%;
}

/* 底部 Tab */
.emoji-tabs {
  display: flex;
  border-top: 1rpx solid var(--border-color);
  background: var(--card-bg);
  flex-shrink: 0;
}

.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12rpx 0;
  transition: background 0.2s;

  &.active {
    background: var(--bg-color);
  }

  &:active {
    opacity: 0.7;
  }
}

.tab-icon {
  font-size: 36rpx;
  margin-bottom: 2rpx;
}

.tab-label {
  font-size: 18rpx;
  color: var(--text-secondary);
}
</style>
