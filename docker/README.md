# Docker 构建和部署指南

本文档说明如何使用 Docker 构建和部署抖音下载工具的前后端服务。

## 📋 前置要求

- 已安装 Docker 和 Docker Compose
- 已登录 Docker Registry（如果需要上传镜像）

## 🚀 快速开始

### 方式一：使用 Docker Compose（推荐）

```bash
# 构建并启动所有服务
cd docker
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

访问：
- 前端：http://localhost:9527
- 后端：http://localhost:9528

### 方式二：单独构建和运行

#### Windows (PowerShell)

```powershell
# 构建镜像
.\docker\build-and-push.ps1

# 运行前端
docker run -d -p 9527:9527 douyin-download-frontend:latest

# 运行后端
docker run -d -p 9528:9528 -v ${PWD}/output:/app/output douyin-download-backend:latest
```

#### Linux/Mac (Bash)

```bash
# 给脚本添加执行权限
chmod +x docker/build-and-push.sh

# 构建镜像
./docker/build-and-push.sh

# 运行前端
docker run -d -p 9527:9527 douyin-download-frontend:latest

# 运行后端
docker run -d -p 9528:9528 -v $(pwd)/output:/app/output douyin-download-backend:latest
```

## 📦 构建和上传镜像

### Windows (PowerShell)

```powershell
# 基本构建
.\docker\build-and-push.ps1

# 构建并上传到 Docker Hub
.\docker\build-and-push.ps1 -Username your-username -Push

# 构建并上传到私有 Registry
.\docker\build-and-push.ps1 -Registry registry.example.com -Username your-username -Tag v1.0.0 -Push

# 不使用缓存构建
.\docker\build-and-push.ps1 -NoCache
```

### Linux/Mac (Bash)

```bash
# 基本构建
./docker/build-and-push.sh

# 构建并上传到 Docker Hub
./docker/build-and-push.sh --username your-username --push

# 构建并上传到私有 Registry
./docker/build-and-push.sh --registry registry.example.com --username your-username --tag v1.0.0 --push

# 不使用缓存构建
./docker/build-and-push.sh --no-cache

# 查看帮助
./docker/build-and-push.sh --help
```

### 使用环境变量 (Bash)

```bash
export DOCKER_USERNAME=your-username
export DOCKER_TAG=v1.0.0
export DOCKER_PUSH=true
./docker/build-and-push.sh
```

## 🔧 配置说明

### 镜像标签格式

- 默认：`douyin-download-frontend:latest` 和 `douyin-download-backend:latest`
- 带 Registry：`registry/username/douyin-download-frontend:tag`

### 端口配置

- 前端：9527
- 后端：9528

### 数据持久化

后端容器的输出目录会挂载到主机的 `output/` 目录，确保下载的文件不会丢失。

## 📝 脚本参数说明

### PowerShell 脚本参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-Registry` | Docker Registry 地址 | `docker.io` |
| `-Username` | Registry 用户名 | 空 |
| `-ImageName` | 镜像名称前缀 | `douyin-download` |
| `-Tag` | 镜像标签 | `latest` |
| `-Push` | 是否上传镜像 | `false` |
| `-NoCache` | 是否不使用缓存 | `false` |

### Bash 脚本参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--registry` | Docker Registry 地址 | `docker.io` |
| `--username` | Registry 用户名 | 空 |
| `--image-name` | 镜像名称前缀 | `douyin-download` |
| `--tag` | 镜像标签 | `latest` |
| `--push` | 是否上传镜像 | `false` |
| `--no-cache` | 是否不使用缓存 | `false` |

## 🔍 故障排查

### 构建失败：无法拉取基础镜像

如果遇到以下错误：
```
ERROR: failed to do request: Head "https://registry-1.docker.io/v2/library/nginx/manifests/alpine": EOF
```

这通常是因为无法访问 Docker Hub。解决方案：

#### 方案 1：配置 Docker Desktop 镜像加速器（推荐）

1. **Windows 用户**：
   - 打开 Docker Desktop
   - 点击设置（Settings）→ Docker Engine
   - 添加以下配置：
   ```json
   {
     "registry-mirrors": [
       "https://docker.mirrors.ustc.edu.cn",
       "https://hub-mirror.c.163.com",
       "https://mirror.baidubce.com"
     ]
   }
   ```
   - 点击 "Apply & Restart" 重启 Docker

2. **使用配置脚本**：
   ```powershell
   .\docker\setup-docker-mirror.ps1
   ```

3. **详细说明**：查看 [DOCKER_MIRROR_SETUP.md](./DOCKER_MIRROR_SETUP.md)

#### 方案 2：使用国内镜像源 Dockerfile（临时方案）

如果无法配置镜像加速器，可以使用备选 Dockerfile：

```powershell
# 使用国内镜像源构建前端
docker build -f docker/Dockerfile.frontend.mirror -t douyin-download-frontend:latest .

# 使用国内镜像源构建后端
docker build -f docker/Dockerfile.backend.mirror -t douyin-download-backend:latest .
```

或修改 `docker-compose.yml` 中的 `dockerfile` 路径。

### 其他构建失败问题

1. 检查 Docker 是否正常运行：`docker --version`
2. 检查网络连接（下载依赖需要）
3. 尝试使用 `--no-cache` 参数重新构建

### 上传失败

1. 确保已登录 Docker Registry：`docker login`
2. 检查镜像标签是否正确
3. 检查是否有推送权限

### 容器无法启动

1. 检查端口是否被占用：`netstat -an | grep 9527` (Linux/Mac) 或 `netstat -an | findstr 9527` (Windows)
2. 查看容器日志：`docker logs <container-name>`
3. 检查挂载的目录权限

## 📚 更多信息

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)

