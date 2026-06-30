<template>
  <view class="chat-page">
    <!-- 导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-content">
        <view class="nav-left" @tap="goBack">
          <text class="back-icon">←</text>
          <view v-if="unreadTotal > 0" class="back-badge">
            <text>{{ unreadTotal > 99 ? '99+' : unreadTotal }}</text>
          </view>
        </view>
        <text class="nav-title">{{ chatName }}</text>
        <view class="nav-right">
          <view class="nav-icon-btn" @tap="toggleSearch">
            <text>🔍</text>
          </view>
          <view class="nav-icon-btn" @tap="showGroupInfo = true">
            <text>👤</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 搜索栏 -->
    <view v-if="showSearch" class="search-overlay" :style="{ top: (statusBarHeight + 44) + 'px' }">
      <view class="search-bar">
        <text class="search-icon">🔍</text>
        <input
          v-model="searchKeyword"
          class="search-input"
          placeholder="搜索聊天记录..."
          :focus="showSearch"
          @input="onSearchInput"
        />
        <text v-if="searchKeyword" class="search-clear" @tap="clearSearch">✕</text>
      </view>
      <text class="search-cancel" @tap="toggleSearch">取消</text>
      <view v-if="searchResults.length > 0" class="search-results">
        <text class="search-count">找到 {{ searchResults.length }}{{ searchResults.length >= SEARCH_RESULT_LIMIT ? '+' : '' }} 条结果</text>
        <scroll-view scroll-y class="search-results-list">
          <view
            v-for="result in searchResults"
            :key="result.id"
            class="search-result-item"
            @tap="jumpToSearchResult(result)"
          >
            <text class="result-sender">{{ result.sender_name }}</text>
            <text class="result-content">{{ result.content }}</text>
            <text class="result-time">{{ formatMsgTime(result.created_at) }}</text>
          </view>
        </scroll-view>
      </view>
      <view v-else-if="searchKeyword && !searching" class="search-empty">
        <text>没有找到相关消息</text>
      </view>
    </view>

    <!-- 群公告 -->
    <view v-if="announcement && showAnnouncement" class="announcement-bar" @tap="announcementExpanded = !announcementExpanded">
      <view class="announcement-content">
        <text class="announcement-icon">📢</text>
        <view class="announcement-text-wrap">
          <text class="announcement-label">群公告</text>
          <text class="announcement-text" :class="{ expanded: announcementExpanded }">{{ announcement }}</text>
        </view>
        <text class="announcement-toggle">{{ announcementExpanded ? '收起' : '展开' }}</text>
      </view>
      <view class="announcement-close" @tap.stop="showAnnouncement = false">
        <text>✕</text>
      </view>
    </view>

    <!-- 消息区域 -->
    <scroll-view
      scroll-y
      :scroll-into-view="scrollTarget"
      :scroll-with-animation="true"
      class="message-area"
      :style="{ height: msgAreaHeight + 'px' }"
      @scrolltoupper="onScrollToUpper"
      refresher-enabled
      :refresher-triggered="refreshing"
      @refresherrefresh="onRefresh"
    >
      <!-- 加载更多 -->
      <view v-if="hasMore" class="load-more">
        <text class="load-more-text">{{ loadingMore ? '加载中...' : '加载更多' }}</text>
      </view>

      <!-- 消息列表 -->
      <view
        v-for="(msg, index) in filteredMessages"
        :key="msg.id || index"
        :id="'msg-' + (msg.id || index)"
        class="msg-row msg-anim"
        :class="{
          self: msg.sender_id === currentUserId,
          'msg-highlight': highlightMsgId === msg.id
        }"
      >
        <!-- 时间分割线 -->
        <view v-if="shouldShowTime(msg, index)" class="time-divider">
          <text class="time-text">{{ formatMsgTime(msg.created_at) }}</text>
        </view>

        <!-- 系统消息 -->
        <view v-if="msg.msg_type === 'system'" class="system-msg">
          <text class="system-text">{{ msg.content }}</text>
        </view>

        <!-- 撤回消息 -->
        <view v-else-if="msg.recalled" class="system-msg">
          <view class="recall-wrap">
            <text class="system-text">
              {{ msg.sender_id === currentUserId ? '你' : msg.sender_name }}撤回了一条消息
            </text>
            <text v-if="msg.sender_id === currentUserId" class="recall-edit-btn" @tap="reEditMessage(msg)">重新编辑</text>
          </view>
        </view>

        <!-- 普通消息 -->
        <view v-else class="msg-content-row">
          <!-- 头像 -->
          <view
            class="msg-avatar"
            :class="{ 'avatar-self': msg.sender_id === currentUserId }"
          >
            <image
              v-if="msg.sender_avatar"
              :src="msg.sender_avatar"
              class="avatar-img"
              mode="aspectFill"
            />
            <view v-else class="avatar-placeholder">
              <text>{{ (msg.sender_name || '?')[0] }}</text>
            </view>
          </view>

          <!-- 气泡 -->
          <view class="msg-bubble-wrap" @longpress="onMsgLongPress(msg)">
            <text
              v-if="msg.sender_id !== currentUserId"
              class="sender-name"
            >{{ msg.sender_name }}</text>
            <view
              class="msg-bubble"
              :class="{
                'bubble-self': msg.sender_id === currentUserId,
                'bubble-other': msg.sender_id !== currentUserId
              }"
            >
              <!-- 引用回复 -->
              <view v-if="msg.reply_to" class="reply-quote" @tap="onScrollToMsg(msg.reply_to)">
                <view class="reply-quote-bar"></view>
                <view class="reply-quote-body">
                  <text class="reply-sender">{{ msg.reply_sender_name || '消息' }}</text>
                  <text class="reply-snippet">{{ msg.reply_content || '[图片/文件]' }}</text>
                </view>
              </view>

              <!-- 文字消息 -->
              <text
                v-if="msg.msg_type === 'text' || !msg.msg_type"
                class="msg-text"
                :class="{ 'text-self': msg.sender_id === currentUserId }"
              >{{ msg.content }}</text>

              <!-- 图片消息 -->
              <view
                v-else-if="msg.msg_type === 'image'"
                class="msg-image-wrap"
                @tap="previewImage(msg)"
              >
                <image
                  :src="msg.media_url || msg.content"
                  class="msg-image"
                  mode="widthFix"
                  :style="{ maxWidth: '400rpx', maxHeight: '500rpx' }"
                />
              </view>

              <!-- 语音消息 -->
              <view
                v-else-if="msg.msg_type === 'voice'"
                class="msg-voice"
                :class="{ 'voice-self': msg.sender_id === currentUserId }"
                @tap="playVoice(msg)"
              >
                <text class="voice-icon">{{ playingVoiceId === msg.id ? '🔊' : '🔉' }}</text>
                <text class="voice-duration">{{ msg.duration || '3' }}″</text>
              </view>

              <!-- 文件消息 -->
              <view v-else-if="msg.msg_type === 'file'" class="msg-file">
                <text class="file-icon">📎</text>
                <view class="file-info">
                  <text class="file-name">{{ msg.file_name || '文件' }}</text>
                  <text class="file-size">{{ msg.file_size || '' }}</text>
                </view>
              </view>

              <!-- 红包消息 -->
              <view
                v-else-if="msg.msg_type === 'red_envelope'"
                class="msg-red"
                @tap="openRedEnvelope(msg)"
              >
                <view class="red-header">
                  <text class="red-icon">🧧</text>
                  <text class="red-text">恭喜发财，大吉大利</text>
                </view>
                <text class="red-hint">红包</text>
              </view>

              <!-- 未知消息 -->
              <text v-else class="msg-text">[不支持的消息类型]</text>
            </view>

            <!-- 快速表情回应栏 -->
            <view v-if="quickReactMsgId === msg.id" class="quick-react-bar">
              <view
                v-for="emoji in quickEmojis"
                :key="emoji"
                class="quick-react-item"
                @tap.stop="sendQuickReaction(msg, emoji)"
              >
                <text>{{ emoji }}</text>
              </view>
            </view>

            <!-- 表情反应 -->
            <view v-if="hasReactions(msg)" class="reactions-wrap">
              <view
                v-for="(users, emoji) in msg.reactions"
                :key="emoji"
                class="reaction-item"
                :class="{ active: users.includes(currentUserId) }"
                @tap="toggleReaction(msg, emoji)"
              >
                <text class="reaction-emoji">{{ emoji }}</text>
                <text class="reaction-count">{{ users.length }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <!-- 占位，确保最后一条消息可见 -->
      <view id="msg-bottom" style="height: 20rpx;"></view>
    </scroll-view>

    <!-- 正在输入提示 -->
    <view v-if="typingName" class="typing-bar">
      <text class="typing-dots">●●●</text>
      <text class="typing-label">{{ typingName }} 正在输入...</text>
    </view>

    <!-- 底部输入栏 -->
    <view class="input-bar safe-area-bottom">
      <view class="input-bar-inner">
        <!-- 语音按钮 -->
        <view class="bar-btn" @tap="toggleVoiceMode">
          <text>{{ voiceMode ? '⌨️' : '🎤' }}</text>
        </view>

        <!-- @成员按钮 -->
        <view class="bar-btn mention-btn" @tap="toggleMentionPanel">
          <text>@</text>
        </view>

        <!-- 文字输入 / 语音录入 -->
        <view v-if="!voiceMode" class="input-wrap">
          <textarea
            v-model="inputText"
            class="msg-input"
            :auto-height="true"
            :maxlength="-1"
            :adjust-position="true"
            :confirm-hold="true"
            placeholder="输入消息..."
            :style="{ maxHeight: textareaMaxHeight + 'px' }"
            @confirm="sendTextMessage"
            @input="onInputChange"
          />
        </view>
        <view
          v-else
          class="voice-btn"
          :class="{ recording: isRecording }"
          @touchstart="startRecording"
          @touchend="stopRecording"
          @touchcancel="cancelRecording"
        >
          <text>{{ isRecording ? '松开发送' : '按住说话' }}</text>
        </view>

        <!-- 表情按钮 -->
        <view class="bar-btn" @tap="toggleEmojiPanel">
          <text>😊</text>
        </view>

        <!-- 更多按钮 -->
        <view class="bar-btn" @tap="toggleMorePanel">
          <text>➕</text>
        </view>

        <!-- 发送按钮 -->
        <view
          v-if="inputText.trim()"
          class="send-btn"
          @tap="sendTextMessage"
        >
          <text>发送</text>
        </view>
      </view>

      <!-- @成员面板 -->
      <view v-show="showMentionPanel" class="mention-panel">
        <view class="mention-title-row">
          <text class="mention-title">@ 家庭成员</text>
          <text class="mention-tip">点头像快速插入</text>
        </view>
        <scroll-view scroll-x class="mention-scroll" show-scrollbar="false">
          <view class="mention-list">
            <view
              v-for="member in mentionableMembers"
              :key="member.id"
              class="mention-chip"
              :class="{ agent: member.is_agent }"
              @tap="insertMention(member)"
            >
              <text class="mention-avatar">{{ member.avatar || '😀' }}</text>
              <view class="mention-meta">
                <text class="mention-name">{{ member.name }}</text>
                <text class="mention-role">{{ member.is_agent ? '数字人' : '真人' }}</text>
              </view>
            </view>
          </view>
        </scroll-view>
      </view>

      <!-- 表情面板 -->
      <view v-show="showEmoji" class="panel-area" :class="{ 'panel-visible': showEmoji }">
        <emoji-panel @select="onEmojiSelect" @delete="onEmojiDelete" />
      </view>

      <!-- 更多面板 -->
      <view v-show="showMore" class="panel-area" :class="{ 'panel-visible': showMore }">
        <view class="more-grid">
          <view class="more-item" @tap="chooseImage">
            <view class="more-icon">🖼️</view>
            <text class="more-label">图片</text>
          </view>
          <view class="more-item" @tap="chooseFile">
            <view class="more-icon">📎</view>
            <text class="more-label">文件</text>
          </view>
          <view class="more-item" @tap="sendRedEnvelope">
            <view class="more-icon">🧧</view>
            <text class="more-label">红包</text>
          </view>
          <view class="more-item" @tap="chooseLocation">
            <view class="more-icon">📍</view>
            <text class="more-label">位置</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 消息操作菜单 -->
    <view v-if="showMsgMenu" class="modal-mask" @tap="showMsgMenu = false; quickReactMsgId = null">
      <view class="msg-menu" :style="menuStyle" @tap.stop>
        <view class="menu-item" @tap="handleCopy">
          <text>📋 复制</text>
        </view>
        <view class="menu-item" @tap="handleForward">
          <text>↗️ 转发</text>
        </view>
        <view class="menu-item" @tap="handleFavorite">
          <text>⭐ 收藏</text>
        </view>
        <view class="menu-item" @tap="handleReply">
          <text>↩️ 回复</text>
        </view>
        <view class="menu-item" @tap="handleReaction">
          <text>😀 表情</text>
        </view>
        <view v-if="selectedMsg?.sender_id === currentUserId" class="menu-item" @tap="handleRecall">
          <text>🗑️ 撤回</text>
        </view>
      </view>
    </view>

    <!-- 群信息 / 成员列表 -->
    <view v-if="showGroupInfo" class="modal-mask" @tap="showGroupInfo = false">
      <view class="group-info-panel" @tap.stop>
        <view class="group-info-header">
          <view>
            <text class="group-info-title">{{ chatName }}</text>
            <text class="group-info-subtitle">{{ groupMembers.length }} 位成员 · 可直接 @</text>
          </view>
          <text class="group-info-close" @tap="showGroupInfo = false">✕</text>
        </view>
        <scroll-view scroll-y class="group-member-list">
          <view
            v-for="member in groupMembers"
            :key="member.id"
            class="group-member-item"
            @tap="insertMention(member); showGroupInfo = false"
          >
            <text class="group-member-avatar">{{ member.avatar || '😀' }}</text>
            <view class="group-member-main">
              <text class="group-member-name">{{ member.name }}</text>
              <text class="group-member-desc">{{ member.is_agent ? '数字人，可@唤起回复' : '家庭成员' }}</text>
            </view>
            <text class="group-member-at">@</text>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import { useUserStore } from '../../stores/user'
import { useChatStore } from '../../stores/chat'
import { getDraft, setDraft } from '../../utils/storage'
import ws from '../../utils/ws'
import * as api from '../../utils/api'
import { normalizeReactions } from '../../utils/response'

const userStore = useUserStore()
const chatStore = useChatStore()

const statusBarHeight = ref(44)
const msgAreaHeight = ref(500)
const groupId = ref('')
const chatName = ref('聊天')
const inputText = ref('')
const voiceMode = ref(false)
const isRecording = ref(false)
const showEmoji = ref(false)
const showMore = ref(false)
const showGroupInfo = ref(false)
const showMentionPanel = ref(false)
const showMsgMenu = ref(false)
const selectedMsg = ref(null)
const menuStyle = ref({})
const scrollTarget = ref('')
const refreshing = ref(false)
const loadingMore = ref(false)
const hasMore = ref(true)
const playingVoiceId = ref(null)
const typingName = ref('')
const textareaMaxHeight = ref(120) // ~5 lines
const announcement = ref('')
const showAnnouncement = ref(true)
const announcementExpanded = ref(false)

// 搜索相关
const showSearch = ref(false)
const searchKeyword = ref('')
const searchResults = ref([])
const searching = ref(false)
const highlightMsgId = ref(null)
const SEARCH_RESULT_LIMIT = 200
const reactingMsgId = ref(null) // 防并发锁
const groupMembers = ref([])

// 快速表情回应
const quickReactMsgId = ref(null)
const quickEmojis = ['👍', '❤️', '😂', '😮', '😢', '🎉']

let typingTimer = null
let recorderManager = null
let searchDebounce = null

const currentUserId = computed(() => userStore.userInfo?.id)
const messages = computed(() => chatStore.messagesMap[groupId.value] || [])
const mentionableMembers = computed(() => {
  return groupMembers.value.filter(member => member.id !== currentUserId.value)
})

// 过滤消息（搜索模式下只显示匹配的）
const filteredMessages = computed(() => {
  if (!showSearch.value || !searchKeyword.value.trim()) return messages.value
  const kw = searchKeyword.value.trim().toLowerCase()
  const result = messages.value.filter(m => {
    if (!m.content) return false
    return m.content.toLowerCase().includes(kw)
  })
  return result.slice(0, SEARCH_RESULT_LIMIT)
})
const unreadTotal = computed(() => {
  let total = 0
  for (const key in chatStore.unreadMap) {
    total += chatStore.unreadMap[key] || 0
  }
  return total
})

onLoad((options) => {
  groupId.value = options.groupId || ''
  chatName.value = decodeURIComponent(options.name || '聊天')

  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  const navH = statusBarHeight.value + 44
  msgAreaHeight.value = sysInfo.windowHeight - navH - 120

  chatStore.currentGroupId = groupId.value

  // 加载草稿
  inputText.value = getDraft(groupId.value)

  // 加载消息
  loadMessages()

  // 加载群公告
  loadAnnouncement()

  // 加载群成员，供@面板使用
  loadGroupMembers()

  // 监听 WebSocket 消息
  ws.on('message', onWsMessage)
  ws.on('typing', onWsTyping)
  ws.on('recall', onWsRecall)
  ws.on('reaction', onWsReaction)
  ws.on('reaction_v2', onWsReaction)
  // 断线重连后重新同步消息
  ws.on('connected', onWsReconnected)

  // 初始化录音
  initRecorder()
})

onUnload(() => {
  // 保存草稿
  setDraft(groupId.value, inputText.value)
  chatStore.currentGroupId = null
  ws.off('message', onWsMessage)
  ws.off('typing', onWsTyping)
  ws.off('recall', onWsRecall)
  ws.off('reaction', onWsReaction)
  ws.off('reaction_v2', onWsReaction)
  ws.off('connected', onWsReconnected)
  if (typingTimer) clearTimeout(typingTimer)
})

function initRecorder() {
  recorderManager = uni.getRecorderManager()
  recorderManager.onStop((res) => {
    if (isRecording.value) {
      uploadAndSendVoice(res.tempFilePath)
    }
    isRecording.value = false
  })
  recorderManager.onError((err) => {
    console.error('录音错误:', err)
    isRecording.value = false
    uni.showToast({ title: '录音失败', icon: 'none' })
  })
}

async function loadMessages() {
  try {
    await chatStore.loadMessages(groupId.value)
    scrollToBottom()
  } catch (e) {
    console.error('加载消息失败:', e)
  }
}

async function loadGroupMembers() {
  if (!groupId.value) return
  try {
    const res = await api.getGroupMembers(groupId.value)
    groupMembers.value = Array.isArray(res) ? res : (res.members || [])
  } catch (e) {
    console.error('加载群成员失败:', e)
    groupMembers.value = []
  }
}

function loadAnnouncement() {
  const group = chatStore.groups.find(g => g.id === groupId.value)
  if (group && group.announcement) {
    announcement.value = group.announcement
  }
}

async function onRefresh() {
  refreshing.value = true
  await loadMessages()
  refreshing.value = false
}

function onScrollToUpper() {
  // 加载更多历史消息
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  setTimeout(() => {
    loadingMore.value = false
    hasMore.value = false
  }, 1000)
}

function scrollToBottom() {
  nextTick(() => {
    scrollTarget.value = ''
    setTimeout(() => {
      scrollTarget.value = 'msg-bottom'
    }, 50)
  })
}

// WebSocket 事件处理
function onWsMessage(msg) {
  if (msg.group_id === groupId.value) {
    chatStore.addMessage(groupId.value, msg)
    scrollToBottom()
  }
}

function onWsTyping(data) {
  if (data.group_id === groupId.value) {
    typingName.value = data.name
    if (typingTimer) clearTimeout(typingTimer)
    typingTimer = setTimeout(() => {
      typingName.value = ''
    }, 3000)
  }
}

function onWsRecall(data) {
  chatStore.handleRecall(data.message_id)
}

function onWsReaction(data) {
  if (!data || !data.message_id) return
  const msg = messages.value.find(m => m.id === data.message_id)
  if (!msg) return
  if (!msg.reactions) msg.reactions = {}
  // 标准化：确保是 {emoji: [uid]} 格式
  if (Array.isArray(msg.reactions)) {
    msg.reactions = normalizeReactions(msg.reactions)
  }
  const action = data.action || 'add'
  const uid = data.user_id || data.userId
  if (action === 'remove') {
    if (msg.reactions[data.emoji]) {
      const idx = msg.reactions[data.emoji].indexOf(uid)
      if (idx > -1) msg.reactions[data.emoji].splice(idx, 1)
      if (msg.reactions[data.emoji].length === 0) delete msg.reactions[data.emoji]
    }
  } else {
    if (!msg.reactions[data.emoji]) msg.reactions[data.emoji] = []
    if (uid && !msg.reactions[data.emoji].includes(uid)) {
      msg.reactions[data.emoji].push(uid)
    }
  }
}

// 断线重连后重新加载消息
async function onWsReconnected() {
  if (groupId.value) {
    try {
      await chatStore.loadMessages(groupId.value)
    } catch (e) {
      console.error('重连后同步消息失败:', e)
    }
  }
}

// 发送文字消息
async function sendTextMessage() {
  const text = inputText.value.trim()
  if (!text) return

  inputText.value = ''
  showEmoji.value = false
  showMore.value = false
  showMentionPanel.value = false

  try {
    await chatStore.sendMessage({
      group_id: groupId.value,
      content: text,
      msg_type: 'text'
    })
    scrollToBottom()
  } catch (e) {
    // 恢复输入内容
    inputText.value = text
    console.error('发送失败:', e)
  }
}

// 输入变化 - 发送正在输入状态
let inputThrottle = null
function onInputChange() {
  if (inputText.value.endsWith('@')) {
    showMentionPanel.value = true
    showEmoji.value = false
    showMore.value = false
  }
  if (inputThrottle) return
  inputThrottle = setTimeout(() => {
    inputThrottle = null
    ws.sendTyping(groupId.value, userStore.userInfo?.nickname || '我')
  }, 1000)
}

function toggleMentionPanel() {
  showMentionPanel.value = !showMentionPanel.value
  if (showMentionPanel.value) {
    showEmoji.value = false
    showMore.value = false
    if (!groupMembers.value.length) loadGroupMembers()
  }
}

function toggleEmojiPanel() {
  showEmoji.value = !showEmoji.value
  if (showEmoji.value) {
    showMentionPanel.value = false
    showMore.value = false
  }
}

function toggleMorePanel() {
  showMore.value = !showMore.value
  if (showMore.value) {
    showMentionPanel.value = false
    showEmoji.value = false
  }
}

function insertMention(member) {
  if (!member?.name) return
  const mentionText = `@${member.name} `
  if (inputText.value.endsWith('@')) {
    inputText.value = inputText.value.slice(0, -1) + mentionText
  } else if (!inputText.value || /\s$/.test(inputText.value)) {
    inputText.value += mentionText
  } else {
    inputText.value += ` ${mentionText}`
  }
  showMentionPanel.value = false
}

// 选择表情
function onEmojiSelect(emoji) {
  inputText.value += emoji
}

function onEmojiDelete() {
  // 删除最后一个字符（考虑 emoji 可能是多字节）
  inputText.value = inputText.value.slice(0, -1)
}

// 切换语音模式
function toggleVoiceMode() {
  voiceMode.value = !voiceMode.value
  showEmoji.value = false
  showMore.value = false
  showMentionPanel.value = false
}

// 录音
function startRecording() {
  isRecording.value = true
  recorderManager.start({
    format: 'mp3',
    duration: 60000
  })
  uni.showToast({ title: '正在录音...', icon: 'none', duration: 60000 })
}

function stopRecording() {
  uni.hideToast()
  recorderManager.stop()
}

function cancelRecording() {
  uni.hideToast()
  isRecording.value = false
  recorderManager.stop()
}

// 上传并发送语音
async function uploadAndSendVoice(filePath) {
  try {
    uni.showLoading({ title: '发送中...' })
    const res = await api.uploadVoice(filePath)
    await chatStore.sendMessage({
      group_id: groupId.value,
      content: res.url || '',
      msg_type: 'voice',
      media_url: res.url
    })
    uni.hideLoading()
    scrollToBottom()
  } catch (e) {
    uni.hideLoading()
    uni.showToast({ title: '发送语音失败', icon: 'none' })
  }
}

// 选择图片
function chooseImage() {
  uni.chooseImage({
    count: 9,
    sizeType: ['compressed'],
    sourceType: ['album', 'camera'],
    success: async (res) => {
      showMore.value = false
      for (const path of res.tempFilePaths) {
        try {
          uni.showLoading({ title: '上传中...' })
          const uploadRes = await api.uploadMomentImage(path)
          await chatStore.sendMessage({
            group_id: groupId.value,
            content: uploadRes.url || path,
            msg_type: 'image',
            media_url: uploadRes.url || path
          })
          uni.hideLoading()
        } catch (e) {
          uni.hideLoading()
          console.error('图片发送失败:', e)
        }
      }
      scrollToBottom()
    }
  })
}

// 选择文件
function chooseFile() {
  showMore.value = false
  // #ifdef H5
  const input = document.createElement('input')
  input.type = 'file'
  input.onchange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    uni.showLoading({ title: '上传中...' })
    try {
      const uploadRes = await api.uploadVoice(file.path || file.name)
      await chatStore.sendMessage({
        group_id: groupId.value,
        content: file.name || '文件',
        msg_type: 'file',
        media_url: uploadRes.url || '',
        file_name: file.name,
        file_size: file.size
      })
      uni.hideLoading()
      scrollToBottom()
    } catch (e) {
      uni.hideLoading()
      uni.showToast({ title: '文件发送失败', icon: 'none' })
    }
  }
  input.click()
  // #endif
  // #ifndef H5
  uni.chooseMessageFile({
    count: 1,
    type: 'file',
    success: async (res) => {
      const file = res.tempFiles[0]
      uni.showLoading({ title: '上传中...' })
      try {
        const uploadRes = await api.uploadVoice(file.path || file.url)
        await chatStore.sendMessage({
          group_id: groupId.value,
          content: file.name || '文件',
          msg_type: 'file',
          media_url: uploadRes.url || file.path,
          file_name: file.name,
          file_size: file.size
        })
        uni.hideLoading()
        scrollToBottom()
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: '文件发送失败', icon: 'none' })
      }
    }
  })
  // #endif
}

// 发红包
function sendRedEnvelope() {
  showMore.value = false
  uni.showModal({
    title: '🧧 发红包',
    editable: true,
    placeholderText: '金额（元）',
    success: async (res) => {
      if (res.confirm && res.content) {
        const amount = parseFloat(res.content)
        if (!amount || amount <= 0 || amount > 200) {
          uni.showToast({ title: '金额需在 0.01-200 之间', icon: 'none' })
          return
        }
        uni.showModal({
          title: '祝福语',
          editable: true,
          placeholderText: '恭喜发财',
          success: async (res2) => {
            const greeting = res2.content || '恭喜发财'
            try {
              await api.sendMessage({
                group_id: groupId.value,
                content: greeting,
                msg_type: 'red_envelope',
                extra: JSON.stringify({ amount, greeting })
              })
              uni.showToast({ title: '红包已发出', icon: 'success' })
              scrollToBottom()
            } catch (e) {
              uni.showToast({ title: '发送失败', icon: 'none' })
            }
          }
        })
      }
    }
  })
}

// 选择位置
function chooseLocation() {
  showMore.value = false
  uni.chooseLocation({
    success: async (res) => {
      try {
        await chatStore.sendMessage({
          group_id: groupId.value,
          content: `${res.name}\n${res.address}`,
          msg_type: 'text'
        })
        scrollToBottom()
      } catch (e) {
        console.error('位置发送失败:', e)
      }
    },
    fail: () => {}
  })
}

// 播放语音
function playVoice(msg) {
  if (playingVoiceId.value === msg.id) {
    uni.stopBackgroundAudio()
    playingVoiceId.value = null
    return
  }
  const url = msg.media_url || msg.content
  playingVoiceId.value = msg.id
  const audioCtx = uni.createInnerAudioContext()
  audioCtx.src = url
  audioCtx.play()
  audioCtx.onEnded(() => {
    playingVoiceId.value = null
    audioCtx.destroy()
  })
  audioCtx.onError(() => {
    playingVoiceId.value = null
    audioCtx.destroy()
  })
}

// 预览图片
function previewImage(msg) {
  const url = msg.media_url || msg.content
  uni.previewImage({
    current: url,
    urls: [url]
  })
}

// 打开红包
async function openRedEnvelope(msg) {
  try {
    // 解析红包信息
    let extra = {}
    try { extra = JSON.parse(msg.extra || '{}') } catch (e) {}
    const amount = extra.amount || '未知'
    const greeting = extra.greeting || '恭喜发财'
    uni.showModal({
      title: '🧧 ' + greeting,
      content: `金额: ${amount}元`,
      showCancel: false,
      confirmText: '好的'
    })
  } catch (e) {
    uni.showToast({ title: '红包已领取', icon: 'success' })
  }
}

// 消息长按
// 搜索功能
function toggleSearch() {
  showSearch.value = !showSearch.value
  if (!showSearch.value) {
    searchKeyword.value = ''
    searchResults.value = []
    highlightMsgId.value = null
  }
}

function clearSearch() {
  searchKeyword.value = ''
  searchResults.value = []
  highlightMsgId.value = null
}

function onSearchInput() {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    doSearch()
  }, 300)
}

function doSearch() {
  const kw = searchKeyword.value.trim().toLowerCase()
  if (!kw) {
    searchResults.value = []
    return
  }
  searching.value = true
  searchResults.value = messages.value.filter(m => {
    if (!m.content) return false
    return m.content.toLowerCase().includes(kw)
  })
  searching.value = false
}

function jumpToSearchResult(msg) {
  showSearch.value = false
  searchKeyword.value = ''
  searchResults.value = []
  highlightMsgId.value = msg.id
  scrollTarget.value = ''
  nextTick(() => {
    scrollTarget.value = 'msg-' + msg.id
    setTimeout(() => {
      highlightMsgId.value = null
    }, 2000)
  })
}

function highlightText(text, keyword) {
  if (!keyword || !text) return text
  const regex = new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

// 消息引用跳转
function onScrollToMsg(msgId) {
  highlightMsgId.value = msgId
  scrollTarget.value = ''
  nextTick(() => {
    scrollTarget.value = 'msg-' + msgId
    setTimeout(() => {
      highlightMsgId.value = null
    }, 2000)
  })
}

// 快速表情回应
function onMsgLongPress(msg) {
  selectedMsg.value = msg
  quickReactMsgId.value = msg.id
  showMsgMenu.value = true
  // #ifdef H5
  menuStyle.value = {
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)'
  }
  // #endif
}

async function sendQuickReaction(msg, emoji) {
  quickReactMsgId.value = null
  if (reactingMsgId.value === msg.id) return // 防并发
  reactingMsgId.value = msg.id
  try {
    await api.addReactionV2(msg.id, emoji)
    if (!msg.reactions) msg.reactions = {}
    if (Array.isArray(msg.reactions)) msg.reactions = normalizeReactions(msg.reactions)
    if (!msg.reactions[emoji]) msg.reactions[emoji] = []
    if (currentUserId.value && !msg.reactions[emoji].includes(currentUserId.value)) {
      msg.reactions[emoji].push(currentUserId.value)
    }
  } catch (e) {
    console.error('表情回应失败:', e)
    uni.showToast({ title: '操作失败', icon: 'none', duration: 1500 })
  } finally {
    reactingMsgId.value = null
  }
}

// 是否显示时间
function shouldShowTime(msg, index) {
  if (index === 0) return true
  const prev = messages.value[index - 1]
  if (!prev || !msg.created_at || !prev.created_at) return false
  return new Date(msg.created_at) - new Date(prev.created_at) > 300000 // 5分钟
}

function formatMsgTime(time) {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diffDays = Math.floor((now - date) / 86400000)
  const h = date.getHours().toString().padStart(2, '0')
  const m = date.getMinutes().toString().padStart(2, '0')

  if (diffDays === 0) return `${h}:${m}`
  if (diffDays === 1) return `昨天 ${h}:${m}`
  if (diffDays < 7) {
    const days = ['日', '一', '二', '三', '四', '五', '六']
    return `星期${days[date.getDay()]} ${h}:${m}`
  }
  return `${date.getMonth() + 1}月${date.getDate()}日 ${h}:${m}`
}

function hasReactions(msg) {
  if (!msg.reactions) return false
  if (Array.isArray(msg.reactions)) return msg.reactions.length > 0
  if (typeof msg.reactions === 'object') return Object.keys(msg.reactions).length > 0
  return false
}

async function toggleReaction(msg, emoji) {
  if (reactingMsgId.value) return // 防并发
  reactingMsgId.value = msg.id
  try {
    if (!msg.reactions) msg.reactions = {}
    if (Array.isArray(msg.reactions)) msg.reactions = normalizeReactions(msg.reactions)
    const users = msg.reactions[emoji] || []
    const isMine = users.includes(currentUserId.value)
    if (isMine) {
      await api.removeReactionV2(msg.id, emoji)
      const idx = users.indexOf(currentUserId.value)
      if (idx > -1) users.splice(idx, 1)
      if (users.length === 0) delete msg.reactions[emoji]
    } else {
      await api.addReactionV2(msg.id, emoji)
      if (!msg.reactions[emoji]) msg.reactions[emoji] = []
      if (currentUserId.value) msg.reactions[emoji].push(currentUserId.value)
    }
  } catch (e) {
    console.error('反应失败:', e)
    uni.showToast({ title: '操作失败', icon: 'none', duration: 1500 })
  } finally {
    reactingMsgId.value = null
  }
}

// 消息操作
function handleCopy() {
  if (selectedMsg.value) {
    uni.setClipboardData({
      data: selectedMsg.value.content || '',
      success: () => uni.showToast({ title: '已复制', icon: 'success' })
    })
  }
  showMsgMenu.value = false
}

async function handleForward() {
  if (!selectedMsg.value) return
  showMsgMenu.value = false
  // 简化：选择目标群
  const groupNames = chatStore.groups.map(g => g.name)
  uni.showActionSheet({
    itemList: groupNames,
    success: async (res) => {
      const targetGroup = chatStore.groups[res.tapIndex]
      try {
        await chatStore.forwardMsg(selectedMsg.value.id, targetGroup.id)
        uni.showToast({ title: '已转发', icon: 'success' })
      } catch (e) {
        console.error('转发失败:', e)
      }
    }
  })
}

async function handleFavorite() {
  if (!selectedMsg.value) return
  showMsgMenu.value = false
  try {
    await api.addFavorite({
      content: selectedMsg.value.content,
      msg_type: selectedMsg.value.msg_type,
      source: 'chat'
    })
    uni.showToast({ title: '已收藏', icon: 'success' })
  } catch (e) {
    console.error('收藏失败:', e)
  }
}

function handleReply() {
  if (!selectedMsg.value) return
  showMsgMenu.value = false
  inputText.value = `@${selectedMsg.value.sender_name} `
}

async function handleReaction() {
  if (!selectedMsg.value) return
  showMsgMenu.value = false
  const emojis = ['👍', '❤️', '😂', '😮', '😢', '🙏']
  uni.showActionSheet({
    itemList: emojis,
    success: async (res) => {
      try {
        await chatStore.reactMsg(selectedMsg.value.id, emojis[res.tapIndex])
      } catch (e) {
        console.error('反应失败:', e)
      }
    }
  })
}

async function handleRecall() {
  if (!selectedMsg.value) return
  showMsgMenu.value = false
  uni.showModal({
    title: '提示',
    content: '确定撤回这条消息？',
    success: async (res) => {
      if (res.confirm) {
        try {
          await chatStore.recallMsg(selectedMsg.value.id)
          uni.showToast({ title: '已撤回', icon: 'success' })
        } catch (e) {
          console.error('撤回失败:', e)
        }
      }
    }
  })
}

function goBack() {
  uni.navigateBack()
}

// 撤回后重新编辑
function reEditMessage(msg) {
  if (msg.content) {
    inputText.value = msg.content
    uni.showToast({ title: '已恢复到输入框', icon: 'none' })
  }
}
</script>

<style lang="scss" scoped>
.chat-page {
  min-height: 100vh;
  background: var(--chat-bg);
  display: flex;
  flex-direction: column;
}

.nav-bar {
  background: $primary-color;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 88rpx;
  padding: 0 30rpx;
}

.nav-left {
  position: relative;
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;

  &:active {
    opacity: 0.7;
  }
}

.back-icon {
  font-size: 40rpx;
  color: #ffffff;
  font-weight: bold;
}

.back-badge {
  position: absolute;
  top: -6rpx;
  right: -12rpx;
  min-width: 32rpx;
  height: 32rpx;
  padding: 0 8rpx;
  background: $danger-color;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18rpx;
  color: #ffffff;
}

.nav-title {
  font-size: $font-lg;
  font-weight: bold;
  color: #ffffff;
  max-width: 400rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.nav-icon-btn {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36rpx;

  &:active {
    opacity: 0.7;
  }
}

/* 搜索栏 */
.search-overlay {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-color);
  z-index: 99;
  display: flex;
  flex-direction: column;
}

.search-bar {
  display: flex;
  align-items: center;
  padding: 16rpx 24rpx;
  gap: 12rpx;
  background: var(--card-bg);
  border-bottom: 1rpx solid var(--border-color);
}

.search-icon {
  font-size: 32rpx;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  height: 64rpx;
  font-size: $font-base;
  color: var(--text-primary);
}

.search-clear {
  font-size: 28rpx;
  color: var(--text-secondary);
  padding: 8rpx;
}

.search-cancel {
  font-size: $font-sm;
  color: $primary-color;
  padding: 8rpx 24rpx;
  position: absolute;
  right: 16rpx;
  top: 16rpx;
}

.search-results {
  flex: 1;
  overflow-y: auto;
}

.search-count {
  font-size: $font-xs;
  color: var(--text-secondary);
  padding: 12rpx 24rpx;
  display: block;
}

.search-results-list {
  max-height: 600rpx;
}

.search-result-item {
  display: flex;
  flex-direction: column;
  padding: 16rpx 24rpx;
  background: var(--card-bg);
  border-bottom: 1rpx solid var(--border-color);
  gap: 4rpx;

  &:active {
    background: var(--bg-color);
  }
}

.result-sender {
  font-size: $font-xs;
  color: $primary-color;
  font-weight: 500;
}

.result-content {
  font-size: $font-sm;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-time {
  font-size: $font-xs;
  color: var(--text-secondary);
}

.search-empty {
  text-align: center;
  padding: 60rpx;
  color: var(--text-secondary);
  font-size: $font-sm;
}

/* 消息高亮闪烁 */
.msg-highlight {
  animation: highlightFlash 2s ease;
}

@keyframes highlightFlash {
  0%, 100% { background: transparent; }
  10%, 50% { background: rgba(7, 193, 96, 0.15); }
  70% { background: rgba(7, 193, 96, 0.05); }
}

/* 快速表情回应栏 */
.quick-react-bar {
  display: flex;
  gap: 4rpx;
  padding: 8rpx 12rpx;
  background: var(--card-bg);
  border-radius: 36rpx;
  box-shadow: $shadow-base;
  margin-bottom: 8rpx;
  align-self: center;
  animation: scaleIn 0.2s ease;
}

.quick-react-item {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36rpx;
  border-radius: 50%;
  transition: transform 0.15s;

  &:active {
    transform: scale(1.3);
    background: var(--bg-color);
  }
}

.message-area {
  flex: 1;
  background: var(--chat-bg);
}

.load-more {
  text-align: center;
  padding: 20rpx;
}

.load-more-text {
  font-size: $font-sm;
  color: var(--text-secondary);
}

.msg-row {
  padding: 0 20rpx;
}

.msg-anim {
  animation: fadeInUp 0.3s ease-out;
}

/* 群公告 */
.announcement-bar {
  background: var(--card-bg);
  border-bottom: 1rpx solid var(--border-color);
  padding: 16rpx 24rpx;
  position: relative;
}

.announcement-content {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
}

.announcement-icon {
  font-size: 32rpx;
  flex-shrink: 0;
  margin-top: 2rpx;
}

.announcement-text-wrap {
  flex: 1;
  min-width: 0;
}

.announcement-label {
  font-size: $font-xs;
  color: var(--text-secondary);
  display: block;
  margin-bottom: 4rpx;
}

.announcement-text {
  font-size: $font-sm;
  color: var(--text-primary);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
  transition: all 0.3s ease;

  &.expanded {
    -webkit-line-clamp: unset;
    display: block;
  }
}

.announcement-toggle {
  font-size: $font-xs;
  color: $primary-color;
  flex-shrink: 0;
  margin-top: 4rpx;
}

.announcement-close {
  position: absolute;
  top: 12rpx;
  right: 16rpx;
  width: 40rpx;
  height: 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;

  text {
    font-size: 24rpx;
    color: var(--text-placeholder);
  }

  &:active {
    opacity: 0.6;
  }
}

.time-divider {
  display: flex;
  justify-content: center;
  padding: 20rpx 0;
}

.time-text {
  font-size: $font-xs;
  color: var(--text-secondary);
  background: rgba(0, 0, 0, 0.05);
  padding: 6rpx 16rpx;
  border-radius: $radius-sm;
}

.system-msg {
  display: flex;
  justify-content: center;
  padding: 16rpx 0;
}

.system-text {
  font-size: $font-xs;
  color: var(--text-secondary);
  background: rgba(0, 0, 0, 0.04);
  padding: 6rpx 20rpx;
  border-radius: $radius-sm;
}

.recall-wrap {
  display: flex;
  align-items: center;
  gap: $space-sm;
}

.recall-edit-btn {
  font-size: $font-xs;
  color: $primary-color;
  background: rgba(0, 0, 0, 0.04);
  padding: 6rpx 16rpx;
  border-radius: $radius-sm;
  font-weight: 500;
  transition: opacity $transition-fast;

  &:active {
    opacity: 0.7;
  }
}

.msg-content-row {
  display: flex;
  padding: 12rpx 0;
  align-items: flex-start;
}

.self .msg-content-row {
  flex-direction: row-reverse;
}

.msg-avatar {
  flex-shrink: 0;
  margin: 0 16rpx;
}

.avatar-img {
  width: 80rpx;
  height: 80rpx;
  border-radius: $radius-base;
}

.avatar-placeholder {
  width: 80rpx;
  height: 80rpx;
  border-radius: $radius-base;
  background: $primary-color;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  font-weight: bold;
  color: #ffffff;
}

.msg-bubble-wrap {
  max-width: 70%;
  display: flex;
  flex-direction: column;
}

.sender-name {
  font-size: $font-xs;
  color: var(--text-secondary);
  margin-bottom: 6rpx;
  padding-left: 8rpx;
}

.msg-bubble {
  padding: 20rpx 24rpx;
  border-radius: $radius-base;
  position: relative;
  word-break: break-all;
  min-width: 80rpx;
}

/* 引用回复 */
.reply-quote {
  display: flex;
  align-items: stretch;
  margin-bottom: 12rpx;
  background: rgba(0,0,0,0.04);
  border-radius: $radius-sm;
  overflow: hidden;
  transition: background $transition-fast;
  &:active { background: rgba(0,0,0,0.08); }
}

.reply-quote-bar {
  width: 6rpx;
  flex-shrink: 0;
  background: $primary-color;
}

.reply-quote-body {
  flex: 1;
  padding: 8rpx 12rpx;
  overflow: hidden;
}

.reply-sender {
  font-size: 20rpx;
  color: $primary-color;
  font-weight: 500;
  display: block;
  margin-bottom: 2rpx;
}

.reply-snippet {
  font-size: $font-xs;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.bubble-self {
  background: var(--bubble-self);
  border-top-right-radius: 4rpx;
}

.bubble-other {
  background: var(--bubble-other);
  border-top-left-radius: 4rpx;
  box-shadow: $shadow-sm;
}

.msg-text {
  font-size: $font-base;
  line-height: 1.5;
  color: $text-primary;
}

.text-self {
  color: #000000;
}

.msg-image-wrap {
  margin: -8rpx -12rpx;
}

.msg-image {
  border-radius: $radius-sm;
  max-width: 400rpx;
  max-height: 500rpx;
}

.msg-voice {
  display: flex;
  align-items: center;
  gap: 12rpx;
  min-width: 120rpx;
}

.voice-self {
  flex-direction: row-reverse;
}

.voice-icon {
  font-size: 36rpx;
}

.voice-duration {
  font-size: $font-sm;
  color: var(--text-secondary);
}

.msg-file {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.file-icon {
  font-size: 48rpx;
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.file-name {
  font-size: $font-sm;
  color: var(--text-primary);
  max-width: 300rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: $font-xs;
  color: var(--text-secondary);
}

.msg-red {
  background: linear-gradient(135deg, #FA9D3B, #E8553D);
  border-radius: $radius-base;
  padding: 24rpx;
  margin: -8rpx -12rpx;
}

.red-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 12rpx;
}

.red-icon {
  font-size: 40rpx;
}

.red-text {
  font-size: $font-base;
  color: #ffffff;
  font-weight: 500;
}

.red-hint {
  font-size: $font-xs;
  color: rgba(255, 255, 255, 0.7);
}

.reactions-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 8rpx;
}

.reaction-item {
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 4rpx 12rpx;
  background: var(--bg-color);
  border-radius: 20rpx;
  border: 1rpx solid var(--border-color);

  &.active {
    border-color: $primary-color;
    background: rgba(7, 193, 96, 0.1);
  }
}

.reaction-emoji {
  font-size: 28rpx;
}

.reaction-count {
  font-size: $font-xs;
  color: var(--text-secondary);
}

.typing-bar {
  display: flex;
  align-items: center;
  padding: 8rpx 30rpx;
  gap: 8rpx;
  background: var(--chat-bg);
}

.typing-dots {
  font-size: 16rpx;
  color: $primary-color;
  animation: typingBounce 1.4s infinite ease-in-out;
}

.typing-label {
  font-size: $font-xs;
  color: var(--text-secondary);
}

/* 输入栏 */
.input-bar {
  background: var(--card-bg);
  border-top: 1rpx solid var(--border-color);
}

.input-bar-inner {
  display: flex;
  align-items: center;
  padding: 16rpx 20rpx;
  gap: 12rpx;
}

.bar-btn {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  flex-shrink: 0;

  &:active {
    opacity: 0.7;
  }
}

.mention-btn {
  font-weight: 700;
  color: $primary-color;
}

.input-wrap {
  flex: 1;
  background: var(--bg-color);
  border-radius: $radius-base;
  padding: 12rpx 20rpx;
  min-height: 72rpx;
  display: flex;
  align-items: center;
}

.msg-input {
  width: 100%;
  min-height: 48rpx;
  max-height: 120rpx;
  font-size: $font-base;
  color: var(--text-primary);
  line-height: 1.5;
  overflow-y: auto;
}

.voice-btn {
  flex: 1;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-color);
  border-radius: $radius-base;
  font-size: $font-base;
  color: var(--text-primary);
  transition: background 0.2s;

  &.recording {
    background: $danger-color;
    color: #ffffff;
  }

  &:active {
    opacity: 0.8;
  }
}

.send-btn {
  padding: 0 24rpx;
  height: 64rpx;
  background: $primary-color;
  border-radius: $radius-base;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: $font-base;
  color: #ffffff;
  flex-shrink: 0;

  &:active {
    opacity: 0.8;
  }
}

.mention-panel {
  border-top: 1rpx solid var(--border-color);
  background: var(--card-bg);
  padding: 18rpx 20rpx 22rpx;
}

.mention-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14rpx;
}

.mention-title {
  font-size: $font-sm;
  font-weight: 600;
  color: var(--text-primary);
}

.mention-tip {
  font-size: $font-xs;
  color: var(--text-secondary);
}

.mention-scroll {
  white-space: nowrap;
}

.mention-list {
  display: inline-flex;
  gap: 14rpx;
  padding-right: 20rpx;
}

.mention-chip {
  display: flex;
  align-items: center;
  gap: 12rpx;
  min-width: 190rpx;
  padding: 14rpx 18rpx;
  border-radius: 999rpx;
  background: var(--bg-color);
  border: 1rpx solid var(--border-color);

  &.agent {
    border-color: rgba(7, 193, 96, 0.35);
    background: rgba(7, 193, 96, 0.08);
  }

  &:active {
    opacity: 0.75;
  }
}

.mention-avatar {
  width: 52rpx;
  height: 52rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  font-size: 30rpx;
}

.mention-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.mention-name {
  font-size: $font-sm;
  color: var(--text-primary);
  font-weight: 600;
  max-width: 150rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mention-role {
  font-size: 20rpx;
  color: var(--text-secondary);
}

.panel-area {
  height: 400rpx;
  border-top: 1rpx solid var(--border-color);
  overflow: hidden;
  transition: height 0.3s ease, opacity 0.3s ease;
  opacity: 0;
  height: 0;

  &.panel-visible {
    height: 400rpx;
    opacity: 1;
  }
}

.more-grid {
  display: flex;
  flex-wrap: wrap;
  padding: 30rpx;
  gap: 30rpx;
}

.more-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
  width: calc(25% - 24rpx);

  &:active {
    opacity: 0.7;
  }
}

.more-icon {
  width: 100rpx;
  height: 100rpx;
  background: var(--bg-color);
  border-radius: $radius-base;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48rpx;
}

.more-label {
  font-size: $font-xs;
  color: var(--text-secondary);
}

/* 消息菜单 */
.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.msg-menu {
  background: var(--card-bg);
  border-radius: $radius-lg;
  padding: 16rpx 0;
  box-shadow: $shadow-lg;
  min-width: 300rpx;
}

.group-info-panel {
  width: 640rpx;
  max-height: 78vh;
  background: var(--card-bg);
  border-radius: $radius-lg;
  overflow: hidden;
  box-shadow: $shadow-lg;
}

.group-info-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 32rpx;
  border-bottom: 1rpx solid var(--border-color);
}

.group-info-title {
  display: block;
  font-size: $font-lg;
  font-weight: 700;
  color: var(--text-primary);
}

.group-info-subtitle {
  display: block;
  margin-top: 8rpx;
  font-size: $font-xs;
  color: var(--text-secondary);
}

.group-info-close {
  font-size: 34rpx;
  color: var(--text-secondary);
  padding: 10rpx;
}

.group-member-list {
  max-height: 640rpx;
}

.group-member-item {
  display: flex;
  align-items: center;
  gap: 18rpx;
  padding: 22rpx 32rpx;
  border-bottom: 1rpx solid var(--border-color);

  &:active {
    background: var(--bg-color);
  }
}

.group-member-avatar {
  width: 72rpx;
  height: 72rpx;
  border-radius: 16rpx;
  background: var(--bg-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  flex-shrink: 0;
}

.group-member-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.group-member-name {
  font-size: $font-base;
  color: var(--text-primary);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-member-desc {
  font-size: $font-xs;
  color: var(--text-secondary);
}

.group-member-at {
  width: 48rpx;
  height: 48rpx;
  border-radius: 50%;
  background: rgba(7, 193, 96, 0.12);
  color: $primary-color;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.menu-item {
  padding: 24rpx 40rpx;
  font-size: $font-base;
  color: var(--text-primary);
  transition: background 0.2s;

  &:active {
    background: var(--bg-color);
  }
}
</style>
