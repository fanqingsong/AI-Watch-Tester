# Cloud Backend Image
# 不使用 mcr.microsoft.com 镜像（国内直连不稳定，769MB Chromium 层会超时），
# 改用 Docker Hub python 镜像（国内源可加速）+ playwright 1.50.0（经典 chromium build，
# npmmirror 镜像有完整文件）。
FROM python:3.10-slim

# apt 阿里云镜像（Debian）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# pip 清华镜像
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

# 系统依赖：Tesseract OCR + Playwright 所需基础工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（cloud backend）
COPY cloud/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 钉死 playwright==1.50.0：用经典 chromium build 1148（npmmirror 镜像完整可用），
# 避免最新版走 cft 路径（国内镜像无该文件）
RUN pip install --no-cache-dir playwright==1.50.0

# 安装 AAT core（依赖 playwright>=1.40,<2.0，已被 1.50.0 满足，pip 不会升级）
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# Chromium 浏览器 + 系统依赖（npmmirror 国内加速，build 1148）
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright
RUN playwright install --with-deps chromium && chmod -R a+rX /ms-playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 复制 cloud 应用
COPY cloud/app/ ./app/
COPY cloud/scripts/ ./scripts/

# 运行时目录
RUN mkdir -p screenshots uploads

# 非 root 用户
RUN useradd -m -r appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
