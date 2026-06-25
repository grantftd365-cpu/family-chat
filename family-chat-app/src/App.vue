<script>
import { onLaunch, onShow, onHide } from '@dcloudio/uni-app'
import { useUserStore } from './stores/user'
import { useThemeStore } from './stores/theme'
import { useChatStore } from './stores/chat'
import ws from './utils/ws'

export default {
  setup() {
    const userStore = useUserStore()
    const themeStore = useThemeStore()
    const chatStore = useChatStore()

    onLaunch(() => {
      console.log('App Launch')
      // 初始化主题
      themeStore.init()
      // 如果已登录，连接 WebSocket 并加载数据
      if (userStore.isLoggedIn) {
        ws.connect()
        chatStore.loadGroups()
      }
      // 注册 WebSocket 事件
      setupWsListeners(userStore, chatStore)
    })

    onShow(() => {
      console.log('App Show')
    })

    onHide(() => {
      console.log('App Hide')
    })

    function setupWsListeners(userStore, chatStore) {
      ws.on('message', (msg) => {
        chatStore.addMessage(msg.group_id, msg)
        chatStore.incrementUnread(msg.group_id)
      })
      ws.on('recall', (data) => {
        chatStore.handleRecall(data.message_id)
      })
      ws.on('reaction', (data) => {
        chatStore.handleReaction(data.message_id, data.emoji, data.user_id)
      })
      ws.on('typing', (data) => {
        chatStore.setTyping(data.group_id, data.name)
      })
      ws.on('connected', () => {
        console.log('WS 已连接')
      })
      ws.on('disconnected', () => {
        console.log('WS 已断开')
      })
    }
  }
}
</script>

<style lang="scss">
@import './uni.scss';

/* 全局样式重置 */
page {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  font-size: $font-base;
  color: $text-primary;
  background-color: $bg-color;
  box-sizing: border-box;
  -webkit-font-smoothing: antialiased;
}

/* 暗黑模式 */
page,
[data-theme="dark"] {
  --bg-color: #{$bg-color-dark};
  --card-bg: #{$card-bg-dark};
  --text-primary: #{$text-primary-dark};
  --text-secondary: #{$text-secondary-dark};
  --text-placeholder: #{$text-placeholder-dark};
  --border-color: #{$border-color-dark};
  --bubble-self: #{$bubble-self-dark};
  --bubble-other: #{$bubble-other-dark};
  --chat-bg: #{$chat-bg-dark};
  color: var(--text-primary);
  background-color: var(--bg-color);
}

page {
  --bg-color: #{$bg-color};
  --card-bg: #{$card-bg};
  --text-primary: #{$text-primary};
  --text-secondary: #{$text-secondary};
  --text-placeholder: #{$text-placeholder};
  --border-color: #{$border-color};
  --bubble-self: #{$bubble-self};
  --bubble-other: #{$bubble-other};
  --chat-bg: #{$chat-bg};
}

/* 通用样式 */
.container {
  min-height: 100vh;
  background-color: var(--bg-color);
}

.safe-area-bottom {
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
}

/* 隐藏滚动条 */
::-webkit-scrollbar {
  display: none;
}

/* 动画 */
.fade-in {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20rpx); }
  to { opacity: 1; transform: translateY(0); }
}

.slide-up {
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(100%); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
