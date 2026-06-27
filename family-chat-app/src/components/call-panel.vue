<template>
  <!-- 通话界面 -->
  <view v-if="visible" class="call-overlay">
    <!-- 通话状态 -->
    <view class="call-status">
      <text class="call-status-text">{{ statusText }}</text>
      <text v-if="callDuration" class="call-duration">{{ callDuration }}</text>
    </view>

    <!-- 对方信息 -->
    <view class="call-user-info">
      <view class="call-avatar">
        <image v-if="remoteAvatar" :src="remoteAvatar" class="avatar-img" mode="aspectFill" />
        <view v-else class="avatar-placeholder">
          <text>{{ (remoteName || '?')[0] }}</text>
        </view>
      </view>
      <text class="call-user-name">{{ remoteName }}</text>
      <text class="call-type-label">{{ callType === 'video' ? '视频通话' : '语音通话' }}</text>
    </view>

    <!-- 视频预览（视频通话时） -->
    <view v-if="callType === 'video' && callStatus === 'connected'" class="video-container">
      <view class="remote-video" id="remoteVideo">
        <!-- 远程视频流 -->
      </view>
      <view class="local-video" id="localVideo">
        <!-- 本地视频预览 -->
      </view>
    </view>

    <!-- 操作按钮 -->
    <view class="call-actions">
      <!-- 被叫方：接听/拒接 -->
      <view v-if="callStatus === 'ringing' && !isCaller" class="action-row">
        <view class="action-btn reject-btn" @tap="rejectCall">
          <text class="btn-icon">📞</text>
          <text class="btn-label">拒接</text>
        </view>
        <view class="action-btn accept-btn" @tap="acceptCall">
          <text class="btn-icon">📞</text>
          <text class="btn-label">接听</text>
        </view>
      </view>

      <!-- 呼叫方：等待中/挂断 -->
      <view v-if="callStatus === 'ringing' && isCaller" class="action-row">
        <view class="action-btn reject-btn" @tap="endCall">
          <text class="btn-icon">📞</text>
          <text class="btn-label">取消</text>
        </view>
      </view>

      <!-- 通话中：静音/扬声器/挂断/摄像头 -->
      <view v-if="callStatus === 'connected'" class="action-row">
        <view class="action-btn" :class="{ active: isMuted }" @tap="toggleMute">
          <text class="btn-icon">{{ isMuted ? '🔇' : '🔊' }}</text>
          <text class="btn-label">{{ isMuted ? '取消静音' : '静音' }}</text>
        </view>
        <view class="action-btn" :class="{ active: isSpeaker }" @tap="toggleSpeaker">
          <text class="btn-icon">{{ isSpeaker ? '🔈' : '🔊' }}</text>
          <text class="btn-label">{{ isSpeaker ? '听筒' : '扬声器' }}</text>
        </view>
        <view v-if="callType === 'video'" class="action-btn" @tap="toggleCamera">
          <text class="btn-icon">🔄</text>
          <text class="btn-label">翻转</text>
        </view>
        <view class="action-btn reject-btn" @tap="endCall">
          <text class="btn-icon">📞</text>
          <text class="btn-label">挂断</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import ws from '../utils/ws'

export default {
  name: 'CallPanel',
  data() {
    return {
      visible: false,
      callId: '',
      callType: 'voice', // voice / video
      callStatus: '', // ringing / connected / ended
      isCaller: false,
      remoteUserId: '',
      remoteName: '',
      remoteAvatar: '',
      isMuted: false,
      isSpeaker: false,
      duration: 0,
      durationTimer: null,
      // WebRTC
      peerConnection: null,
      localStream: null,
    }
  },
  computed: {
    statusText() {
      if (this.callStatus === 'ringing') {
        return this.isCaller ? '正在呼叫...' : '对方正在呼叫...'
      }
      if (this.callStatus === 'connected') {
        return '通话中'
      }
      return ''
    },
    callDuration() {
      if (this.callStatus !== 'connected' || !this.duration) return ''
      const m = Math.floor(this.duration / 60)
      const s = this.duration % 60
      return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    },
  },
  created() {
    this.setupWebSocketListeners()
  },
  beforeUnmount() {
    this.cleanup()
  },
  methods: {
    setupWebSocketListeners() {
      ws.on('call_event', (data) => {
        const event = data.data || data
        const action = event.action

        if (action === 'call_invite') {
          this.handleIncomingCall(event)
        } else if (action === 'call_accept') {
          this.handleCallAccepted(event)
        } else if (action === 'call_reject') {
          this.handleCallRejected(event)
        } else if (action === 'call_end') {
          this.handleCallEnded(event)
        } else if (action === 'call_failed') {
          this.handleCallFailed(event)
        } else if (action === 'call_offer') {
          this.handleOffer(event)
        } else if (action === 'call_answer') {
          this.handleAnswer(event)
        } else if (action === 'call_candidate') {
          this.handleCandidate(event)
        }
      })
    },

    // 发起通话
    startCall(userId, userName, userAvatar, type = 'voice') {
      this.remoteUserId = userId
      this.remoteName = userName
      this.remoteAvatar = userAvatar
      this.callType = type
      this.callStatus = 'ringing'
      this.isCaller = true
      this.visible = true

      ws.send({
        type: 'call',
        action: 'call_invite',
        target_id: userId,
        call_type: type,
      })
    },

    // 收到通话邀请
    handleIncomingCall(event) {
      this.callId = event.call_id
      this.callType = event.call_type
      this.remoteUserId = event.caller_id
      this.remoteName = event.caller_name
      this.remoteAvatar = event.caller_avatar
      this.callStatus = 'ringing'
      this.isCaller = false
      this.visible = true

      // 振动提示
      uni.vibrateShort()
    },

    // 接听
    async acceptCall() {
      ws.send({
        type: 'call',
        action: 'call_accept',
        call_id: this.callId,
      })
      this.callStatus = 'connected'
      this.startTimer()
      await this.setupWebRTC()
    },

    // 拒接
    rejectCall() {
      ws.send({
        type: 'call',
        action: 'call_reject',
        call_id: this.callId,
      })
      this.cleanup()
    },

    // 挂断
    endCall() {
      ws.send({
        type: 'call',
        action: 'call_end',
        call_id: this.callId,
      })
      this.cleanup()
    },

    // 对方接听
    handleCallAccepted(event) {
      this.callId = event.call_id
      this.callStatus = 'connected'
      this.startTimer()
      this.setupWebRTC()
    },

    // 对方拒接
    handleCallRejected() {
      uni.showToast({ title: '对方已拒接', icon: 'none' })
      this.cleanup()
    },

    // 对方挂断
    handleCallEnded() {
      uni.showToast({ title: '通话已结束', icon: 'none' })
      this.cleanup()
    },

    // 呼叫失败
    handleCallFailed(event) {
      uni.showToast({ title: event.reason || '呼叫失败', icon: 'none' })
      this.cleanup()
    },

    // WebRTC 设置
    async setupWebRTC() {
      try {
        // 创建 RTCPeerConnection
        const config = {
          iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' },
          ]
        }
        this.peerConnection = new RTCPeerConnection(config)

        // 获取本地媒体流
        const constraints = {
          audio: true,
          video: this.callType === 'video',
        }

        try {
          this.localStream = await navigator.mediaDevices.getUserMedia(constraints)
        } catch (e) {
          console.error('获取媒体流失败:', e)
          uni.showToast({ title: '无法访问麦克风/摄像头', icon: 'none' })
          this.endCall()
          return
        }

        // 添加本地流到连接
        this.localStream.getTracks().forEach(track => {
          this.peerConnection.addTrack(track, this.localStream)
        })

        // ICE candidate 处理
        this.peerConnection.onicecandidate = (event) => {
          if (event.candidate) {
            ws.send({
              type: 'call',
              action: 'call_candidate',
              call_id: this.callId,
              candidate: event.candidate,
            })
          }
        }

        // 远程流处理
        this.peerConnection.ontrack = (event) => {
          // 远程音频/视频自动播放
          if (event.streams && event.streams[0]) {
            const remoteAudio = document.createElement('audio')
            remoteAudio.srcObject = event.streams[0]
            remoteAudio.autoplay = true
            document.body.appendChild(remoteAudio)
          }
        }

        // 如果是呼叫方，创建 offer
        if (this.isCaller) {
          const offer = await this.peerConnection.createOffer()
          await this.peerConnection.setLocalDescription(offer)
          ws.send({
            type: 'call',
            action: 'call_offer',
            call_id: this.callId,
            sdp: offer,
          })
        }
      } catch (e) {
        console.error('WebRTC 设置失败:', e)
      }
    },

    // 收到 SDP offer
    async handleOffer(event) {
      if (!this.peerConnection) return
      try {
        await this.peerConnection.setRemoteDescription(new RTCSessionDescription(event.sdp))
        const answer = await this.peerConnection.createAnswer()
        await this.peerConnection.setLocalDescription(answer)
        ws.send({
          type: 'call',
          action: 'call_answer',
          call_id: this.callId,
          sdp: answer,
        })
      } catch (e) {
        console.error('处理 offer 失败:', e)
      }
    },

    // 收到 SDP answer
    async handleAnswer(event) {
      if (!this.peerConnection) return
      try {
        await this.peerConnection.setRemoteDescription(new RTCSessionDescription(event.sdp))
      } catch (e) {
        console.error('处理 answer 失败:', e)
      }
    },

    // 收到 ICE candidate
    async handleCandidate(event) {
      if (!this.peerConnection) return
      try {
        await this.peerConnection.addIceCandidate(new RTCIceCandidate(event.candidate))
      } catch (e) {
        console.error('处理 candidate 失败:', e)
      }
    },

    // 静音
    toggleMute() {
      this.isMuted = !this.isMuted
      if (this.localStream) {
        this.localStream.getAudioTracks().forEach(track => {
          track.enabled = !this.isMuted
        })
      }
    },

    // 扬声器
    toggleSpeaker() {
      this.isSpeaker = !this.isSpeaker
      // 移动端需要原生 API 切换音频路由
    },

    // 翻转摄像头
    toggleCamera() {
      if (this.localStream) {
        const videoTrack = this.localStream.getVideoTracks()[0]
        if (videoTrack) {
          const currentFacing = videoTrack.getSettings().facingMode
          videoTrack.applyConstraints({
            facingMode: currentFacing === 'user' ? 'environment' : 'user'
          })
        }
      }
    },

    // 开始计时
    startTimer() {
      this.duration = 0
      this.durationTimer = setInterval(() => {
        this.duration++
      }, 1000)
    },

    // 清理
    cleanup() {
      if (this.durationTimer) {
        clearInterval(this.durationTimer)
        this.durationTimer = null
      }
      if (this.localStream) {
        this.localStream.getTracks().forEach(track => track.stop())
        this.localStream = null
      }
      if (this.peerConnection) {
        this.peerConnection.close()
        this.peerConnection = null
      }
      this.visible = false
      this.callId = ''
      this.callStatus = ''
      this.duration = 0
      this.isMuted = false
      this.isSpeaker = false
    },
  },
}
</script>

<style scoped>
.call-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  padding: 120rpx 60rpx 100rpx;
}

.call-status {
  text-align: center;
}

.call-status-text {
  color: rgba(255,255,255,0.8);
  font-size: 28rpx;
}

.call-duration {
  display: block;
  color: rgba(255,255,255,0.6);
  font-size: 24rpx;
  margin-top: 8rpx;
}

.call-user-info {
  text-align: center;
}

.call-avatar {
  width: 180rpx;
  height: 180rpx;
  border-radius: 50%;
  overflow: hidden;
  margin: 0 auto 30rpx;
  border: 4rpx solid rgba(255,255,255,0.3);
}

.avatar-img {
  width: 100%;
  height: 100%;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: rgba(255,255,255,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 60rpx;
  color: #fff;
}

.call-user-name {
  display: block;
  color: #fff;
  font-size: 40rpx;
  font-weight: 600;
  margin-bottom: 10rpx;
}

.call-type-label {
  color: rgba(255,255,255,0.6);
  font-size: 24rpx;
}

.call-actions {
  width: 100%;
}

.action-row {
  display: flex;
  justify-content: space-around;
  align-items: center;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
}

.btn-icon {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  background: rgba(255,255,255,0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48rpx;
}

.btn-label {
  color: rgba(255,255,255,0.8);
  font-size: 22rpx;
}

.reject-btn .btn-icon {
  background: #FA5151;
}

.accept-btn .btn-icon {
  background: #07C160;
}

.active .btn-icon {
  background: rgba(255,255,255,0.4);
}

.video-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 300rpx;
}

.remote-video {
  width: 100%;
  height: 100%;
  background: #000;
}

.local-video {
  position: absolute;
  top: 100rpx;
  right: 30rpx;
  width: 200rpx;
  height: 260rpx;
  border-radius: 16rpx;
  overflow: hidden;
  background: #333;
  border: 2rpx solid rgba(255,255,255,0.3);
}
</style>
