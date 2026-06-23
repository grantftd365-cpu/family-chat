/**
 * 工具函数
 */

/**
 * 格式化时间戳为可读时间
 */
function formatTime(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  const now = new Date();
  const diff = (now - date) / 1000;

  const pad = n => String(n).padStart(2, '0');
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`;

  if (diff < 60) return '刚刚';
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;

  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const msgDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const dayDiff = (today - msgDay) / 86400000;

  if (dayDiff === 0) return time;
  if (dayDiff === 1) return `昨天 ${time}`;
  if (dayDiff < 7) return `${['日', '一', '二', '三', '四', '五', '六'][date.getDay()]} ${time}`;
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${time}`;
}

/**
 * 格式化消息预览
 */
function formatLastMessage(msg, type) {
  if (!msg) return '';
  if (type === 'image') return '[图片]';
  if (type === 'voice') return '[语音]';
  if (type === 'file') return '[文件]';
  if (type === 'red_envelope') return '[红包]';
  return msg;
}

/**
 * 防抖
 */
function debounce(fn, delay = 300) {
  let timer = null;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

module.exports = { formatTime, formatLastMessage, debounce };
