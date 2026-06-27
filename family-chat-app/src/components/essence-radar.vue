<template>
  <view class="radar-wrap">
    <!-- #ifdef MP-WEIXIN -->
    <canvas
      type="2d"
      id="radarCanvas"
      class="radar-canvas"
      :style="{ width: canvasSize + 'px', height: canvasSize + 'px' }"
    />
    <!-- #endif -->
    <!-- #ifndef MP-WEIXIN -->
    <canvas
      canvas-id="radarCanvas"
      class="radar-canvas"
      :style="{ width: canvasSize + 'px', height: canvasSize + 'px' }"
    />
    <!-- #endif -->
    <view class="radar-legend">
      <view
        v-for="(dim, i) in dimensions"
        :key="dim.key"
        class="legend-item"
      >
        <view class="legend-dot" :style="{ background: dimColors[i] }"></view>
        <text class="legend-name">{{ dim.label }}</text>
        <text class="legend-value">{{ getPercent(dim.key) }}%</text>
        <view class="legend-bar-wrap">
          <view class="legend-bar" :style="{ width: getPercent(dim.key) + '%', background: dimColors[i] }"></view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  data: { type: Object, default: () => ({}) },
  size: { type: Number, default: 280 }
})

const canvasSize = ref(props.size)

const dimensions = [
  { key: 'cognition', label: '认知' },
  { key: 'knowledge', label: '知识' },
  { key: 'emotion', label: '情感' },
  { key: 'language', label: '语言' },
  { key: 'value', label: '价值' },
  { key: 'relation', label: '关系' },
  { key: 'narrative', label: '叙事' }
]

const dimColors = [
  '#07C160', '#10AEFF', '#FA5151', '#FFC300',
  '#6467F0', '#E855D3', '#FF8C42'
]

function getPercent(key) {
  const val = props.data?.[key]
  if (val === undefined || val === null || isNaN(val)) return 0
  return Math.round(Math.min(val * 100, 100))
}

/** 是否有有效数据 */
function hasValidData() {
  if (!props.data) return false
  return dimensions.some(d => {
    const v = props.data[d.key]
    return v !== undefined && v !== null && v > 0
  })
}

// ======== 统一渲染逻辑 ========

function renderToContext(ctx, size, progress, isH5) {
  const cx = size / 2
  const cy = size / 2
  const maxR = size / 2 - 30
  const count = dimensions.length
  const angleStep = (Math.PI * 2) / count
  const startAngle = -Math.PI / 2

  function setColor(hex, alpha) {
    if (isH5) {
      ctx.globalAlpha = alpha || 1
      ctx.strokeStyle = hex
      ctx.fillStyle = hex
    } else {
      // 小程序旧 API 用 setStrokeStyle/setFillStyle
      if (alpha !== undefined && alpha !== 1) {
        // 解析 hex 为 rgba
        const r = parseInt(hex.slice(1, 3), 16)
        const g = parseInt(hex.slice(3, 5), 16)
        const b = parseInt(hex.slice(5, 7), 16)
        const rgba = `rgba(${r},${g},${b},${alpha})`
        if (ctx.setStrokeStyle) ctx.setStrokeStyle(rgba)
        if (ctx.setFillStyle) ctx.setFillStyle(rgba)
      } else {
        if (ctx.setStrokeStyle) ctx.setStrokeStyle(hex)
        if (ctx.setFillStyle) ctx.setFillStyle(hex)
      }
    }
  }

  function setLineWidth(w) {
    if (isH5) ctx.lineWidth = w
    else if (ctx.setLineWidth) ctx.setLineWidth(w)
  }

  function beginPath() {
    if (isH5) ctx.beginPath()
    else if (ctx.beginPath) ctx.beginPath()
  }

  function moveTo(x, y) {
    if (isH5) ctx.moveTo(x, y)
    else if (ctx.moveTo) ctx.moveTo(x, y)
  }

  function lineTo(x, y) {
    if (isH5) ctx.lineTo(x, y)
    else if (ctx.lineTo) ctx.lineTo(x, y)
  }

  function arc(x, y, r, s, e) {
    if (isH5) ctx.arc(x, y, r, s, e)
    else if (ctx.arc) ctx.arc(x, y, r, s, e)
  }

  function fill() {
    if (isH5) ctx.fill()
    else if (ctx.fill) ctx.fill()
  }

  function stroke() {
    if (isH5) ctx.stroke()
    else if (ctx.stroke) ctx.stroke()
  }

  function fillText(text, x, y) {
    if (isH5) {
      ctx.font = '12px sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillStyle = '#666'
      ctx.fillText(text, x, y)
    } else {
      if (ctx.setFontSize) ctx.setFontSize(12)
      if (ctx.setTextAlign) ctx.setTextAlign('center')
      if (ctx.setTextBaseline) ctx.setTextBaseline('middle')
      setColor('#666')
      if (ctx.fillText) ctx.fillText(text, x, y)
    }
  }

  // 清空
  if (isH5) {
    ctx.clearRect(0, 0, size, size)
  }

  // 背景网格 (5层)
  for (let level = 1; level <= 5; level++) {
    const r = (maxR / 5) * level
    beginPath()
    for (let i = 0; i <= count; i++) {
      const angle = startAngle + (i % count) * angleStep
      const x = cx + r * Math.cos(angle)
      const y = cy + r * Math.sin(angle)
      if (i === 0) moveTo(x, y)
      else lineTo(x, y)
    }
    setColor('#E5E5E5', 0.6)
    setLineWidth(1)
    stroke()
  }

  // 轴线
  for (let i = 0; i < count; i++) {
    const angle = startAngle + i * angleStep
    beginPath()
    moveTo(cx, cy)
    lineTo(cx + maxR * Math.cos(angle), cy + maxR * Math.sin(angle))
    setColor('#E5E5E5', 0.5)
    setLineWidth(1)
    stroke()
  }

  // 数据多边形
  beginPath()
  for (let i = 0; i <= count; i++) {
    const idx = i % count
    const dim = dimensions[idx]
    const val = (props.data?.[dim.key] || 0) * progress
    const angle = startAngle + idx * angleStep
    const r = maxR * Math.min(val, 1)
    const x = cx + r * Math.cos(angle)
    const y = cy + r * Math.sin(angle)
    if (i === 0) moveTo(x, y)
    else lineTo(x, y)
  }
  setColor('#07C160', 0.2)
  fill()
  setColor('#07C160')
  setLineWidth(2)
  stroke()

  // 数据点
  for (let i = 0; i < count; i++) {
    const dim = dimensions[i]
    const val = (props.data?.[dim.key] || 0) * progress
    const angle = startAngle + i * angleStep
    const r = maxR * Math.min(val, 1)
    const x = cx + r * Math.cos(angle)
    const y = cy + r * Math.sin(angle)
    beginPath()
    arc(x, y, 4, 0, Math.PI * 2)
    setColor(dimColors[i])
    fill()
  }

  // 标签
  for (let i = 0; i < count; i++) {
    const dim = dimensions[i]
    const angle = startAngle + i * angleStep
    const labelR = maxR + 18
    const x = cx + labelR * Math.cos(angle)
    const y = cy + labelR * Math.sin(angle)
    fillText(dim.label, x, y)
  }
}

// ======== H5 渲染 ========
function drawH5(progress) {
  const query = uni.createSelectorQuery().in(this)
  query.select('.radar-canvas').fields({ node: true, size: true }).exec((res) => {
    if (!res || !res[0] || !res[0].node) {
      // fallback: 尝试旧方式
      drawLegacy(progress)
      return
    }
    const canvas = res[0].node
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const dpr = uni.getSystemInfoSync().pixelRatio || 2
    canvas.width = canvasSize.value * dpr
    canvas.height = canvasSize.value * dpr
    ctx.scale(dpr, dpr)
    renderToContext(ctx, canvasSize.value, progress, true)
  })
}

// ======== 小程序渲染 (type="2d") ========
function drawMP2D(progress) {
  const query = uni.createSelectorQuery().in(this)
  query.select('#radarCanvas').fields({ node: true, size: true }).exec((res) => {
    if (!res || !res[0] || !res[0].node) {
      drawLegacy(progress)
      return
    }
    const canvas = res[0].node
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const dpr = uni.getSystemInfoSync().pixelRatio || 2
    canvas.width = canvasSize.value * dpr
    canvas.height = canvasSize.value * dpr
    ctx.scale(dpr, dpr)
    renderToContext(ctx, canvasSize.value, progress, true)
  })
}

// ======== 旧版小程序 fallback ========
function drawLegacy(progress) {
  try {
    const ctx = uni.createCanvasContext('radarCanvas', this)
    if (!ctx) return
    renderToContext(ctx, canvasSize.value, progress, false)
    ctx.draw()
  } catch (e) {
    console.warn('Canvas 渲染失败:', e)
  }
}

// ======== 统一入口 ========
function drawRadar(progress = 1) {
  // #ifdef H5
  drawH5(progress)
  // #endif
  // #ifdef MP-WEIXIN
  drawMP2D(progress)
  // #endif
  // #ifdef MP-ALIPAY || MP-BAIDU || MP-TOUTIAO || MP-QQ
  drawLegacy(progress)
  // #endif
  // #ifdef APP-PLUS
  drawLegacy(progress)
  // #endif
}

let animTimer = null

function animateDraw() {
  if (animTimer) clearInterval(animTimer)
  if (!hasValidData()) return
  let progress = 0
  animTimer = setInterval(() => {
    progress += 0.03
    if (progress >= 1) {
      progress = 1
      clearInterval(animTimer)
      animTimer = null
    }
    drawRadar(progress)
  }, 16)
}

watch(() => props.data, (newVal) => {
  if (newVal && hasValidData()) {
    nextTick(() => animateDraw())
  }
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    // 延迟一帧确保 canvas 已渲染
    setTimeout(() => animateDraw(), 100)
  })
})
</script>

<style lang="scss" scoped>
.radar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24rpx 0;
}

.radar-canvas {
  margin-bottom: 24rpx;
}

.radar-legend {
  width: 100%;
  padding: 0 24rpx;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 8rpx 0;
}

.legend-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-name {
  font-size: $font-sm;
  color: var(--text-primary);
  width: 60rpx;
  flex-shrink: 0;
}

.legend-value {
  font-size: $font-sm;
  color: var(--text-secondary);
  width: 60rpx;
  text-align: right;
  flex-shrink: 0;
}

.legend-bar-wrap {
  flex: 1;
  height: 12rpx;
  background: var(--bg-color);
  border-radius: 6rpx;
  overflow: hidden;
}

.legend-bar {
  height: 100%;
  border-radius: 6rpx;
  transition: width 0.6s ease;
}
</style>
