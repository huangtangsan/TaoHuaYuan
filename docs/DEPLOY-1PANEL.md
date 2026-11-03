# 用 1Panel 部署 WebStack（FastAPI + Vue 单域名）

> 适用：1Panel 社区版 v1.10.x，Ubuntu 22.04/24.04 或 Debian 12
> 目标：浏览器访问 `https://你的域名` → OpenResty(443) → 容器 `webstack:8300` → FastAPI（同时提供 `/api` 和前端静态文件）
> 这套流程也适用于以后迁移服务器：换台机器从第 2 节重做一遍即可。

---

## 0. 先搞清楚这套东西的结构

前后端**不分开部署**。`app/main.py` 除了注册 `/api/*`，还会把 `frontend/dist` 当静态目录托管，并在找不到文件时回落到 `index.html`（SPA 路由需要）。所以对外只有**一个** 8300 端口，不需要给前端单独建站，也不存在跨域。

```text
Internet
   │  :80 / :443
   ▼
1Panel OpenResty（容器，负责 TLS、重定向、安全头、限流）
   │  http://webstack:8300  或  http://127.0.0.1:8300   ← 取决于 OpenResty 网络模式
   ▼
容器 webstack（uvicorn 单进程）
   ├─ /api/*        → FastAPI 路由
   ├─ /assets/*     → frontend/dist（长缓存）
   └─ 其他路径       → frontend/dist/index.html
        │
        └─ ./data/webstack.db（SQLite，挂载到宿主机持久化）
```

| 项目 | 值 |
|---|---|
| 容器名 | `webstack` |
| 容器内端口 | `8300` |
| 宿主机发布端口 | `127.0.0.1:8300`（仅回环，公网直连不到） |
| 数据目录 | `/opt/webstack/data`（SQLite + backup） |
| 健康检查 | `GET /api/health` → `{"status":"ok"}` |
| 首次启动 | 自动建表 + 写入 `app/services/seed_sites.json` 里的真实数据（4 分类 28 站点） |
| 默认账号 | `admin / admin`（**上线前必须改**） |

---

## TL;DR（熟手六步）

```bash
# 本地：构建前端 + 打包上传
cd frontend && npm ci && npm run build && cd ..
tar --exclude=.venv --exclude=frontend/node_modules --exclude=.pytest_cache \
    --exclude=.idea --exclude=data/backup --exclude=.env -czf /tmp/webstack.tar.gz .
scp /tmp/webstack.tar.gz root@SERVER_IP:/root/

# 服务器：解包 + 配置 + 启动
mkdir -p /opt/webstack && tar -xzf /root/webstack.tar.gz -C /opt/webstack
cd /opt/webstack && cp .env.example .env && chmod 600 .env
sed -i "s|^WEBSTACK_JWT_SECRET=.*|WEBSTACK_JWT_SECRET=$(openssl rand -hex 32)|" .env
docker compose up -d --build

# 1Panel：创建「反向代理」网站 → 代理地址按第 5 节二选一 → 申请证书 → 开 HTTPS
```

然后**立刻**去 `https://域名/admin` 改掉 `admin/admin`。

---

## 1. 动手前的检查清单

| 检查项 | 怎么确认 | 不满足的后果 |
|---|---|---|
| 域名 A 记录指向服务器公网 IP | `ping 你的域名` 或 `dig +short 你的域名` | 证书签不下来、访问不到 |
| 80 / 443 在云厂商安全组放行 | 云控制台「安全组」入方向 | Let's Encrypt HTTP 验证失败 |
| 1Panel「网站」功能可用（已装 OpenResty） | 左侧有「网站」菜单且能打开 | 没法做反向代理 |
| 服务器配置 ≥ 1 核 1 G，磁盘 ≥ 10 G | 1Panel 首页概览 | 构建/运行吃紧 |
| 8300 端口**没有**对公网放行 | 1Panel「主机 → 防火墙」+ 云安全组 | 后端被绕过 nginx 直接访问 |
| 旧静态站是否占用同一域名 | 1Panel「网站」列表 | 80/443 冲突，新站起不来 |

> 如果你要沿用的就是 `go.huangtang.link` 这台机器和这个域名：先在「网站」里把旧的静态站点**停用**（不要直接删，留着回滚），再建新的反向代理站。

---

## 2. 本地准备（Windows / Git Bash）

### 2.1 构建前端

必须先在本地构建出 `frontend/dist`，服务器上不装 Node，省内存也省时间。

```bash
cd C:/project/TaoHuaYuan/webstack-python/frontend
npm ci            # 首次或 package-lock 变了才需要；已有 node_modules 可跳过
npm run build     # 内含 vue-tsc 类型检查，失败就先修类型错误
ls -lh dist       # 应能看到 index.html 和 assets/
```

### 2.2 打包

只排除依赖缓存和备份，**保留 `data/`**——这样服务器首启就用你现在这份整理好的数据库（含全部图标和后台配置），而不是重新抓一遍。`--exclude=.env` 是为了不把本地的开发配置带上服务器。

> 打包前先把本地后端停掉（关掉 `run.py` 的窗口），避免 SQLite 正在写的时候打包。

```bash
cd C:/project/TaoHuaYuan/webstack-python

tar --exclude=.venv \
    --exclude=frontend/node_modules \
    --exclude=.pytest_cache \
    --exclude=.idea \
    --exclude=data/backup \
    --exclude=.env \
    --exclude='*.log' \
    -czf /tmp/webstack.tar.gz .

ls -lh /tmp/webstack.tar.gz    # 约 3–5 MB
scp /tmp/webstack.tar.gz root@你的服务器IP:/root/
```

> 如果你希望服务器**全新初始化**（清空所有后台改动、重新写入种子数据），打包时连 `data` 一起排除即可：`--exclude=data`。

### 2.3 服务器解包

在 1Panel「主机 → 终端」或 SSH 里执行：

```bash
mkdir -p /opt/webstack
tar -xzf /root/webstack.tar.gz -C /opt/webstack
cd /opt/webstack
ls -l
# 期望看到：app/  deploy/  docker-compose.yml  .env.example  requirements.txt  frontend/dist  data/
```

> ⚠️ **`-C /opt/webstack` 不能漏**。如果写成 `cd /opt && tar -zxvf webstack.tar.gz`，文件会散落在 `/opt` 下，和 1Panel 自己的 `1panel` 目录混在一起。
> 补救不用重传，移进去就行：
>
> ```bash
> cd /opt && mkdir -p /opt/webstack
> mv app data deploy docs frontend tests tools \
>    docker-compose.yml README.md requirements.txt run.py \
>    .dockerignore .env.example .gitignore /opt/webstack/
> ls -la /opt        # 确认只剩 webstack/ 和 1panel/ 等原有目录
> ```
>
> 千万别用 `rm -rf /opt/*` 清场——`/opt/1panel` 删了面板就没了。

---

## 3. 生成生产配置 `.env`

`.env` 里全是密钥，权限必须是 600。

```bash
cd /opt/webstack
cp .env.example .env
chmod 600 .env

# 生成 32 字节随机 JWT 密钥，直接写进 .env
sed -i "s|^WEBSTACK_JWT_SECRET=.*|WEBSTACK_JWT_SECRET=$(openssl rand -hex 32)|" .env

# 确认三个关键项
grep -E '^(WEBSTACK_JWT_SECRET|WEBSTACK_COOKIE_SECURE|WEBSTACK_DOCS)=' .env
# WEBSTACK_JWT_SECRET=<64 位十六进制>
# WEBSTACK_COOKIE_SECURE=1
# WEBSTACK_DOCS=0
```

这三个值的含义：

| 变量 | 生产值 | 为什么 |
|---|---|---|
| `WEBSTACK_JWT_SECRET` | 随机 64 位 | 签名密钥泄露 = 别人能伪造管理员 token。仓库里的默认值是公开的。 |
| `WEBSTACK_COOKIE_SECURE` | `1` | 登录 Cookie 只通过 HTTPS 发送。不设的话，用户手动敲 `http://` 时 Cookie 会明文回传。 |
| `WEBSTACK_DOCS` | `0` | 关掉 `/api/docs` 与 `/api/openapi.json`，不让陌生人拿到完整后台接口清单。 |

> 注意：`WEBSTACK_COOKIE_SECURE=1` 之后，**必须**走 HTTPS 才能登录成功。如果证书还没配好，先用 `0` 验证，配好 HTTPS 再改回 `1` 并重启。

---

## 4. 启动容器

### 4.1 确认 1Panel 网络存在

```bash
docker network ls | grep 1panel-network
```

没有输出就建一个（正常装过 1Panel 应用一般都有）：

```bash
docker network create 1panel-network
```

### 4.2 方式 A：1Panel 图形界面

左侧「容器」→「编排」→「创建编排」：

| 字段 | 填什么 |
|---|---|
| 名称 | `webstack` |
| 路径 | 选择 `/opt/webstack/docker-compose.yml`（有的版本是选目录后填文件名） |
| 内容 | 自动读取文件，不用改 |

确认后 1Panel 会执行 `docker compose up -d --build`，首次构建约 1–3 分钟（主要是装 Python 依赖）。

### 4.3 方式 B：命令行（更直观，能看到构建日志）

```bash
cd /opt/webstack
docker compose up -d --build
```

> **构建报 `failed to resolve source metadata ... 403 Forbidden` 或 `i/o timeout`？**
> 这是 Docker 的镜像加速器不可用，跟项目代码无关。`docker.nju.edu.cn` 这类公共镜像站
> 已停止对匿名请求提供服务（返回 403），而直连 `docker.io` 在国内又会超时。
>
> 仓库里的 `deploy/Dockerfile` 已把 `FROM` 写成带域名的完整地址
> `docker.m.daocloud.io/library/python:3.12-slim`，不再经过 daemon 的 `registry-mirrors`，
> 所以 `FROM python:3.12-slim` 那种解析失败不会再出现。换其他源见 11.1 节。
>
> 顺带把 apt 和 pip 也指向了国内镜像（`mirrors.aliyun.com`），否则构建会卡在
> `apt-get update` 十几分钟。海外服务器可在 `.env` 里覆盖 `BASE_IMAGE`、`APT_MIRROR`、`PIP_INDEX_URL`。

### 4.4 验证

```bash
docker compose ps
# 状态应为 Up (healthy)，health 可能要等 20 秒才变绿

docker compose logs --tail=50 webstack
# 期望看到：WebStack Python ready; frontend dist: /app/frontend/dist

curl -s http://127.0.0.1:8300/api/health
# {"status":"ok"}

curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8300/
# 200

curl -s http://127.0.0.1:8300/api/home | head -c 200
# {"categories":[...],"sites":[...]}
```

四个都通过，说明容器这一层没问题，剩下的只是 nginx 转发。**此时公网还访问不到，这是对的**。

仓库里带了一个自检脚本，可以把上面这些检查一次跑完（每次改完配置都建议跑）：

```bash
bash /opt/webstack/deploy/scripts/preflight.sh
```

它会检查：docker/compose、1panel-network、`.env` 权限与关键变量、容器健康、8300 是否只监听回环、OpenResty 网络模式（直接告诉你代理地址该填哪个）、磁盘余量。

> 首次启动会在 `data/` 下建 `webstack.db`。如果打包时带了旧的 `data/webstack.db`，会直接沿用；没带就自动初始化。

---

## 5. 配置反向代理（最容易卡住的一步）

### 5.1 先判断 OpenResty 的网络模式

1Panel 的 OpenResty 跑在容器里，但不同安装方式网络模式不同，**代理地址填错就是 502**。

```bash
docker ps --format '{{.Names}}' | grep -i openresty
# 例如：1Panel-openresty-AbCd

docker inspect 1Panel-openresty-AbCd --format '{{.HostConfig.NetworkMode}}'
```

| 输出 | 说明 | 代理地址填 |
|---|---|---|
| `host` | 与宿主机共用网络栈 | `http://127.0.0.1:8300` |
| `bridge` / `1panel-network` | 独立容器网络 | `http://webstack:8300` |

> 为什么不能一律写 `127.0.0.1`：OpenResty 在 bridge 模式下，`127.0.0.1` 指的是**它自己**，不是宿主机，必然 502。这是 1Panel 部署后端服务最常见的坑。

### 5.2 创建站点

1Panel 左侧「网站」→「网站」→「创建网站」：

| 字段 | 填什么 |
|---|---|
| 类型 | **反向代理** |
| 主域名 | `go.huangtang.link`（或你的新域名） |
| 代号 | 留空即可 |
| 代理地址 | 按 5.1 的结论填 |
| 端口 | 80 |

创建后先访问 `http://你的域名`，应该直接看到导航站首页。

### 5.3 502 的排查顺序

```bash
# 1) 后端自己活着吗？
curl -s http://127.0.0.1:8300/api/health

# 2) OpenResty 能不能解析/连上容器？（把容器名换成你的）
docker run --rm --network 1panel-network curlimages/curl -s -m 5 http://webstack:8300/api/health

# 3) 如果 2) 不通，说明 OpenResty 不在同一网络，把它接进来：
docker network connect 1panel-network 1Panel-openresty-AbCd
docker exec 1Panel-openresty-AbCd openresty -s reload
```

改完代理地址后 1Panel 会自动 reload；不生效就手动 `docker exec <容器> openresty -t && docker exec <容器> openresty -s reload`。

---

## 6. 开启 HTTPS

1Panel「网站」→ 点你的站点 →「HTTPS」：

1. **证书**：没有证书就点「创建证书」→ Let's Encrypt → 验证方式选 **HTTP**（需要 80 端口通、域名已解析）→ 申请。
2. **开启 HTTPS**：选中刚签的证书。
3. **HTTP 自动跳转 HTTPS**：打开。
4. **HSTS**：打开（浏览器之后只走 HTTPS）。确认全站 HTTPS 正常后再开，开了以后回退比较麻烦。

验证：

```bash
curl -sI http://你的域名 | head -3
# 301 或 308，Location: https://...

curl -sI https://你的域名 | grep -iE 'strict-transport|HTTP/'
# HTTP/2 200
# strict-transport-security: max-age=...

# 证书到期时间
echo | openssl s_client -servername 你的域名 -connect 你的域名:443 2>/dev/null \
  | openssl x509 -noout -dates
```

证书到期前 1Panel 会自动续期，但**续期依赖 80 端口一直可达**——别把 80 关了。

---

## 7. 安全头、SSE 与登录限流

### 7.1 追加安全响应头（必做）

1Panel「网站」→ 站点 →「配置文件」，在 `server { ... }` 内部粘贴下面内容（对应仓库 `deploy/nginx/server-security.conf`）：

```nginx
# 若这段上方已经有 client_max_body_size，改它的值即可，不要重复写（nginx 会报 duplicate）
client_max_body_size 10m;

add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

# 后台仪表盘是 SSE 长连接，必须关缓冲
location = /api/admin/dashboard {
    proxy_pass http://webstack:8300;   # ← host 网络时改成 127.0.0.1:8300
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
    chunked_transfer_encoding off;
}
```

保存即热加载。验证：

```bash
curl -sI https://你的域名 | grep -iE 'x-content-type|x-frame|referrer-policy'
```

> 不配这段的后果：后台首页的 CPU/内存曲线不动（nginx 默认缓冲 SSE），图标上传超过 1 MB 报 413。

### 7.2 登录限流（建议）

`limit_req_zone` 只能写在 `nginx.conf` 的 `http { }` 里。1Panel 入口：左侧「网站」→ 顶部「配置」（部分版本叫「全局配置」），把这两行加进去：

```nginx
limit_req_zone $binary_remote_addr zone=webstack_login:10m rate=10r/m;
limit_req_status 429;
```

然后回到站点的「配置文件」，在 `server { }` 里加：

```nginx
location = /api/login {
    limit_req zone=webstack_login burst=5 nodelay;
    proxy_pass http://webstack:8300;   # ← 同上，按网络模式调整
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

改完检查语法再 reload，别把站弄挂：

```bash
docker exec 1Panel-openresty-AbCd openresty -t
docker exec 1Panel-openresty-AbCd openresty -s reload
```

> 如果你的版本找不到全局配置入口，就**跳过限流**——强密码 + 面板本身不暴露比配错 nginx 更重要。

---

## 8. 上线前安全清单

按顺序过一遍，每项打勾再对外宣布上线。

- [ ] **改管理员密码**：`https://域名/admin` 登录 `admin/admin` → 右上角「修改密码」。这是最高优先级，密码是 MD5 存储的，弱密码等于没有。
- [ ] **`.env` 权限**：`ls -l /opt/webstack/.env` 应为 `-rw-------`，且 `grep JWT .env` 不是默认值。
- [ ] **`WEBSTACK_COOKIE_SECURE=1`、`WEBSTACK_DOCS=0`** 已生效（改完 `docker compose up -d` 重建容器使环境变量生效）。
- [ ] **8300 不对公网**：`curl -m 3 http://服务器公网IP:8300/api/health` 应该超时/拒绝。若通，立刻在 1Panel 防火墙和云安全组关掉。
- [ ] **面板自身加固**：1Panel「面板设置」→ 开启面板 SSL、改强密码、改安全入口路径；能限制来源 IP 就限制。面板被登进来等于服务器失守。
- [ ] **SSH**：密钥登录、关掉 root 密码登录（`/etc/ssh/sshd_config` 里 `PasswordAuthentication no`），改默认 22 端口可选。
- [ ] **防火墙只开必要端口**：80、443、面板端口、SSH（最好限制来源）。
- [ ] **站点文案**：后台「网站配置」里的标题/关键词/描述、关于页还带「桃花源」初始文案，按需改。
- [ ] **内网链接**：数据里 `VoHive → http://192.168.1.22:3001/login` 是内网地址，公网打不开，建议后台禁用。
- [ ] **备份已跑通**：见第 9 节，先手动执行一次确认产物存在。
- [ ] **HTTPS 强制跳转 + HSTS** 已开。

---

## 9. 备份与恢复

### 9.1 为什么不能直接 `cp`

SQLite 开了 WAL，热拷贝可能拿到「半份」数据。脚本用 `sqlite3` 的 backup API，一致性有保证。

### 9.2 每天自动备份

1Panel「计划任务」→「创建任务」：

| 字段 | 填什么 |
|---|---|
| 任务类型 | Shell 脚本 |
| 任务名称 | `webstack-db-backup` |
| 执行周期 | 每天 03:10 |
| 脚本内容 | `bash /opt/webstack/deploy/scripts/backup-sqlite.sh` |

手动跑一次确认：

```bash
bash /opt/webstack/deploy/scripts/backup-sqlite.sh
ls -lh /opt/webstack/data/backup/ | tail -3
```

产物在 `/opt/webstack/data/backup/webstack-YYYYmmdd-HHMMSS.db`，默认保留 14 天。

### 9.3 异地备份（强烈建议）

同一块盘上的备份挡不住磁盘故障和误删。1Panel「计划任务」再建一个：

- 任务类型：**备份目录**
- 备份目录：`/opt/webstack/data`
- 保留份数：7
- 备份账号：先在「计划任务 → 备份账号」里加一个 S3/阿里云 OSS/OneDrive 等

这样每天会把整个 `data/`（数据库 + 本地备份）传到对象存储。

### 9.4 恢复

```bash
cd /opt/webstack

# 1) 停服务，避免写入
docker compose stop webstack

# 2) 现有库留个后路
mv data/webstack.db data/webstack.db.broken-$(date +%Y%m%d-%H%M%S)
rm -f data/webstack.db-wal data/webstack.db-shm

# 3) 放回备份
cp data/backup/webstack-20261103-031000.db data/webstack.db

# 4) 启动并检查
docker compose start webstack
sleep 3
curl -s http://127.0.0.1:8300/api/health
```

---

## 10. 日常维护

### 10.1 只改了前端

前端产物是挂载进容器的（`./frontend/dist`），FastAPI 每次请求都从磁盘读文件。所以**原地覆盖文件即生效，不用重启**。

```bash
# 本地
cd frontend && npm run build
tar -czf /tmp/dist.tar.gz -C frontend dist

# 上传并原地覆盖（注意是解到 frontend/ 目录，不是替换 dist 目录本身）
scp /tmp/dist.tar.gz root@SERVER:/tmp/
ssh root@SERVER 'tar -xzf /tmp/dist.tar.gz -C /opt/webstack/frontend && echo updated'
```

浏览器强刷一次就能看到新版（`index.html` 带 `no-cache`，`assets/` 是带 hash 的长缓存文件，所以不会看到半新半旧）。

> ⚠️ 别用「把 dist 改名、再把新目录改成 dist」的方式更新：容器是对**目录**做的 bind mount，改名后它仍然挂在旧目录上，页面不会变。真这么做了就 `docker compose restart webstack` 重新挂载一次。
>
> 旧版本的 hash 文件会留在 `dist/assets` 里，不影响访问。攒多了可以清：
> `find /opt/webstack/frontend/dist/assets -type f -mtime +30 -delete`

### 10.2 只改了后端

后端代码也是挂载的（`./app`），替换后重启容器即可，**不用重建镜像**。

```bash
# 本地打包 app/（顺手先跑测试）
.venv/Scripts/python.exe -m pytest -q
tar -czf /tmp/app.tar.gz app

# 上传替换
scp /tmp/app.tar.gz root@SERVER:/tmp/
ssh root@SERVER '
  cd /opt/webstack &&
  cp -a app app.bak-$(date +%Y%m%d-%H%M%S) &&
  tar -xzf /tmp/app.tar.gz &&
  docker compose restart webstack
'

# 验证
curl -s http://127.0.0.1:8300/api/health
docker compose logs --tail=30 webstack
```

> 保留 `app.bak-时间戳` 就是回滚点：`rm -rf app && mv app.bak-20261103-141500 app && docker compose restart webstack`。
>
> tar 是「覆盖 + 新增」，不会删除服务器上已有但本地已删掉的文件。如果你删过模块文件（比如重构拆掉了某个 router），解包前先 `rm -rf app`，回滚点已经留好了。

### 10.3 改了依赖（requirements.txt）

这时候必须重建镜像：

```bash
cd /opt/webstack
docker compose build --no-cache
docker compose up -d
```

### 10.4 常用运维命令

```bash
cd /opt/webstack

docker compose ps                      # 状态
docker compose logs -f --tail=100 webstack   # 实时日志（Ctrl+C 退出）
docker compose restart webstack        # 重启
docker compose down                    # 停止并删除容器（数据在宿主机，不会丢）
docker compose up -d                   # 起回来

docker stats webstack --no-stream      # 内存/CPU 占用

# 进容器排查（例如看数据库里到底有多少条）
docker compose exec webstack python -c "
import sqlite3
c = sqlite3.connect('/app/data/webstack.db')
print(c.execute('select count(*) from st_site').fetchone())
"
```

### 10.5 磁盘与日志

- 容器日志已限制为 10 MB × 3 份（写死在 compose 里），不会无限涨。
- 真正会涨的是 `data/backup`（每天一份）和 1Panel 自己的备份。每周看一眼：

```bash
du -sh /opt/webstack/data /opt/webstack/data/backup
df -h /
```

磁盘满的直接表现是登录报 500、`database is locked`、图标保存失败。

---

## 11. 排错速查

| 现象 | 最可能的原因 | 处理 |
|---|---|---|
| 构建报 `failed to resolve source metadata ... 403 Forbidden` | 镜像加速器失效（`docker.nju.edu.cn` 已停止匿名服务） | 用仓库自带 Dockerfile（已写全地址）；或按 11.1 换源 |
| 构建报 `i/o timeout` / `TLS handshake timeout` | 服务器连不到 `docker.io` | 同上，必须走加速地址 |
| 构建卡在 `apt-get update` 很久 | Debian 源是 `deb.debian.org` | Dockerfile 已替换为阿里云源，确认用的是最新版 Dockerfile |
| 502 Bad Gateway | 代理地址填错（bridge 模式写了 127.0.0.1） | 按 5.1 重新判断，改 `http://webstack:8300` |
| 502 但代理地址对 | OpenResty 不在 `1panel-network` | `docker network connect 1panel-network <openresty容器>` 后 reload |
| 503 且提示「前端尚未构建」 | `frontend/dist` 没挂上或为空 | `ls /opt/webstack/frontend/dist/index.html`；本地重新 `npm run build` 上传 |
| 首页 200，`/admin` 登录一直转圈 | `WEBSTACK_COOKIE_SECURE=1` 但还在用 HTTP 访问 | 用 `https://` 访问，或临时改 0 排查 |
| 登录提示「用户名和密码错误」但密码没错 | 密码是客户端 MD5 后提交的；手工调 API 时传了明文以外的格式 | 前端登录即可；脚本调用传 `md5(密码)` 或明文（后端兼容两种） |
| 卡在 429 | 触发了登录限流 | 等 1 分钟，或临时注释 `limit_req` 后 reload |
| 后台监控曲线不动 | SSE 被 nginx 缓冲 | 加 7.1 里的 `/api/admin/dashboard` 段 |
| 上传图标 413 | nginx 默认 1 MB | `client_max_body_size 10m;` |
| `database is locked` | 两个进程同时写同一个 db 文件 | 确认只有一个 `webstack` 容器在跑：`docker ps \| grep webstack` |
| 图标抓取很慢/失败 | 目标站 404 或网络不通 | 正常，单站最多 12 秒；后台「同步」可重试 |
| 中文首字母图标显示成方块 | 容器缺中文字体 | 本 Dockerfile 已装 `fonts-wqy-zenhei`；自建镜像要补 |
| 时间差 8 小时 | 容器 TZ 没设 | compose 里已有 `TZ: Asia/Shanghai`，检查是否被覆盖 |
| 改了 `.env` 不生效 | 环境变量只在容器创建时注入 | `docker compose up -d`（不是 restart） |

看后端真实报错：

```bash
docker compose logs --tail=200 webstack | grep -iE 'error|traceback' -A 5
```

### 11.1 镜像源怎么换（403 / 超时）

**先确认当前配置**：

```bash
cat /etc/docker/daemon.json 2>/dev/null || echo "没有 daemon.json"
```

如果里面 `registry-mirrors` 有 `docker.nju.edu.cn`、`dockerproxy.com`、`docker.1panel.live`
这类已失效的地址，就是它们导致了 403。三个选择，从轻到重：

**① 什么都不改（推荐，最省事）**
仓库的 `deploy/Dockerfile` 已经写了完整地址，`docker compose up -d --build` 直接用。

**② 临时换一个源构建一次**
```bash
cd /opt/webstack
docker compose build --build-arg BASE_IMAGE=docker.1ms.run/library/python:3.12-slim
docker compose up -d
```
国内可用的加速地址（2026-11 实测，均返回正常 manifest）：

| 地址 | 说明 |
|---|---|
| `docker.m.daocloud.io` | DaoCloud 公开加速，稳定，本仓库默认 |
| `docker.1ms.run` | 速度较快，备用 |

用的时候拼成 `<地址>/library/python:3.12-slim`。**注意别用** `docker.nju.edu.cn`（403）、
`docker.1panel.live`（403）。

**③ 彻底修 daemon.json**
去掉失效的 mirror，加可用的：
```bash
cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d)
cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://docker.m.daocloud.io", "https://docker.1ms.run"],
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
EOF
systemctl reload docker || systemctl restart docker
docker info | grep -A3 "Registry Mirrors"
```

> ⚠️ **重启 Docker 会重启所有容器，包括 1Panel 自己**（面板会断几十秒）。
> 选个没人用的时段做，做完 `docker ps` 确认各容器都起来了。业务容器都设了
> `restart: unless-stopped`，会自动恢复；如果 1Panel 面板打不开，SSH 里
> `docker start 1panel` 即可。
>
> 如果你的服务器在阿里云，还有更快的选择：控制台「容器镜像服务 → 镜像加速器」
> 会给你一个专属地址 `https://<你的ID>.mirror.aliyuncs.com`，填进 `registry-mirrors` 即可。

**验证源是否可用**（不用真拉镜像，两秒出结果）：
```bash
curl -s -o /dev/null -w '%{http_code}\n' https://docker.m.daocloud.io/v2/
# 401 是正常的（表示服务在线、要认证）；403 才是被封
```

---

## 12. 从零重建 / 迁移到新服务器

1. 老服务器：`bash deploy/scripts/backup-sqlite.sh`，把最新 `data/backup/*.db` 下载回来。
2. 新服务器：按第 1–4 节装好，解包时用「不带 data」的包（全新初始化），或者把备份库放到 `/opt/webstack/data/webstack.db`。
3. 域名 A 记录切到新 IP，等 TTL 生效。
4. 新服务器申请证书（HTTP 验证需要域名已指向新机，所以先切 DNS 再签证书）。
5. 老服务器观察 1–2 天再下线。

---

## 附录 A：不用 Docker（systemd 直跑）

适合不想在服务器上跑容器的场景。要求宿主机 Python ≥ 3.10（Ubuntu 22.04 自带 3.10、Debian 12 自带 3.11）。

```bash
# 1) 依赖（Debian/Ubuntu）
apt-get update && apt-get install -y python3-venv python3-pip fonts-wqy-zenhei

# 2) 建用户和目录
useradd -r -s /usr/sbin/nologin -d /opt/webstack webstack
mkdir -p /opt/webstack && tar -xzf /root/webstack.tar.gz -C /opt/webstack
cd /opt/webstack

# 3) 虚拟环境 + 依赖
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 4) 配置
cp .env.example .env && chmod 600 .env
sed -i "s|^WEBSTACK_JWT_SECRET=.*|WEBSTACK_JWT_SECRET=$(openssl rand -hex 32)|" .env
chown -R webstack:webstack /opt/webstack

# 5) 装服务
cp deploy/systemd/webstack.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now webstack
systemctl status webstack --no-pager

curl -s http://127.0.0.1:8300/api/health
```

反向代理地址：systemd 版本监听 `0.0.0.0:8300`，所以 OpenResty 是 host 网络时用 `http://127.0.0.1:8300`；是 bridge 网络时用宿主机内网 IP 或 docker0 网关：

```bash
ip -4 addr show docker0 | grep inet     # 通常是 172.17.0.1
# 代理地址填 http://172.17.0.1:8300
```

代价：更新后端要 `systemctl restart webstack`，更新前端同样是替换 `frontend/dist`；没有容器隔离，依赖装坏了要重建 venv。

---

## 附录 B：文件与变量速查

```text
webstack-python/
├─ docker-compose.yml           1Panel 编排用的主文件
├─ .env.example                 环境变量模板（复制成 .env）
├─ .dockerignore
├─ deploy/
│  ├─ Dockerfile                运行镜像（只装依赖）
│  ├─ nginx/
│  │  ├─ server-security.conf   粘到站点 server{} 里：安全头 + SSE
│  │  └─ http-limit-zone.conf   粘到 nginx.conf 的 http{} 里：登录限流
│  ├─ scripts/
│  │  ├─ preflight.sh           部署自检（环境/端口/代理地址建议）
│  │  └─ backup-sqlite.sh       每日备份（给 1Panel 计划任务用）
│  └─ systemd/webstack.service  不用 Docker 时的服务单元
├─ app/                         后端（挂载进容器）
├─ frontend/dist/               前端产物（挂载进容器）
├─ data/                        SQLite + backup（挂载进容器）
└─ docs/DEPLOY-1PANEL.md        本手册
```

| 环境变量 | 生产值 | 作用 |
|---|---|---|
| `WEBSTACK_JWT_SECRET` | 随机 64 位 | 登录 token 签名 |
| `WEBSTACK_COOKIE_SECURE` | `1` | Cookie 仅 HTTPS |
| `WEBSTACK_DOCS` | `0` | 关闭接口文档 |
| `WEBSTACK_TOKEN_EXPIRE_HOURS` | `24` | 登录有效期 |
| `WEBSTACK_DATA_DIR` | `/app/data`（compose 固定） | 数据目录 |
| `WEBSTACK_FRONTEND_DIST` | `/app/frontend/dist`（compose 固定） | 前端产物 |
| `WEBSTACK_ICON_TIMEOUT` / `_BUDGET` | `3` / `12` | 图标抓取超时 |
| `PIP_INDEX_URL` | 阿里云 | 构建镜像时的 PyPI 源 |

| 端口 | 用途 | 是否对公网 |
|---|---|---|
| 80 | HTTP（ACME 验证 + 跳转） | 是 |
| 443 | HTTPS | 是 |
| 8300 | 后端 | **否**（仅 127.0.0.1） |
| 1Panel 面板端口 | 管理面板 | 建议限制来源 IP |
| 22 | SSH | 建议限制来源 IP |

---

## 附录 C：用「运行环境」代替 docker compose（可行，但只建议试跑）

1Panel 的「运行环境 → Python」本质也是 Docker 容器，官方实现是：

```yaml
image: python:${PYTHON_VERSION}      # 官方镜像，没有自定义 Dockerfile 的余地
working_dir: /app
volumes:
  - ${CODE_DIR}:/app                 # 你的项目目录整个挂进去
  - ./.env:/.env                     # 面板生成的 env 文件
  - ./run.sh:/run.sh                 # 你的启动命令被写进这个脚本
restart: on-failure:5
network: 1panel-network
```

所以**能跑起来**，但和本手册的 compose 方案有四处实质差异。

### C.1 表单怎么填

| 字段 | 填什么 | 说明 |
|---|---|---|
| 名称 | `webstack` | 也是容器名，反向代理可用 `webstack:8300` |
| 应用 | Python 3.12 | 对应官方 `python:3.12.x` |
| 运行目录 | `/opt/webstack` | 会挂到容器内 `/app` |
| 应用端口 | `8300` | 容器内部端口 |
| 外部映射端口 | `8300` | 宿主端口 |
| 端口外部访问 | **不勾选** | 勾了会绑 `0.0.0.0`，公网能直连 8300 绕过 HTTPS |
| 启动命令 | 见下 | 必须带 `-i` 指向国内 PyPI |

```bash
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ && \
uvicorn app.main:app --host 0.0.0.0 --port 8300 \
  --proxy-headers --forwarded-allow-ips '*' --no-server-header
```

环境变量（面板的「环境变量」区域，一行一个）：

```ini
TZ=Asia/Shanghai
WEBSTACK_JWT_SECRET=换成 openssl rand -hex 32 的输出
WEBSTACK_COOKIE_SECURE=1
WEBSTACK_DOCS=0
```

`WEBSTACK_DATA_DIR` / `WEBSTACK_FRONTEND_DIST` **不要填**：代码默认就是
`<项目根>/data` 和 `<项目根>/frontend/dist`，挂载后在容器里正好是 `/app/data`、`/app/frontend/dist`。

### C.2 四处差异

| 差异 | compose 方案 | 运行环境方案 | 影响 |
|---|---|---|---|
| 中文字体 | Dockerfile 装 `fonts-wqy-zenhei` | 官方镜像**没有** | 中文标题的首字母图标显示成方块 □ |
| 依赖安装 | 构建时装一次，重启秒起 | 每次容器启动都跑一遍 `pip install` | 首次 1–3 分钟；网络抖动会导致起不来，重试 5 次后放弃 |
| 重启策略 | `unless-stopped` | `on-failure:5` | 服务器重启后可能不会自动拉起，需手动 `docker start webstack` |
| 日志上限 | 10MB × 3 | 无限制 | 长期跑占满磁盘（`docker logs` 排查后会变大） |

另外：**它同样卡镜像源**。`image: python:3.12.x` 走的是 daemon 的 `registry-mirrors`，
你现在配的 `docker.nju.edu.cn` 返回 403，所以选运行环境照样拉不下来。要先用 11.1 节把
daemon.json 修好，而 compose 方案因为 Dockerfile 写了完整地址，反而不受影响。

### C.3 想补字体怎么办

只能塞进启动命令，代价是每次启动都多花十几秒：

```bash
apt-get update -qq && apt-get install -y -qq --no-install-recommends fonts-wqy-zenhei >/dev/null 2>&1; \
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ && \
uvicorn app.main:app --host 0.0.0.0 --port 8300 --proxy-headers --forwarded-allow-ips '*'
```

容器不重建时 apt 缓存还在，重启会快一些；但 1Panel 一旦重建容器（改配置、升级），全部重来。

### C.4 结论

- **想快速看一眼效果**：运行环境可以，两三分钟能起来。
- **要长期跑、要能维护**：用第 4 节的 docker compose。字体、重启策略、日志、权限都在
  `docker-compose.yml` 里定死了，重建一次之后每次启动都是秒级，服务器重启也会自动恢复。

两套不要同时开：它们会抢同一个 `8300` 端口和同一个 `data/webstack.db`（SQLite 写锁会报
`database is locked`）。切换前先 `docker rm -f webstack`。
