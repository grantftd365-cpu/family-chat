<template>
  <view class="contacts-page">
    <!-- 导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-content">
        <text class="nav-title">通讯录</text>
        <view class="nav-right" @tap="showAddFriend = true">
          <text>➕</text>
        </view>
      </view>
    </view>

    <!-- 搜索栏 -->
    <view class="search-bar">
      <view class="search-inner" @tap="goSearch">
        <text class="search-icon">🔍</text>
        <text class="search-placeholder">搜索联系人</text>
      </view>
    </view>

    <!-- 功能入口 -->
    <view class="func-section">
      <view class="func-item" @tap="goFriendRequests">
        <view class="func-icon">👥</view>
        <text class="func-label">新的朋友</text>
        <view v-if="friendRequests.length" class="func-badge">
          <text>{{ friendRequests.length }}</text>
        </view>
        <text class="func-arrow">›</text>
      </view>
      <view class="func-item" @tap="goGroups">
        <view class="func-icon">👨‍👩‍👧‍👦</view>
        <text class="func-label">我的群聊</text>
        <text class="func-arrow">›</text>
      </view>
      <view class="func-item" @tap="showJoinFamily = true">
        <view class="func-icon">🔑</view>
        <text class="func-label">加入家庭群</text>
        <text class="func-arrow">›</text>
      </view>
      <view class="func-item" @tap="goAgents">
        <view class="func-icon">🤖</view>
        <text class="func-label">数字人</text>
        <text class="func-arrow">›</text>
      </view>
    </view>

    <!-- 好友列表 -->
    <scroll-view scroll-y class="friend-list" :style="{ height: listHeight + 'px' }">
      <!-- 加载骨架屏 -->
      <skeleton v-if="loading" mode="list" :count="8" />

      <!-- 空状态 -->
      <empty-state
        v-else-if="friends.length === 0"
        icon="👤"
        title="暂无联系人"
        description="点击右上角添加好友"
      />
      <view v-else>
        <!-- 字母索引分组 -->
        <view
          v-for="(group, letter) in groupedFriends"
          :key="letter"
          class="friend-group"
        >
          <view class="group-header">
            <text class="group-letter">{{ letter }}</text>
          </view>
          <view
            v-for="friend in group"
            :key="friend.id"
            class="friend-item"
            @tap="goChat(friend)"
          >
            <view class="friend-avatar">
              <image
                v-if="friend.avatar_url"
                :src="api.toAbsoluteMediaUrl(friend.avatar_url)"
                class="avatar-img"
                mode="aspectFill"
              />
              <view v-else class="avatar-placeholder">
                <text>{{ friend.avatar || (friend.nickname || friend.username || '?')[0] }}</text>
              </view>
            </view>
            <view class="friend-info">
              <text class="friend-name">{{ friend.nickname || friend.username }}</text>
              <text v-if="friend.signature" class="friend-sign">{{ friend.signature }}</text>
            </view>
          </view>
        </view>
      </view>
    </scroll-view>

    <!-- 添加好友弹窗 -->
    <view v-if="showAddFriend" class="modal-mask" @tap="showAddFriend = false">
      <view class="modal-content" @tap.stop>
        <text class="modal-title">添加好友</text>
        <view class="modal-input-wrap">
          <input
            v-model="searchKeyword"
            placeholder="输入用户名或邮箱搜索"
            class="modal-input"
          />
        </view>
        <view class="modal-btns">
          <view class="modal-btn cancel" @tap="showAddFriend = false">
            <text>取消</text>
          </view>
          <view class="modal-btn confirm" @tap="handleSearchFriend">
            <text>搜索</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 好友请求弹窗 -->
    <view v-if="showRequests" class="modal-mask" @tap="showRequests = false">
      <view class="modal-content request-modal" @tap.stop>
        <text class="modal-title">新的朋友</text>
        <scroll-view scroll-y class="request-list">
          <view v-if="friendRequests.length === 0" class="request-empty">
            <text>暂无新的好友请求</text>
          </view>
          <view v-for="req in friendRequests" :key="req.id" class="request-item">
            <view class="friend-avatar">
              <image v-if="req.avatar_url" :src="api.toAbsoluteMediaUrl(req.avatar_url)" class="avatar-img" mode="aspectFill" />
              <view v-else class="avatar-placeholder"><text>{{ req.avatar || (req.nickname || '?')[0] }}</text></view>
            </view>
            <view class="request-info">
              <text class="friend-name">{{ req.nickname || '新朋友' }}</text>
              <text class="friend-sign">{{ req.message || '请求添加你为好友' }}</text>
            </view>
            <view class="request-actions">
              <view class="request-btn reject" @tap="handleFriendRequest(req, 'reject')"><text>拒绝</text></view>
              <view class="request-btn accept" @tap="handleFriendRequest(req, 'accept')"><text>接受</text></view>
            </view>
          </view>
        </scroll-view>
      </view>
    </view>

    <!-- 加入家庭群弹窗 -->
    <view v-if="showJoinFamily" class="modal-mask" @tap="showJoinFamily = false">
      <view class="modal-content" @tap.stop>
        <text class="modal-title">加入家庭群</text>
        <text class="modal-desc">输入家人分享的邀请码，加入后你的数字人也会进入这个家庭群。</text>
        <view class="modal-input-wrap">
          <input
            v-model="familyCode"
            placeholder="请输入 6 位邀请码"
            class="modal-input code-input"
            :maxlength="12"
          />
        </view>
        <view class="modal-btns">
          <view class="modal-btn cancel" @tap="showJoinFamily = false">
            <text>取消</text>
          </view>
          <view class="modal-btn confirm" @tap="handleJoinFamily">
            <text>加入</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useUserStore } from '../../stores/user'
import { useChatStore } from '../../stores/chat'
import * as api from '../../utils/api'
import Skeleton from '../../components/skeleton.vue'
import EmptyState from '../../components/empty-state.vue'

const userStore = useUserStore()
const chatStore = useChatStore()

const statusBarHeight = ref(44)
const listHeight = ref(500)
const loading = ref(false)
const friends = ref([])
const friendRequests = ref([])
const showAddFriend = ref(false)
const showRequests = ref(false)
const showJoinFamily = ref(false)
const searchKeyword = ref('')
const familyCode = ref('')

// 按首字母分组
const groupedFriends = computed(() => {
  const groups = {}
  friends.value.forEach(f => {
    const name = (f.nickname || f.username || '').trim()
    let letter = '#'
    if (name) {
      const first = name[0].toUpperCase()
      if (/[A-Z]/.test(first)) {
        letter = first
      } else if (/[\u4e00-\u9fa5]/.test(first)) {
        // 简化：中文按拼音首字母分组
        letter = getPinyinInitial(first)
      } else {
        letter = '#'
      }
    }
    if (!groups[letter]) groups[letter] = []
    groups[letter].push(f)
  })
  // 排序
  const sorted = {}
  Object.keys(groups).sort().forEach(k => {
    sorted[k] = groups[k]
  })
  return sorted
})

onShow(() => {
  if (!userStore.checkLogin()) return
  const sysInfo = uni.getSystemInfoSync()
  statusBarHeight.value = sysInfo.statusBarHeight || 44
  const navH = statusBarHeight.value + 44
  const searchBarH = 56
  const funcH = 240
  listHeight.value = sysInfo.windowHeight - navH - searchBarH - funcH - 50
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const [friendsRes, requestsRes] = await Promise.all([
      api.getFriends().catch(() => []),
      api.getFriendRequests().catch(() => [])
    ])
    friends.value = Array.isArray(friendsRes) ? friendsRes : (friendsRes.friends || [])
    friendRequests.value = Array.isArray(requestsRes) ? requestsRes : (requestsRes.requests || [])
  } finally {
    loading.value = false
  }
}

function goSearch() {
  uni.navigateTo({ url: '/pages/search/search' })
}

async function goFriendRequests() {
  showRequests.value = true
  await loadData()
}

function goGroups() {
  uni.switchTab({ url: '/pages/index/index' })
}

function goAgents() {
  uni.navigateTo({ url: '/pages/agents/manage' })
}

async function goChat(friend) {
  uni.showLoading({ title: '正在打开聊天...' })
  try {
    const group = await api.getOrCreateDirectGroup(friend.id)
    uni.hideLoading()
    uni.navigateTo({
      url: `/pages/chat/chat?groupId=${group.id}&name=${encodeURIComponent(friend.remark || friend.nickname || '私聊')}`
    })
  } catch (e) {
    uni.hideLoading()
    uni.showToast({ title: e.message || '打开聊天失败', icon: 'none' })
  }
}

function handleSearchFriend() {
  if (!searchKeyword.value.trim()) {
    uni.showToast({ title: '请输入搜索内容', icon: 'none' })
    return
  }
  showAddFriend.value = false
  uni.navigateTo({
    url: `/pages/search/search?q=${encodeURIComponent(searchKeyword.value)}`
  })
}

async function handleFriendRequest(req, action) {
  try {
    await api.handleFriendRequest({ request_id: req.id, action })
    uni.showToast({ title: action === 'accept' ? '已添加好友' : '已拒绝', icon: 'success' })
    await loadData()
  } catch (e) {
    uni.showToast({ title: e.message || '处理失败', icon: 'none' })
  }
}

async function handleJoinFamily() {
  const code = familyCode.value.trim().toUpperCase()
  if (!code) {
    uni.showToast({ title: '请输入邀请码', icon: 'none' })
    return
  }
  uni.showLoading({ title: '正在加入...' })
  try {
    const res = await api.joinFamilyByCode(code)
    uni.hideLoading()
    showJoinFamily.value = false
    familyCode.value = ''
    await chatStore.loadGroups()
    uni.showToast({ title: res?.already_joined ? '已在群内' : '加入成功', icon: 'success' })
    uni.navigateTo({
      url: `/pages/chat/chat?groupId=${res.group_id}&name=${encodeURIComponent(res.group_name || '家庭群')}`
    })
  } catch (e) {
    uni.hideLoading()
    uni.showToast({ title: e.message || '加入失败', icon: 'none' })
  }
}

// 获取拼音首字母（简化版）
function getPinyinInitial(char) {
  const code = char.charCodeAt(0)
  // 简单映射常用中文字符到字母
  const table = 'ABCDEFGHJKLMNOPQRSTWXYZ'
  const gbCode = code - 0x4e00
  const idx = gbCode % 26
  return table[idx] || '#'
}
</script>

<style lang="scss" scoped>
.contacts-page {
  min-height: 100vh;
  background: var(--bg-color);
}

.nav-bar {
  background: $primary-color;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 88rpx;
  padding: 0 30rpx;
}

.nav-title {
  font-size: $font-lg;
  font-weight: bold;
  color: #ffffff;
}

.nav-right {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36rpx;
  color: #ffffff;

  &:active {
    opacity: 0.7;
  }
}

.search-bar {
  padding: 16rpx 30rpx;
  background: $primary-color;
}

.search-inner {
  display: flex;
  align-items: center;
  height: 72rpx;
  background: rgba(255, 255, 255, 0.2);
  border-radius: $radius-base;
  padding: 0 24rpx;
}

.search-icon {
  font-size: 28rpx;
  margin-right: 12rpx;
}

.search-placeholder {
  font-size: $font-base;
  color: rgba(255, 255, 255, 0.7);
}

.func-section {
  background: var(--card-bg);
  margin-bottom: 16rpx;
}

.func-item {
  display: flex;
  align-items: center;
  padding: 28rpx 30rpx;
  border-bottom: 1rpx solid var(--border-color);
  transition: background 0.2s;

  &:last-child {
    border-bottom: none;
  }

  &:active {
    background: var(--bg-color);
  }
}

.func-icon {
  font-size: 44rpx;
  margin-right: 24rpx;
}

.func-label {
  flex: 1;
  font-size: $font-base;
  color: var(--text-primary);
}

.func-badge {
  min-width: 36rpx;
  height: 36rpx;
  padding: 0 10rpx;
  background: $danger-color;
  border-radius: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: $font-xs;
  color: #ffffff;
  margin-right: 16rpx;
}

.func-arrow {
  font-size: $font-lg;
  color: var(--text-placeholder);
}

.friend-list {
  background: var(--card-bg);
}



.group-header {
  padding: 12rpx 30rpx;
  background: var(--bg-color);
}

.group-letter {
  font-size: $font-sm;
  color: var(--text-secondary);
  font-weight: 500;
}

.friend-item {
  display: flex;
  align-items: center;
  padding: 20rpx 30rpx;
  border-bottom: 1rpx solid var(--border-color);
  transition: background 0.2s;

  &:active {
    background: var(--bg-color);
  }
}

.friend-avatar {
  margin-right: 24rpx;
  flex-shrink: 0;
}

.avatar-img {
  width: 80rpx;
  height: 80rpx;
  border-radius: $radius-base;
}

.avatar-placeholder {
  width: 80rpx;
  height: 80rpx;
  border-radius: $radius-base;
  background: $primary-color;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  font-weight: bold;
  color: #ffffff;
}

.friend-info {
  flex: 1;
  min-width: 0;
}

.friend-name {
  font-size: $font-base;
  color: var(--text-primary);
  font-weight: 500;
}

.friend-sign {
  font-size: $font-sm;
  color: var(--text-secondary);
  margin-top: 6rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 弹窗 */
.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  width: 600rpx;
  background: var(--card-bg);
  border-radius: $radius-lg;
  padding: 48rpx 40rpx;
}

.modal-title {
  font-size: $font-lg;
  font-weight: bold;
  color: var(--text-primary);
  text-align: center;
  margin-bottom: 40rpx;
}

.modal-desc {
  display: block;
  margin: -20rpx 0 28rpx;
  color: var(--text-secondary);
  font-size: $font-sm;
  line-height: 1.5;
  text-align: center;
}

.modal-input-wrap {
  margin-bottom: 24rpx;
}

.modal-input {
  height: 88rpx;
  background: var(--bg-color);
  border-radius: $radius-base;
  padding: 0 24rpx;
  font-size: $font-base;
  color: var(--text-primary);
}

.code-input {
  text-align: center;
  letter-spacing: 8rpx;
  font-weight: 700;
}

.modal-btns {
  display: flex;
  gap: 24rpx;
  margin-top: 40rpx;
}

.modal-btn {
  flex: 1;
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: $radius-base;
  font-size: $font-base;
  font-weight: 500;

  &:active {
    opacity: 0.8;
  }

  &.cancel {
    background: var(--bg-color);
    color: var(--text-secondary);
  }

  &.confirm {
    background: $primary-color;
    color: #ffffff;
  }
}

.request-modal {
  width: 680rpx;
}
.request-list {
  max-height: 640rpx;
}
.request-empty {
  padding: 56rpx 0;
  text-align: center;
  color: var(--text-secondary);
  font-size: $font-base;
}
.request-item {
  display: flex;
  align-items: center;
  padding: 22rpx 0;
  border-bottom: 1rpx solid var(--border-color);
}
.request-info {
  flex: 1;
  min-width: 0;
}
.request-actions {
  display: flex;
  gap: 12rpx;
}
.request-btn {
  min-width: 84rpx;
  height: 56rpx;
  border-radius: 28rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: $font-sm;
}
.request-btn.reject {
  background: var(--bg-color);
  color: var(--text-secondary);
}
.request-btn.accept {
  background: $primary-color;
  color: #fff;
}
</style>
