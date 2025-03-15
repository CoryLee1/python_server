# AI VTuber 多模型后端

这是一个基于 LiteLLM 的多模型 AI VTuber 后端，支持多种 AI 模型，包括 OpenAI、Claude、Gemini、DeepSeek 和 Llama。

## 功能特点

- 支持多种 AI 模型（OpenAI、Claude、Gemini、Vertex AI、DeepSeek、Llama）
- WebSocket 实时通信
- REST API 接口
- 文本和视觉模型分开配置
- 音频生成和效果处理
- 灵活的配置管理

## 项目结构

- `ai_manager.py` - AI 模型管理器，处理与不同 AI 模型的通信
- `server.py` - 主服务器，提供 WebSocket 和 REST API 接口
- `voice.py` - 语音合成模块（未包含在示例中）
- `client_example.py` - REST API 客户端示例

## 安装

1. 克隆仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 创建 `.env` 文件并配置 API 密钥

## 环境变量配置

在项目根目录创建 `.env` 文件，包含以下配置：

```
# OpenAI API
OPENAI_API_KEY=sk-...

# Anthropic API
ANTHROPIC_API_KEY=sk-...

# Google API
GEMINI_API_KEY=...

# Vertex AI (Google Cloud)
VERTEX_API_KEY=...
VERTEX_PROJECT=your-project-id
VERTEX_LOCATION=us-central1

# DeepSeek API
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Llama API
LLAMA_API_KEY=...
LLAMA_API_BASE=https://api.llama-api.com
```

## 使用方法

### 启动服务器

```bash
python server.py
```

服务器将在 `http://localhost:8000` 上运行。

### WebSocket 接口

连接到 WebSocket 端点:

```
ws://localhost:8000/ws
```

WebSocket 支持以下消息类型：

1. `realtimeInput` - 实时用户输入
2. `configUpdate` - 更新配置
3. `image_data` - 发送图像数据进行处理
4. `model_request` - 请求可用模型信息

### REST API 接口

- `GET /available_models` - 获取可用模型
- `GET /health` - 健康检查
- `GET /config` - 获取当前配置
- `POST /update_config` - 更新配置
- `POST /generate_response` - 生成 AI 响应
- `POST /process_image` - 处理图像（待实现）

## 示例客户端

查看 `client_example.py` 以了解如何使用 REST API 接口。

```bash
python client_example.py
```

## 自定义和扩展

- 添加新模型：在 `ai_manager.py` 的 `model_map` 和 `vision_model_map` 中添加新模型
- 自定义提示：修改 `DEFAULT_SYSTEM_PROMPT` 或通过配置接口更新
- 添加更多 API 端点：在 `server.py` 中添加新的 FastAPI 路由

## 注意事项

- 这是一个示例项目，生产环境使用时请添加适当的安全措施
- 不同 AI 模型有不同的计费方式和限制，请参考各自的文档
- 某些模型可能需要特定的提示工程技术才能获得最佳效果