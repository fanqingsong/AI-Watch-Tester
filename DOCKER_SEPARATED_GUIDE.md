# Docker Compose Separated Configuration Guide

## 🎯 Overview

The AI-Watch-Tester project now uses **separated Docker Compose configurations** for better maintainability and clarity:

- **`docker-compose.aat.yml`** - AAT testing environment (CLI tools, automated testing)
- **`cloud/docker-compose.cloud.yml`** - Cloud SaaS platform (multi-user, web UI, database)

## 🚀 Quick Start

### AAT Testing Environment
```bash
# Start AAT environment
docker compose -f docker-compose.aat.yml up -d

# Run tests
docker compose -f docker-compose.aat.yml exec aat aat run test_scenario.yaml

# Scan pages
docker compose -f docker-compose.aat.yml exec aat aat scan --url https://example.com

# Generate scenarios
docker compose -f docker-compose.aat.yml exec aat aat generate --spec requirements.md
```

### Cloud SaaS Platform
```bash
# Start Cloud platform
docker compose -f cloud/docker-compose.cloud.yml up -d

# Access services
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## 📋 Configuration Comparison

### AAT Testing Environment (`docker-compose.aat.yml`)

**Purpose**: Core testing functionality, command-line tools

**Features**:
- ✅ AAT CLI tools (run, scan, generate, etc.)
- ✅ Playwright browser automation
- ✅ AI integration (Claude, GPT, Ollama, etc.)
- ✅ Image matching and OCR
- ✅ Test execution and reporting
- ❌ No web dashboard (removed)
- ❌ No database
- ❌ Single-user mode

**Use Cases**:
- Local development testing
- CI/CD integration
- Automated test execution
- Command-line based workflows

**Service**:
- `aat` - AAT testing environment container

### Cloud SaaS Platform (`docker-compose.cloud.yml`)

**Purpose**: Multi-user testing platform with web interface

**Features**:
- ✅ Multi-user support
- ✅ Web-based UI (Next.js frontend)
- ✅ Authentication and authorization
- ✅ Database (SQLite/PostgreSQL)
- ✅ Test scenario management
- ✅ Team collaboration
- ✅ Persistent storage
- ✅ Rate limiting and user tiers

**Use Cases**:
- Team testing collaboration
- Managed testing platform
- Production deployment
- Web-based test management

**Services**:
- `cloud-backend` - FastAPI backend server (port 8000)
- `cloud-frontend` - Next.js web UI (port 3000)
- `cloud_screenshots` - Screenshot storage volume
- `cloud_uploads` - File upload volume
- `cloud_db` - Database volume

**Configuration File**: `cloud/docker-compose.cloud.yml`

## 🔧 Usage Examples

### AAT Environment

#### Basic Usage
```bash
# Start environment
docker compose -f docker-compose.aat.yml up -d

# Interactive shell
docker compose -f docker-compose.aat.yml exec aat bash

# Run AAT commands
docker compose -f docker-compose.aat.yml exec aat aat --help
docker compose -f docker-compose.aat.yml exec aat aat run test.yaml
docker compose -f docker-compose.aat.yml exec aat aat scan --url https://example.com

# View logs
docker compose -f docker-compose.aat.yml logs -f aat

# Stop environment
docker compose -f docker-compose.aat.yml down
```

#### Advanced Usage
```bash
# Rebuild image
docker compose -f docker-compose.aat.yml build --no-cache

# Start with custom environment
ZHIPUAI_API_KEY=your_key docker compose -f docker-compose.aat.yml up -d

# Mount custom scenarios directory
docker compose -f docker-compose.aat.yml up -d \
  -v /path/to/scenarios:/app/scenarios
```

### Cloud Platform

#### Basic Usage
```bash
# Start platform
docker compose -f docker-compose.cloud.yml up -d

# Check status
docker compose -f docker-compose.cloud.yml ps

# View logs
docker compose -f docker-compose.cloud.yml logs -f cloud-backend
docker compose -f docker-compose.cloud.yml logs -f cloud-frontend

# Stop platform
docker compose -f docker-compose.cloud.yml down
```

#### Advanced Usage
```bash
# Rebuild images
docker compose -f docker-compose.cloud.yml build --no-cache

# Start with encryption key
AWT_ENCRYPTION_KEY=your_key docker compose -f docker-compose.cloud.yml up -d

# Access backend logs
docker compose -f docker-compose.cloud.yml logs -f cloud-backend

# Clean volumes
docker compose -f docker-compose.cloud.yml down -v
```

## 🔑 Environment Variables

### AAT Environment

Create a `.env` file:
```bash
# AI Provider (choose one)
ZHIPUAI_API_KEY=your_zhipu_api_key_here
ZHIPUAI_MODEL=glm-4.7
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### Cloud Platform

Create a `.env` file:
```bash
# AI Provider
ZHIPUAI_API_KEY=your_zhipu_api_key_here
ZHIPUAI_MODEL=glm-4.7

# Cloud Configuration
AWT_ENCRYPTION_KEY=your_generated_encryption_key_here
AWT_AI_PROVIDER=zhipuai
AWT_AI_API_KEY=your_zhipu_api_key_here
AWT_AI_MODEL=glm-4.7

# Database (optional, defaults to SQLite)
# AWT_DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database

# Rate Limiting
AWT_RATE_LIMIT_FREE=5
AWT_RATE_LIMIT_PRO=100
AWT_RATE_LIMIT_TEAM=500

# Debug Mode
AWT_DEBUG=false
```

## 📊 Migration from Legacy Config

### Old Commands → New Commands

```bash
# Old: Start AAT Dashboard
docker compose up aat -d

# New: Start AAT environment
docker compose -f docker-compose.aat.yml up -d


# Old: Start Cloud platform
docker compose up cloud-backend cloud-frontend -d

# New: Start Cloud platform
docker compose -f docker-compose.cloud.yml up -d


# Old: Run AAT commands
docker compose exec aat aat run test.yaml

# New: Run AAT commands
docker compose -f docker-compose.aat.yml exec aat aat run test.yaml
```

## 🎯 Choosing the Right Configuration

### Use AAT Environment (`docker-compose.aat.yml`) when:
- ✅ You need command-line testing tools
- ✅ You're working locally or in CI/CD
- ✅ You prefer CLI over web interface
- ✅ You don't need multi-user support
- ✅ You want minimal setup

### Use Cloud Platform (`docker-compose.cloud.yml`) when:
- ✅ You need team collaboration features
- ✅ You prefer web-based interface
- ✅ You need user authentication
- ✅ You want persistent test storage
- ✅ You're deploying for production

## 🔍 Troubleshooting

### AAT Environment Issues

```bash
# Check if container is running
docker compose -f docker-compose.aat.yml ps

# View logs for errors
docker compose -f docker-compose.aat.yml logs aat

# Restart container
docker compose -f docker-compose.aat.yml restart aat

# Rebuild if issues persist
docker compose -f docker-compose.aat.yml down
docker compose -f docker-compose.aat.yml build --no-cache
docker compose -f docker-compose.aat.yml up -d
```

### Cloud Platform Issues

```bash
# Check service health
docker compose -f docker-compose.cloud.yml ps

# View backend logs
docker compose -f docker-compose.cloud.yml logs cloud-backend

# View frontend logs
docker compose -f docker-compose.cloud.yml logs cloud-frontend

# Restart services
docker compose -f docker-compose.cloud.yml restart

# Check database connectivity
docker compose -f docker-compose.cloud.yml exec cloud-backend \
  python -c "from app.database import engine; print('Database OK')"
```

## 📝 Best Practices

1. **Use separated configs** - Always prefer `docker-compose.aat.yml` or `docker-compose.cloud.yml`
2. **Environment variables** - Use `.env` file for sensitive data
3. **Volume management** - Regular backup of Cloud platform volumes
4. **Image updates** - Rebuild images when pulling latest code
5. **Resource limits** - Consider memory/CPU limits for production

## 🎓 Additional Resources

- [Main README](README.md) - Project overview and features
- [Docker Guide](DOCKER_GUIDE.md) - Detailed Docker usage guide
- [Cloud Documentation](cloud/README.md) - Cloud platform specific docs

---

**Last Updated**: 2024-06-23
**Maintainer**: AILoopLab
