<template>
  <view class="radar-wrap">
    <canvas
      canvas-id="radarCanvas"
      :style="{ width: canvasSize + 'px', height: canvasSize + 'px' }"
      class="radar-canvas"
      @tap="onTap"
    />
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
  if (val === undefined || val === null) return 0
  return Math.round(val * 100)
}

let ctx = null
let animFrame = 0

function drawRadar(progress = 1) {
  // #ifdef H5
  const query = uni.createSelectorQuery()
  query.select('.radar-canvas').fields({ node: true, size: true }).exec((res) => {
    if (!res || !res[0]) return
    const canvas = res[0].node
    const cctx = canvas.getContext('2d')
    const dpr = uni.getSystemInfoSync().pixelRatio || 2
    canvas.width = canvasSize.value * dpr
    canvas.height = canvasSize.value * dpr
    cctx.scale(dpr, dpr)
    renderCanvas(cctx, canvasSize.value, progress)
  })
  // #endif
  // #ifndef H5
  ctx = uni.createCanvasContext('radarCanvas')
  renderCanvasCtx(ctx, canvasSize.value, progress)
  ctx.draw()
  // #endif
}

function renderCanvas(cctx, size, progress) {
  const cx = size / 2
  const cy = size / 2
  const maxR = size / 2 - 30
  const count = dimensions.length
  const angleStep = (Math.PI * 2) / count
  const startAngle = -Math.PI / 2

  // 背景网格
  for (let level = 1; level <= 5; level++) {
    const r = (maxR / 5) * level
    cctx.beginPath()
    for (let i = 0; i <= count; i++) {
      const angle = startAngle + i * angleStep
      const x = cx + r * Math.cos(angle)
      const y = cy + r * Math.sin(angle)
      if (i === 0) cctx.moveTo(x, y)
      else cctx.lineTo(x, y)
    }
    cctx.strokeStyle = 'rgba(0,0,0,0.06)'
    cctx.lineWidth = 1
    cctx.stroke()
  }

  // 轴线
  for (let i = 0; i < count; i++) {
    const angle = startAngle + i * angleStep
    cctx.beginPath()
    cctx.moveTo(cx, cy)
    cctx.lineTo(cx + maxR * Math.cos(angle), cy + maxR * Math.sin(angle))
    cctx.strokeStyle = 'rgba(0,0,0,0.08)'
    cctx.lineWidth = 1
    cctx.stroke()
  }

  // 数据多边形
  cctx.beginPath()
  for (let i = 0; i <= count; i++) {
    const idx = i % count
    const dim = dimensions[idx]
    const val = (props.data?.[dim.key] || 0) * progress
    const angle = startAngle + idx * angleStep
    const r = maxR * val
    const x = cx + r * Math.cos(angle)
    const y = cy + r * Math.sin(angle)
    if (i === 0) cctx.moveTo(x, y)
    else cctx.lineTo(x, y)
  }
  cctx.fillStyle = 'rgba(7, 193, 96, 0.2)'
  cctx.fill()
  cctx.strokeStyle = '#07C160'
  cctx.lineWidth = 2
  cctx.stroke()

  // 数据点
  for (let i = 0; i < count; i++) {
    const dim = dimensions[i]
    const val = (props.data?.[dim.key] || 0) * progress
    const angle = startAngle + i * angleStep
    const r = maxR * val
    const x = cx + r * Math.cos(angle)
    const y = cy + r * Math.sin(angle)
    cctx.beginPath()
    cctx.arc(x, y, 4, 0, Math.PI * 2)
    cctx.fillStyle = dimColors[i]
    cctx.fill()
  }

  // 标签
  cctx.font = '12px sans-serif'
  cctx.textAlign = 'center'
  cctx.textBaseline = 'middle'
  for (let i = 0; i < count; i++) {
    const dim = dimensions[i]
    const angle = startAngle + i * angleStep
    const labelR = maxR + 18
    let x = cx + labelR * Math.cos(angle)
    let y = cy + labelR * Math.sin(angle)
    cctx.fillStyle = '#333'
    cctx.fillText(dim.label, x, y)
  }
}

function renderCanvasCtx(cctx, size, progress) {
  const cx = size / 2
  const cy = size / 2
  const maxR = size / 2 - 30
  const count = dimensions.length
  const angleStep = (Math.PI * 2) / count
  const startAngle = -Math.PI / 2

  // 背景网格
  for (let level = 1; level <= 5; level++) {
    const r = (maxR / 5) * level
    cctx.beginPath()
    for (let i = 0; i <= count; i++) {
      const angle = startAngle + i * angleStep
      const x = cx + r * Math.cos(angle)
      const y = cy + r * Math.sin(angle)
      if (i === 0) cctx.moveTo(x, y)
      else cctx.lineTo(x, y)
    }
    cctx.setStrokeStyle('rgba(0,0,0,0.06)')
    cctx.setLineWidth(1)
    cctx.stroke()
  }

  // 轴线
  for (let i = 0; i < count; i++) {
    const angle = startAngle + i * angleStep
    cctx.beginPath()
    cctx.moveTo(cx, cy)
    cctx.lineTo(cx + maxR * Math.cos(angle), cy + maxR * Math.sin(angle))
    cctx.setStrokeStyle('rgba(0,0,0,0.08)')
    cctx.setLineWidth(1)
    cctx.stroke()
  }

  // 数据多边形
  cctx.beginPath()
  for (let i = 0; i <= count; i++) {
    const idx = i % count
    const dim = dimensions[idx]
    const val = (props.data?.[dim.key] || 0) * progress
    const angle = startAngle + idx * angleStep
    const r = maxR * val
    const x = cx + r * Math.cos(angle)
    const y = cy + r * Math.sin(angle)
    if (i === 0) cctx.moveTo(x, y)
    else cctx.lineTo(x, y)
  }
  cctx.setFillStyle('rgba(7, 193, 96, 0.2)')
  cctx.fill()
  cctx.setStrokeStyle('#07C160')
  cctx.setLineWidth(2)
  cctx.stroke()

  // 数据点
  for (let i = 0; i < count; i++) {
    const dim = dimensions[i]
    const val = (props.data?.[dim.key] || 0) * progress
    const angle = startAngle + i * angleStep
    const r = maxR * val
    const x = cx + r * Math.cos(angle)
    const y = cy + r * Math.sin(angle)
    cctx.beginPath()
    cctx.arc(x, y, 4, 0, Math.PI * 2)
    cctx.setFillStyle(dimColors[i])
    cctx.fill()
  }

  // 标签
  for (let i = 0; i < count; i++) {
    const dim = dimensions[i]
    const angle = startAngle + i * angleStep
    const labelR = maxR + 18
    let x = cx + labelR * Math.cos(angle)
    let y = cy + labelR * Math.sin(angle)
    cctx.setFillStyle('#333')
    cctx.setFontSize(12)
    cctx.setTextAlign('center')
    cctx.setTextBaseline('middle')
    cctx.fillText(dim.label, x, y)
  }
}

function animateDraw() {
  let progress = 0
  const step = 0.02
  const interval = setInterval(() => {
    progress += step
    if (progress >= 1) {
      progress = 1
      clearInterval(interval)
    }
    drawRadar(progress)
  }, 16)
}

function onTap() {}

watch(() => props.data, () => {
  nextTick(() => animateDraw())
}, { deep: true })

onMounted(() => {
  nextTick(() => animateDraw())
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
