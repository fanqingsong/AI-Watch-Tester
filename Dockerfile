# AI Watch Tester Docker Image
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 配置apt使用阿里云镜像源（国内加速）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 配置pip使用清华镜像源（国内加速）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    # Playwright 浏览器依赖
    wget \
    gnupg \
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
RUN pip install --no-cache-dir -e .[web,watch]

# 安装Playwright浏览器
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
# ENV ZHIPUAI_MODEL=glm-4-flash

# 默认命令
CMD ["aat", "--help"]
