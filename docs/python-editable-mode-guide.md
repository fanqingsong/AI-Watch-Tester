# Python Editable Mode 开发指南

## 什么是 Editable Mode？

Editable Mode（开发模式）是一种 Python 包安装方式，允许你在开发过程中修改代码后无需重新安装即可立即生效。

## 当前项目状态

检查你的项目安装方式：

```bash
pip show aat-devqa
```

如果看到以下输出，说明已处于 editable mode：

```
Name: aat-devqa
Version: 1.6.2
Location: /home/song/workspace/me/AI-Watch-Tester/.venv/lib/python3.12/site-packages
Editable project location: /home/song/workspace/me/AI-Watch-Tester  # ← 关键信息
```

## 如何安装 Editable Mode

### 在项目根目录运行：

```bash
pip install -e .
# 或者完整形式
pip install --editable .
```

### 安装 Editable Mode + 开发依赖：

```bash
pip install -e ".[dev]"
```

## Editable Mode 工作原理

### 传统安装模式（`pip install .`）

```
源码目录 → 构建 Wheel → 复制到 site-packages → Python 导入
         ↑                    ↑
      修改代码              需要重新安装才能生效
```

**特点：**
- 代码被复制到 `.venv/lib/python3.12/site-packages/aat-devqa/`
- 修改源码不会影响已安装的版本
- 每次修改需要重新 `pip install .`

### Editable 安装模式（`pip install -e .`）

```
源码目录 → 创建引用链接(.egg-link) → Python 直接从源码导入
              ↑                              ↑
           一次性操作                    修改立即生效
```

**特点：**
- 在 `site-packages` 创建 `.egg-link` 文件（指向项目根目录）
- 修改 `src/aat/` 下的代码，运行时立即读取最新版本
- 无需重新安装

## 实际工作流程对比

### ❌ 传统模式的工作流

```bash
# 1. 初始安装
pip install .

# 2. 修改代码
vim src/aat/engine/humanizer.py

# 3. 必须重新安装才能生效
pip install .

# 4. 运行命令
aat agent chat
```

### ✅ Editable Mode 的工作流

```bash
# 1. 初始安装（只需一次）
pip install -e .

# 2. 修改代码
vim src/aat/engine/humanizer.py

# 3. 直接运行，修改立即生效
aat agent chat

# 4. 继续修改，继续运行，无需重复安装
vim src/aat/adapters/claude.py
aat run test_scenario.yaml
```

## 项目配置支持

### pyproject.toml 配置

当前项目使用 hatchling 作为构建后端：

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "aat-devqa"
version = "1.6.2"

[project.scripts]
aat = "aat.cli.main:app"  # CLI 入口点

[tool.hatch.build.targets.wheel]
packages = ["src/aat"]  # 指定包目录
```

### setup.py 配置（传统方式）

如果使用 setup.py：

```python
from setuptools import setup, find_packages

setup(
    name="aat-devqa",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
```

## 常见问题

### Q: 我忘记是否安装了 editable mode，如何检查？

```bash
pip show aat-devqa | grep "Editable"
```

如果有输出 `Editable project location:`，说明是 editable mode。

### Q: 如何切换到 editable mode？

```bash
# 先卸载现有版本
pip uninstall aat-devqa

# 重新安装为 editable mode
pip install -e .
```

### Q: Editable mode 有什么缺点？

1. **部署时不适用**：Editable mode 仅用于开发，生产环境应使用标准安装
2. **路径依赖**：移动项目目录后需要重新安装
3. **IDE索引**：某些 IDE 需要额外配置才能正确索引代码

### Q: 何时需要重新安装？

仅在以下情况需要重新运行 `pip install -e .`：

- 新增了依赖包（修改了 `pyproject.toml` 的 `dependencies`）
- 修改了包结构（新增/删除了子模块）
- 移动了项目目录

修改函数、类、逻辑代码都**无需**重新安装。

## 最佳实践

### 开发流程

```bash
# 1. 克隆项目
git clone https://github.com/ksgisang/AI-Watch-Tester
cd AI-Watch-Tester

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 3. 安装 editable mode + 开发依赖（只需一次）
pip install -e ".[dev]"

# 4. 开始开发
# 修改代码 → 直接运行 → 无需重复安装
```

### 推荐的 .gitignore 条目

```gitignore
# Virtual environment
.venv/
venv/

# Python cache
__pycache__/
*.pyc
*.pyo

# Build artifacts
dist/
build/
*.egg-info/
.eggs/
```

## 总结

✅ **推荐使用 Editable Mode 进行开发**
- 一次安装，持续生效
- 代码修改立即反映到运行结果
- 符合敏捷开发节奏

⚠️ **生产部署使用标准安装**
- 部署时使用 `pip install .` 或从 PyPI 安装
- 确保依赖版本锁定

## 相关命令速查

```bash
# 安装 editable mode
pip install -e .

# 安装 editable + 开发依赖
pip install -e ".[dev]"

# 检查安装模式
pip show aat-devqa

# 卸载
pip uninstall aat-devqa

# 查看包文件位置（editable mode 会显示源码路径）
pip show -f aat-devqa
```

---

**文档版本**: 1.0  
**最后更新**: 2026-06-26  
**适用于**: AAT 项目（使用 hatchling 构建系统）
