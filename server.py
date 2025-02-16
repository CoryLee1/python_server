from fastapi import FastAPI, WebSocket
from google import genai
from google.genai import types
import json
import os
from dotenv import load_dotenv
from vision_module import VisionModule  # 导入 Vision 模块

# ----------------------------
# 读取 API Key
load_dotenv()
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GENAI_API_KEY:
    raise ValueError("🚨 ERROR: 未找到 GEMINI_API_KEY，请在 .env 文件中设置")

# ----------------------------
# 初始化 Gemini Client（新版用法）
client = genai.Client(api_key=GENAI_API_KEY)

# ----------------------------
# 默认模型参数和系统提示
DEFAULT_MODEL_CONFIG = {
    "temperature": 0.95,
    "max_output_tokens": 100,
    "top_p": 0.9,
    "top_k": 40
}
DEFAULT_SYSTEM_PROMPT = "你是一个很会整活的VTuber，与你的观众互动，并提供反叛有趣回答。可以中日英运用。"

# ----------------------------
# 共享配置模块（同时包含 Vision 和 文本生成相关配置）
class Config:
    vision_enabled: bool = False
    blink_frequency: float = 3.0
    vision_input_source: str = "camera"
    text_prompt: str = DEFAULT_SYSTEM_PROMPT
    model_config: dict = DEFAULT_MODEL_CONFIG.copy()

config = Config()

# ----------------------------
# 初始化 Vision 模块（内部使用最新文档用法）
vision_module = VisionModule(api_key=GENAI_API_KEY)

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ Unity 连接成功！")
    try:
        while True:
            raw_data = await websocket.receive_text()
            print(f"📩 收到 Unity 消息: {raw_data}")
            try:
                data = json.loads(raw_data)

                # 1. 实时文本输入：生成文本回复
                if "realtimeInput" in data:
                    user_input = data["realtimeInput"].get("text", "").strip()
                    if user_input:
                        print(f"💬 收到文本输入: {user_input}")
                        # 将系统 prompt 与用户输入组合为最终提示
                        final_prompt = config.text_prompt + "\n" + user_input
                        # 调用 Gemini 文本生成 API，传入自定义参数（若支持）
                        response = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=[final_prompt],
                            **config.model_config
                        )
                        text_response = response.text.strip() if response.text else "⚠️ AI 没有返回文本"
                        await websocket.send_text(json.dumps({"response": text_response}))
                    else:
                        print("⚠️ 空文本输入，忽略")

                # 2. 配置更新：允许更新视觉配置、文本提示及生成参数
                elif "configUpdate" in data:
                    update_data = data["configUpdate"]
                    config.vision_enabled = update_data.get("vision_enabled", config.vision_enabled)
                    config.blink_frequency = update_data.get("blink_frequency", config.blink_frequency)
                    config.vision_input_source = update_data.get("vision_input_source", config.vision_input_source)
                    if "text_prompt" in update_data:
                        config.text_prompt = update_data["text_prompt"]
                    if "model_config" in update_data:
                        # 允许部分更新参数，确保是字典类型
                        config.model_config.update(update_data["model_config"])
                    print(f"🛠️ 配置更新: vision_enabled={config.vision_enabled}, "
                          f"blink_frequency={config.blink_frequency}, "
                          f"vision_input_source={config.vision_input_source}, "
                          f"text_prompt={config.text_prompt}, model_config={config.model_config}")

                # 3. 处理 Vision 图像数据：调用 Vision 模块生成图像描述
                elif "image_data" in data:
                    image_data = data["image_data"]
                    vision_response = vision_module.process_image(image_data)
                    await websocket.send_text(json.dumps(vision_response))

                else:
                    print(f"❓ 收到未知消息: {data}")

            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")

    except Exception as e:
        print(f"❌ 连接异常关闭: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
