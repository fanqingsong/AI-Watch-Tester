# AI Watch Tester Docker Image
# 使用微软官方 Playwright 镜像：Chromium 已预装，省去 ~150MB 浏览器下载
# （国内镜像源均不镜像 mcr.microsoft.com，但 mcr 走 Azure CDN 国内直连可用）
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

# 设置工作目录
WORKDIR /app

# 配置apt使用阿里云镜像源（国内加速，Ubuntu noble）
RUN sed -i 's|http://archive.ubuntu.com|http://mirrors.aliyun.com|g; s|http://security.ubuntu.com|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null || true

# 配置pip使用清华镜像源（国内加速）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装系统依赖（Chromium 及其系统依赖已由基础镜像提供）
RUN apt-get update && apt-get install -y \
    # X11 for headed browser mode (xvfb)
    xvfb \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng \
    libtesseract-dev \
    # 图像处理（使用新包名）
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

# 安装Python依赖
# 基础镜像已含 playwright==1.50.0（满足 >=1.40,<2.0），pip 不会重装/升级，直接复用预装 Chromium
RUN pip install --no-cache-dir -e .[web,watch]

# 创建必要的目录
RUN mkdir -p .aat scenarios

# 暴露Web Dashboard端口
EXPOSE 8000

# 设置环境变量
ENV PYTHONUNBUFFERED=1
# 预装 Chromium 位于 /ms-playwright（基础镜像默认路径）
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 智谱AI配置（可选）
# ENV ZHIPUAI_API_KEY=your_zhipuai_key_here
# ENV ZHIPUAI_MODEL=glm-4-flash

# 默认命令
CMD ["aat", "--help"]
