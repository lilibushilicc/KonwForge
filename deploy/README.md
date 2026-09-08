# KonwForge 部署到阿里云 VPS (39.98.69.153)

架构：nginx(:80) 同域托管前端静态文件 + 反代 `/api` → uvicorn(:8001)；数据库继续用 Turso(libSQL)。
前端已在本机预构建（`quiz-web/dist`），VPS 只需 Python3.12 + nginx，不依赖 node。

## 本机已完成
- `quiz-web/dist` 已构建（Vite）
- 部署包文件在 `deploy/`：`quiz-server.service` / `knowforge.nginx` / `.env.vps` / `deploy.sh`

## 你需要做的（3 步，用自己的 SSH 凭据）

> 我无法从这里无人值守 SSH（密钥未授权、密码交互式），最后的上传/执行由你在终端完成。
> 下面命令在本机 Git Bash / PowerShell 跑；`root@39.98.69.153` 改成你的实际用户名（探测显示 root 可登录且开了密码）。

### 0) 重新构建前端（VPS 同域版，API 走相对路径 /api/v1）
```bash
cd /d/study/system/quiz/quiz-web
# 用托管 node + 关掉 safe-delete 钩子（否则 vite 清 dist 会失败）
NODE_OPTIONS='' npx vite build --mode vps
# 校验：产物里不应含 onrender 后端地址，且应出现 /api/v1
grep -rl "quiz-server-83xe.onrender.com" dist && echo "!! 含 Render 地址，构建错了" || echo "OK: 纯 /api/v1"
```

### 1) 打包（构建完再打）
```bash
cd /d/study/system/quiz
tar czf /tmp/quiz-deploy.tar.gz \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='quiz-server/.venv' --exclude='quiz-server/.env' --exclude='quiz-server/data' \
  --exclude='.pytest_cache' \
  --exclude='quiz-web/node_modules' --exclude='quiz-web/src' --exclude='quiz-web/public' \
  quiz-server quiz-web/dist deploy
```

### 2) 上传并解压到 VPS
```bash
cat /tmp/quiz-deploy.tar.gz | ssh root@39.98.69.153 'mkdir -p /opt/knowforge && cd /opt/knowforge && tar xzf -'
```

### 3) 在 VPS 上填 Turso token 并部署
```bash
# 登录 VPS
ssh root@39.98.69.153

# 编辑 .env，把 REPLACE_WITH_TURSO_TOKEN 换成真实 authToken（从 Render 控制台或你的记录取）
nano /opt/knowforge/quiz-server/.env

# 一键部署
bash /opt/knowforge/deploy/deploy.sh
```

## 验证
- 前端：浏览器打开 http://39.98.69.153/
- 后端健康：http://39.98.69.153/health → `{"status":"ok",...}`
- 日志：`journalctl -u quiz-server -f` / `journalctl -u nginx -f`

## 常用运维
- 重启后端：`systemctl restart quiz-server`
- 改代码后重部署：本机重新 `tar` → `ssh` 解压 → `systemctl restart quiz-server`（仅后端变更无需动 nginx）
- 看迁移：`cd /opt/knowforge/quiz-server && /opt/knowforge/venv/bin/alembic upgrade head`

## 注意
- Turso 在东京，VPS 在国内，偶有延迟；属正常。
- 裸 IP + HTTP，无 HTTPS。要 HTTPS 后续可在 Cloudflare 把 knowforge.270312.xyz 指向该 IP 并开代理（另议）。
- `quiz-server/.env` 含密钥，**不要**提交进公开仓库。
