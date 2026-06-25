<template>
  <!-- 系统消息 -->
  <view v-if="msg.msg_type === 'system'" class="system-msg">
    <text>{{ msg.content }}</text>
  </view>

  <!-- 普通消息气泡 -->
  <view v-else class="bubble-row" :class="isSelf ? 'right' : 'left'">
    <!-- 头像 -->
    <view class="bubble-avatar" @tap="$emit('avatar', msg.sender_id)">
      <text>{{ avatarText }}</text>
    </view>

    <view class="bubble-body">
      <!-- 昵称 -->
      <text v-if="!isSelf" class="bubble-name">
        <text v-if="msg.is_agent" class="agent-tag">AI</text>
        {{ msg.sender_name }}
      </text>

      <!-- 转发标记 -->
      <text v-if="msg.forwarded_from" class="forward-mark">↪ 转发</text>

      <!-- 引用回复 -->
      <view v-if="msg.reply_to && msg.reply_content" class="reply-quote">
        <text>↩ {{ msg.reply_content }}</text>
      </view>

      <!-- 文字消息 -->
      <view v-if="msg.msg_type === 'text' || (!msg.msg_type && !msg.media_url)" class="bubble-content" :class="isSelf ? 'bubble-right' : 'bubble-left'">
        <text>{{ msg.content }}</text>
      </view>

      <!-- 图片消息 -->
      <image v-else-if="msg.msg_type === 'image'" :src="msg.media_url" class="msg-image" mode="widthFix" @tap="previewImage" />

      <!-- 语音消息 -->
      <view v-else-if="msg.msg_type === 'voice'" class="voice-bubble" :class="isSelf ? 'bubble-right' : 'bubble-left'" @tap="playVoice">
        <text class="voice-icon">🔊</text>
        <view class="voice-waves">
          <view class="wave"></view>
          <view class="wave"></view>
          <view class="wave"></view>
          <view class="wave"></view>
          <view class="wave"></view>
        </view>
        <text class="voice-text">语音</text>
      </view>

      <!-- 文件消息 -->
      <view v-else-if="msg.msg_type === 'file'" class="file-bubble" :class="isSelf ? 'bubble-right' : 'bubble-left'">
        <text class="file-icon">📄</text>
        <view class="file-info">
          <text class="file-name">{{ msg.file_name || '文件' }}</text>
          <text class="file-size">{{ formatSize(msg.file_size) }}</text>
        </view>
      </view>

      <!-- 红包消息 -->
      <view v-else-if="msg.msg_type === 'red_envelope'" class="red-envelope" @tap="$emit('open-envelope', msg.id)">
        <view class="envelope-header">
          <text class="envelope-icon">🧧</text>
          <text class="envelope-title">红包</text>
        </view>
        <text class="envelope-greeting">{{ msg.content }}</text>
      </view>

      <!-- 兜底：文本 -->
      <view v-else class="bubble-content" :class="isSelf ? 'bubble-right' : 'bubble-left'">
        <text>{{ msg.content }}</text>
      </view>

      <!-- 表情反应 -->
      <view v-if="reactions.length" class="reactions">
        <view v-for="r in reactions" :key="r.emoji" class="reaction-item" :class="{ mine: r.mine }" @tap="$emit('reaction', msg.id, r.emoji)">
          <text>{{ r.emoji }}{{ r.count > 1 ? r.count : '' }}</text>
        </view>
      </view>

      <!-- 时间 -->
      <text class="bubble-time">{{ formatTime(msg.created_at) }}</text>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  msg: { type: Object, required: true },
  selfId: { type: String, default: '' }
})

defineEmits(['avatar', 'reaction', 'open-envelope', 'longpress'])

const isSelf = computed(() => props.msg.sender_id === props.selfId)

const avatarText = computed(() => {
  const av = props.msg.agent_avatar || props.msg.sender_avatar || props.msg.sender_name || '?'
  return av.length > 2 ? av[0] : av
})

const reactions = computed(() => {
  const r = props.msg.reactions
  if (!r) return []
  if (Array.isArray(r)) {
    const grouped = {}
    r.forEach(item => {
      if (!grouped[item.emoji]) grouped[item.emoji] = { emoji: item.emoji, count: 0, mine: false }
      grouped[item.emoji].count++
    })
    return Object.values(grouped)
  }
  return []
})

function previewImage() {
  if (props.msg.media_url) {
    uni.previewImage({ urls: [props.msg.media_url] })
  }
}

function playVoice() {
  if (!props.msg.media_url) return
  const audio = uni.createInnerAudioContext()
  audio.src = props.msg.media_url
  audio.play()
  audio.onEnded(() => audio.destroy())
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes > 1048576) return (bytes / 1048576).toFixed(1) + 'MB'
  return (bytes / 1024).toFixed(0) + 'KB'
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(typeof ts === 'number' && ts < 1e12 ? ts * 1000 : ts)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<style lang="scss" scoped>
.system-msg {
  text-align: center; padding: 20rpx 0;
  text { font-size: $font-xs; color: var(--text-secondary); background: var(--bg-color); padding: 6rpx 24rpx; border-radius: 8rpx; }
}
.bubble-row {
  display: flex; margin-bottom: 24rpx; max-width: 85%;
  &.right { margin-left: auto; flex-direction: row-reverse; }
}
.bubble-avatar {
  width: 72rpx; height: 72rpx; border-radius: 8rpx; flex-shrink: 0;
  background: #4A90D9; display: flex; align-items: center; justify-content: center;
  font-size: 32rpx; color: #fff; font-weight: bold;
}
.bubble-body { margin: 0 12rpx; display: flex; flex-direction: column; }
.bubble-name { font-size: $font-xs; color: var(--text-secondary); margin-bottom: 6rpx; padding: 0 8rpx; }
.agent-tag {
  font-size: 18rpx; background: $primary-color; color: #fff;
  padding: 0 8rpx; border-radius: 4rpx; margin-right: 6rpx; vertical-align: middle;
}
.forward-mark { font-size: $font-xs; color: var(--text-secondary); margin-bottom: 6rpx; }
.reply-quote {
  font-size: $font-xs; color: var(--text-secondary); background: rgba(0,0,0,0.04);
  padding: 8rpx 16rpx; border-radius: 8rpx; margin-bottom: 8rpx;
  border-left: 6rpx solid $primary-color; max-width: 100%; overflow: hidden;
  text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
}
.bubble-content {
  padding: 16rpx 24rpx; border-radius: 8rpx; font-size: $font-base; line-height: 1.5;
  word-break: break-all; position: relative;
}
.bubble-right { background: #95EC69; color: #000; }
.bubble-left { background: var(--card-bg); color: var(--text-primary); }
.msg-image { max-width: 360rpx; max-height: 360rpx; border-radius: 8rpx; }
.voice-bubble {
  display: flex; align-items: center; gap: 12rpx; padding: 16rpx 24rpx;
  border-radius: 8rpx; min-width: 160rpx;
}
.voice-icon { font-size: 28rpx; }
.voice-waves { display: flex; align-items: center; gap: 4rpx; height: 32rpx; }
.voice-wave { width: 6rpx; border-radius: 3rpx; background: currentColor;
  &:nth-child(1){height:12rpx} &:nth-child(2){height:20rpx} &:nth-child(3){height:16rpx}
  &:nth-child(4){height:24rpx} &:nth-child(5){height:12rpx}
}
.voice-text { font-size: $font-xs; color: var(--text-secondary); }
.file-bubble {
  display: flex; align-items: center; gap: 16rpx; padding: 16rpx 24rpx; border-radius: 8rpx;
}
.file-icon { font-size: 48rpx; }
.file-name { font-size: $font-sm; font-weight: 500; color: var(--text-primary); display: block; }
.file-size { font-size: $font-xs; color: var(--text-secondary); display: block; margin-top: 4rpx; }
.red-envelope {
  background: linear-gradient(135deg, #FA9D3B, #E8652B); color: #fff;
  padding: 20rpx 24rpx; border-radius: 12rpx; min-width: 360rpx;
}
.envelope-header { display: flex; align-items: center; gap: 12rpx; margin-bottom: 8rpx; }
.envelope-icon { font-size: 40rpx; }
.envelope-title { font-size: $font-base; font-weight: 500; }
.envelope-greeting { font-size: $font-sm; opacity: 0.8; }
.reactions { display: flex; flex-wrap: wrap; gap: 8rpx; margin-top: 8rpx; }
.reaction-item {
  font-size: 24rpx; background: var(--bg-color); border: 1rpx solid var(--border-color);
  border-radius: 20rpx; padding: 4rpx 12rpx;
  &.mine { border-color: $primary-color; background: rgba(7,193,96,0.1); }
}
.bubble-time { font-size: 20rpx; color: var(--text-placeholder); margin-top: 6rpx; padding: 0 8rpx; }
</style>
