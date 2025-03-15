from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
import json
import os
import asyncio
from dotenv import load_dotenv
from voice import synthesize_speech, add_echo_effect
from ai_manager import ai_manager, DEFAULT_MODEL_CONFIG, DEFAULT_SYSTEM_PROMPT
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# 加载环境变量
load_dotenv()

# ======= 修改这个变量切换默认模型 =======
# 可选值: "gemini", "gpt-4", "gpt-3.5-turbo", "claude-3-opus", 
#        "claude-3-sonnet", "claude-3-haiku", "deepseek-chat", 
#        "vertex-gemini-1.5-flash", "vertex-gemini-1.5-pro"
ACTIVE_MODEL = os.getenv("DEFAULT_MODEL", "gemini")

# 确保输出目录存在
OUTPUT_DIR = os.path.abspath("outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"✅ 确保输出目录存在: {OUTPUT_DIR}")

# 创建credentials目录（如果不存在）
CREDENTIALS_DIR = os.path.abspath("credentials")
os.makedirs(CREDENTIALS_DIR, exist_ok=True)
print(f"✅ 确保凭据目录存在: {CREDENTIALS_DIR}")

class Config:
    vision_enabled: bool = False
    blink_frequency: float = 3.0
    vision_input_source: str = "camera"
    text_prompt: str = DEFAULT_SYSTEM_PROMPT
    model_config: dict = DEFAULT_MODEL_CONFIG.copy()
    text_model: str = ACTIVE_MODEL  # 使用ACTIVE_MODEL变量
    vision_model: str = os.getenv("DEFAULT_VISION_MODEL", "gemini")  # 可选择不同的视觉模型

config = Config()

def sanitize_string(s):
    """清理字符串,移除可能导致编码问题的字符"""
    if not isinstance(s, str):
        return s
    return ''.join(c for c in s if not (0xD800 <= ord(c) <= 0xDFFF))

def get_absolute_audio_path(audio_path):
    """获取音频文件的绝对路径"""
    if not os.path.isabs(audio_path):
        return os.path.join(OUTPUT_DIR, os.path.basename(audio_path))
    return audio_path

class WebSocketManager:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.is_connected = False
        self.retry_count = 0
        self.max_retries = 5

    async def connect(self):
        """建立连接"""
        if not self.is_connected:
            try:
                # 避免重复 accept
                try:
                    await self.websocket.accept()
                except RuntimeError as e:
                    if "already accepted" not in str(e).lower():
                        raise
                self.is_connected = True
                self.retry_count = 0
                print("✅ Unity 连接成功！")
            except Exception as e:
                print(f"❌ 连接失败: {str(e)}")
                self.is_connected = False

    async def disconnect(self):
        """断开连接"""
        if self.is_connected:
            self.is_connected = False
            try:
                await self.websocket.close()
            except Exception as e:
                print(f"❌ 关闭连接时出错: {str(e)}")
        print("🔌 连接已断开")

    async def send_json(self, data: dict):
        """安全地发送JSON数据"""
        if not self.is_connected:
            print("⚠️ WebSocket未连接，无法发送消息")
            return

        try:
            # 处理音频路径
            if isinstance(data, dict) and "audio_path" in data:
                data["audio_path"] = get_absolute_audio_path(data["audio_path"])
            
            # 递归清理所有字符串值
            cleaned_data = self._clean_dict(data)
            json_str = json.dumps(cleaned_data, ensure_ascii=False)
            await self.websocket.send_text(json_str)
            print(f"📤 发送消息: {json_str}")
        except Exception as e:
            print(f"❌ 发送消息时出错: {str(e)}")
            self.is_connected = False
            await self.try_reconnect()

    async def try_reconnect(self):
        """尝试重新连接"""
        while not self.is_connected and self.retry_count < self.max_retries:
            self.retry_count += 1
            print(f"🔄 尝试重新连接... ({self.retry_count}/{self.max_retries})")
            await asyncio.sleep(2)  # 等待2秒后重试
            await self.connect()

    def _clean_dict(self, d):
        """递归清理字典中的所有字符串值"""
        if isinstance(d, dict):
            return {key: self._clean_dict(value) for key, value in d.items()}
        elif isinstance(d, list):
            return [self._clean_dict(item) for item in d]
        elif isinstance(d, str):
            return sanitize_string(d)
        return d

app = FastAPI(title="AI VTuber Server", description="基于LiteLLM的多模型AI VTuber后端")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境请指定具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)

@app.on_event("startup")
async def startup_event():
    """FastAPI服务器启动时运行"""
    print(f"🚀 服务器启动，当前默认模型: {ACTIVE_MODEL}")
    print("🔍 检查可用模型...")
    available_models = ai_manager.get_available_models()
    print(f"✅ 可用模型: {json.dumps(available_models, indent=2, ensure_ascii=False)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    ws_manager = WebSocketManager(websocket)
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            await ws_manager.connect()
            if not ws_manager.is_connected:
                retry_count += 1
                await asyncio.sleep(2)
                continue
                
            # 连接时发送可用模型
            try:
                available_models = ai_manager.get_available_models()
                await ws_manager.send_json({
                    "type": "models_info",
                    "available_models": available_models
                })
            except Exception as e:
                print(f"❌ 发送模型信息时出错: {str(e)}")
                
            while ws_manager.is_connected:
                try:
                    raw_data = await websocket.receive_text()
                    print(f"📩 收到 Unity 消息: {raw_data}")
                    
                    data = json.loads(raw_data)
                    
                    if "realtimeInput" in data:
                        user_input = sanitize_string(data["realtimeInput"].get("text", "").strip())
                        if user_input:
                            try:
                                # 使用AIManager生成响应
                                ai_response = await ai_manager.generate_text_response(
                                    user_input=user_input,
                                    system_prompt=config.text_prompt,
                                    model_name=config.text_model,
                                    config=config.model_config
                                )
                                
                                ai_response = sanitize_string(ai_response)
                                
                                tts_path = synthesize_speech(ai_response)
                                tts_with_echo_path = add_echo_effect(tts_path)
                                
                                print(f"🎵 生成音频文件: {tts_with_echo_path}")
                                
                                await ws_manager.send_json({
                                    "type": "chat",
                                    "response_text": ai_response,
                                    "audio_path": tts_path
                                })
                            except Exception as e:
                                print(f"❌ 生成AI响应时出错: {str(e)}")
                                await ws_manager.send_json({
                                    "type": "error",
                                    "error_message": f"生成响应时出错: {str(e)}"
                                })

                    elif "configUpdate" in data:
                        try:
                            update_data = data["configUpdate"]
                            config.vision_enabled = update_data.get("vision_enabled", config.vision_enabled)
                            config.blink_frequency = update_data.get("blink_frequency", config.blink_frequency)
                            config.vision_input_source = update_data.get("vision_input_source", config.vision_input_source)
                            if "text_prompt" in update_data:
                                config.text_prompt = sanitize_string(update_data["text_prompt"])
                            if "model_config" in update_data:
                                config.model_config.update(update_data["model_config"])
                            # 添加新的配置选项
                            if "text_model" in update_data:
                                config.text_model = update_data["text_model"]
                            if "vision_model" in update_data:
                                config.vision_model = update_data["vision_model"]
                            print("✅ 配置更新成功")
                            
                            # 发送可用模型给客户端
                            available_models = ai_manager.get_available_models()
                            await ws_manager.send_json({
                                "type": "models_info",
                                "available_models": available_models,
                                "current_config": {
                                    "text_model": config.text_model,
                                    "vision_model": config.vision_model,
                                    "text_prompt": config.text_prompt,
                                    "vision_enabled": config.vision_enabled,
                                    "model_config": config.model_config,
                                    "blink_frequency": config.blink_frequency,
                                    "vision_input_source": config.vision_input_source
                                }
                            })
                        except Exception as e:
                            print(f"❌ 更新配置时出错: {str(e)}")
                            await ws_manager.send_json({
                                "type": "error",
                                "error_message": f"更新配置时出错: {str(e)}"
                            })

                    elif "image_data" in data:
                        if not config.vision_enabled:
                            await ws_manager.send_json({
                                "type": "error",
                                "error_message": "视觉功能未启用，请在配置中启用"
                            })
                            continue
                            
                        try:
                            image_data = data["image_data"]
                            # 使用AIManager进行视觉处理
                            vision_result = await ai_manager.process_image(
                                image_data=image_data,
                                prompt="Describe what you see in this image",
                                model_name=config.vision_model,
                                config=config.model_config
                            )
                            
                            vision_text = vision_result.get("vision_response", "⚠️ 视觉模块无描述返回")
                            vision_text = sanitize_string(vision_text)
                            
                            tts_path = synthesize_speech(vision_text)
                            tts_with_echo_path = add_echo_effect(tts_path)
                            
                            print(f"🎵 生成视觉响应音频文件: {tts_with_echo_path}")
                            
                            await ws_manager.send_json({
                                "type": "vision",
                                "vision_response": vision_text,
                                "audio_path": tts_path
                            })
                        except Exception as e:
                            print(f"❌ 处理图像时出错: {str(e)}")
                            await ws_manager.send_json({
                                "type": "error",
                                "error_message": f"处理图像时出错: {str(e)}"
                            })
                    
                    elif "model_request" in data:
                        # 发送可用模型给客户端
                        try:
                            available_models = ai_manager.get_available_models()
                            await ws_manager.send_json({
                                "type": "models_info",
                                "available_models": available_models,
                                "current_config": {
                                    "text_model": config.text_model,
                                    "vision_model": config.vision_model
                                }
                            })
                        except Exception as e:
                            print(f"❌ 获取可用模型时出错: {str(e)}")
                            await ws_manager.send_json({
                                "type": "error",
                                "error_message": f"获取可用模型时出错: {str(e)}"
                            })
                    
                except WebSocketDisconnect:
                    print("🔌 WebSocket断开连接")
                    break
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {str(e)}")
                    if ws_manager.is_connected:
                        await ws_manager.send_json({
                            "type": "error",
                            "error_message": f"JSON解析失败: {str(e)}"
                        })
                except Exception as e:
                    print(f"❌ 处理消息时出错: {str(e)}")
                    if ws_manager.is_connected:
                        await ws_manager.send_json({
                            "type": "error",
                            "error_message": f"处理消息时出错: {str(e)}"
                        })
                    break
            
            retry_count += 1
            if ws_manager.is_connected:
                break
                    
        except Exception as e:
            print(f"❌ 发生错误: {str(e)}")
            retry_count += 1
            await asyncio.sleep(2)
            continue
            
    print(f"{'✅ 连接成功' if ws_manager.is_connected else '❌ 达到最大重试次数'}")
    await ws_manager.disconnect()

@app.get("/available_models")
async def get_available_models():
    """获取可用模型的API端点"""
    try:
        available_models = ai_manager.get_available_models()
        return {"available_models": available_models}
    except Exception as e:
        return {"error": str(e)}

@app.get("/health")
async def health_check():
    """简单的健康检查端点"""
    return {"status": "ok", "active_model": ACTIVE_MODEL}

@app.get("/config")
async def get_config():
    """获取当前配置"""
    return {
        "text_model": config.text_model,
        "vision_model": config.vision_model,
        "text_prompt": config.text_prompt,
        "vision_enabled": config.vision_enabled,
        "model_config": config.model_config,
        "blink_frequency": config.blink_frequency,
        "vision_input_source": config.vision_input_source
    }

@app.post("/update_config")
async def update_config(request: Request):
    """更新配置"""
    try:
        data = await request.json()
        if "text_model" in data:
            config.text_model = data["text_model"]
        if "vision_model" in data:
            config.vision_model = data["vision_model"]
        if "text_prompt" in data:
            config.text_prompt = data["text_prompt"]
        if "vision_enabled" in data:
            config.vision_enabled = data["vision_enabled"]
        if "model_config" in data:
            config.model_config.update(data["model_config"])
        if "blink_frequency" in data:
            config.blink_frequency = data["blink_frequency"]
        if "vision_input_source" in data:
            config.vision_input_source = data["vision_input_source"]
            
        return {"status": "success", "message": "配置已更新"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"更新配置失败: {str(e)}"}
        )

@app.post("/generate_response")
async def generate_response(request: Request):
    """生成AI文本响应的REST API端点"""
    try:
        data = await request.json()
        user_input = data.get("user_input", "")
        system_prompt = data.get("system_prompt", config.text_prompt)
        model_name = data.get("model_name", config.text_model)
        model_config = data.get("model_config", config.model_config)
        
        response_text = await ai_manager.generate_text_response(
            user_input=user_input,
            system_prompt=system_prompt,
            model_name=model_name,
            config=model_config
        )
        
        # 如果配置了语音合成
        audio_path = None
        if data.get("generate_audio", False):
            try:
                audio_path = synthesize_speech(response_text)
                if data.get("add_echo", False):
                    audio_path = add_echo_effect(audio_path)
            except Exception as e:
                print(f"❌ 生成音频失败: {str(e)}")
        
        return {
            "status": "success",
            "response": response_text,
            "model_used": model_name,
            "audio_path": audio_path
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"生成响应失败: {str(e)}"}
        )

# 简单的模型切换接口，支持指定模型名称直接测试
@app.get("/test/{model_name}")
async def test_model(model_name: str, prompt: str = "请介绍一下你自己"):
    """直接测试指定模型的简单接口"""
    try:
        response_text = await ai_manager.generate_text_response(
            user_input=prompt,
            system_prompt=config.text_prompt,
            model_name=model_name,
            config=config.model_config
        )
        
        return {
            "model": model_name,
            "prompt": prompt,
            "response": response_text
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"测试模型失败: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动服务器...")
    uvicorn.run(app, host="0.0.0.0", port=8000)