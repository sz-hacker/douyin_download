# 抖音视频下载与处理工具

一个功能强大的抖音视频下载和处理工具，支持视频下载、文字提取、人声分离等多种功能。提供现代化的 Web 界面和完整的 REST API 服务。

## 📱 效果展示

<div align="center">

### Web 界面效果
<img src="docs/web的截图.png" alt="Web 界面效果" width="800"/>

### 手机端效果
<img src="docs/手机的截图.png" alt="手机端效果" width="400"/>

### 原视频演示
[点击查看原视频演示](https://github.com/sz-hacker/douyin_download/raw/main/docs/%E5%8E%9F%E8%A7%86%E9%A2%91.mp4)

### 去人声效果演示
[点击查看去人声效果演示](https://github.com/sz-hacker/douyin_download/raw/main/docs/%E5%8E%BB%E4%BA%BA%E5%A3%B0%E8%A7%86%E9%A2%91.mp4)

### 提取的文字内容
```
C,你为什么一定要进重点来呀?因为两个高智商的人是不会吵起来的。两个人发生矛盾,其中必有一方的智商冰下。所以你现在都没有跟同学发生过矛盾吗?将人赶路,不断一瞬。哦,高人生活,远离罗乐。
```

</div>

## ✨ 功能特性

### 🎬 视频下载
- **智能解析**: 使用 Playwright 自动解析抖音视频真实地址
- **多方法提取**: 支持网络拦截、页面解析、API 提取等多种方式
- **视频代理**: 后端代理视频流，绕过防盗链限制
- **批量支持**: 支持解析页面中的多个视频链接

### 📝 文字提取
支持三种方式从视频中提取文字，按优先级自动尝试：
- **嵌入字幕提取**: 优先提取视频中的软字幕（SRT/TXT 格式）
- **语音转文字 (ASR)**: 使用 OpenAI Whisper 进行语音识别（如果字幕提取失败）
- **OCR 识别**: 识别视频画面中的硬字幕（支持 PaddleOCR、EasyOCR、Tesseract）

### 🎵 人声分离
- **AI 音频分离**: 使用 Demucs 分离人声和背景音乐
- **灵活处理**: 支持去除人声保留背景音乐，或保留人声去除背景音乐
- **视频合成**: 自动将处理后的音频合并回视频

### 🖥️ Web 界面
- **现代化 UI**: 基于 React + TypeScript + Tailwind CSS 构建，终端风格设计
- **实时进度**: 显示下载和处理进度，支持任务进度查询
- **任务管理**: 支持多任务并行处理，任务历史记录
- **视频预览**: 内置视频播放器，支持在线预览
- **文件下载**: 一键下载处理后的视频、文字文件

### 🔌 REST API
- **FastAPI 框架**: 基于 FastAPI 构建的高性能 API 服务
- **完整接口**: 提供视频下载、处理、文字提取等完整 API
- **流式传输**: 支持视频流式传输和断点续传
- **任务追踪**: 支持异步任务处理和进度查询

## 📋 系统要求

### 必需依赖
- **Python 3.8+**
- **Node.js 18+** (用于前端开发)
- **FFmpeg**: 用于视频和音频处理
  - Windows: `winget install ffmpeg` 或从 [ffmpeg.org](https://ffmpeg.org/download.html) 下载
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt-get install ffmpeg`

### 可选依赖（根据功能需求）
- **OCR 工具**: EasyOCR、PaddleOCR 或 Tesseract（用于文字识别）
- **ASR 工具**: OpenAI Whisper（用于语音转文字，首次使用会自动下载模型）

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd douyin_download
```

### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

安装 Playwright 浏览器：

```bash
playwright install chromium
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
# 或
pnpm install
```

### 4. 运行项目

#### 方式一：Web 界面（推荐）

**启动后端 API 服务**:

```bash
cd backend
python main.py
```

后端服务将在 `http://localhost:9528` 启动。

**启动前端开发服务器**:

```bash
cd frontend
npm run dev
# 或
pnpm dev
```

前端服务将在 `http://localhost:5173` 启动。

访问 `http://localhost:5173` 使用 Web 界面。

#### 方式二：命令行工具

```bash
# 下载视频
python backend/douyin_downloader.py https://v.douyin.com/xxxxx/

# 提取文字
python backend/extract_video_text.py video.mp4 --method asr

# 去除人声
python backend/remove_vocals.py video.mp4
```

## 📖 使用说明

### Web 界面使用

1. **输入视频链接**: 在输入框中粘贴抖音分享链接（支持包含文本的完整分享内容）
2. **解析视频**: 点击"执行"按钮，系统会自动解析视频链接
3. **预览视频**: 解析成功后，可以在线预览视频
4. **下载视频**: 点击下载按钮，选择要下载的视频
5. **处理视频**: 
   - **去除人声**: 点击"下载"按钮下的"无背景音版本"，系统会自动处理并下载
   - **提取文字**: 点击"提取视频文字"，系统会尝试多种方法提取文字并下载

### API 使用

#### 视频下载

```bash
curl -X POST "http://localhost:9528/download" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://v.douyin.com/xxxxx/"}'
```

#### 视频代理（用于播放）

```bash
# 获取视频代理 URL
http://localhost:9528/proxy/video?video_url=<视频URL>
```

#### 下载视频文件

```bash
http://localhost:9528/download/video?video_url=<视频URL>&filename=video.mp4
```

#### 处理视频（去除人声）

```bash
curl -X POST "http://localhost:9528/process/no-vocals?video_url=<视频URL>"
```

#### 提取视频文字

```bash
curl -X POST "http://localhost:9528/process/extract-text?video_url=<视频URL>"
```

#### 查询任务进度

```bash
curl "http://localhost:9528/task/progress/<task_id>"
```

### 命令行工具使用

#### 视频下载

```bash
python backend/douyin_downloader.py <抖音视频链接>
```

示例：
```bash
python backend/douyin_downloader.py https://v.douyin.com/Qs-1HC5bzqQ/
```

下载的视频会保存在 `output/downloads/` 目录下。

#### 文字提取

**提取嵌入字幕**:
```bash
python backend/extract_video_text.py video.mp4 --method subtitle
```

**OCR 识别画面文字**:
```bash
# 使用 EasyOCR（推荐，支持中文）
python backend/extract_video_text.py video.mp4 --method ocr --ocr-method easyocr

# 使用 PaddleOCR（中文优化）
python backend/extract_video_text.py video.mp4 --method ocr --ocr-method paddleocr

# 使用 Tesseract
python backend/extract_video_text.py video.mp4 --method ocr --ocr-method tesseract
```

**语音转文字（ASR）**:
```bash
python backend/extract_video_text.py video.mp4 --method asr --asr-method whisper
```

**列出视频字幕流**:
```bash
python backend/extract_video_text.py video.mp4 --list-streams
```

#### 人声分离

**去除人声，保留背景音乐（默认）**:
```bash
python backend/remove_vocals.py video.mp4
```

**保留人声，去除背景音乐**:
```bash
python backend/remove_vocals.py video.mp4 --keep-vocals
```

**使用不同的分离方法**:
```bash
# 使用 Demucs（默认，推荐）
python backend/remove_vocals.py video.mp4 --method demucs

# 使用 Spleeter
python backend/remove_vocals.py video.mp4 --method spleeter
```

**指定输出文件**:
```bash
python backend/remove_vocals.py video.mp4 -o output.mp4
```

## 📁 项目结构

```
douyin_download/
├── backend/                    # 后端 Python 代码
│   ├── main.py                   # FastAPI 主服务
│   ├── douyin_downloader.py      # 视频下载器
│   ├── extract_video_text.py    # 文字提取工具
│   ├── remove_vocals.py          # 人声分离工具
│   └── requirements.txt          # Python 依赖
├── frontend/                  # 前端 React 代码
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/
│   │   │   │   ├── video-downloader.tsx  # 主组件
│   │   │   │   └── ui/                    # UI 组件库
│   │   │   ├── services/
│   │   │   │   └── api.ts                 # API 服务封装
│   │   │   ├── config.ts                 # 配置文件
│   │   │   └── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── docker/                    # Docker 配置
│   ├── docker-compose.yml
│   ├── Dockerfile.backend.ghcr
│   ├── Dockerfile.frontend.ghcr
│   └── nginx.conf
├── docs/                      # 文档和测试资源
│   ├── 原视频.mp4              # 原始测试视频
│   ├── 去人声视频.mp4          # 处理后的测试视频
│   ├── 视频中提取文字.txt      # 提取的文字示例
│   ├── web的截图.png           # Web 界面截图
│   ├── 手机的截图.png          # 手机端截图
│   ├── 微信支付码.jpg          # 微信打赏码
│   └── 支付宝支付码.jpg        # 支付宝打赏码
├── output/                    # 输出目录
│   ├── downloads/              # 下载的文件
│   ├── temp_audio/             # 音频处理临时文件
│   └── temp_text/              # 文字提取临时文件
└── README.md
```

## 🔧 配置说明

### API 配置

前端 API 基础 URL 可通过环境变量配置：

```bash
# 设置后端 API 地址
export VITE_API_BASE_URL=http://localhost:9528
```

### 输出目录

默认输出目录为 `output/`，包含：
- `output/downloads/`: 下载和处理后的文件
- `output/temp_audio/`: 音频处理临时文件
- `output/temp_text/`: 文字提取临时文件

### OCR 参数
- `--ocr-interval`: 采样间隔（秒，默认 0.5）
- `--ocr-lang`: 语言代码（默认 `ch` 或 `ch_sim+en`）

### ASR 参数
- `--asr-method`: ASR 方法（`whisper` 或 `vosk`，默认 `whisper`）

## 📸 测试资源

项目提供了完整的测试资源，位于 `docs/` 目录：

- **原视频.mp4**: 原始测试视频，可用于测试各种功能
- **去人声视频.mp4**: 使用人声分离功能处理后的视频示例
- **视频中提取文字.txt**: 从视频中提取的文字内容示例
- **web的截图.png**: Web 界面的使用截图
- **手机的截图.png**: 移动端使用截图

这些资源可以帮助您：
- 了解工具的处理效果
- 测试和验证功能
- 作为开发参考

## ⚠️ 注意事项

1. **法律合规**: 请确保下载和使用视频符合相关法律法规和平台服务条款
2. **版权保护**: 下载的视频仅供个人学习研究使用，请勿用于商业用途
3. **性能要求**: 
   - OCR 和 ASR 处理需要较长时间，请耐心等待
   - 建议使用 GPU 加速以提高处理速度
   - 首次使用 Whisper 需要下载模型文件（约 1.5GB）
4. **依赖安装**: 某些功能需要额外的依赖包，首次使用时会提示安装
5. **网络要求**: 视频下载和处理需要稳定的网络连接

## 🐛 常见问题

### Q: 下载失败怎么办？
A: 
- 检查网络连接，确保抖音链接有效
- 如果问题持续，可能是平台更新了反爬机制，需要更新代码
- 确保 Playwright 浏览器已正确安装

### Q: OCR 识别不准确？
A: 可以尝试：
- 调整采样间隔（`--ocr-interval`）
- 更换 OCR 方法（EasyOCR、PaddleOCR、Tesseract）
- 确保视频画面清晰
- 优先使用 PaddleOCR（对中文支持更好）

### Q: 人声分离效果不好？
A: 可以尝试：
- 使用不同的分离方法（Demucs 或 Spleeter）
- 确保音频质量良好
- 某些复杂的音频可能分离效果有限

### Q: FFmpeg 未找到？
A: 确保 FFmpeg 已正确安装并添加到系统 PATH 环境变量中。

### Q: Web 界面无法连接后端？
A: 
- 确保后端服务已启动（`python backend/main.py`）
- 检查后端服务地址是否正确（默认 `http://localhost:9528`）
- 检查浏览器控制台是否有 CORS 错误

### Q: 文字提取很慢？
A: 
- ASR 处理需要较长时间，特别是长视频
- 首次使用 Whisper 需要下载模型文件
- 建议优先使用嵌入字幕提取（最快）
- 如果视频有字幕，系统会自动优先使用字幕提取

## 🐳 使用方式

```bash
# 使用 docker-compose 启动服务（会自动拉取镜像）
docker-compose -f docker/docker-compose.yml up -d

# 更新镜像（体验则无需使用）
docker-compose -f docker/docker-compose.yml pull
```

## 📝 开发计划

- [x] Docker 容器化部署
- [x] GitHub Actions 自动构建
- [x] Web 界面开发
- [x] REST API 服务
- [x] 视频代理功能
- [x] 任务进度追踪
- [ ] 支持更多视频平台（B站等）
- [ ] 批量下载功能
- [ ] 视频格式转换
- [ ] 字幕编辑功能
- [ ] 用户认证和权限管理

## 📄 许可证

详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请通过 Issue 反馈。

## ☕ 请作者喝咖啡

如果这个项目对您有帮助，欢迎请作者喝杯咖啡，支持项目的持续开发！

<div align="center">

### 微信赞赏
<img src="docs/微信支付码.jpg" alt="微信赞赏码" width="300"/>

### 支付宝赞赏
<img src="docs/支付宝支付码.jpg" alt="支付宝赞赏码" width="300"/>

</div>

感谢您的支持！🙏

---

## ⚖️ 免责声明

**重要提示：请在使用本工具前仔细阅读以下免责声明**

### 1. 软件状态
本软件按"现状"提供，不提供任何明示或暗示的保证，包括但不限于：
- 对适销性、特定用途适用性和非侵权性的保证
- 对软件功能、性能、准确性、可靠性、安全性或可用性的保证
- 对软件不会中断、无错误或缺陷的保证

### 2. 责任限制
在任何情况下，作者或版权持有人均不对以下事项承担责任：
- 因使用或无法使用本软件而导致的任何直接、间接、偶然、特殊、惩罚性或后果性损害
- 数据丢失、利润损失、业务中断、商誉损失或其他经济损失
- 因使用本软件而导致的任何法律后果或法律责任

### 3. 使用限制
- **仅供学习研究**: 本工具仅供个人学习、研究和教育目的使用
- **遵守法律法规**: 使用者必须遵守所在国家/地区的法律法规，包括但不限于：
  - 版权法和知识产权法
  - 数据保护法
  - 计算机安全法
- **遵守平台条款**: 使用者必须遵守相关视频平台的服务条款和使用协议
- **禁止商业用途**: 禁止将本工具用于任何商业目的或盈利活动
- **禁止非法用途**: 禁止使用本工具下载、传播或使用任何未经授权的内容

### 4. 用户责任
使用者明确理解并同意：
- 使用本工具的所有行为均由使用者自行决定和负责
- 使用者需自行判断下载内容的合法性和合规性
- 使用者需自行承担因使用本工具而产生的所有风险和责任
- 使用者需自行处理因使用本工具而产生的任何法律纠纷

### 5. 不承担责任
作者不对以下事项承担责任：
- 因违反平台服务条款而导致的账户封禁或其他后果
- 因下载或使用受版权保护内容而导致的任何法律后果
- 因使用本工具而导致的任何数据泄露、隐私侵犯或安全问题
- 因软件缺陷、错误或故障而导致的任何损失

### 6. 知识产权
- 本软件本身的知识产权归作者所有
- 通过本工具下载的视频、音频或其他内容的知识产权归原作者所有
- 使用者不得将下载的内容用于侵犯他人知识产权的用途

### 7. 服务可用性
- 作者不保证本工具能够持续、稳定地访问任何第三方平台
- 第三方平台可能随时更改其技术架构、API 或访问策略
- 本工具可能因平台更新而失效，作者不承担维护或更新的义务

### 8. 接受条款
通过使用本工具，您表示已阅读、理解并同意接受本免责声明的所有条款。如果您不同意本免责声明的任何部分，请立即停止使用本工具。

**再次提醒**: 使用本工具即表示您已充分理解并接受所有风险和责任。作者不对您的使用行为承担任何法律责任。
