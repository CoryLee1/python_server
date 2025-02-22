from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types
import json
import os
import sys
import asyncio
from dotenv import load_dotenv
from vision_module import VisionModule
from voice import synthesize_speech, add_echo_effect

# 确保输出目录存在
OUTPUT_DIR = os.path.abspath("outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"✅ 确保输出目录存在: {OUTPUT_DIR}")

load_dotenv()
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GENAI_API_KEY:
    raise ValueError("🚨 ERROR: 未找到 GEMINI_API_KEY，请在 .env 文件中设置")

client = genai.Client(api_key=GENAI_API_KEY)

DEFAULT_MODEL_CONFIG = {
    "temperature": 0.95,
    "max_output_tokens": 100,
    "top_p": 0.9,
    "top_k": 40
}
DEFAULT_SYSTEM_PROMPT = "You are very 'brat' VTuber who interacts with your audience and provides rebellious and interesting responses. You can use Chinese, Japanese, and English.Limit your dialogue into 60 words or less."

class Config:
    vision_enabled: bool = False
    blink_frequency: float = 3.0
    vision_input_source: str = "camera"
    text_prompt: str = DEFAULT_SYSTEM_PROMPT
    model_config: dict = DEFAULT_MODEL_CONFIG.copy()

config = Config()
vision_module = VisionModule(api_key=GENAI_API_KEY)

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

app = FastAPI()

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
                
            while ws_manager.is_connected:
                try:
                    raw_data = await websocket.receive_text()
                    print(f"📩 收到 Unity 消息: {raw_data}")
                    
                    data = json.loads(raw_data)
                    
                    if "realtimeInput" in data:
                        user_input = sanitize_string(data["realtimeInput"].get("text", "").strip())
                        if user_input:
                            final_prompt = config.text_prompt + "\n" + user_input
                            
                            try:
                                gemini_response = client.models.generate_content(
                                    model="gemini-2.0-flash",
                                    contents=[final_prompt],
                                    #generation_config=types.GenerationConfig(**config.model_config)
                                )
                                ai_response = gemini_response.text.strip() if gemini_response.text else "⚠️ AI 没有返回文本"
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
                            print("✅ 配置更新成功")
                        except Exception as e:
                            print(f"❌ 更新配置时出错: {str(e)}")

                    elif "image_data" in data:
                        try:
                            image_data = data["image_data"]
                            vision_result = vision_module.process_image(image_data)
                            vision_text = vision_result.get("vision_response", "⚠️ 视觉模块无描述返回")
                            vision_text = sanitize_string(vision_text)
                            
                            tts_path = synthesize_speech(vision_text)
                            tts_with_echo_path = add_echo_effect(tts_path)
                            
                            print(f"🎵 生成视觉响应音频文件: {tts_with_echo_path}")
                            
                            await ws_manager.send_json({
                                "type": "vision",
                                "vision_response": vision_text,
                                "audio_path": tts_with_echo_path
                            })
                        except Exception as e:
                            print(f"❌ 处理图像时出错: {str(e)}")
                            await ws_manager.send_json({
                                "type": "error",
                                "error_message": f"处理图像时出错: {str(e)}"
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

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动服务器...")
    uvicorn.run(app, host="0.0.0.0", port=8000)