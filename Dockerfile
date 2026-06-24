# AI Watch Tester Docker Image
# 不使用 mcr.microsoft.com 镜像（国内直连不稳定，769MB Chromium 层会超时），
# 改用 Docker Hub python 镜像（国内源可加速）+ playwright 1.50.0（经典 chromium build，
# npmmirror 镜像有完整文件）。
FROM python:3.12-slim-bookworm

# 设置工作目录
WORKDIR /app

# 配置apt使用阿里云镜像源（国内加速，Debian）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# 配置pip使用清华镜像源（国内加速）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装系统依赖（Playwright 浏览器系统依赖由 playwright install-deps 安装）
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    # X11 for headed browser mode (xvfb)
    xvfb \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng \
    libtesseract-dev \
    # 图像处理
    libgl1 \
    libglib2.0-0 \
    libstdc++6 \
    libgomp1 \
    # 其他工具
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml README.md ./
COPY src/ ./src/

# 升级pip
RUN pip install --no-cache-dir --upgrade pip

# 钉死 playwright==1.50.0：用经典 chromium build 1148（npmmirror 镜像完整可用），
# 避免最新版走 cft 路径（国内镜像无该文件）
RUN pip install --no-cache-dir playwright==1.50.0

# 安装Python依赖（playwright>=1.40,<2.0 已被 1.50.0 满足，pip 不会升级）
RUN pip install --no-cache-dir -e .[web,watch]

# 安装Playwright浏览器（npmmirror 国内加速，build 1148）
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# 创建必要的目录
RUN mkdir -p .aat scenarios

# 暴露Web Dashboard端口
EXPOSE 8000

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

# 智谱AI配置（可选）
# ENV ZHIPUAI_API_KEY=your_zhipuai_key_here
# ENV ZHIPUAI_MODEL=glm-4.7

# 默认命令
CMD ["aat", "--help"]
