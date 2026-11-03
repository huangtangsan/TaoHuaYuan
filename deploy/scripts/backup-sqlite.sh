#!/usr/bin/env bash
# 备份 WebStack 的 SQLite 数据库（WAL 模式下也安全）
#
# 用法：在 1Panel「计划任务 → 创建任务 → Shell 脚本」里填这一行：
#   bash /opt/webstack/deploy/scripts/backup-sqlite.sh
# 建议每天 03:10 执行一次，保留 14 天。
#
# 可覆盖的环境变量：
#   APP_DIR   项目目录（默认 /opt/webstack）
#   CONTAINER 容器名（默认 webstack）
#   KEEP_DAYS 备份保留天数（默认 14）

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/webstack}"
CONTAINER="${CONTAINER:-webstack}"
KEEP_DAYS="${KEEP_DAYS:-14}"

stamp="$(date +%Y%m%d-%H%M%S)"
target="$APP_DIR/data/backup/webstack-${stamp}.db"

mkdir -p "$APP_DIR/data/backup"

# 用 sqlite3 的 backup API，而不是 cp：WAL 里未落盘的事务也能一起带上
docker exec "$CONTAINER" python -c "
import sqlite3
src = sqlite3.connect('/app/data/webstack.db')
dst = sqlite3.connect('/app/data/backup/webstack-${stamp}.db')
src.backup(dst)
dst.close()
src.close()
"

if [ ! -s "$target" ]; then
    echo "备份失败：$target 不存在或为空" >&2
    exit 1
fi

# 只清理本脚本产生的文件，别碰 data/backup 里手工存的其他东西
find "$APP_DIR/data/backup" -maxdepth 1 -type f -name 'webstack-*.db' -mtime "+${KEEP_DAYS}" -delete

echo "[$(date '+%F %T')] 备份完成 -> $target ($(du -h "$target" | cut -f1))"
