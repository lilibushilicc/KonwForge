#!/usr/bin/env bash
# KonwForge 一键部署脚本（在 VPS 上以 root 运行）
# 前置：已把 quiz-deploy.tar.gz 解压到 /opt/knowforge（含 quiz-server/ quiz-web/dist deploy/）
set -euo pipefail

APP_DIR=/opt/knowforge
SRV=$APP_DIR/quiz-server
VENV=$APP_DIR/venv

if [ "$(id -u)" -ne 0 ]; then
  echo "!! 请用 root 运行（sudo bash deploy/deploy.sh）"
  exit 1
fi

echo "==> [1/7] 安装系统依赖"
# 发行版差异：Debian/Ubuntu 走 apt；Alibaba Cloud Linux / RHEL 系走 dnf，
# 且 Python 不用系统包（系统 python 往往是 3.6），统一交给 uv 管理。
if command -v apt-get >/dev/null 2>&1; then
  if ! command -v python3.12 >/dev/null 2>&1; then
    apt-get update
    apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip nginx git curl
  fi
  command -v nginx >/dev/null 2>&1 || { apt-get update; apt-get install -y nginx; }
elif command -v dnf >/dev/null 2>&1; then
  command -v nginx >/dev/null 2>&1 || dnf install -y nginx
else
  echo "!! 未识别的包管理器（无 apt-get/dnf），请自行确保 nginx 与 Python 3.12 可用"
fi

echo "==> [2/7] 创建虚拟环境并安装后端依赖（uv 优先）"
if [ ! -x "$VENV/bin/python" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv "$VENV" --python 3.12
  else
    python3.12 -m venv "$VENV"
  fi
fi
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$VENV/bin/python" -r "$SRV/requirements.txt"
else
  "$VENV/bin/pip" install --upgrade pip
  "$VENV/bin/pip" install -r "$SRV/requirements.txt"
fi

echo "==> [3/7] 准备 .env"
if [ ! -f "$SRV/.env" ]; then
  cp "$APP_DIR/deploy/.env.vps" "$SRV/.env"
  echo "    已生成 $SRV/.env（基于模板）"
fi
if grep -q "REPLACE_WITH_TURSO_TOKEN" "$SRV/.env"; then
  echo "!! 请先把 $SRV/.env 里的 REPLACE_WITH_TURSO_TOKEN 换成真实 Turso authToken 再运行。"
  echo "   编辑：nano $SRV/.env   然后重跑：bash $APP_DIR/deploy/deploy.sh"
  exit 1
fi

echo "==> [4/7] 执行数据库迁移 (alembic upgrade head)"
cd "$SRV"
"$VENV/bin/alembic" upgrade head

echo "==> [5/7] 安装 systemd 服务"
cp "$APP_DIR/deploy/quiz-server.service" /etc/systemd/system/quiz-server.service
systemctl daemon-reload
systemctl enable quiz-server
systemctl restart quiz-server
sleep 3
if systemctl is-active --quiet quiz-server; then
  echo "    backend: active"
else
  echo "!! backend 启动失败，看日志：journalctl -u quiz-server -n 50 --no-pager"
  exit 1
fi

echo "==> [6/7] 安装 nginx 站点"
cp "$APP_DIR/deploy/knowforge.nginx" /etc/nginx/sites-available/knowforge
ln -sf /etc/nginx/sites-available/knowforge /etc/nginx/sites-enabled/knowforge
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx

echo "==> [7/7] 开放防火墙 80 端口"
if command -v ufw >/dev/null 2>&1; then
  ufw allow 80/tcp || true
fi

echo ""
echo "==> 完成！访问 http://39.98.69.153/"
echo "    后端健康检查：http://39.98.69.153/health"
