# Docker 环境问题定位指南

## 查看容器日志

### 查看后端容器日志

```bash
# 查看实时日志
docker logs -f douyin-download-backend

# 查看最近 100 行日志
docker logs --tail 100 douyin-download-backend

# 查看特定时间段的日志
docker logs --since 2026-01-02T00:00:00 douyin-download-backend
```

### 查看前端容器日志

```bash
docker logs -f douyin-download-frontend
```

## 常见问题定位

### 1. 页面加载超时

**错误信息：**
```
Page.goto: Timeout 10000ms exceeded.
```

**可能原因：**
- 网络连接不稳定
- 抖音服务器响应慢
- 需要更长的超时时间
- 链接已失效或需要登录

**解决方法：**
1. 检查网络连接：`docker exec douyin-download-backend ping -c 3 www.douyin.com`
2. 查看详细日志，确认超时发生在哪个阶段
3. 检查 URL 是否有效，尝试在浏览器中直接访问
4. 如果是在 Docker 中运行，检查容器的网络配置

### 2. 未找到视频

**错误信息：**
```
页面分析完成，但未找到视频
```

**定位步骤：**

1. **查看详细日志**：
   ```bash
   docker logs douyin-download-backend | grep -A 10 "未找到视频"
   ```

2. **检查页面截图**（如果已生成）：
   ```bash
   docker exec douyin-download-backend ls -la /app/output/debug_screenshot.png
   # 复制截图到本地
   docker cp douyin-download-backend:/app/output/debug_screenshot.png ./debug_screenshot.png
   ```

3. **检查网络拦截情况**：
   日志中会显示：
   - 网络拦截到的视频 URL 数量
   - 页面提取到的视频 URL 数量
   - 导航捕获的视频 URL

4. **检查网络请求失败**：
   日志中会列出失败的请求，帮助定位问题

### 3. 进入容器进行调试

```bash
# 进入后端容器
docker exec -it douyin-download-backend /bin/sh

# 在容器内测试
python -c "from douyin_downloader import EnhancedDouyinDownloader; import asyncio; asyncio.run(EnhancedDouyinDownloader().analyze_douyin_page('https://v.douyin.com/xxxxx/'))"
```

### 4. 检查容器资源使用

```bash
# 查看容器资源使用情况
docker stats douyin-download-backend

# 查看容器详细信息
docker inspect douyin-download-backend
```

### 5. 检查网络连接

```bash
# 在容器内测试网络
docker exec douyin-download-backend ping -c 3 www.douyin.com
docker exec douyin-download-backend curl -I https://www.douyin.com
```

## 日志级别说明

- **INFO**: 正常流程信息，如"开始分析页面"、"找到 X 个视频"
- **WARNING**: 警告信息，如"未找到视频"、"请求失败"
- **ERROR**: 错误信息，如超时、异常等
- **DEBUG**: 详细调试信息，如"浏览器启动成功"、"发现视频 URL"

## 启用更详细的日志

如果需要更详细的日志，可以修改 `backend/main.py` 中的日志级别：

```python
# 将日志级别改为 DEBUG
root_logger.setLevel(logging.DEBUG)
console_handler.setLevel(logging.DEBUG)
```

然后重新构建容器：

```bash
docker-compose build backend
docker-compose up -d backend
```

## 保存调试信息

当遇到问题时，可以保存完整的日志：

```bash
# 保存后端日志
docker logs douyin-download-backend > backend_logs_$(date +%Y%m%d_%H%M%S).txt

# 保存前端日志
docker logs douyin-download-frontend > frontend_logs_$(date +%Y%m%d_%H%M%S).txt

# 保存容器状态
docker inspect douyin-download-backend > container_info_$(date +%Y%m%d_%H%M%S).json
```

## 常见错误码

- **Timeout 10000ms**: Playwright 默认超时，已改为 60 秒
- **Network Error**: 网络连接问题
- **Page not found**: 页面不存在或 URL 错误
- **Video not found**: 未找到视频，可能是页面结构变化

## 联系支持

如果问题持续存在，请提供以下信息：

1. 完整的错误日志
2. 使用的 URL
3. Docker 版本和系统信息
4. 容器日志文件
5. 调试截图（如果有）

