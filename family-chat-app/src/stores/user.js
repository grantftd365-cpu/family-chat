/**
 * 用户状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getToken, setToken, removeToken, getUserInfo, setUserInfo, removeUserInfo, clearStorage } from '../utils/storage'
import * as api from '../utils/api'
import ws from '../utils/ws'

export const useUserStore = defineStore('user', () => {
  const token = ref(getToken())
  const userInfo = ref(getUserInfo())
  const isLoggedIn = computed(() => !!token.value)

  /** 设置登录态 */
  function setLogin(tokenStr, user) {
    token.value = tokenStr
    userInfo.value = user
    setToken(tokenStr)
    setUserInfo(user)
    // 连接 WebSocket
    ws.connect()
  }

  /** 登录 */
  async function login(email, password) {
    const res = await api.login({ email, password })
    setLogin(res.token, res.user)
    return res
  }

  /** 注册 */
  async function register(data) {
    const res = await api.register(data)
    setLogin(res.token, res.user)
    return res
  }

  /** 微信登录 */
  async function wxLogin(code, profile = {}) {
    const res = await api.wxLogin(code, profile)
    setLogin(res.token, res.user)
    return res
  }

  /** 微信 OAuth 登录（App/H5） */
  async function wxOAuthLogin(code) {
    const res = await api.wxOAuthLogin(code)
    setLogin(res.token, res.user)
    return res
  }

  /** 刷新用户信息 */
  async function refreshUserInfo() {
    try {
      const res = await api.getMe()
      userInfo.value = res
      setUserInfo(res)
      return res
    } catch (e) {
      return null
    }
  }

  /** 更新资料 */
  async function updateProfile(data) {
    const res = await api.updateMe(data)
    await refreshUserInfo()
    return res
  }

  /** 退出登录 */
  function logout() {
    token.value = ''
    userInfo.value = null
    removeToken()
    removeUserInfo()
    clearStorage()
    ws.disconnect()
    uni.reLaunch({ url: '/pages/login/login' })
  }

  /** 检查登录态 */
  function checkLogin() {
    if (!isLoggedIn.value) {
      uni.reLaunch({ url: '/pages/login/login' })
      return false
    }
    return true
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    login,
    register,
    wxLogin,
    wxOAuthLogin,
    refreshUserInfo,
    updateProfile,
    logout,
    checkLogin,
    setLogin
  }
})
