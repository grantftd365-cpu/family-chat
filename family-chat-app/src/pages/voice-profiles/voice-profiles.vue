<template>
  <view class="voice-page">
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-content">
        <view class="nav-back" @tap="goBack"><text>‹</text></view>
        <text class="nav-title">语音音色管理</text>
        <view class="nav-action" @tap="showAddVoice = true"><text>➕</text></view>
      </view>
    </view>

    <scroll-view scroll-y class="voice-list">
      <view class="diagnostic-card">
        <view>
          <text class="diagnostic-title">数字人语音能力</text>
          <text class="diagnostic-desc">Edge-TTS 可直接说话；真声音克隆需要服务器配置 ElevenLabs Key</text>
        </view>
        <text class="diagnostic-badge" :class="{ ok: cloneAvailable }">{{ cloneAvailable ? '克隆可用' : '克隆未启用' }}</text>
      </view>

      <!-- 可用声音列表 -->
      <view class="section-title">
        <text>可用声音</text>
      </view>
      <view class="voice-grid">
        <view
          v-for="voice in availableVoices"
          :key="voice.id"
          class="voice-card"
          :class="{ active: selectedVoice === voice.id }"
          @tap="selectVoice(voice)"
          @longpress="previewVoice(voice)"
        >
          <view class="voice-avatar" :class="voice.gender">
            <text>{{ voice.gender === 'male' ? '👨' : '👩' }}</text>
          </view>
          <text class="voice-name">{{ voice.name }}</text>
          <text class="voice-desc">{{ voice.desc }}</text>
          <view v-if="selectedVoice === voice.id" class="voice-check">
            <text>✓</text>
          </view>
        </view>
      </view>

      <!-- 自定义音色 -->
      <view class="section-title">
        <text>自定义音色</text>
      </view>

      <view v-if="customProfiles.length === 0" class="empty-state">
        <text class="empty-icon">🎤</text>
        <text class="empty-text">暂无自定义音色</text>
        <text class="empty-hint">点击右上角添加录音或上传音频</text>
      </view>

      <view v-for="profile in customProfiles" :key="profile.id" class="profile-card">
        <view class="profile-header">
          <view class="profile-avatar" :class="profile.gender">
            <text>{{ profile.gender === 'male' ? '👨' : '👩' }}</text>
          </view>
          <view class="profile-info">
            <text class="profile-name">{{ profile.name }}</text>
            <text class="profile-voice">匹配声音: {{ profile.edge_voice_name }}</text>
            <text v-if="profile.duration" class="profile-duration">{{ Math.round(profile.duration) }}秒</text>
          </view>
          <view class="profile-actions">
            <view class="action-btn" @tap="previewCustomVoice(profile)">
              <text>▶️</text>
            </view>
            <view class="action-btn" @tap="deleteProfile(profile)">
              <text>🗑️</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 数字人音色分配 -->
      <view class="section-title">
        <text>数字人音色分配</text>
      </view>

      <view v-for="agent in agents" :key="agent.id" class="assign-card">
        <view class="assign-header">
          <text class="assign-avatar">{{ agent.avatar || '🤖' }}</text>
          <text class="assign-name">{{ agent.name }}</text>
          <text class="assign-voice">{{ getAgentVoiceName(agent.id) }}</text>
        </view>
        <view class="assign-btn" @tap="showAssignVoice(agent)">
          <text>更换音色</text>
        </view>
      </view>
    </scroll-view>

    <!-- 添加音色弹窗 -->
    <view v-if="showAddVoice" class="modal-mask" @tap="showAddVoice = false">
      <view class="modal-box" @tap.stop>
        <text class="modal-title">添加音色</text>

        <!-- 录音 -->
        <view class="add-option" @tap="startRecordVoice">
          <text class="option-icon">🎙️</text>
          <view class="option-info">
            <text class="option-title">录音</text>
            <text class="option-desc">录制你的声音作为数字人音色</text>
          </view>
        </view>

        <!-- 上传音频 -->
        <view class="add-option" @tap="uploadAudio">
          <text class="option-icon">📁</text>
          <view class="option-info">
            <text class="option-title">上传音频</text>
            <text class="option-desc">上传 MP3/WAV 等音频文件</text>
          </view>
        </view>

        <!-- 从视频提取 -->
        <view class="add-option" @tap="uploadVideoForVoice">
          <text class="option-icon">🎬</text>
          <view class="option-info">
            <text class="option-title">从视频提取</text>
            <text class="option-desc">从视频中提取说话人的音色</text>
          </view>
        </view>

        <view class="modal-cancel" @tap="showAddVoice = false">
          <text>取消</text>
        </view>
      </view>
    </view>

    <!-- 录音弹窗 -->
    <view v-if="showRecording" class="modal-mask" @tap="showRecording = false">
      <view class="record-modal" @tap.stop>
        <text class="record-title">录制音色</text>
        <input v-model="recordName" placeholder="输入音色名称（如：我的声音）" class="record-name-input" />

        <view class="engine-switch">
          <view class="engine-option" :class="{ active: voiceEngine === 'edge-tts' }" @tap="voiceEngine = 'edge-tts'">
            <text class="engine-title">快速匹配</text>
            <text class="engine-desc">分析声线，匹配中文 TTS</text>
          </view>
          <view class="engine-option" :class="{ active: voiceEngine === 'elevenlabs', disabled: !cloneAvailable }" @tap="selectCloneEngine">
            <text class="engine-title">声音克隆</text>
            <text class="engine-desc">需要 1 分钟以上录音</text>
          </view>
        </view>

        <view class="record-area">
          <view class="record-wave" :class="{ active: isRecording }">
            <view v-for="i in 5" :key="i" class="wave-bar" :style="{ animationDelay: i * 0.1 + 's' }"></view>
          </view>
          <text class="record-time">{{ recordTime }}s</text>
        </view>

        <view class="record-btns">
          <view v-if="!isRecording" class="record-btn start" @tap="startRecord">
            <text>开始录音</text>
          </view>
          <view v-else class="record-btn stop" @tap="stopRecord">
            <text>停止录音</text>
          </view>
        </view>

        <text class="record-hint">快速匹配建议10-30秒；声音克隆建议至少1分钟清晰语音</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import * as api from '../../utils/api'

const statusBarHeight = ref(44)
const availableVoices = ref([])
const customProfiles = ref([])
const agents = ref([])
const selectedVoice = ref('')
const showAddVoice = ref(false)
const showRecording = ref(false)
const voiceEngine = ref('edge-tts')
const voiceDiagnostics = ref(null)
const isRecording = ref(false)
const recordName = ref('')
const recordTime = ref(0)
const agentVoiceMap = ref({})
let recorderManager = null
let recordTimer = null

const cloneAvailable = computed(() => !!voiceDiagnostics.value?.clone?.available)

onLoad(() => {
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  loadData()
  initRecorder()
})

async function loadData() {
  try {
    const [voicesRes, profilesRes, agentsRes] = await Promise.all([
      api.getAvailableVoices(),
      api.getVoiceProfiles(),
      api.getAgents()
    ])
    availableVoices.value = voicesRes.voices || []
    customProfiles.value = profilesRes.profiles || []
    agents.value = Array.isArray(agentsRes) ? agentsRes : (agentsRes.agents || [])
    api.getVoiceDiagnostics()
      .then(res => { voiceDiagnostics.value = res })
      .catch(() => { voiceDiagnostics.value = null })

    // 加载每个 agent 的音色映射
    for (const agent of agents.value) {
      try {
        const res = await api.getAgentVoice(agent.id)
        if (res.profile) {
          agentVoiceMap.value[agent.id] = res.profile
        }
      } catch (e) {}
    }
  } catch (e) {
    console.error('加载数据失败:', e)
  }
}

function initRecorder() {
  recorderManager = uni.getRecorderManager()
  recorderManager.onStop(async (res) => {
    if (isRecording.value) return
    clearInterval(recordTimer)
    if (recordTime.value < 3) {
      uni.showToast({ title: '录音太短，请至少录3秒', icon: 'none' })
      return
    }
    // 上传录音
    uni.showLoading({ title: '分析音色中...' })
    try {
      const profile = await api.uploadVoiceProfile(recordName.value || '我的声音', res.tempFilePath, '', voiceEngine.value)
      customProfiles.value.push(profile)
      showRecording.value = false
      recordName.value = ''
      voiceEngine.value = 'edge-tts'
      uni.showToast({ title: '音色创建成功', icon: 'success' })
    } catch (e) {
      uni.showToast({ title: '创建失败: ' + (e.message || '未知错误'), icon: 'none' })
    } finally {
      uni.hideLoading()
    }
  })
  recorderManager.onError((err) => {
    isRecording.value = false
    clearInterval(recordTimer)
    uni.showToast({ title: '录音失败', icon: 'none' })
  })
}

function selectVoice(voice) {
  selectedVoice.value = voice.id
}

function previewVoice(voice) {
  // 使用 edge-tts 合成预览
  uni.showLoading({ title: '生成预览...' })
  api.synthesizeVoicePreview('你好，我是' + voice.name, voice.id)
    .then(() => {
      uni.hideLoading()
    })
    .catch(() => {
      uni.hideLoading()
      uni.showToast({ title: '预览失败', icon: 'none' })
    })
}

function previewCustomVoice(profile) {
  uni.showLoading({ title: '生成预览...' })
  api.synthesizeVoicePreview('你好，我是' + profile.name, '', profile.id)
    .then(() => uni.hideLoading())
    .catch(() => {
      uni.hideLoading()
      uni.showToast({ title: '预览失败', icon: 'none' })
    })
}

async function deleteProfile(profile) {
  uni.showModal({
    title: '确认删除',
    content: `确定删除音色"${profile.name}"？`,
    success: async (res) => {
      if (res.confirm) {
        try {
          await api.deleteVoiceProfile(profile.id)
          customProfiles.value = customProfiles.value.filter(p => p.id !== profile.id)
          uni.showToast({ title: '已删除', icon: 'success' })
        } catch (e) {
          uni.showToast({ title: '删除失败', icon: 'none' })
        }
      }
    }
  })
}

function startRecordVoice() {
  showAddVoice.value = false
  showRecording.value = true
  recordTime.value = 0
  voiceEngine.value = 'edge-tts'
}

function selectCloneEngine() {
  if (!cloneAvailable.value) {
    uni.showToast({ title: '服务器未配置声音克隆 Key', icon: 'none' })
    return
  }
  voiceEngine.value = 'elevenlabs'
}

function chooseVoiceEngine() {
  return new Promise(resolve => {
    if (!cloneAvailable.value) {
      resolve('edge-tts')
      return
    }
    uni.showActionSheet({
      itemList: ['快速匹配音色', '声音克隆（需1分钟以上）'],
      success: res => resolve(res.tapIndex === 1 ? 'elevenlabs' : 'edge-tts'),
      fail: () => resolve('edge-tts')
    })
  })
}

function startRecord() {
  isRecording.value = true
  recordTime.value = 0
  recorderManager.start({
    format: 'mp3',
    sampleRate: 16000,
    numberOfChannels: 1,
    duration: 60000
  })
  recordTimer = setInterval(() => {
    recordTime.value++
    if (recordTime.value >= 60) stopRecord()
  }, 1000)
}

function stopRecord() {
  isRecording.value = false
  recorderManager.stop()
}

async function uploadAudio() {
  showAddVoice.value = false
  const engine = await chooseVoiceEngine()
  uni.chooseImage({
    count: 1,
    extension: ['mp3', 'wav', 'ogg', 'm4a'],
    success: async (res) => {
      const filePath = res.tempFiles[0].path || res.tempFilePaths[0]
      uni.showLoading({ title: '分析音色中...' })
      try {
        const profile = await api.uploadVoiceProfile('上传的音色', filePath, '', engine)
        customProfiles.value.push(profile)
        uni.showToast({ title: '创建成功', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: '创建失败', icon: 'none' })
      } finally {
        uni.hideLoading()
      }
    }
  })
}

async function uploadVideoForVoice() {
  showAddVoice.value = false
  const engine = await chooseVoiceEngine()
  uni.chooseVideo({
    count: 1,
    success: async (res) => {
      uni.showLoading({ title: '提取音色中...' })
      try {
        const profile = await api.uploadVoiceProfile('视频提取的音色', res.tempFilePath, '', engine)
        customProfiles.value.push(profile)
        uni.showToast({ title: '提取成功', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: '提取失败', icon: 'none' })
      } finally {
        uni.hideLoading()
      }
    }
  })
}

function showAssignVoice(agent) {
  const voices = [...availableVoices.value.map(v => v.name), ...customProfiles.value.map(p => p.name)]
  uni.showActionSheet({
    itemList: voices,
    success: async (res) => {
      const idx = res.tapIndex
      let profileId = ''
      if (idx < availableVoices.value.length) {
        // 选择预设声音 - 创建一个 profile
        const voice = availableVoices.value[idx]
        try {
          const profile = await api.createVoiceProfile(agent.name + '的声音', voice.id)
          profileId = profile.id
        } catch (e) {
          uni.showToast({ title: '创建失败', icon: 'none' })
          return
        }
      } else {
        const customIdx = idx - availableVoices.value.length
        profileId = customProfiles.value[customIdx]?.id
      }
      if (profileId) {
        try {
          await api.assignVoiceToAgent(agent.id, profileId)
          agentVoiceMap.value[agent.id] = customProfiles.value.find(p => p.id === profileId) ||
            { name: availableVoices.value.find(v => v.id === profileId)?.name || '未知' }
          uni.showToast({ title: '分配成功', icon: 'success' })
        } catch (e) {
          uni.showToast({ title: '分配失败', icon: 'none' })
        }
      }
    }
  })
}

function getAgentVoiceName(agentId) {
  const v = agentVoiceMap.value[agentId]
  return v ? v.name || v.edge_voice_name || '已配置' : '使用默认声音'
}

function goBack() { uni.navigateBack() }
</script>

<style lang="scss" scoped>
.voice-page { min-height: 100vh; background: linear-gradient(180deg, #101828 0%, #18233a 30%, #f5f7fb 30%, #f5f7fb 100%); }
.nav-bar { background: transparent; }
.nav-content { display: flex; align-items: center; height: 88rpx; padding: 0 30rpx; }
.nav-back { font-size: 48rpx; color: #fff; padding-right: 16rpx; }
.nav-title { flex: 1; text-align: center; font-size: $font-lg; font-weight: bold; color: #fff; }
.nav-action { font-size: 36rpx; padding: 8rpx; }
.voice-list { height: calc(100vh - 88rpx); }
.section-title { padding: 24rpx 30rpx 12rpx; font-size: $font-sm; color: var(--text-secondary); font-weight: 500; }

.diagnostic-card {
  margin: 22rpx 24rpx 8rpx;
  padding: 26rpx;
  border-radius: 32rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18rpx;
  background: rgba(255,255,255,0.94);
  box-shadow: 0 18rpx 50rpx rgba(16,24,40,0.14);
  border: 1rpx solid rgba(255,255,255,0.68);
}
.diagnostic-title { display: block; font-size: 30rpx; font-weight: 800; color: #101828; }
.diagnostic-desc { display: block; margin-top: 8rpx; font-size: 22rpx; line-height: 1.45; color: #667085; }
.diagnostic-badge {
  flex-shrink: 0;
  padding: 10rpx 16rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  color: #b42318;
  background: #fff1f3;
  &.ok { color: #027a48; background: #ecfdf3; }
}

.voice-grid { display: flex; flex-wrap: wrap; padding: 0 20rpx; gap: 16rpx; }
.voice-card {
  width: calc(33.33% - 12rpx); background: var(--card-bg); border-radius: $radius-base;
  padding: 20rpx 12rpx; text-align: center; position: relative;
  border: 2rpx solid transparent; transition: all 0.2s;
  &.active { border-color: $primary-color; background: rgba(7,193,96,0.05); }
  &:active { transform: scale(0.96); }
}
.voice-avatar {
  width: 80rpx; height: 80rpx; border-radius: 50%; margin: 0 auto 12rpx;
  display: flex; align-items: center; justify-content: center; font-size: 40rpx;
  &.male { background: #E3F2FD; }
  &.female { background: #FCE4EC; }
}
.voice-name { font-size: $font-sm; font-weight: 500; color: var(--text-primary); display: block; }
.voice-desc { font-size: $font-xs; color: var(--text-secondary); display: block; margin-top: 4rpx; }
.voice-check {
  position: absolute; top: 8rpx; right: 8rpx; width: 36rpx; height: 36rpx;
  background: $primary-color; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; font-size: 20rpx; color: #fff;
}

.empty-state { display: flex; flex-direction: column; align-items: center; padding: 60rpx 0; }
.empty-icon { font-size: 80rpx; margin-bottom: 16rpx; }
.empty-text { font-size: $font-base; color: var(--text-secondary); }
.empty-hint { font-size: $font-sm; color: var(--text-placeholder); margin-top: 8rpx; }

.profile-card { background: var(--card-bg); margin: 0 20rpx 12rpx; border-radius: $radius-base; padding: 20rpx; }
.profile-header { display: flex; align-items: center; }
.profile-avatar {
  width: 72rpx; height: 72rpx; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; font-size: 36rpx; margin-right: 16rpx;
  &.male { background: #E3F2FD; }
  &.female { background: #FCE4EC; }
}
.profile-info { flex: 1; }
.profile-name { font-size: $font-base; font-weight: 500; color: var(--text-primary); display: block; }
.profile-voice { font-size: $font-xs; color: var(--text-secondary); display: block; margin-top: 4rpx; }
.profile-duration { font-size: $font-xs; color: var(--text-placeholder); display: block; }
.profile-actions { display: flex; gap: 16rpx; }
.action-btn { width: 64rpx; height: 64rpx; display: flex; align-items: center; justify-content: center; font-size: 28rpx; &:active { opacity: 0.7; } }

.assign-card { background: var(--card-bg); margin: 0 20rpx 12rpx; border-radius: $radius-base; padding: 20rpx; }
.assign-header { display: flex; align-items: center; gap: 12rpx; margin-bottom: 12rpx; }
.assign-avatar { font-size: 36rpx; }
.assign-name { font-size: $font-base; font-weight: 500; color: var(--text-primary); flex: 1; }
.assign-voice { font-size: $font-sm; color: $primary-color; }
.assign-btn {
  text-align: center; padding: 12rpx; background: var(--bg-color);
  border-radius: $radius-base; font-size: $font-sm; color: $primary-color;
  &:active { opacity: 0.8; }
}

/* 弹窗 */
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-box { width: 640rpx; background: var(--card-bg); border-radius: $radius-lg; padding: 40rpx; }
.modal-title { font-size: $font-lg; font-weight: bold; color: var(--text-primary); text-align: center; margin-bottom: 32rpx; display: block; }
.add-option {
  display: flex; align-items: center; padding: 24rpx; background: var(--bg-color);
  border-radius: $radius-base; margin-bottom: 16rpx;
  &:active { opacity: 0.8; }
}
.option-icon { font-size: 48rpx; margin-right: 20rpx; }
.option-info { flex: 1; }
.option-title { font-size: $font-base; font-weight: 500; color: var(--text-primary); display: block; }
.option-desc { font-size: $font-sm; color: var(--text-secondary); display: block; margin-top: 4rpx; }
.modal-cancel { text-align: center; padding: 24rpx; font-size: $font-base; color: var(--text-secondary); margin-top: 16rpx; }

.record-modal { width: 640rpx; background: var(--card-bg); border-radius: $radius-lg; padding: 40rpx; text-align: center; }
.record-title { font-size: $font-lg; font-weight: bold; color: var(--text-primary); margin-bottom: 24rpx; display: block; }
.record-name-input {
  height: 80rpx; background: var(--bg-color); border-radius: $radius-base;
  padding: 0 24rpx; font-size: $font-base; margin-bottom: 32rpx; text-align: left; color: var(--text-primary);
}
.engine-switch { display: flex; gap: 14rpx; margin-bottom: 26rpx; }
.engine-option {
  flex: 1;
  padding: 18rpx;
  border-radius: 22rpx;
  background: #f8fafc;
  border: 2rpx solid transparent;
  text-align: left;
  &.active { border-color: #12b76a; background: #ecfdf3; }
  &.disabled { opacity: 0.52; }
}
.engine-title { display: block; font-size: 26rpx; font-weight: 800; color: #101828; }
.engine-desc { display: block; margin-top: 6rpx; font-size: 20rpx; color: #667085; line-height: 1.35; }
.record-area { margin: 32rpx 0; }
.record-wave { display: flex; justify-content: center; gap: 8rpx; height: 80rpx; align-items: center; }
.wave-bar {
  width: 8rpx; height: 20rpx; background: var(--text-placeholder); border-radius: 4rpx;
  .active & { background: $primary-color; animation: wave 1s ease-in-out infinite; }
}
@keyframes wave { 0%,100%{height:20rpx} 50%{height:60rpx} }
.record-time { font-size: $font-xl; font-weight: bold; color: var(--text-primary); margin-top: 16rpx; display: block; }
.record-btns { margin: 24rpx 0; }
.record-btn {
  display: inline-block; padding: 16rpx 60rpx; border-radius: 40rpx; font-size: $font-base;
  &.start { background: $primary-color; color: #fff; }
  &.stop { background: $danger-color; color: #fff; }
  &:active { opacity: 0.8; }
}
.record-hint { font-size: $font-xs; color: var(--text-secondary); display: block; margin-top: 16rpx; }
</style>
