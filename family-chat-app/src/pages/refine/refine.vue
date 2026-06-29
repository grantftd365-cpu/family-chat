<template>
  <view class="refine-page">
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-content">
        <view class="nav-back" @tap="goBack"><text>‹</text></view>
        <text class="nav-title">炼化数字人</text>
        <view class="nav-placeholder"></view>
      </view>
    </view>

    <scroll-view scroll-y class="refine-content">
      <!-- 七层雷达图 -->
      <view v-if="essenceData" class="section">
        <text class="section-title">七层本质</text>
        <view class="radar-card">
          <essence-radar :data="essenceData" :size="radarSize" />
        </view>
      </view>

      <!-- 炼化进度 -->
      <view v-if="completenessData" class="section">
        <view class="progress-header">
          <text class="section-title">炼化进度</text>
          <text class="overall-percent">{{ overallPercent }}%</text>
        </view>
        <view class="progress-list">
          <view
            v-for="dim in progressDimensions"
            :key="dim.key"
            class="progress-item"
          >
            <view class="progress-label">
              <text class="progress-name">{{ dim.label }}</text>
              <text v-if="dim.percent >= 100" class="progress-check">✅</text>
              <text class="progress-percent">{{ dim.percent }}%</text>
            </view>
            <view class="progress-bar-bg">
              <view
                class="progress-bar-fill"
                :style="{
                  width: dim.percent + '%',
                  background: dim.color
                }"
              ></view>
            </view>
          </view>
        </view>
      </view>

      <!-- 深层问卷入口 -->
      <view class="section">
        <view class="questionnaire-entry" @tap="goToQuestionnaire">
          <view class="entry-icon">📝</view>
          <view class="entry-info">
            <text class="entry-title">深层问卷</text>
            <text class="entry-desc">回答 10 个深层问题，完善数字人的本质认知</text>
          </view>
          <text class="entry-arrow">›</text>
        </view>
      </view>

      <!-- 选择数字人 -->
      <view class="section">
        <text class="section-title">选择数字人</text>
        <view class="agent-grid">
          <view
            v-for="agent in agents"
            :key="agent.id"
            class="agent-card"
            :class="{ active: selectedAgent === agent.id }"
            @tap="selectAgent(agent.id)"
          >
            <text class="agent-avatar">{{ agent.avatar || '🤖' }}</text>
            <text class="agent-name">{{ agent.name }}</text>
          </view>
        </view>
      </view>

      <!-- 炼化方式 -->
      <view class="section">
        <text class="section-title">选择炼化方式</text>

        <view class="method-list">
          <!-- 文本输入 -->
          <view class="method-card" @tap="selectMethod('text')">
            <view class="method-icon">📝</view>
            <view class="method-info">
              <text class="method-title">文本输入</text>
              <text class="method-desc">输入自我介绍、性格描述或聊天风格</text>
            </view>
            <text class="method-arrow">›</text>
          </view>

          <!-- 语音输入 -->
          <view class="method-card" @tap="selectMethod('voice')">
            <view class="method-icon">🎙️</view>
            <view class="method-info">
              <text class="method-title">语音输入</text>
              <text class="method-desc">录制或上传语音，自动分析说话风格</text>
            </view>
            <text class="method-arrow">›</text>
          </view>

          <!-- 视频输入 -->
          <view class="method-card" @tap="selectMethod('video')">
            <view class="method-icon">🎬</view>
            <view class="method-info">
              <text class="method-title">视频输入</text>
              <text class="method-desc">从视频中提取说话风格和音色特征</text>
            </view>
            <text class="method-arrow">›</text>
          </view>

          <!-- 文档输入 -->
          <view class="method-card" @tap="selectMethod('document')">
            <view class="method-icon">📄</view>
            <view class="method-info">
              <text class="method-title">文档输入</text>
              <text class="method-desc">上传 PDF/Word/TXT 文档提取性格</text>
            </view>
            <text class="method-arrow">›</text>
          </view>

          <!-- 聊天记录 -->
          <view class="method-card" @tap="selectMethod('chat')">
            <view class="method-icon">💬</view>
            <view class="method-info">
              <text class="method-title">聊天记录分析</text>
              <text class="method-desc">从群聊记录中自动学习说话习惯</text>
            </view>
            <text class="method-arrow">›</text>
          </view>
        </view>
      </view>

      <!-- 文本输入区域 -->
      <view v-if="currentMethod === 'text'" class="section fade-in">
        <text class="section-title">输入文本</text>
        <textarea
          v-model="textContent"
          class="text-input"
          placeholder="输入自我介绍、性格描述、说话风格等..."
          :maxlength="5000"
        />
        <text class="char-count">{{ textContent.length }}/5000</text>
      </view>

      <!-- 语音录制区域 -->
      <view v-if="currentMethod === 'voice'" class="section fade-in">
        <text class="section-title">录制语音</text>
        <view class="record-area">
          <view class="record-wave" :class="{ active: isRecording }">
            <view v-for="i in 7" :key="i" class="wave-bar" :style="{ animationDelay: i * 0.1 + 's' }"></view>
          </view>
          <text class="record-time">{{ recordTime }}s</text>
          <view class="record-btns">
            <view v-if="!isRecording" class="record-btn start" @tap="startVoiceRecord">
              <text>🎙️ 开始录音</text>
            </view>
            <view v-else class="record-btn stop" @tap="stopVoiceRecord">
              <text>⏹️ 停止录音</text>
            </view>
          </view>
          <text class="record-hint">请用目标人物的语气说一段话（建议15-60秒）</text>
        </view>

        <!-- 上传语音文件 -->
        <view class="upload-alt">
          <view class="upload-btn" @tap="uploadVoiceFile">
            <text>📁 上传语音文件</text>
          </view>
        </view>
      </view>

      <!-- 视频上传区域 -->
      <view v-if="currentMethod === 'video'" class="section fade-in">
        <text class="section-title">上传视频</text>
        <view class="upload-area" @tap="uploadVideo">
          <text class="upload-icon">🎬</text>
          <text class="upload-text">点击选择视频文件</text>
          <text class="upload-hint">支持 MP4/MOV/AVI，最大 500MB</text>
        </view>
        <view v-if="videoFile" class="file-preview">
          <text class="file-name">{{ videoFile.name }}</text>
          <text class="file-size">{{ formatSize(videoFile.size) }}</text>
        </view>
      </view>

      <!-- 文档上传区域 -->
      <view v-if="currentMethod === 'document'" class="section fade-in">
        <text class="section-title">上传文档</text>
        <view class="upload-area" @tap="uploadDocument">
          <text class="upload-icon">📄</text>
          <text class="upload-text">点击选择文档</text>
          <text class="upload-hint">支持 PDF/DOCX/TXT/MD/JSON/Excel</text>
        </view>
        <view v-if="docFile" class="file-preview">
          <text class="file-name">{{ docFile.name }}</text>
          <text class="file-size">{{ formatSize(docFile.size) }}</text>
        </view>
      </view>

      <!-- 聊天记录选择 -->
      <view v-if="currentMethod === 'chat'" class="section fade-in">
        <text class="section-title">选择群聊</text>
        <view class="group-list">
          <view
            v-for="group in groups"
            :key="group.id"
            class="group-item"
            :class="{ active: selectedGroup === group.id }"
            @tap="selectedGroup = group.id"
          >
            <text class="group-avatar">{{ (group.name || '?')[0] }}</text>
            <text class="group-name">{{ group.name }}</text>
            <text v-if="selectedGroup === group.id" class="group-check">✓</text>
          </view>
        </view>
      </view>

      <!-- 提交按钮 -->
      <view class="submit-area">
        <view class="submit-btn" :class="{ disabled: !canSubmit || submitting }" @tap="startRefine">
          <text v-if="submitting" class="loading-icon">⏳</text>
          <text>{{ submitting ? '炼化中...' : '开始炼化' }}</text>
        </view>
      </view>

      <!-- 结果展示 -->
      <view v-if="refineResult" class="section result-section fade-in">
        <text class="section-title">✨ 炼化结果</text>
        <view class="result-card">
          <view v-if="refineResult.traits?.personality_traits" class="result-row">
            <text class="result-label">性格特征</text>
            <text class="result-value">{{ refineResult.traits.personality_traits.join('、') }}</text>
          </view>
          <view v-if="refineResult.traits?.speaking_style" class="result-row">
            <text class="result-label">说话风格</text>
            <text class="result-value">{{ refineResult.traits.speaking_style }}</text>
          </view>
          <view v-if="refineResult.traits?.interests" class="result-row">
            <text class="result-label">兴趣爱好</text>
            <text class="result-value">{{ refineResult.traits.interests.join('、') }}</text>
          </view>
          <view v-if="refineResult.traits?.catchphrases" class="result-row">
            <text class="result-label">口头禅</text>
            <text class="result-value">{{ refineResult.traits.catchphrases.join('、') }}</text>
          </view>
          <view v-if="refineResult.transcript" class="result-row">
            <text class="result-label">转录文本</text>
            <text class="result-value transcript">{{ refineResult.transcript }}</text>
          </view>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import * as api from '../../utils/api'
import { normalizeList, normalizeEssence, normalizeCompleteness } from '../../utils/response'
import EssenceRadar from '../../components/essence-radar.vue'

const statusBarHeight = ref(44)
const agents = ref([])
const groups = ref([])
const selectedAgent = ref('')
const currentMethod = ref('')
const selectedGroup = ref('')
const textContent = ref('')
const isRecording = ref(false)
const recordTime = ref(0)
const videoFile = ref(null)
const docFile = ref(null)
const submitting = ref(false)
const refineResult = ref(null)
const essenceData = ref(null)
const completenessData = ref(null)
const radarSize = ref(280)
let recorderManager = null
let recordTimer = null

const progressDimensions = computed(() => {
  if (!completenessData.value) return []
  const dims = [
    { key: 'cognition', label: '认知', color: '#07C160' },
    { key: 'knowledge', label: '知识', color: '#10AEFF' },
    { key: 'emotion', label: '情感', color: '#FA5151' },
    { key: 'language', label: '语言', color: '#FFC300' },
    { key: 'value', label: '价值', color: '#6467F0' },
    { key: 'relation', label: '关系', color: '#E855D3' },
    { key: 'narrative', label: '叙事', color: '#FF8C42' }
  ]
  return dims.map(d => ({
    ...d,
    percent: Math.round((completenessData.value[d.key] || 0) * 100)
  }))
})

const overallPercent = computed(() => {
  if (!completenessData.value) return 0
  const vals = Object.values(completenessData.value)
  if (!vals.length) return 0
  return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length * 100)
})

const canSubmit = computed(() => {
  if (!selectedAgent.value) return false
  switch (currentMethod.value) {
    case 'text': return textContent.value.trim().length > 0
    case 'voice': return true
    case 'video': return !!videoFile.value
    case 'document': return !!docFile.value
    case 'chat': return !!selectedGroup.value
    default: return false
  }
})

onLoad(() => {
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  radarSize.value = Math.min(sysInfo.windowWidth - 80, 320)
  loadData()
  initRecorder()
})

async function loadData() {
  try {
    const [agentsRes, groupsRes] = await Promise.all([
      api.getAgents().catch(() => []),
      api.getGroups().catch(() => [])
    ])
    agents.value = normalizeList(agentsRes, [])
    groups.value = normalizeList(groupsRes, [])
    if (agents.value.length) {
      selectedAgent.value = agents.value[0].id
      loadEssenceData(agents.value[0].id)
    }
  } catch (e) {
    console.error('加载数据失败:', e)
  }
}

async function loadEssenceData(agentId) {
  if (!agentId) return
  try {
    const [essenceRes, completenessRes] = await Promise.all([
      api.getAgentEssence(agentId).catch(() => null),
      api.getRefinementCompleteness(agentId).catch(() => null)
    ])
    essenceData.value = normalizeEssence(essenceRes)
    completenessData.value = normalizeCompleteness(completenessRes)
  } catch (e) {
    console.error('加载本质数据失败:', e)
  }
}

function selectAgent(id) {
  selectedAgent.value = id
  loadEssenceData(id)
}

function goToQuestionnaire() {
  if (!selectedAgent.value) {
    uni.showToast({ title: '请先选择数字人', icon: 'none' })
    return
  }
  uni.navigateTo({
    url: `/pages/refine/questionnaire?agentId=${selectedAgent.value}`
  })
}

function initRecorder() {
  recorderManager = uni.getRecorderManager()
  recorderManager.onStop(async (res) => {
    if (!isRecording.value) return
    isRecording.value = false
    clearInterval(recordTimer)
    if (recordTime.value < 3) {
      uni.showToast({ title: '录音太短', icon: 'none' })
      return
    }
    // 自动提交语音炼化
    await doRefineVoice(res.tempFilePath)
  })
  recorderManager.onError(() => {
    isRecording.value = false
    clearInterval(recordTimer)
    uni.showToast({ title: '录音失败', icon: 'none' })
  })
}

function selectMethod(method) {
  currentMethod.value = method
  refineResult.value = null
}

function startVoiceRecord() {
  isRecording.value = true
  recordTime.value = 0
  recorderManager.start({ format: 'mp3', sampleRate: 16000, numberOfChannels: 1, duration: 120000 })
  recordTimer = setInterval(() => { recordTime.value++ }, 1000)
}

function stopVoiceRecord() {
  recorderManager.stop()
}

function uploadVoiceFile() {
  uni.chooseMessageFile({
    count: 1,
    type: 'file',
    success: async (res) => {
      const file = res.tempFiles[0]
      await doRefineVoice(file.path || file.url)
    }
  })
}

function uploadVideo() {
  uni.chooseVideo({
    count: 1,
    success: (res) => {
      videoFile.value = { name: res.name || '视频', path: res.tempFilePath, size: res.size }
    }
  })
}

function uploadDocument() {
  uni.chooseMessageFile({
    count: 1,
    type: 'file',
    success: (res) => {
      const file = res.tempFiles[0]
      docFile.value = { name: file.name || '文档', path: file.path || file.url, size: file.size }
    }
  })
}

async function startRefine() {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  refineResult.value = null

  try {
    let result
    switch (currentMethod.value) {
      case 'text':
        result = await api.refineFromText({ agent_id: selectedAgent.value, text: textContent.value.trim() })
        break
      case 'voice':
        // 已在录音回调中处理
        break
      case 'video':
        result = await api.refineFromVideo(selectedAgent.value, videoFile.value.path)
        break
      case 'document':
        result = await api.refineFromDocument(selectedAgent.value, docFile.value.path)
        break
      case 'chat':
        // 获取最近消息
        const msgs = await api.getMessages(selectedGroup.value, 100)
        const messages = Array.isArray(msgs) ? msgs : (msgs.messages || [])
        result = await api.refineFromChatHistory({ agent_id: selectedAgent.value, messages })
        break
    }
    if (result) {
      refineResult.value = result
      uni.showToast({ title: '炼化完成', icon: 'success' })
      // 刷新本质数据
      loadEssenceData(selectedAgent.value)
    }
  } catch (e) {
    uni.showToast({ title: '炼化失败: ' + (e.message || '未知错误'), icon: 'none' })
  } finally {
    submitting.value = false
  }
}

async function doRefineVoice(filePath) {
  submitting.value = true
  refineResult.value = null
  try {
    const result = await api.refineFromVoice(selectedAgent.value, filePath)
    refineResult.value = result
    uni.showToast({ title: '炼化完成', icon: 'success' })
  } catch (e) {
    uni.showToast({ title: '炼化失败', icon: 'none' })
  } finally {
    submitting.value = false
  }
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes > 1048576) return (bytes / 1048576).toFixed(1) + 'MB'
  return (bytes / 1024).toFixed(0) + 'KB'
}

function goBack() { uni.navigateBack() }
</script>

<style lang="scss" scoped>
.refine-page { min-height: 100vh; background: var(--bg-color); }
.nav-bar { background: $primary-color; }
.nav-content { display: flex; align-items: center; height: 88rpx; padding: 0 30rpx; }
.nav-back { font-size: 48rpx; color: #fff; padding-right: 16rpx; }
.nav-title { flex: 1; text-align: center; font-size: $font-lg; font-weight: bold; color: #fff; }
.nav-placeholder { width: 64rpx; }
.refine-content { height: calc(100vh - 88rpx); }
.section { padding: 0 30rpx; margin-bottom: 24rpx; }
.section-title { display: block; padding: 24rpx 0 12rpx; font-size: $font-sm; color: var(--text-secondary); font-weight: 500; }

/* 雷达图卡片 */
.radar-card {
  background: var(--card-bg);
  border-radius: $radius-base;
  padding: 16rpx;
  box-shadow: $shadow-sm;
}

/* 炼化进度 */
.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.overall-percent {
  font-size: $font-lg;
  font-weight: bold;
  color: $primary-color;
}

.progress-list {
  background: var(--card-bg);
  border-radius: $radius-base;
  padding: 16rpx 24rpx;
}

.progress-item {
  padding: 12rpx 0;
}

.progress-label {
  display: flex;
  align-items: center;
  margin-bottom: 8rpx;
}

.progress-name {
  font-size: $font-sm;
  color: var(--text-primary);
  flex: 1;
}

.progress-check {
  font-size: 28rpx;
  margin-right: 8rpx;
}

.progress-percent {
  font-size: $font-sm;
  color: var(--text-secondary);
  width: 60rpx;
  text-align: right;
}

.progress-bar-bg {
  height: 12rpx;
  background: var(--bg-color);
  border-radius: 6rpx;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 6rpx;
  transition: width 0.6s ease;
}

/* 问卷入口 */
.questionnaire-entry {
  display: flex;
  align-items: center;
  padding: 24rpx;
  background: var(--card-bg);
  border-radius: $radius-base;
  border: 2rpx solid $primary-color;
  transition: all 0.2s;

  &:active {
    transform: scale(0.98);
    background: $primary-50;
  }
}

.entry-icon {
  font-size: 48rpx;
  margin-right: 20rpx;
}

.entry-info {
  flex: 1;
}

.entry-title {
  font-size: $font-base;
  font-weight: 500;
  color: var(--text-primary);
  display: block;
}

.entry-desc {
  font-size: $font-sm;
  color: var(--text-secondary);
  display: block;
  margin-top: 4rpx;
}

.entry-arrow {
  font-size: 32rpx;
  color: $primary-color;
}

.agent-grid { display: flex; flex-wrap: wrap; gap: 16rpx; }
.agent-card {
  display: flex; flex-direction: column; align-items: center; padding: 16rpx 20rpx;
  background: var(--card-bg); border-radius: $radius-base; min-width: 140rpx;
  border: 2rpx solid transparent; transition: all 0.2s;
  &.active { border-color: $primary-color; background: rgba(7,193,96,0.05); }
  &:active { transform: scale(0.96); }
}
.agent-avatar { font-size: 48rpx; margin-bottom: 8rpx; }
.agent-name { font-size: $font-sm; color: var(--text-primary); }

.method-list { display: flex; flex-direction: column; gap: 12rpx; }
.method-card {
  display: flex; align-items: center; padding: 24rpx; background: var(--card-bg);
  border-radius: $radius-base; transition: all 0.2s;
  &:active { transform: scale(0.98); background: var(--bg-color); }
}
.method-icon { font-size: 48rpx; margin-right: 20rpx; }
.method-info { flex: 1; }
.method-title { font-size: $font-base; font-weight: 500; color: var(--text-primary); display: block; }
.method-desc { font-size: $font-sm; color: var(--text-secondary); display: block; margin-top: 4rpx; }
.method-arrow { font-size: 32rpx; color: var(--text-placeholder); }

.text-input {
  width: 100%; min-height: 200rpx; background: var(--card-bg); border-radius: $radius-base;
  padding: 20rpx; font-size: $font-base; color: var(--text-primary);
}
.char-count { font-size: $font-xs; color: var(--text-secondary); text-align: right; display: block; margin-top: 8rpx; }

.record-area { text-align: center; padding: 32rpx 0; }
.record-wave { display: flex; justify-content: center; gap: 8rpx; height: 80rpx; align-items: center; }
.wave-bar {
  width: 8rpx; height: 20rpx; background: var(--text-placeholder); border-radius: 4rpx;
  .active & { background: $primary-color; animation: wave 1s ease-in-out infinite; }
}
@keyframes wave { 0%,100%{height:20rpx} 50%{height:60rpx} }
.record-time { font-size: $font-xl; font-weight: bold; color: var(--text-primary); margin: 16rpx 0; display: block; }
.record-btns { margin: 24rpx 0; }
.record-btn {
  display: inline-block; padding: 20rpx 80rpx; border-radius: 48rpx; font-size: $font-base;
  &.start { background: $primary-color; color: #fff; }
  &.stop { background: $danger-color; color: #fff; }
  &:active { opacity: 0.8; }
}
.record-hint { font-size: $font-xs; color: var(--text-secondary); display: block; margin-top: 16rpx; }
.upload-alt { text-align: center; margin-top: 24rpx; }
.upload-btn {
  display: inline-block; padding: 16rpx 40rpx; border: 2rpx solid $primary-color;
  border-radius: $radius-base; color: $primary-color; font-size: $font-sm;
  &:active { background: rgba(7,193,96,0.05); }
}

.upload-area {
  display: flex; flex-direction: column; align-items: center; padding: 60rpx;
  background: var(--card-bg); border-radius: $radius-base; border: 2rpx dashed var(--border-color);
  &:active { border-color: $primary-color; }
}
.upload-icon { font-size: 80rpx; margin-bottom: 16rpx; }
.upload-text { font-size: $font-base; color: var(--text-primary); }
.upload-hint { font-size: $font-sm; color: var(--text-secondary); margin-top: 8rpx; }

.file-preview {
  display: flex; align-items: center; padding: 16rpx 20rpx;
  background: var(--card-bg); border-radius: $radius-base; margin-top: 12rpx;
}
.file-name { flex: 1; font-size: $font-sm; color: var(--text-primary); }
.file-size { font-size: $font-xs; color: var(--text-secondary); }

.group-list { display: flex; flex-direction: column; gap: 8rpx; }
.group-item {
  display: flex; align-items: center; padding: 20rpx; background: var(--card-bg);
  border-radius: $radius-base; border: 2rpx solid transparent;
  &.active { border-color: $primary-color; }
  &:active { background: var(--bg-color); }
}
.group-avatar {
  width: 64rpx; height: 64rpx; border-radius: $radius-base; background: #4A90D9;
  display: flex; align-items: center; justify-content: center;
  font-size: 28rpx; color: #fff; font-weight: bold; margin-right: 16rpx;
}
.group-name { flex: 1; font-size: $font-base; color: var(--text-primary); }
.group-check { font-size: 28rpx; color: $primary-color; font-weight: bold; }

.submit-area { padding: 32rpx 30rpx; }
.submit-btn {
  display: flex; align-items: center; justify-content: center; height: 96rpx;
  background: $primary-color; border-radius: $radius-base; color: #fff;
  font-size: $font-lg; font-weight: bold; gap: 12rpx;
  &.disabled { opacity: 0.5; pointer-events: none; }
  &:active { opacity: 0.8; }
}
.loading-icon { animation: spin 1s linear infinite; }
@keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }

.result-section { margin-top: 24rpx; }
.result-card { background: var(--card-bg); border-radius: $radius-base; padding: 24rpx; }
.result-row { padding: 12rpx 0; border-bottom: 1rpx solid var(--border-color); &:last-child { border-bottom: none; } }
.result-label { font-size: $font-sm; color: var(--text-secondary); display: block; margin-bottom: 6rpx; }
.result-value { font-size: $font-base; color: var(--text-primary); line-height: 1.6; }
.transcript { font-size: $font-sm; color: var(--text-secondary); max-height: 200rpx; overflow-y: auto; }

.fade-in { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from{opacity:0;transform:translateY(10rpx)} to{opacity:1;transform:none} }
</style>
