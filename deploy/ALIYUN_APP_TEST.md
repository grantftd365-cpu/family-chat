# FamilyChat 阿里云部署与 APP 模拟器测试

本文用于把后端部署到阿里云 ECS，并让本机手机模拟器/APP 连接测试。

## 1. 阿里云准备

1. ECS 建议：Ubuntu 22.04/24.04，2C2G 起步。
2. 安全组放行：`22`、`80`、`443`；临时裸端口测试可额外放行 `8000`，正式测试建议走 HTTPS。
3. 域名解析：把 `chat.yourdomain.com` 的 A 记录指向 ECS 公网 IP。

> 没有域名时可以先用 `http://ECS公网IP:8000` 测试 APP；微信小程序和正式 APP 发布必须使用 HTTPS 域名。

## 2. 服务器首次部署

SSH 登录服务器后执行：

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nginx curl sqlite3

sudo mkdir -p /opt
cd /opt
sudo git clone https://github.com/grantftd365-cpu/family-chat.git
sudo chown -R $USER:$USER /opt/family-chat
cd /opt/family-chat

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
python3 - <<'PY'
from pathlib import Path
import secrets

path = Path('.env')
text = path.read_text(encoding='utf-8')
replacements = {
    'SECRET_KEY=': f'SECRET_KEY={secrets.token_hex(32)}',
    'HOST=0.0.0.0': 'HOST=0.0.0.0',
    'PORT=8000': 'PORT=8000',
}
for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)
if 'ENV=' not in text:
    text += '\nENV=production\n'
path.write_text(text, encoding='utf-8')
PY

mkdir -p data/uploads data/voices data/avatars data/backups data/refinement_uploads
python run.py
```

打开另一个 SSH 窗口验证：

```bash
curl http://127.0.0.1:8000/api/status
```

看到 JSON 即表示后端启动成功。确认后按 `Ctrl+C` 退出前台服务。

## 3. systemd 后台运行

```bash
sudo cp deploy/familychat.service /etc/systemd/system/familychat.service
sudo systemctl daemon-reload
sudo systemctl enable --now familychat
sudo systemctl status familychat --no-pager
journalctl -u familychat -f
```

如果 service 使用 `www-data` 权限，请确保数据目录可写：

```bash
sudo chown -R www-data:www-data /opt/family-chat/data
sudo chown www-data:www-data /opt/family-chat/.env
sudo systemctl restart familychat
```

## 4. HTTPS + Nginx

把 `chat.yourdomain.com` 替换为你的域名：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo cp deploy/nginx-familychat.conf /etc/nginx/sites-available/familychat
sudo sed -i 's/chat.yourdomain.com/你的域名/g' /etc/nginx/sites-available/familychat
sudo ln -sf /etc/nginx/sites-available/familychat /etc/nginx/sites-enabled/familychat
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d 你的域名
```

编辑 `/opt/family-chat/.env`，设置 CORS：

```bash
CORS_ORIGINS=https://你的域名,http://localhost:5173,http://127.0.0.1:5173
```

同时确认炼化/聊天使用的 LLM Key 是真实值，不要填 APP 里显示的 `***` 脱敏值：

```bash
sudo nano /opt/family-chat/.env

LLM_PROVIDER=deepseek
LLM_API_KEY=sk-你的真实DeepSeekKey
LLM_MODEL=deepseek-v4-flash
LLM_BASE_URL=
```

> APP 里的“AI 模型配置”可用于临时联调；如果页面提示“API Key 已配置”，留空保存不会覆盖旧 Key，只有输入新的完整 Key 才会更新。

重启并验证：

```bash
sudo systemctl restart familychat
curl https://你的域名/api/status
```

## 5. APP 连接阿里云

在本机项目里创建 `family-chat-app/.env.local`：

```env
VITE_SERVER_URL=https://你的域名
```

没有域名、只做临时联调时：

```env
VITE_SERVER_URL=http://ECS公网IP:8000
```

然后运行：

```bash
cd family-chat-app
npm install
npm run dev:app
```

在模拟器启动后，登录页底部会显示“服务器：...”。如果要临时切换地址，点击该文字，填写 `https://你的域名` 并保存。

## 6. 独立 APK 云打包

项目是经典 `uni-app + Vue 3` 架构，可以打包成独立 Android APK。这个 APK 不是浏览器网页测试，也不是 HBuilderX 调试基座；应用资源会随 APK 安装，运行后通过 API/WebSocket 连接阿里云后端。

云打包前先完成 DCloud 前置配置：

1. 在 HBuilderX 登录 DCloud 账号。
2. 打开 DCloud 账号资料页 `https://dev.dcloud.net.cn/pages/user/info`，确认账号已绑定手机号。
3. 打开 `family-chat-app/src/manifest.json`，用 HBuilderX 的可视化界面重新获取/绑定 DCloud AppID。
4. 确认 `appid` 不再是占位值 `__UNI__FAMILY_CHAT`，当前项目正式 AppID 为 `__UNI__73C711F`。
5. 新应用已不能使用 Android 公共测试证书；测试 APK 和上架包都建议使用自有证书，包名固定为 `com.grantclaw.familychat`。

如果 CLI 返回 `当前账号尚未绑定手机号` 或 `manifest.json中的AppID无效`，先完成上面的第 2–4 步后再重新打包。

在本机创建生产环境配置：

```env
VITE_SERVER_URL=https://grantclaw.com/family-chat
```

文件路径：`family-chat-app/.env.production`。该文件已被 `.gitignore` 忽略，不要提交真实环境文件。

使用 HBuilderX CLI 触发 Android 云打包。测试证书文件不要提交到 GitHub，可放在本机 `_local-certs/`：

```powershell
$project = "C:\path\to\family-chat\family-chat-app"
$keystore = "C:\path\to\family-chat\_local-certs\family-chat-test.keystore"
& "C:\path\to\HBuilderX\cli.exe" pack `
  --project $project `
  --platform android `
  --android.packagename com.grantclaw.familychat `
  --android.androidpacktype 0 `
  --android.certalias familychat `
  --android.certfile $keystore `
  --android.certpassword "你的证书密码" `
  --android.storepassword "你的证书库密码" `
  --safemode false `
  --sourceMap false `
  --ignoreWarnings true
```

查询云打包状态：

```powershell
& "C:\path\to\HBuilderX\cli.exe" pack status --project $project
```

拿到 APK 后安装到模拟器：

```powershell
adb install -r .\FamilyChat.apk
adb shell monkey -p com.grantclaw.familychat -c android.intent.category.LAUNCHER 1
```

后续上架说明：Android 应用商店需要使用同一套自有签名证书持续打包；iOS App Store 仍可走 uni-app/HBuilderX iOS 打包，但需要 Apple Developer 账号、Bundle ID、证书和描述文件。
模拟器兼容性说明：当前 DCloud Android APK 会包含 `armeabi-v7a`、`arm64-v8a`、`x86` 原生库。Windows 模拟器推荐使用普通 4KB page size 的 Android x86 镜像（例如 `system-images;android-29;default;x86`）。不要使用 `ps16k`/16KB page size 镜像测试当前 APK；这类镜像会出现原生库 page-size/alignment 不兼容。纯 `x86_64` 模拟器也可能因为 APK 不含 `x86_64` so 而无法安装。

## 7. 测试账号与流程

1. 登录页点击“注册”，创建第一个用户。
2. 进入首页后发送文字消息。
3. 进入聊天页测试：文字、图片、语音、断网重连。
4. 进入“设置 → 服务器连接”，确认服务器地址为阿里云地址。
5. 进入“设置 → AI 模型配置”，填入可用 LLM API Key 后测试数字人回复。
6. 服务器侧看日志：`journalctl -u familychat -f`。

## 8. 常见问题

- APP 提示网络失败：先确认后端 `https://grantclaw.com/family-chat/api/status` 正常；如果只在 Android 模拟器失败，通常是模拟器 DNS 问题。重启模拟器时指定 DNS：`emulator -avd FamilyChat_x86_4KB -dns-server 223.5.5.5,8.8.8.8`，再用 `adb shell ping -c 1 grantclaw.com` 确认域名能解析。
- 炼化数字人报 401：这通常不是 APP 登录失效，而是 DeepSeek/LLM 上游 Key 无效、过期、余额不足，或误把 `sk-xxxx***` 脱敏值保存成真实 Key。到 `/opt/family-chat/.env` 写入完整 `LLM_API_KEY` 后执行 `sudo systemctl restart familychat`，并用 `journalctl -u familychat -n 100 --no-pager` 查看日志。
- WebSocket 断开：确认 Nginx `/ws` 配置存在，并且证书域名正确。
- 500 错误：查看 `journalctl -u familychat -n 100 --no-pager`。
- AI 不回复：确认 `.env` 里 `LLM_API_KEY`、`LLM_PROVIDER`、`LLM_MODEL` 已配置。
- 小程序不能请求：微信后台必须配置 request/uploadFile/downloadFile/socket 合法域名，且不能使用 IP 或 HTTP。
