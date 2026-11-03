# WebStack Python 运行镜像
#
# 只装运行时和 Python 依赖。app/、frontend/dist/、data/ 由 docker-compose 挂载，
# 因此镜像不需要重建就能更新业务代码，只有 requirements.txt 变化时才需要 build。

# 基础镜像写全地址，绕开 daemon 的 registry-mirrors：
# 国内服务器直连 docker.io 会超时，而部分公共镜像站（如 docker.nju.edu.cn）
# 已对匿名请求返回 403。这里用 DaoCloud 的公开加速地址，海外服务器可覆盖：
#   docker compose build --build-arg BASE_IMAGE=python:3.12-slim
ARG BASE_IMAGE=docker.m.daocloud.io/library/python:3.12-slim
FROM ${BASE_IMAGE}

# Debian 源默认是 deb.debian.org，国内拉取很慢；apt 也走镜像站
ARG APT_MIRROR=mirrors.aliyun.com

# PyPI 国内镜像；海外服务器可覆盖为 https://pypi.org/simple/
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# tzdata         → 日志时间与北京时间对齐
# fonts-wqy-zenhei → 抓不到图标时，中文标题的首字母占位图能正常渲染（不装会显示方块）
#
# 注意 Debian 新版把源写在 /etc/apt/sources.list.d/debian.sources（deb822 格式），
# 老版本是 sources.list，两种都替换一遍；文件不存在时 continue 跳过。
RUN set -eu; \
    for f in /etc/apt/sources.list /etc/apt/sources.list.d/*; do \
        [ -f "$f" ] || continue; \
        sed -i \
            -e "s|deb.debian.org/debian-security|${APT_MIRROR}/debian-security|g" \
            -e "s|security.debian.org/debian-security|${APT_MIRROR}/debian-security|g" \
            -e "s|deb.debian.org|${APT_MIRROR}|g" "$f"; \
    done; \
    apt-get update; \
    apt-get install -y --no-install-recommends tzdata fonts-wqy-zenhei; \
    ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime; \
    echo "${TZ}" > /etc/timezone; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" -r requirements.txt

# 代码会被挂载覆盖，这里保留一份是为了镜像可以独立启动（自检、迁移时有用）
COPY app ./app
RUN mkdir -p /app/data /app/frontend/dist

EXPOSE 8300

# 镜像自检：/api/health 返回 200 即健康（slim 镜像没有 curl，用 Python 自带库）
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8300/api/health', timeout=4).status == 200 else 1)"

# --proxy-headers：让后端拿到真实访客 IP（登录日志、限流排查用）
# --no-server-header：响应里不带 uvicorn 版本信息
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8300", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header"]
