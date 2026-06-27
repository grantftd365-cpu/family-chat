<template>
  <view class="questionnaire-page">
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-content">
        <view class="nav-back" @tap="goBack"><text>‹</text></view>
        <text class="nav-title">深层问卷</text>
        <view class="nav-placeholder"></view>
      </view>
    </view>

    <scroll-view scroll-y class="q-content">
      <!-- 进度条 -->
      <view class="q-progress">
        <view class="q-progress-bar">
          <view class="q-progress-fill" :style="{ width: progressPercent + '%' }"></view>
        </view>
        <text class="q-progress-text">{{ answeredCount }}/{{ questions.length }} 已完成</text>
      </view>

      <!-- 加载中 -->
      <view v-if="loading" class="q-loading">
        <text>加载问卷中...</text>
      </view>

      <!-- 问题列表 -->
      <view v-else-if="!submitted" class="q-list">
        <view
          v-for="(q, index) in questions"
          :key="q.id || index"
          class="q-item"
          :class="{ answered: answers[q.id || index] }"
        >
          <view class="q-header">
            <text class="q-number">{{ index + 1 }}</text>
            <text class="q-label">{{ q.question || q.label || q }}</text>
          </view>
          <textarea
            v-model="answers[q.id || index]"
            class="q-input"
            :placeholder="q.placeholder || '请输入你的回答...'"
            :maxlength="2000"
          />
          <text class="q-char-count">{{ (answers[q.id || index] || '').length }}/2000</text>
        </view>

        <!-- 提交按钮 -->
        <view class="q-submit-area">
          <view
            class="q-submit-btn"
            :class="{ disabled: !canSubmit || submitting }"
            @tap="submitQuestionnaire"
          >
            <text v-if="submitting" class="loading-icon">⏳</text>
            <text>{{ submitting ? '炼化中...' : '提交并炼化' }}</text>
          </view>
        </view>
      </view>

      <!-- 炼化结果对比 -->
      <view v-if="submitted && result" class="q-result">
        <text class="q-result-title">✨ 炼化完成</text>

        <!-- 完成度对比 -->
        <view class="q-compare">
          <text class="compare-title">完成度对比</text>
          <view
            v-for="dim in compareDimensions"
            :key="dim.key"
            class="compare-item"
          >
            <text class="compare-label">{{ dim.label }}</text>
            <view class="compare-bars">
              <view class="compare-bar-wrap">
                <text class="compare-bar-label">前</text>
                <view class="compare-bar-bg">
                  <view class="compare-bar-before" :style="{ width: dim.before + '%' }"></view>
                </view>
                <text class="compare-bar-value">{{ dim.before }}%</text>
              </view>
              <view class="compare-bar-wrap">
                <text class="compare-bar-label">后</text>
                <view class="compare-bar-bg">
                  <view class="compare-bar-after" :style="{ width: dim.after + '%' }"></view>
                </view>
                <text class="compare-bar-value">{{ dim.after }}%</text>
              </view>
            </view>
            <text v-if="dim.after > dim.before" class="compare-delta">+{{ dim.after - dim.before }}%</text>
          </view>
        </view>

        <!-- 炼化结果详情 -->
        <view v-if="result.traits" class="q-traits">
          <text class="traits-title">提取的特征</text>
          <view v-if="result.traits.personality_traits" class="trait-row">
            <text class="trait-label">性格特征</text>
            <text class="trait-value">{{ result.traits.personality_traits.join('、') }}</text>
          </view>
          <view v-if="result.traits.speaking_style" class="trait-row">
            <text class="trait-label">说话风格</text>
            <text class="trait-value">{{ result.traits.speaking_style }}</text>
          </view>
          <view v-if="result.traits.interests" class="trait-row">
            <text class="trait-label">兴趣爱好</text>
            <text class="trait-value">{{ result.traits.interests.join('、') }}</text>
          </view>
          <view v-if="result.traits.values" class="trait-row">
            <text class="trait-label">价值观念</text>
            <text class="trait-value">{{ result.traits.values.join('、') }}</text>
          </view>
          <view v-if="result.traits.catchphrases" class="trait-row">
            <text class="trait-label">口头禅</text>
            <text class="trait-value">{{ result.traits.catchphrases.join('、') }}</text>
          </view>
        </view>

        <!-- 再次填写 -->
        <view class="q-retry-area">
          <view class="q-retry-btn" @tap="resetQuestionnaire">
            <text>重新填写</text>
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
import { normalizeQuestionnaire, normalizeCompleteness } from '../../utils/response'

const statusBarHeight = ref(44)
const agentId = ref('')

const DEFAULT_QUESTIONS = [
  { id: 'q1', question: '你最看重的人生信条是什么？它如何影响你的日常决策？', placeholder: '例如：己所不欲勿施于人...' },
  { id: 'q2', question: '描述一个对你影响最深的人，他/她教会了你什么？', placeholder: '例如：我的母亲教会我...' },
  { id: 'q3', question: '你最擅长用什么方式表达情感？（语言、行动、文字等）', placeholder: '例如：我习惯用文字表达...' },
  { id: 'q4', question: '在与人交流时，你最常使用哪些口头禅或表达习惯？', placeholder: '例如：我经常说“其实吧”...' },
  { id: 'q5', question: '你认为什么是最珍贵的家庭关系？为什么？', placeholder: '例如：我认为相互理解...' },
  { id: 'q6', question: '描述你最难忘的一段经历，它如何塑造了现在的你？', placeholder: '例如：小时候...' },
  { id: 'q7', question: '你在面对困难时通常会怎么想、怎么做？', placeholder: '例如：我会先冷静分析...' },
  { id: 'q8', question: '你最喜欢的话题是什么？和谁聊这些话题最开心？', placeholder: '例如：我喜欢聊历史...' },
  { id: 'q9', question: '如果用三个词来形容你的说话风格，会是什么？', placeholder: '例如：幽默、直接、温和...' },
  { id: 'q10', question: '你希望别人怎样记住你？你留给他人的印象是什么？', placeholder: '例如：我希望别人记住我是一个...' }
]

const questions = ref([])
const answers = ref({})
const loading = ref(true)
const submitting = ref(false)
const submitted = ref(false)
const result = ref(null)
const beforeCompleteness = ref(null)

const answeredCount = computed(() => {
  return Object.values(answers.value).filter(v => v && v.trim()).length
})

const progressPercent = computed(() => {
  if (!questions.value.length) return 0
  return Math.round((answeredCount.value / questions.value.length) * 100)
})

const canSubmit = computed(() => {
  return answeredCount.value >= 1
})

const compareDimensions = computed(() => {
  if (!result.value) return []
  const dims = [
    { key: 'cognition', label: '认知' },
    { key: 'knowledge', label: '知识' },
    { key: 'emotion', label: '情感' },
    { key: 'language', label: '语言' },
    { key: 'value', label: '价值' },
    { key: 'relation', label: '关系' },
    { key: 'narrative', label: '叙事' }
  ]
  const raw = result.value.completeness || result.value.essence || result.value.scores || result.value
  const after = normalizeCompleteness(raw)
  const before = beforeCompleteness.value || {}
  return dims.map(d => ({
    ...d,
    before: Math.round((before[d.key] || 0) * 100),
    after: Math.round((after[d.key] || 0) * 100)
  }))
})

onLoad(async (options) => {
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  agentId.value = options.agentId || ''

  await loadQuestionnaire()
  if (agentId.value) {
    loadBeforeCompleteness()
  }
})

async function loadQuestionnaire() {
  loading.value = true
  try {
    const res = await api.getRefinementQuestionnaire().catch(() => null)
    questions.value = normalizeQuestionnaire(res)
    if (!questions.value.length) {
      questions.value = [
        { id: 'q1', question: '你最看重的人生信条是什么？它如何影响你的日常决策？', placeholder: '例如：己所不欲勿施于人...' },
        { id: 'q2', question: '描述一个对你影响最深的人，他/她教会了你什么？', placeholder: '例如：我的母亲教会我...' },
        { id: 'q3', question: '你最擅长用什么方式表达情感？（语言、行动、文字等）', placeholder: '例如：我习惯用文字表达...' },
        { id: 'q4', question: '在与人交流时，你最常使用哪些口头禅或表达习惯？', placeholder: '例如：我经常说"其实吧"...' },
        { id: 'q5', question: '你认为什么是最珍贵的家庭关系？为什么？', placeholder: '例如：我认为相互理解...' },
        { id: 'q6', question: '描述你最难忘的一段经历，它如何塑造了现在的你？', placeholder: '例如：小时候...' },
        { id: 'q7', question: '你在面对困难时通常会怎么想、怎么做？', placeholder: '例如：我会先冷静分析...' },
        { id: 'q8', question: '你最喜欢的话题是什么？和谁聊这些话题最开心？', placeholder: '例如：我喜欢聊历史...' },
        { id: 'q9', question: '如果用三个词来形容你的说话风格，会是什么？', placeholder: '例如：幽默、直接、温和...' },
        { id: 'q10', question: '你希望别人怎样记住你？你留给他人的印象是什么？', placeholder: '例如：我希望别人记住我是一个...' }
      ]
    }
  } catch (e) {
    questions.value = DEFAULT_QUESTIONS
  } finally {
    loading.value = false
  }
}

async function loadBeforeCompleteness() {
  try {
    const res = await api.getRefinementCompleteness(agentId.value).catch(() => null)
    beforeCompleteness.value = normalizeCompleteness(res)
  } catch (e) {
    console.error('加载完成度失败:', e)
  }
}

async function submitQuestionnaire() {
  if (!canSubmit.value || submitting.value) return
  if (!agentId.value) {
    uni.showToast({ title: '未选择数字人', icon: 'none' })
    return
  }

  submitting.value = true
  try {
    // 构建答案数组
    const answersList = questions.value.map((q, i) => ({
      question: q.question || q.label || q,
      answer: answers.value[q.id || i] || ''
    })).filter(a => a.answer && a.answer.trim())

    const res = await api.refineFromSelfDescription(agentId.value, answersList)
    result.value = res
    submitted.value = true
    uni.showToast({ title: '炼化完成', icon: 'success' })
  } catch (e) {
    uni.showToast({ title: '炼化失败: ' + (e.message || '未知错误'), icon: 'none' })
  } finally {
    submitting.value = false
  }
}

function resetQuestionnaire() {
  submitted.value = false
  result.value = null
  answers.value = {}
  loadBeforeCompleteness()
}

function goBack() {
  uni.navigateBack()
}
</script>

<style lang="scss" scoped>
.questionnaire-page {
  min-height: 100vh;
  background: var(--bg-color);
}

.nav-bar {
  background: $primary-color;
}

.nav-content {
  display: flex;
  align-items: center;
  height: 88rpx;
  padding: 0 30rpx;
}

.nav-back {
  font-size: 48rpx;
  color: #fff;
  padding-right: 16rpx;
}

.nav-title {
  flex: 1;
  text-align: center;
  font-size: $font-lg;
  font-weight: bold;
  color: #fff;
}

.nav-placeholder {
  width: 64rpx;
}

.q-content {
  height: calc(100vh - 88rpx);
}

/* 进度条 */
.q-progress {
  padding: 24rpx 30rpx 12rpx;
}

.q-progress-bar {
  height: 12rpx;
  background: var(--bg-color-secondary, #F7F7F7);
  border-radius: 6rpx;
  overflow: hidden;
  margin-bottom: 8rpx;
}

.q-progress-fill {
  height: 100%;
  background: $primary-color;
  border-radius: 6rpx;
  transition: width 0.4s ease;
}

.q-progress-text {
  font-size: $font-xs;
  color: var(--text-secondary);
}

/* 加载 */
.q-loading {
  text-align: center;
  padding: 100rpx;
  color: var(--text-secondary);
}

/* 问题列表 */
.q-list {
  padding: 0 30rpx;
}

.q-item {
  background: var(--card-bg);
  border-radius: $radius-base;
  padding: 24rpx;
  margin-bottom: 16rpx;
  border-left: 6rpx solid var(--border-color);
  transition: border-color 0.3s;

  &.answered {
    border-left-color: $primary-color;
  }
}

.q-header {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
  margin-bottom: 16rpx;
}

.q-number {
  width: 40rpx;
  height: 40rpx;
  background: $primary-color;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: $font-sm;
  font-weight: bold;
  flex-shrink: 0;
}

.q-label {
  font-size: $font-base;
  color: var(--text-primary);
  line-height: 1.5;
  flex: 1;
}

.q-input {
  width: 100%;
  min-height: 120rpx;
  background: var(--bg-color);
  border-radius: $radius-sm;
  padding: 16rpx;
  font-size: $font-sm;
  color: var(--text-primary);
  line-height: 1.5;
}

.q-char-count {
  font-size: $font-xs;
  color: var(--text-secondary);
  text-align: right;
  display: block;
  margin-top: 4rpx;
}

/* 提交 */
.q-submit-area {
  padding: 32rpx 0 48rpx;
}

.q-submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 96rpx;
  background: $primary-color;
  border-radius: $radius-base;
  color: #fff;
  font-size: $font-lg;
  font-weight: bold;
  gap: 12rpx;

  &.disabled {
    opacity: 0.5;
    pointer-events: none;
  }

  &:active {
    opacity: 0.8;
  }
}

.loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 结果 */
.q-result {
  padding: 24rpx 30rpx;
}

.q-result-title {
  font-size: $font-xl;
  font-weight: bold;
  color: var(--text-primary);
  display: block;
  text-align: center;
  margin-bottom: 32rpx;
}

/* 对比 */
.q-compare {
  background: var(--card-bg);
  border-radius: $radius-base;
  padding: 24rpx;
  margin-bottom: 24rpx;
}

.compare-title {
  font-size: $font-base;
  font-weight: 500;
  color: var(--text-primary);
  display: block;
  margin-bottom: 16rpx;
}

.compare-item {
  padding: 12rpx 0;
  border-bottom: 1rpx solid var(--border-color);

  &:last-child {
    border-bottom: none;
  }
}

.compare-label {
  font-size: $font-sm;
  color: var(--text-primary);
  font-weight: 500;
  display: block;
  margin-bottom: 8rpx;
}

.compare-bars {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.compare-bar-wrap {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.compare-bar-label {
  font-size: $font-xs;
  color: var(--text-secondary);
  width: 30rpx;
}

.compare-bar-bg {
  flex: 1;
  height: 10rpx;
  background: var(--bg-color);
  border-radius: 5rpx;
  overflow: hidden;
}

.compare-bar-before {
  height: 100%;
  background: var(--text-placeholder);
  border-radius: 5rpx;
  transition: width 0.6s ease;
}

.compare-bar-after {
  height: 100%;
  background: $primary-color;
  border-radius: 5rpx;
  transition: width 0.6s ease;
}

.compare-bar-value {
  font-size: $font-xs;
  color: var(--text-secondary);
  width: 60rpx;
  text-align: right;
}

.compare-delta {
  font-size: $font-xs;
  color: $primary-color;
  font-weight: bold;
  display: block;
  margin-top: 4rpx;
  text-align: right;
}

/* 特征 */
.q-traits {
  background: var(--card-bg);
  border-radius: $radius-base;
  padding: 24rpx;
  margin-bottom: 24rpx;
}

.traits-title {
  font-size: $font-base;
  font-weight: 500;
  color: var(--text-primary);
  display: block;
  margin-bottom: 16rpx;
}

.trait-row {
  padding: 12rpx 0;
  border-bottom: 1rpx solid var(--border-color);

  &:last-child {
    border-bottom: none;
  }
}

.trait-label {
  font-size: $font-sm;
  color: var(--text-secondary);
  display: block;
  margin-bottom: 4rpx;
}

.trait-value {
  font-size: $font-base;
  color: var(--text-primary);
  line-height: 1.5;
}

/* 重试 */
.q-retry-area {
  padding: 24rpx 0 48rpx;
  text-align: center;
}

.q-retry-btn {
  display: inline-block;
  padding: 16rpx 60rpx;
  border: 2rpx solid $primary-color;
  border-radius: $radius-base;
  color: $primary-color;
  font-size: $font-base;

  &:active {
    background: $primary-50;
  }
}
</style>
