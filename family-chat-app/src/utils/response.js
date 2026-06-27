/**
 * API 响应格式标准化工具
 * 防御后端返回格式不一致的问题
 */

/**
 * 标准化列表响应
 * 支持: [], {data:[]}, {list:[]}, {items:[]}, {records:[]}, {result:[]}
 */
export function normalizeList(res, fallback = []) {
  if (!res) return fallback
  if (Array.isArray(res)) return res
  // 常见嵌套 key
  for (const key of ['data', 'list', 'items', 'records', 'result', 'rows']) {
    if (Array.isArray(res[key])) return res[key]
  }
  // 两层嵌套: {data: {list: []}}
  if (res.data && typeof res.data === 'object') {
    for (const key of ['list', 'items', 'records', 'result', 'rows']) {
      if (Array.isArray(res.data[key])) return res.data[key]
    }
  }
  return fallback
}

/**
 * 标准化对象响应
 * 支持: {}, {data:{}}, {result:{}}
 */
export function normalizeObj(res, fallback = null) {
  if (!res) return fallback
  if (typeof res === 'object' && !Array.isArray(res)) {
    // 如果直接就是数据对象（含目标 key）
    if (Object.keys(res).length > 0 && !res.code && !res.status) return res
    if (res.data && typeof res.data === 'object') return res.data
    if (res.result && typeof res.result === 'object') return res.result
  }
  return fallback
}

/**
 * 标准化七层本质数据
 * 后端可能返回 0-1 或 0-100，统一为 0-1
 */
export function normalizeEssence(raw) {
  const d = normalizeObj(raw, {})
  const keys = ['cognition', 'knowledge', 'emotion', 'language', 'value', 'relation', 'narrative']
  const result = {}
  for (const k of keys) {
    let val = d[k]
    if (val === undefined || val === null) {
      // 尝试嵌套: {scores: {cognition: 0.8}}
      if (d.scores) val = d.scores[k]
      if (d.dimensions) val = d.dimensions[k]
      if (d.layers) val = d.layers[k]
    }
    if (val === undefined || val === null) {
      result[k] = 0
    } else if (val > 1) {
      // 后端返回 0-100，转为 0-1
      result[k] = val / 100
    } else {
      result[k] = val
    }
  }
  return result
}

/**
 * 标准化完成度数据
 */
export function normalizeCompleteness(raw) {
  return normalizeEssence(raw) // 结构相同
}

/**
 * 标准化问卷数据
 * 支持: [{id,question}], [{id,label}], {questions:[]}, {data:[]}
 */
export function normalizeQuestionnaire(res) {
  let list = normalizeList(res, [])
  if (!list.length && res && typeof res === 'object') {
    // 可能是 {q1: '...', q2: '...'} 格式
    const keys = Object.keys(res).filter(k => /^q\d+/.test(k) || /^question/.test(k))
    if (keys.length) {
      list = keys.map(k => ({ id: k, question: res[k] }))
    }
  }
  // 标准化每个问题
  return list.map((q, i) => {
    if (typeof q === 'string') return { id: `q${i + 1}`, question: q }
    return {
      id: q.id || `q${i + 1}`,
      question: q.question || q.label || q.text || q.title || '',
      placeholder: q.placeholder || q.hint || ''
    }
  })
}

/**
 * 标准化表情回应数据
 */
export function normalizeReactions(raw) {
  if (!raw) return {}
  // 已经是 {emoji: [userId]} 格式
  if (typeof raw === 'object' && !Array.isArray(raw) && !raw.code) {
    // 检查是否是 [{emoji, user_id}] 数组格式
    const vals = Object.values(raw)
    if (vals.length > 0 && Array.isArray(vals[0])) return raw
  }
  // 数组格式 [{emoji: '👍', user_id: 'xxx'}]
  if (Array.isArray(raw)) {
    const result = {}
    raw.forEach(item => {
      const emoji = item.emoji || item.reaction
      const uid = item.user_id || item.userId || item.uid
      if (emoji) {
        if (!result[emoji]) result[emoji] = []
        if (uid && !result[emoji].includes(uid)) result[emoji].push(uid)
      }
    })
    return result
  }
  return {}
}
