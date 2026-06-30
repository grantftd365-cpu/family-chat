<template>
  <view class="agents-page">
    <view class="hero" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="hero-top">
        <view class="back-btn" @tap="goBack">‹</view>
        <view>
          <text class="hero-title">数字人管理</text>
          <text class="hero-subtitle">让每个家人都持续成长，而不是普通机器人</text>
        </view>
        <view class="refresh-btn" @tap="loadAgents">↻</view>
      </view>
      <view class="stats-card">
        <view class="stat-item">
          <text class="stat-num">{{ agents.length }}</text>
          <text class="stat-label">数字人</text>
        </view>
        <view class="stat-item">
          <text class="stat-num">{{ activeVoiceCount }}</text>
          <text class="stat-label">已绑定语音</text>
        </view>
        <view class="stat-item">
          <text class="stat-num">{{ refinedCount }}</text>
          <text class="stat-label">已炼化</text>
        </view>
      </view>
    </view>

    <scroll-view scroll-y class="agent-list">
      <view v-if="loading" class="loading-card">加载数字人中...</view>
      <view v-else-if="!agents.length" class="empty-card">
        <text class="empty-icon">🧬</text>
        <text class="empty-title">还没有数字人</text>
        <text class="empty-desc">先去“炼化数字人”创建或完善你的家庭成员</text>
      </view>

      <view v-for="agent in agents" :key="agent.id" class="agent-card">
        <view class="agent-avatar-wrap">
          <text class="agent-avatar">{{ agent.avatar || '🤖' }}</text>
          <view class="pulse-dot" />
        </view>
        <view class="agent-main">
          <view class="agent-header">
            <text class="agent-name">{{ agent.name }}</text>
            <text class="agent-tag">{{ agent.identity?.role_in_family || '家庭数字人' }}</text>
          </view>
          <text class="agent-desc">{{ agent.backstory || agent.identity?.self_description || '还需要继续炼化他的经历、认知和说话方式' }}</text>
          <view class="agent-traits">
            <text v-for="trait in topTraits(agent)" :key="trait" class="trait-chip">{{ trait }}</text>
          </view>
          <view class="agent-actions">
            <button class="action-btn primary" @tap="openEdit(agent)">编辑</button>
            <button class="action-btn" @tap="goRefine(agent)">炼化</button>
            <button class="action-btn" @tap="goVoice(agent)">语音</button>
            <button class="action-btn danger" @tap="confirmDelete(agent)">删除</button>
          </view>
        </view>
      </view>
    </scroll-view>

    <view v-if="showEditor" class="modal-mask" @tap="closeEditor">
      <view class="editor-card" @tap.stop>
        <view class="editor-head">
          <text class="editor-title">编辑数字人</text>
          <text class="editor-close" @tap="closeEditor">×</text>
        </view>
        <scroll-view scroll-y class="editor-body">
          <label class="field-label">名字</label>
          <input v-model="form.name" class="field-input" placeholder="比如：老婆" />
          <label class="field-label">头像 Emoji</label>
          <input v-model="form.avatar" class="field-input" placeholder="比如：🌶️" />
          <label class="field-label">背景故事</label>
          <textarea v-model="form.backstory" class="field-textarea" placeholder="她是谁、做什么、经历和家庭角色" />
          <label class="field-label">说话风格</label>
          <textarea v-model="form.speaking_style" class="field-textarea" placeholder="比如：东北人，直接、泼辣、关心家人" />
          <label class="field-label">性格标签（逗号分隔）</label>
          <input v-model="form.traitsText" class="field-input" placeholder="沉稳, 有思想, 数字化出海" />
          <label class="field-label">兴趣/专业（逗号分隔）</label>
          <input v-model="form.interestsText" class="field-input" placeholder="SAP, ERP, APO, 供应链" />
          <label class="field-label">口头禅（逗号分隔）</label>
          <input v-model="form.catchphrasesText" class="field-input" placeholder="我直说哈, 这事儿吧" />
          <label class="switch-row">
            <text>允许主动联系</text>
            <switch :checked="form.proactiveEnabled" @change="form.proactiveEnabled = $event.detail.value" />
          </label>
        </scroll-view>
        <view class="editor-actions">
          <button class="cancel-btn" @tap="closeEditor">取消</button>
          <button class="save-btn" :disabled="saving" @tap="saveAgent">{{ saving ? '保存中...' : '保存' }}</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import * as api from '../../utils/api'

const statusBarHeight = ref(44)
const loading = ref(false)
const saving = ref(false)
const agents = ref([])
const voiceMap = ref({})
const showEditor = ref(false)
const editingAgentId = ref('')
const form = ref(emptyForm())

const activeVoiceCount = computed(() => Object.values(voiceMap.value).filter(Boolean).length)
const refinedCount = computed(() => agents.value.filter(agent => (agent.soul_values || []).length || agent.identity?.self_description).length)

onShow(() => {
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  loadAgents()
})

function emptyForm() {
  return {
    name: '',
    avatar: '',
    backstory: '',
    speaking_style: '',
    traitsText: '',
    interestsText: '',
    catchphrasesText: '',
    proactiveEnabled: true,
  }
}

function splitTags(value) {
  return String(value || '')
    .split(/[，,\n]/)
    .map(item => item.trim())
    .filter(Boolean)
}

function topTraits(agent) {
  const traits = agent.traits || []
  if (traits.length) return traits.slice(0, 4)
  const values = agent.soul_values || []
  return values.slice(0, 4)
}

async function loadAgents() {
  loading.value = true
  try {
    const list = await api.getAgents()
    agents.value = Array.isArray(list) ? list : []
    const voiceEntries = await Promise.all(agents.value.map(async agent => {
      try {
        const result = await api.getAgentVoice(agent.id)
        return [agent.id, result?.profile || null]
      } catch (error) {
        return [agent.id, null]
      }
    }))
    voiceMap.value = Object.fromEntries(voiceEntries)
  } catch (error) {
    uni.showToast({ title: '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

async function openEdit(agent) {
  editingAgentId.value = agent.id
  showEditor.value = true
  try {
    const detail = await api.getAgent(agent.id)
    form.value = {
      name: detail.name || agent.name || '',
      avatar: detail.avatar || agent.avatar || '',
      backstory: detail.backstory || '',
      speaking_style: detail.speaking_style || '',
      traitsText: (detail.traits || []).join('，'),
      interestsText: (detail.interests || []).join('，'),
      catchphrasesText: (detail.catchphrases || []).join('，'),
      proactiveEnabled: detail.proactive_config?.enabled !== false,
    }
  } catch (error) {
    form.value = {
      ...emptyForm(),
      name: agent.name || '',
      avatar: agent.avatar || '',
    }
  }
}

function closeEditor() {
  showEditor.value = false
  editingAgentId.value = ''
  form.value = emptyForm()
}

async function saveAgent() {
  if (!editingAgentId.value || !form.value.name.trim()) {
    uni.showToast({ title: '名字不能为空', icon: 'none' })
    return
  }
  saving.value = true
  try {
    await api.updateAgent(editingAgentId.value, {
      name: form.value.name.trim(),
      avatar: form.value.avatar.trim() || '🤖',
      backstory: form.value.backstory.trim(),
      speaking_style: form.value.speaking_style.trim(),
      traits: splitTags(form.value.traitsText),
      interests: splitTags(form.value.interestsText),
      catchphrases: splitTags(form.value.catchphrasesText),
      proactive_config: { enabled: form.value.proactiveEnabled },
    })
    uni.showToast({ title: '已保存', icon: 'success' })
    closeEditor()
    loadAgents()
  } catch (error) {
    uni.showToast({ title: error.message || '保存失败', icon: 'none' })
  } finally {
    saving.value = false
  }
}

function confirmDelete(agent) {
  uni.showModal({
    title: `删除 ${agent.name}?`,
    content: '会删除数字人配置、记忆和音色绑定，历史聊天记录会保留。',
    confirmText: '删除',
    confirmColor: '#FF4D67',
    success: async result => {
      if (!result.confirm) return
      try {
        await api.deleteAgent(agent.id)
        uni.showToast({ title: '已删除', icon: 'success' })
        loadAgents()
      } catch (error) {
        uni.showToast({ title: error.message || '删除失败', icon: 'none' })
      }
    }
  })
}

function goRefine(agent) {
  uni.navigateTo({ url: `/pages/refine/refine?agentId=${agent.id}` })
}

function goVoice(agent) {
  uni.navigateTo({ url: `/pages/voice-profiles/voice-profiles?agentId=${agent.id}` })
}

function goBack() {
  uni.navigateBack()
}
</script>

<style lang="scss" scoped>
.agents-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #101828 0%, #18233a 34%, #f5f7fb 34%, #f5f7fb 100%);
}

.hero {
  padding: 0 28rpx 28rpx;
  color: #ffffff;
}

.hero-top {
  height: 96rpx;
  display: flex;
  align-items: center;
  gap: 22rpx;
}

.back-btn,
.refresh-btn {
  width: 68rpx;
  height: 68rpx;
  border-radius: 24rpx;
  background: rgba(255,255,255,0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44rpx;
  backdrop-filter: blur(16rpx);
}

.refresh-btn { margin-left: auto; font-size: 34rpx; }

.hero-title {
  display: block;
  font-size: 40rpx;
  font-weight: 800;
  letter-spacing: 1rpx;
}

.hero-subtitle {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: rgba(255,255,255,0.72);
}

.stats-card {
  margin-top: 20rpx;
  padding: 26rpx;
  border-radius: 34rpx;
  background: rgba(255,255,255,0.14);
  border: 1rpx solid rgba(255,255,255,0.18);
  display: flex;
  justify-content: space-around;
  backdrop-filter: blur(20rpx);
}

.stat-item { display: flex; flex-direction: column; align-items: center; gap: 6rpx; }
.stat-num { font-size: 42rpx; font-weight: 800; }
.stat-label { font-size: 22rpx; color: rgba(255,255,255,0.72); }

.agent-list { height: calc(100vh - 330rpx); padding: 24rpx 24rpx 60rpx; box-sizing: border-box; }

.loading-card,
.empty-card,
.agent-card {
  border-radius: 34rpx;
  background: rgba(255,255,255,0.92);
  box-shadow: 0 18rpx 50rpx rgba(16,24,40,0.12);
  border: 1rpx solid rgba(255,255,255,0.7);
}

.loading-card { padding: 40rpx; text-align: center; color: #667085; }
.empty-card { padding: 80rpx 30rpx; display: flex; flex-direction: column; align-items: center; gap: 14rpx; }
.empty-icon { font-size: 76rpx; }
.empty-title { font-size: 32rpx; font-weight: 700; color: #101828; }
.empty-desc { font-size: 24rpx; color: #667085; text-align: center; }

.agent-card {
  display: flex;
  gap: 22rpx;
  padding: 26rpx;
  margin-bottom: 22rpx;
}

.agent-avatar-wrap { position: relative; flex-shrink: 0; }
.agent-avatar {
  width: 92rpx;
  height: 92rpx;
  border-radius: 30rpx;
  background: linear-gradient(135deg, #eef4ff, #ecfdf3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 52rpx;
}
.pulse-dot {
  position: absolute;
  right: -2rpx;
  bottom: -2rpx;
  width: 22rpx;
  height: 22rpx;
  border-radius: 50%;
  background: #12b76a;
  border: 4rpx solid #fff;
}

.agent-main { flex: 1; min-width: 0; }
.agent-header { display: flex; align-items: center; gap: 12rpx; margin-bottom: 8rpx; }
.agent-name { font-size: 34rpx; font-weight: 800; color: #101828; }
.agent-tag { padding: 6rpx 12rpx; border-radius: 999rpx; background: #eef4ff; color: #3538cd; font-size: 20rpx; }
.agent-desc { font-size: 24rpx; line-height: 1.45; color: #667085; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.agent-traits { display: flex; flex-wrap: wrap; gap: 10rpx; margin-top: 16rpx; }
.trait-chip { padding: 8rpx 14rpx; border-radius: 999rpx; background: #f2f4f7; color: #475467; font-size: 20rpx; }
.agent-actions { display: flex; gap: 10rpx; margin-top: 20rpx; flex-wrap: wrap; }
.action-btn { margin: 0; height: 58rpx; line-height: 58rpx; padding: 0 20rpx; border-radius: 18rpx; font-size: 22rpx; color: #344054; background: #f2f4f7; }
.action-btn::after, .save-btn::after, .cancel-btn::after { border: none; }
.action-btn.primary { color: #fff; background: linear-gradient(135deg, #12b76a, #00a3ff); }
.action-btn.danger { color: #ff4d67; background: #fff1f3; }

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15,23,42,0.5);
  display: flex;
  align-items: flex-end;
  z-index: 999;
}

.editor-card {
  width: 100%;
  max-height: 86vh;
  background: #ffffff;
  border-radius: 36rpx 36rpx 0 0;
  overflow: hidden;
}
.editor-head { height: 96rpx; padding: 0 28rpx; display: flex; align-items: center; justify-content: space-between; border-bottom: 1rpx solid #eef2f6; }
.editor-title { font-size: 34rpx; font-weight: 800; color: #101828; }
.editor-close { font-size: 48rpx; color: #98a2b3; }
.editor-body { max-height: 62vh; padding: 24rpx 28rpx; box-sizing: border-box; }
.field-label { display: block; margin: 18rpx 0 10rpx; color: #344054; font-size: 24rpx; font-weight: 700; }
.field-input, .field-textarea { width: 100%; box-sizing: border-box; border-radius: 22rpx; background: #f8fafc; border: 1rpx solid #eaecf0; padding: 18rpx 20rpx; font-size: 26rpx; color: #101828; }
.field-textarea { min-height: 140rpx; line-height: 1.45; }
.switch-row { margin-top: 24rpx; display: flex; align-items: center; justify-content: space-between; color: #344054; font-size: 26rpx; font-weight: 700; }
.editor-actions { padding: 20rpx 28rpx 34rpx; display: flex; gap: 16rpx; border-top: 1rpx solid #eef2f6; }
.cancel-btn, .save-btn { flex: 1; height: 76rpx; line-height: 76rpx; border-radius: 24rpx; font-size: 28rpx; }
.cancel-btn { background: #f2f4f7; color: #344054; }
.save-btn { background: linear-gradient(135deg, #12b76a, #00a3ff); color: #ffffff; }
</style>
