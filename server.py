from fastapi import FastAPI, WebSocket
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# ✅ 读取 API Key
load_dotenv()
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GENAI_API_KEY:
    raise ValueError("🚨 ERROR: 未找到 GEMINI_API_KEY，请在 .env 文件中设置")

# ✅ 初始化 Gemini Standard API
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel("gemini-pro")
# ✅ 设置默认模型参数 & Prompt
DEFAULT_MODEL_CONFIG = {
    "temperature": 0.7,
    "max_output_tokens": 512,
    "top_p": 0.9,
    "top_k": 40
}
DEFAULT_SYSTEM_PROMPT = "你是一个 AI VTuber，与你的观众互动，并提供有趣的回答。"

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ Unity 连接成功！")

    try:
        while True:
            raw_data = await websocket.receive_text()
            print(f"📩 收到 Unity 消息: {raw_data}")

            # ✅ 确保 Unity 发送的是 JSON 并解析
            try:
                data = json.loads(raw_data)
                user_input = data.get("realtimeInput", {}).get("text", "").strip()
                if not user_input:
                    print("⚠️ 错误: Unity 发送的 JSON 没有 'realtimeInput.text'")
                    continue
            except json.JSONDecodeError:
                print("❌ 错误: Unity 发送的不是有效的 JSON")
                continue

            # ✅ 直接调用 Gemini Standard API
            response = model.generate_content(user_input)
            text_response = response.text.strip() if response.text else "⚠️ AI 没有返回文本"

            print(f"🤖 Gemini 回复: {text_response}")
            await websocket.send_text(json.dumps({"response": text_response}))

    except Exception as e:
        print(f"❌ 连接关闭: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
