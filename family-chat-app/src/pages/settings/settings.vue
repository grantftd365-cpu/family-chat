<template>
  <view class="settings-page">
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-content">
        <view class="nav-back" @tap="goBack"><text>‹</text></view>
        <text class="nav-title">设置</text>
        <view class="nav-placeholder"></view>
      </view>
    </view>

    <scroll-view scroll-y class="settings-list">
      <!-- 暗黑模式 -->
      <view class="settings-group">
        <view class="settings-item">
          <text class="item-icon">🌙</text>
          <text class="item-label">深色模式</text>
          <view class="toggle" :class="{ on: isDark }" @tap="toggleDark">
            <view class="toggle-dot"></view>
          </view>
        </view>
      </view>

      <!-- 功能列表 -->
      <view class="settings-group">
        <view class="settings-item" @tap="goPage('moments')">
          <text class="item-icon">📷</text>
          <text class="item-label">朋友圈</text>
          <text class="item-arrow">›</text>
        </view>
        <view class="settings-item" @tap="goPage('favorites')">
          <text class="item-icon">⭐</text>
          <text class="item-label">我的收藏</text>
          <text class="item-arrow">›</text>
        </view>
        <view class="settings-item" @tap="goPage('refine')">
          <text class="item-icon">🧪</text>
          <text class="item-label">炼化数字人</text>
          <text class="item-arrow">›</text>
        </view>
        <view class="settings-item" @tap="goPage('voice-profiles')">
          <text class="item-icon">🎤</text>
          <text class="item-label">语音音色管理</text>
          <text class="item-arrow">›</text>
        </view>
        <view class="settings-item" @tap="showLLMConfig">
          <text class="item-icon">🤖</text>
          <text class="item-label">AI 模型配置</text>
          <text class="item-arrow">›</text>
        </view>
      </view>

      <!-- 个人信息 -->
      <view class="settings-group">
        <view class="settings-item" @tap="showEditProfile">
          <text class="item-icon">👤</text>
          <text class="item-label">编辑资料</text>
          <text class="item-arrow">›</text>
        </view>
      </view>

      <!-- 版本信息 -->
      <view class="settings-group">
        <view class="settings-item">
          <text class="item-icon">📱</text>
          <text class="item-label">版本</text>
          <text class="item-value">v2.0.0</text>
        </view>
      </view>

      <!-- 退出登录 -->
      <view class="logout-btn" @tap="handleLogout">
        <text>退出登录</text>
      </view>
    </scroll-view>

    <!-- LLM 配置弹窗 -->
    <view v-if="showLLM" class="modal-mask" @tap="showLLM = false">
      <view class="modal-box" @tap.stop>
        <text class="modal-title">🤖 AI 模型配置</text>
        <picker :range="providerNames" @change="onProviderChange">
          <view class="picker-field">
            <text>{{ providerNames[providerIdx] || '选择模型' }}</text>
            <text class="picker-arrow">▼</text>
          </view>
        </picker>
        <input v-model="llmForm.apiKey" type="password" placeholder="API Key" class="modal-input" />
        <input v-model="llmForm.model" placeholder="模型名称（如 deepseek-chat）" class="modal-input" />
        <input v-model="llmForm.baseUrl" placeholder="Base URL（可选）" class="modal-input" />
        <view class="modal-btns">
          <view class="modal-btn cancel" @tap="showLLM = false"><text>取消</text></view>
          <view class="modal-btn confirm" @tap="saveLLM"><text>保存</text></view>
        </view>
      </view>
    </view>

    <!-- 炼化弹窗 -->
    <view v-if="showRefineModal" class="modal-mask" @tap="showRefineModal = false">
      <view class="modal-box" @tap.stop>
        <text class="modal-title">🧪 炼化数字人</text>
        <text class="modal-desc">输入聊天记录或自我介绍，AI 提取性格特征</text>
        <picker :range="agentNames" @change="onAgentChange">
          <view class="picker-field">
            <text>{{ agentNames[agentIdx] || '选择数字人' }}</text>
            <text class="picker-arrow">▼</text>
          </view>
        </picker>
        <textarea v-model="refineText" placeholder="粘贴聊天记录或自我介绍..." class="modal-textarea" />
        <view class="modal-btns">
          <view class="modal-btn cancel" @tap="showRefineModal = false"><text>取消</text></view>
          <view class="modal-btn confirm" @tap="doRefine"><text>开始炼化</text></view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useUserStore } from '../../stores/user'
import { useThemeStore } from '../../stores/theme'
import * as api from '../../utils/api'

const userStore = useUserStore()
const themeStore = useThemeStore()
const statusBarHeight = ref(44)
const isDark = ref(false)
const showLLM = ref(false)
const showRefineModal = ref(false)

const providers = ['deepseek', 'openai', 'zhipu', 'qwen', 'local']
const providerNames = ['DeepSeek', 'OpenAI', '智谱AI', '通义千问', '本地模型']
const providerIdx = ref(0)
const llmForm = reactive({ apiKey: '', model: '', baseUrl: '' })

const agents = ref([])
const agentNames = ref([])
const agentIdx = ref(0)
const refineText = ref('')

onLoad(() => {
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  isDark.value = themeStore.theme === 'dark'
  loadAgents()
})

async function loadAgents() {
  try {
    const res = await api.getAgents()
    agents.value = Array.isArray(res) ? res : (res.agents || [])
    agentNames.value = agents.value.map(a => a.name)
  } catch (e) {}
}

function toggleDark() {
  themeStore.toggleTheme()
  isDark.value = themeStore.theme === 'dark'
}

function onProviderChange(e) { providerIdx.value = e.detail.value }
function onAgentChange(e) { agentIdx.value = e.detail.value }

async function showLLMConfig() {
  try {
    const cfg = await api.getLLMConfig()
    llmForm.apiKey = cfg.api_key || ''
    llmForm.model = cfg.model || ''
    llmForm.baseUrl = cfg.base_url || ''
    const idx = providers.indexOf(cfg.provider)
    if (idx >= 0) providerIdx.value = idx
  } catch (e) {}
  showLLM.value = true
}

async function saveLLM() {
  try {
    await api.updateLLMConfig({
      provider: providers[providerIdx.value],
      api_key: llmForm.apiKey,
      model: llmForm.model,
      base_url: llmForm.baseUrl
    })
    showLLM.value = false
    uni.showToast({ title: '保存成功', icon: 'success' })
  } catch (e) {
    uni.showToast({ title: '保存失败', icon: 'none' })
  }
}

function showRefine() { showRefineModal.value = true }

async function doRefine() {
  if (!refineText.value.trim()) return uni.showToast({ title: '请输入内容', icon: 'none' })
  if (!agents.value.length) return uni.showToast({ title: '暂无数字人', icon: 'none' })
  try {
    await api.refineText({
      agent_id: agents.value[agentIdx.value].id,
      text: refineText.value.trim(),
      source: 'text'
    })
    showRefineModal.value = false
    refineText.value = ''
    uni.showToast({ title: '炼化完成', icon: 'success' })
  } catch (e) {
    uni.showToast({ title: '炼化失败', icon: 'none' })
  }
}

function showEditProfile() {
  uni.showToast({ title: '编辑资料', icon: 'none' })
}

function goPage(name) {
  const routes = {
    moments: '/pages/moments/moments',
    favorites: '/pages/favorites/favorites',
    refine: '/pages/refine/refine',
    'voice-profiles': '/pages/voice-profiles/voice-profiles'
  }
  const url = routes[name]
  if (url) uni.navigateTo({ url })
}

function handleLogout() {
  uni.showModal({
    title: '提示',
    content: '确定退出登录？',
    success: (res) => {
      if (res.confirm) userStore.logout()
    }
  })
}

function goBack() { uni.navigateBack() }
</script>

<style lang="scss" scoped>
.settings-page { min-height: 100vh; background: var(--bg-color); }
.nav-bar { background: $primary-color; }
.nav-content { display: flex; align-items: center; height: 88rpx; padding: 0 30rpx; }
.nav-back { font-size: 48rpx; color: #fff; padding-right: 16rpx; }
.nav-title { flex: 1; text-align: center; font-size: $font-lg; font-weight: bold; color: #fff; }
.nav-placeholder { width: 64rpx; }
.settings-list { height: calc(100vh - 88rpx); }
.settings-group { margin: 20rpx 0; }
.settings-item {
  display: flex; align-items: center; padding: 28rpx 30rpx;
  background: var(--card-bg); border-bottom: 1rpx solid var(--border-color);
  &:active { background: var(--bg-color); }
}
.item-icon { font-size: 36rpx; margin-right: 20rpx; }
.item-label { flex: 1; font-size: $font-base; color: var(--text-primary); }
.item-value { font-size: $font-sm; color: var(--text-secondary); margin-right: 12rpx; }
.item-arrow { font-size: 32rpx; color: var(--text-placeholder); }
.toggle {
  width: 88rpx; height: 48rpx; border-radius: 24rpx;
  background: var(--text-placeholder); position: relative;
  transition: background 0.3s;
  &.on { background: $primary-color; }
}
.toggle-dot {
  position: absolute; top: 4rpx; left: 4rpx;
  width: 40rpx; height: 40rpx; border-radius: 50%;
  background: #fff; transition: transform 0.3s;
  .on & { transform: translateX(40rpx); }
}
.logout-btn {
  margin: 60rpx 30rpx; height: 88rpx; display: flex;
  align-items: center; justify-content: center;
  border: 2rpx solid $danger-color; border-radius: $radius-base;
  color: $danger-color; font-size: $font-base;
  &:active { opacity: 0.8; }
}
/* 弹窗 */
.modal-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-box {
  width: 640rpx; background: var(--card-bg); border-radius: $radius-lg;
  padding: 40rpx; max-height: 80vh; overflow-y: auto;
}
.modal-title { font-size: $font-lg; font-weight: bold; color: var(--text-primary); text-align: center; margin-bottom: 16rpx; display: block; }
.modal-desc { font-size: $font-sm; color: var(--text-secondary); text-align: center; margin-bottom: 24rpx; display: block; }
.modal-input {
  height: 88rpx; background: var(--bg-color); border-radius: $radius-base;
  padding: 0 24rpx; font-size: $font-base; margin-bottom: 20rpx; color: var(--text-primary);
}
.modal-textarea {
  width: 100%; min-height: 200rpx; background: var(--bg-color); border-radius: $radius-base;
  padding: 20rpx 24rpx; font-size: $font-base; margin-bottom: 20rpx; color: var(--text-primary);
}
.picker-field {
  display: flex; align-items: center; justify-content: space-between;
  height: 88rpx; background: var(--bg-color); border-radius: $radius-base;
  padding: 0 24rpx; margin-bottom: 20rpx; font-size: $font-base; color: var(--text-primary);
}
.picker-arrow { font-size: 20rpx; color: var(--text-placeholder); }
.modal-btns { display: flex; gap: 24rpx; margin-top: 24rpx; }
.modal-btn {
  flex: 1; height: 88rpx; display: flex; align-items: center; justify-content: center;
  border-radius: $radius-base; font-size: $font-base; &:active { opacity: 0.8; }
  &.cancel { background: var(--bg-color); color: var(--text-secondary); }
  &.confirm { background: $primary-color; color: #fff; }
}
</style>
