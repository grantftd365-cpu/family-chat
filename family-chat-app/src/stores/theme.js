/**
 * 主题状态管理
 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { getTheme, setTheme } from '../utils/storage'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref(getTheme())

  /** 切换主题 */
  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    setTheme(theme.value)
    applyTheme()
  }

  /** 设置主题 */
  function setThemeMode(mode) {
    theme.value = mode
    setTheme(mode)
    applyTheme()
  }

  /** 应用主题 */
  function applyTheme() {
    // #ifdef H5
    document.documentElement.setAttribute('data-theme', theme.value)
    // #endif
    // #ifdef APP-PLUS
    plus.nativeUI.setUIStyle?.(theme.value)
    // #endif
  }

  /** 初始化 */
  function init() {
    applyTheme()
    // #ifdef H5
    // 监听系统主题变化
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (getTheme() === 'auto') {
          theme.value = e.matches ? 'dark' : 'light'
          applyTheme()
        }
      })
    }
    // #endif
  }

  return {
    theme,
    toggleTheme,
    setThemeMode,
    init,
    applyTheme
  }
})
