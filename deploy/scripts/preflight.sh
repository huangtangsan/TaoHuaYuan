#!/usr/bin/env bash
# 部署自检：首次部署后、或每次改完配置跑一遍
# 用法：bash /opt/webstack/deploy/scripts/preflight.sh
# 只读检查，不会修改任何东西。

set -uo pipefail

APP_DIR="${APP_DIR:-/opt/webstack}"
CONTAINER="${CONTAINER:-webstack}"
ok=0
warn=0
bad=0

pass() { printf '  \033[32m✓\033[0m %s\n' "$1"; ok=$((ok + 1)); }
warn_() { printf '  \033[33m!\033[0m %s\n' "$1"; warn=$((warn + 1)); }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1"; bad=$((bad + 1)); }

echo "== 1. 运行环境 =="
command -v docker >/dev/null 2>&1 && pass "docker 已安装" || fail "找不到 docker"
docker compose version >/dev/null 2>&1 && pass "compose 插件可用" || fail "docker compose 不可用"
docker network inspect 1panel-network >/dev/null 2>&1 \
    && pass "1panel-network 存在" \
    || fail "1panel-network 不存在：docker network create 1panel-network"

echo "== 2. 项目文件 =="
for path in app/main.py requirements.txt frontend/dist/index.html docker-compose.yml; do
    [ -e "$APP_DIR/$path" ] && pass "$path" || fail "$path 缺失"
done

echo "== 3. 环境变量 =="
if [ -f "$APP_DIR/.env" ]; then
    perm=$(stat -c '%a' "$APP_DIR/.env" 2>/dev/null || echo '?')
    [ "$perm" = "600" ] && pass ".env 权限 600" || warn_ ".env 权限是 $perm，建议 chmod 600"
    if grep -q '^WEBSTACK_JWT_SECRET=replace-with' "$APP_DIR/.env"; then
        fail "WEBSTACK_JWT_SECRET 还是模板值"
    else
        pass "JWT 密钥已替换"
    fi
    grep -q '^WEBSTACK_COOKIE_SECURE=1' "$APP_DIR/.env" \
        && pass "Cookie 仅 HTTPS" \
        || warn_ "WEBSTACK_COOKIE_SECURE 不是 1（HTTPS 配好后应打开）"
    grep -q '^WEBSTACK_DOCS=0' "$APP_DIR/.env" \
        && pass "接口文档已关闭" \
        || warn_ "WEBSTACK_DOCS 不是 0，/api/docs 对公网可见"
else
    fail ".env 不存在：cp .env.example .env"
fi

echo "== 4. 容器与后端 =="
if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    pass "容器 $CONTAINER 运行中"
    if docker inspect "$CONTAINER" --format '{{.State.Health.Status}}' 2>/dev/null | grep -qx healthy; then
        pass "健康检查通过"
    else
        warn_ "健康检查未通过（启动 20 秒内属正常）"
    fi
    if docker exec "$CONTAINER" python -c \
        "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8300/api/health', timeout=4).status==200 else 1)" >/dev/null 2>&1; then
        pass "容器内 /api/health 200"
    else
        fail "容器内 /api/health 不通，看 docker compose logs"
    fi
else
    fail "容器 $CONTAINER 没在跑：cd $APP_DIR && docker compose up -d"
fi

echo "== 5. 端口暴露面 =="
if command -v ss >/dev/null 2>&1; then
    if ss -tlnp 2>/dev/null | grep -q '127.0.0.1:8300'; then
        pass "8300 只监听回环地址"
    elif ss -tlnp 2>/dev/null | grep -q '0.0.0.0:8300'; then
        fail "8300 监听 0.0.0.0，可能对公网暴露，检查防火墙"
    else
        warn_ "没看到 8300 监听"
    fi
fi

echo "== 6. 反向代理地址建议 =="
openresty=$(docker ps --format '{{.Names}}' | grep -i openresty | head -1)
if [ -n "$openresty" ]; then
    mode=$(docker inspect "$openresty" --format '{{.HostConfig.NetworkMode}}')
    if [ "$mode" = "host" ]; then
        echo "  OpenResty 网络模式 host  → 代理地址填 http://127.0.0.1:8300"
    else
        echo "  OpenResty 网络模式 $mode → 代理地址填 http://$CONTAINER:8300"
        docker network inspect 1panel-network --format '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null \
            | grep -q "$openresty" || warn_ "OpenResty 不在 1panel-network 里，代理可能 502：docker network connect 1panel-network $openresty"
    fi
else
    warn_ "没找到 OpenResty 容器，先在 1Panel 应用商店安装/启动"
fi

echo "== 7. 磁盘 =="
df -h / | awk 'NR==2 {print "  根分区已用 "$5"，剩余 "$4}'
avail=$(df -P / | awk 'NR==2 {print $4}')
[ "${avail:-0}" -lt 1048576 ] && warn_ "剩余空间不足 1 GB" || pass "磁盘空间充足"

echo
echo "结果：通过 $ok 项，提醒 $warn 项，失败 $bad 项"
[ "$bad" -eq 0 ] || exit 1
