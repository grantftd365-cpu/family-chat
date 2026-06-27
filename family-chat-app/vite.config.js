import { defineConfig, loadEnv } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const serverUrl = env.VITE_SERVER_URL || ''

  return {
    plugins: [uni()],
    define: {
      // 编译时常量，非 H5 模式下用于连接服务器
      __SERVER_URL__: JSON.stringify(serverUrl),
    },
    server: {
      proxy: {
        '/api': {
          target: serverUrl || 'http://localhost:8000',
          changeOrigin: true
        },
        '/ws': {
          target: (serverUrl || 'http://localhost:8000').replace('http', 'ws'),
          ws: true
        }
      }
    }
  }
})
