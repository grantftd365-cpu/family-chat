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
2. 打开 `family-chat-app/src/manifest.json`，用 HBuilderX 的可视化界面重新获取/绑定 DCloud AppID。
3. 确认 `appid` 不再是占位值 `__UNI__FAMILY_CHAT`，而是 DCloud 分配的 `__UNI__...` 正式应用标识。
4. 测试 APK 可先用公共证书；准备上架 Android 应用商店时再切换为自有证书。

在本机创建生产环境配置：

```env
VITE_SERVER_URL=https://grantclaw.com/family-chat
```

文件路径：`family-chat-app/.env.production`。该文件已被 `.gitignore` 忽略，不要提交真实环境文件。

使用 HBuilderX CLI 触发 Android 云打包：

```powershell
$project = "C:\path\to\family-chat\family-chat-app"
& "C:\path\to\HBuilderX\cli.exe" pack `
  --project $project `
  --platform android `
  --android.packagename com.grantclaw.familychat `
  --android.androidpacktype 1 `
  --safemode true `
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

后续上架说明：Android 应用商店需要使用自有签名证书重新打包；iOS App Store 仍可走 uni-app/HBuilderX iOS 打包，但需要 Apple Developer 账号、Bundle ID、证书和描述文件。

## 7. 测试账号与流程

1. 登录页点击“注册”，创建第一个用户。
2. 进入首页后发送文字消息。
3. 进入聊天页测试：文字、图片、语音、断网重连。
4. 进入“设置 → 服务器连接”，确认服务器地址为阿里云地址。
5. 进入“设置 → AI 模型配置”，填入可用 LLM API Key 后测试数字人回复。
6. 服务器侧看日志：`journalctl -u familychat -f`。

## 8. 常见问题

- APP 提示网络失败：确认模拟器能打开 `https://你的域名/api/status`，并检查 ECS 安全组和 Nginx。
- WebSocket 断开：确认 Nginx `/ws` 配置存在，并且证书域名正确。
- 500 错误：查看 `journalctl -u familychat -n 100 --no-pager`。
- AI 不回复：确认 `.env` 里 `LLM_API_KEY`、`LLM_PROVIDER`、`LLM_MODEL` 已配置。
- 小程序不能请求：微信后台必须配置 request/uploadFile/downloadFile/socket 合法域名，且不能使用 IP 或 HTTP。
