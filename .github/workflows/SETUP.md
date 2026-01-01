# GitHub Actions 快速设置指南

## 🚀 快速开始

### 1. 启用 GitHub Actions

1. 将代码推送到 GitHub 仓库
2. 访问仓库的 "Actions" 标签页
3. 如果提示启用 Actions，点击 "I understand my workflows, go ahead and enable them"

### 2. 使用默认工作流（推荐）

**docker-build.yml** 会自动：
- 在推送到主分支时构建镜像
- 推送到 GitHub Container Registry (ghcr.io)
- 使用 `GITHUB_TOKEN`（自动配置，无需设置）

**无需任何配置即可使用！**

### 3. 查看构建结果

1. 访问仓库的 "Actions" 标签页
2. 点击最新的工作流运行
3. 查看构建日志和结果

### 4. 使用构建的镜像

构建完成后，镜像会自动推送到：
- `ghcr.io/<username>/<repo-name>-frontend:latest`
- `ghcr.io/<username>/<repo-name>-backend:latest`

#### 拉取镜像

```bash
# 需要先登录 GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin

# 拉取镜像
docker pull ghcr.io/<username>/<repo-name>-frontend:latest
docker pull ghcr.io/<username>/<repo-name>-backend:latest
```

#### 公开镜像（可选）

默认情况下，镜像为私有。要公开镜像：

1. 访问 https://github.com/<username>/<repo-name>/packages
2. 选择对应的包（frontend 或 backend）
3. 点击 "Package settings"
4. 在 "Danger Zone" 中选择 "Change visibility" → "Public"

公开后，任何人都可以拉取镜像，无需登录。

## 🔧 高级配置

### 推送到 Docker Hub（可选）

如果需要同时推送到 Docker Hub：

1. **创建 Docker Hub 访问令牌**：
   - 访问 https://hub.docker.com/settings/security
   - 点击 "New Access Token"
   - 创建令牌并复制

2. **配置 GitHub Secrets**：
   - 访问仓库：Settings → Secrets and variables → Actions
   - 添加以下 secrets：
     - `DOCKERHUB_USERNAME`：您的 Docker Hub 用户名
     - `DOCKERHUB_PASSWORD`：刚才创建的访问令牌

3. **启用 Docker Hub 工作流**：
   - 工作流文件 `docker-build-dockerhub.yml` 会自动检测 secrets
   - 如果配置了 secrets，工作流会自动运行

### 手动触发工作流

1. 访问仓库的 "Actions" 标签页
2. 选择 "Build and Push Docker Images"
3. 点击 "Run workflow"
4. 选择分支和选项
5. 点击 "Run workflow"

### 使用语义化版本标签

创建 Git 标签来触发版本构建：

```bash
# 创建版本标签
git tag v1.0.0
git push origin v1.0.0
```

工作流会自动创建以下标签：
- `1.0.0`（完整版本）
- `1.0`（主版本.次版本）
- `latest`（主分支）

## 📋 工作流说明

### docker-build.yml（默认）

- **触发**：Push、Pull Request、标签、手动触发
- **推送**：GitHub Container Registry
- **权限**：自动使用 `GITHUB_TOKEN`
- **缓存**：使用 GitHub Actions 缓存加速构建

### docker-build-dockerhub.yml（可选）

- **触发**：Push 到主分支、标签、手动触发
- **推送**：Docker Hub
- **要求**：需要配置 `DOCKERHUB_USERNAME` 和 `DOCKERHUB_PASSWORD` secrets

## 🐛 故障排查

### 构建失败

1. **检查 Dockerfile 路径**：
   - 确保 `docker/Dockerfile.frontend.ghcr` 和 `docker/Dockerfile.backend.ghcr` 存在
   - 检查构建上下文路径是否正确

2. **查看构建日志**：
   - 在 Actions 页面查看详细错误信息
   - 检查是否有依赖安装失败

3. **检查权限**：
   - GitHub Container Registry：确保 `GITHUB_TOKEN` 有写入权限（通常自动配置）
   - Docker Hub：验证 secrets 是否正确

### 推送失败

1. **GitHub Container Registry**：
   - 检查仓库权限设置
   - 确认 `GITHUB_TOKEN` 有效

2. **Docker Hub**：
   - 验证用户名和密码/令牌是否正确
   - 检查 Docker Hub 账户状态

### 镜像无法拉取

1. **私有镜像**：
   - 需要先登录：`docker login ghcr.io -u <username> -p <token>`
   - 或公开镜像（见上方说明）

2. **权限问题**：
   - 确保有访问仓库的权限
   - 检查镜像是否已公开

## 📚 更多信息

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [GitHub Container Registry 文档](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Hub 文档](https://docs.docker.com/docker-hub/)

