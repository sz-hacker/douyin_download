# GitHub Actions 工作流说明

本项目包含两个 Docker 镜像构建工作流：

## 1. docker-build.yml - GitHub Container Registry

**默认工作流**，将镜像推送到 GitHub Container Registry (ghcr.io)。

### 触发条件

- **Push 到主分支**：main、master、develop
- **创建标签**：v* 格式（如 v1.0.0）
- **Pull Request**：仅构建，不推送
- **手动触发**：workflow_dispatch

### 镜像位置

- 前端：`ghcr.io/<username>/<repo-name>-frontend:latest`
- 后端：`ghcr.io/<username>/<repo-name>-backend:latest`

### 使用方式

```bash
# 拉取镜像
docker pull ghcr.io/<username>/<repo-name>-frontend:latest
docker pull ghcr.io/<username>/<repo-name>-backend:latest

# 运行容器
docker run -d -p 9527:9527 ghcr.io/<username>/<repo-name>-frontend:latest
docker run -d -p 9528:9528 ghcr.io/<username>/<repo-name>-backend:latest
```

### 权限设置

GitHub Container Registry 的镜像默认是私有的。要公开镜像：

1. 访问 https://github.com/<username>/<repo-name>/packages
2. 选择对应的包
3. 点击 "Package settings"
4. 在 "Danger Zone" 中选择 "Change visibility" → "Public"

## 2. docker-build-dockerhub.yml - Docker Hub

可选工作流，将镜像推送到 Docker Hub。

### 前置要求

需要在 GitHub Secrets 中配置：

- `DOCKERHUB_USERNAME`：Docker Hub 用户名
- `DOCKERHUB_PASSWORD`：Docker Hub 访问令牌（推荐）或密码

### 配置 Secrets

1. 访问 GitHub 仓库设置：Settings → Secrets and variables → Actions
2. 点击 "New repository secret"
3. 添加以下 secrets：
   - Name: `DOCKERHUB_USERNAME`，Value: 您的 Docker Hub 用户名
   - Name: `DOCKERHUB_PASSWORD`，Value: 您的 Docker Hub 访问令牌

### 触发条件

- **Push 到主分支**：main、master
- **创建标签**：v* 格式
- **手动触发**：需要提供 Docker Hub 用户名

### 镜像位置

- 前端：`<username>/douyin-download-frontend:latest`
- 后端：`<username>/douyin-download-backend:latest`

## 功能特性

### 自动标签管理

- **分支标签**：`main`、`develop` 等
- **语义化版本**：`v1.0.0` → `1.0.0`、`1.0`
- **SHA 标签**：`main-abc1234`
- **Latest 标签**：主分支自动标记为 `latest`

### 构建缓存

使用 GitHub Actions 缓存（GHA Cache）加速构建：
- 缓存 Docker 层
- 减少重复构建时间
- 自动管理缓存生命周期

### 多架构支持（可选）

如需支持多架构（amd64、arm64），可以在工作流中添加：

```yaml
platforms: linux/amd64,linux/arm64
```

## 手动触发工作流

1. 访问 GitHub 仓库的 "Actions" 标签页
2. 选择对应的工作流
3. 点击 "Run workflow"
4. 选择分支和选项
5. 点击 "Run workflow" 按钮

## 故障排查

### 构建失败

1. 检查 Dockerfile 路径是否正确
2. 检查构建上下文路径
3. 查看工作流日志中的详细错误信息

### 推送失败

1. **GitHub Container Registry**：
   - 检查 `GITHUB_TOKEN` 权限（通常自动配置）
   - 确认仓库权限设置

2. **Docker Hub**：
   - 验证 `DOCKERHUB_USERNAME` 和 `DOCKERHUB_PASSWORD` secrets
   - 确认 Docker Hub 账户状态

### 权限问题

- GitHub Container Registry：镜像默认私有，需要手动公开
- Docker Hub：确保账户有推送权限

## 最佳实践

1. **使用 GitHub Container Registry**：更简单，无需额外配置
2. **使用语义化版本标签**：便于版本管理
3. **启用构建缓存**：加速后续构建
4. **定期清理旧镜像**：避免存储空间浪费

