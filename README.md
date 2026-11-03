# 桃花源 · 网址导航（TaoHuaYuan）

一个自部署的网址导航站，前端沿用 `TaoHuaYuan` 的侧栏、卡片与关于页视觉，后端 **FastAPI + SQLAlchemy + SQLite**，管理后台的页面与接口契约保持兼容。

- 🎯 **公共导航**：分类侧栏、分组卡片、本地搜索、移动端抽屉
- 📝 **关于页**：Markdown 渲染 + DOMPurify 消毒
- ⚙️ **管理后台**：仪表盘（SSE）、网站增删改查、批量抓取、同步、Excel 导出、分类管理、站点配置、关于页编辑、修改密码
- 🖼️ **图标智能抓取**：apple-touch-icon → favicon → manifest → 页面 logo → 图标镜像 → 首字母占位图，逐级兜底并做有效性校验
- 🔌 **零依赖部署**：FastAPI 同时提供 `/api` 与前端静态资源，对外只需一个端口

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+ · FastAPI · SQLAlchemy 2 · SQLite · PyJWT |
| 前端 | Vue 3 · TypeScript · Vite · Naive UI · Pinia |
| 部署 | Docker · 1Panel · systemd · Nginx |

## 快速开始

### 环境要求

- Python 3.11–3.14（已在 3.13 / 3.14 验证）
- Node.js 18+（仅构建前端时需要）

### 1. 启动后端

```bash
git clone https://github.com/huangtangsan/TaoHuaYuan.git
cd TaoHuaYuan

python -m venv .venv
# Windows
.venv\Scripts\python -m pip install -r requirements.txt
# Linux / macOS
# .venv/bin/python -m pip install -r requirements.txt

python run.py
```

默认监听 `127.0.0.1:8300`（可用 `WEBSTACK_HOST` / `WEBSTACK_PORT` 覆盖）。首次启动会自动建表、写入管理员与示例数据。

### 2. 构建前端（生产模式）

```bash
cd frontend
npm install
npm run build
```

构建完成后刷新 `http://127.0.0.1:8300/`，FastAPI 会直接托管 `frontend/dist` 并处理 SPA history fallback。

### 3. 前端开发模式

两个终端分别运行：

```bash
# 终端一：后端
python run.py

# 终端二：前端
cd frontend
npm run dev
```

打开 `http://127.0.0.1:4173/`，Vite 会将 `/api` 代理到后端 8300 端口。

## 默认账号

| 项 | 值 |
|---|---|
| 用户名 | `admin` |
| 密码 | `admin` |

> ⚠️ 密码兼容原管理端（前端先 MD5 再提交，后端也接受明文）。**生产环境请立即修改密码**，并设置新的 `WEBSTACK_JWT_SECRET`。

## 生产部署

完整步骤、安全加固、备份恢复与排错见 **[docs/DEPLOY-1PANEL.md](docs/DEPLOY-1PANEL.md)**。核心要点：

- 对外只有 **一个端口**：FastAPI 同时提供 `/api` 和前端静态文件，无跨域、无需单独建前端站。
- 推荐用根目录的 `docker-compose.yml` 跑容器，代码 / `frontend/dist` / `data` 挂载进去，改完重启即生效。
- 生产必须设置 `WEBSTACK_JWT_SECRET`、`WEBSTACK_COOKIE_SECURE=1`、`WEBSTACK_DOCS=0`，并第一时间改掉默认密码。

```bash
cp .env.example .env && chmod 600 .env
sed -i "s|^WEBSTACK_JWT_SECRET=.*|WEBSTACK_JWT_SECRET=$(openssl rand -hex 32)|" .env
docker compose up -d --build
curl -s http://127.0.0.1:8300/api/health
```

## 页面与 API

| 地址 | 说明 |
|---|---|
| `/` | 公共导航首页 |
| `/about` | 关于本站 / 关于站长 |
| `/login` | 管理后台登录 |
| `/admin/dashboard` | 系统指标（SSE） |
| `/admin/site` | 网站管理 |
| `/admin/category` | 分类管理 |
| `/admin/config` | 站点设置 |
| `/admin/about_page` | 关于页 Markdown |
| `/admin/modify_password` | 修改密码 |
| `/api/docs` | Swagger 接口文档（`WEBSTACK_DOCS=0` 关闭） |

成功响应直接返回业务对象；错误响应为 `{code, message, data}`。鉴权顺序为 `Token` 请求头 → `_login_token_` Cookie → 查询参数。完整接口列表见 README 顶部目录中的 Swagger 文档，或查看 `app/routers/` 源码。

## 目录结构

```text
TaoHuaYuan/
├─ app/
│  ├─ main.py              FastAPI 入口与 SPA 托管
│  ├─ models.py            数据模型
│  ├─ routers/             公共、认证、分类、网站、配置、仪表盘
│  ├─ services/
│  │  ├─ scraper.py        标题/描述抓取
│  │  ├─ icons.py          图标候选发现、校验与兜底
│  │  ├─ images.py         图片下载、缩放与 base64
│  │  ├─ seed.py           首次启动初始化
│  │  └─ seed_sites.json   内置示例数据（含内联图标）
│  └─ security.py          MD5 兼容与 JWT
├─ deploy/
│  ├─ Dockerfile           生产镜像
│  ├─ nginx/               Nginx 安全头 / SSE / 限流片段
│  ├─ scripts/             SQLite 备份脚本
│  └─ systemd/             systemd 服务单元
├─ docs/DEPLOY-1PANEL.md   1Panel 部署与维护手册
├─ docker-compose.yml      容器编排
├─ frontend/               Vue 3 + TypeScript + Vite
├─ tools/                  数据导入脚本
└─ tests/                  接口与图标抓取测试
```

## 测试

```bash
python -m pytest -q
```

测试使用独立的临时 SQLite 数据库，不会修改运行数据。

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `WEBSTACK_DATABASE_URL` | `sqlite:///data/webstack.db` | SQLAlchemy 数据库地址 |
| `WEBSTACK_DATA_DIR` | `./data` | 数据目录 |
| `WEBSTACK_HOST` | `127.0.0.1` | 监听地址 |
| `WEBSTACK_PORT` | `8300` | 监听端口 |
| `WEBSTACK_FRONTEND_DIST` | `./frontend/dist` | 前端构建产物目录 |
| `WEBSTACK_JWT_SECRET` | 内置开发密钥 | **生产必须修改** |
| `WEBSTACK_COOKIE_SECURE` | `0` | 全站 HTTPS 后设 `1` |
| `WEBSTACK_DOCS` | `1` | 设 `0` 关闭接口文档 |
| `WEBSTACK_TOKEN_EXPIRE_HOURS` | `24` | 登录有效期（小时） |
| `WEBSTACK_ICON_TIMEOUT` | `3` | 单个图标候选下载超时（秒） |
| `WEBSTACK_ICON_BUDGET` | `12` | 单站点找图标总预算（秒） |
| `WEBSTACK_ICON_FALLBACK` | DuckDuckGo | 图标镜像模板 |
| `WEBSTACK_ICON_LETTER` | `1` | 无图标时是否生成首字母占位图 |

## 与 Go 版的有意差异

- 不再每次启动都 drop 并重建表，后台修改可持久化。
- 登录 Cookie 改为 HttpOnly，不再由 JS 写入 Token。
- 删除分类时检查子分类与网站，避免孤儿数据。
- 批量新增时非法 URL、重复 URL、抓取失败会明确计入失败列表。
- 网站 Logo 等比缩放居中到 64×64，避免强制拉伸。
- 图标抓取多级兜底并做有效性校验。
- 新增 `/api/home`，让首页一次拿到配置、分类与启用站点。

## License

[MIT](LICENSE) © 2026 SKJ-Huangtang

## 致谢

本项目基于以下开源项目改写，特此致谢：

- 前端视觉与导航站生态：[@ViggoZ](https://github.com/ViggoZ) 与 [@Anjaxs](https://github.com/Anjaxs) 的 WebStack 生态
- 后台管理端：[@ch3nnn](https://github.com/ch3nnn/webstack-go) 的 [webstack-go](https://github.com/ch3nnn/webstack-go)，本项目的管理后台基于其 Go 版实现改写成 Python
