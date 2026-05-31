FROM python:3.12-slim

WORKDIR /app

# 安装 Playwright 所需的系统依赖 + Chromium 依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（使用清华镜像加速）
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    fastapi==0.115.0 \
    uvicorn[standard]==0.30.0 \
    apscheduler==3.10.4 \
    sqlalchemy==2.0.35 \
    jinja2==3.1.4 \
    python-multipart==0.0.12 \
    pydantic==2.9.0 \
    playwright==1.52.0

# 安装 Chromium 浏览器（使用国内镜像）
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/
RUN playwright install chromium && \
    rm -rf /root/.cache/ms-playwright-browser/

# 复制应用代码
COPY app/ ./app/

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# 启动服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--root-path", "/stock"]
