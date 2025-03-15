import asyncio
import websockets
import requests
import json
import time
import os
import firebase_admin
from firebase_admin import credentials, storage
from dotenv import load_dotenv

# 1️⃣ 加载 .env 配置
load_dotenv()
API_KEY = os.getenv("TRIPOD3D_API_KEY")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
FIREBASE_BUCKET_NAME = os.getenv("FIREBASE_BUCKET_NAME")

# 2️⃣ 初始化 Firebase
cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_BUCKET_NAME})
bucket = storage.bucket()

# 3️⃣ 发送 Tripod3D 生成 3D 模型的请求
def request_tripod3d(prompt):
    API_URL = "https://api.tripo3d.ai/v2/openapi/task"
    HEADERS = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    PAYLOAD = {
        "type": "text_to_model",
        "prompt": prompt,
        "model_version": "v1.4-20240625",
        "negative_prompt": "bad topology, low resolution",
        "image_seed": 42
    }

    response = requests.post(API_URL, headers=HEADERS, json=PAYLOAD)
    if response.status_code == 200:
        task_info = response.json()
        task_id = task_info.get("data", {}).get("task_id")
        print(f"✅ 任务已提交，task_id: {task_id}")
        return task_id
    else:
        print(f"❌ 任务提交失败，状态码: {response.status_code}, 响应: {response.text}")
        return None

# 4️⃣ 轮询任务状态，等待 3D 模型生成
def check_task_status(task_id):
    status_url = f"https://api.tripo3d.ai/v2/openapi/task/{task_id}"
    HEADERS = {"Authorization": f"Bearer {API_KEY}"}
    start_time = time.time()

    while True:
        response = requests.get(status_url, headers=HEADERS)
        elapsed_time = time.time() - start_time

        if response.status_code == 200:
            task_status = response.json()
            status = task_status.get("data", {}).get("status")
            print(f"⏳ 任务状态：{status} | 已等待 {elapsed_time:.2f} 秒")

            if status == "success":
                print(f"🎉 任务已成功完成！总耗时 {elapsed_time:.2f} 秒")
                return task_status
            elif status in ["failed", "cancelled", "unknown"]:
                print("❌ 任务失败或取消。")
                return None
            else:
                time.sleep(10)
        else:
            print(f"❌ 无法获取任务状态，状态码: {response.status_code}, 响应: {response.text}")
            return None

# 5️⃣ 下载 3D 模型文件
def download_file(url, filename):
    print(f"📥 正在下载 {filename} ...")
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, "wb") as file:
            file.write(response.content)
        print(f"✅ {filename} 下载完成！")
        return filename
    else:
        print(f"❌ {filename} 下载失败，状态码: {response.status_code}")
        return None

# 6️⃣ 上传文件到 Firebase
def upload_to_firebase(local_file, remote_filename):
    blob = bucket.blob(remote_filename)
    blob.upload_from_filename(local_file)
    blob.make_public()
    public_url = blob.public_url
    
    print(f"🚀 文件已上传至 Firebase: {public_url}")
    return public_url

# 7️⃣ 生成 3D 模型（等 Unity 连接后触发）
def generate_3d_model(prompt="Crocodile Eye Drops"):
    task_id = request_tripod3d(prompt)
    if not task_id:
        return None

    task_status_info = check_task_status(task_id)
    if not task_status_info:
        return None

    result_data = task_status_info.get("data", {}).get("output", {})
    model_glb = result_data.get("model")

    if model_glb:
        os.makedirs("3D_Models", exist_ok=True)
        local_glb = download_file(model_glb, "3D_Models/generated_model.glb")
        if local_glb:
            firebase_url = upload_to_firebase(local_glb, "models/generated_model.glb")
            print(f"🎉 3D 模型已生成并上传: {firebase_url}")
            return firebase_url
    return None

# 8️⃣ 处理客户端消息
async def handle_client_message(websocket, message):
    try:
        # 尝试解析 JSON
        data = json.loads(message)
        
        # 检查是否是文本输入
        if "realtimeInput" in data and "text" in data["realtimeInput"]:
            input_text = data["realtimeInput"]["text"]
            print(f"📝 收到文本输入: {input_text}")
            
            # 如果输入包含生成3D模型的请求
            if ("generate" in input_text.lower() and "model" in input_text.lower()) or "3d" in input_text.lower():
                print("🔥 开始生成 3D 模型...")
                
                # 提取提示词
                prompt = input_text.lower()
                prompt = prompt.replace("generate model", "").replace("generate 3d model", "").strip()
                if not prompt:
                    prompt = "Crocodile Eye Drops"  # 默认提示词
                
                # 先发送处理中的消息
                await websocket.send(json.dumps({
                    "type": "chat",
                    "response_text": f"正在生成3D模型: {prompt}，请稍候..."
                }))
                
                # 生成模型
                firebase_url = generate_3d_model(prompt)
                
                if firebase_url:
                    # 发送模型URL
                    model_response = {
                        "type": "model",
                        "model_url": firebase_url,
                        "prompt": prompt
                    }
                    print(f"✅ 向 Unity 发送模型 URL: {firebase_url}")
                    await websocket.send(json.dumps(model_response))
                    
                    # 发送成功消息
                    success_message = {
                        "type": "chat",
                        "response_text": f"3D模型生成成功！已加载模型: {prompt}"
                    }
                    await websocket.send(json.dumps(success_message))
                else:
                    # 发送失败消息
                    error_message = {
                        "type": "chat",
                        "response_text": "很抱歉，3D模型生成失败。请稍后再试。"
                    }
                    await websocket.send(json.dumps(error_message))
            else:
                # 处理普通聊天消息
                normal_response = {
                    "type": "chat",
                    "response_text": f"您说: {input_text}。如果您想生成3D模型，请说'generate model [物品名称]'"
                }
                await websocket.send(json.dumps(normal_response))
        else:
            # 处理其他类型的消息
            await websocket.send(json.dumps({
                "type": "chat",
                "response_text": "收到您的消息。如果您想生成3D模型，请使用文本输入'generate model [物品名称]'"
            }))
    except json.JSONDecodeError:
        # 如果不是JSON格式，检查是否是特定命令
        if message == "request_model" or message == "generate_model":
            print("🔥 开始生成默认3D模型...")
            firebase_url = generate_3d_model()
            
            if firebase_url:
                model_response = {
                    "type": "model",
                    "model_url": firebase_url
                }
                print(f"✅ 向 Unity 发送模型 URL: {firebase_url}")
                await websocket.send(json.dumps(model_response))
            else:
                await websocket.send(json.dumps({
                    "type": "chat",
                    "response_text": "很抱歉，3D模型生成失败。请稍后再试。"
                }))
        else:
            # 处理其他纯文本消息
            await websocket.send(json.dumps({
                "type": "chat",
                "response_text": f"收到您的消息: {message}。如果您想生成3D模型，请使用JSON格式发送请求。"
            }))

# 9️⃣ WebSocket 连接处理
async def handle_connection(websocket, path):
    # 检查路径是否是 /ws
    if path != "/ws":
        print(f"❌ 客户端尝试连接到错误的路径: {path}")
        await websocket.close(1008, "路径不正确，请使用 /ws")
        return
    
    print(f"🔗 客户端连接成功！路径: {path}")
    
    try:
        # 监听客户端消息
        async for message in websocket:
            print(f"📩 收到消息: {message}")
            await handle_client_message(websocket, message)
            
    except websockets.exceptions.ConnectionClosed:
        print("❌ 客户端连接已关闭")
    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")

# 🔟 主程序
async def main():
    # 使用端口8000，不指定path参数，在handler中处理路径
    server = await websockets.serve(handle_connection, "localhost", 8000)
    print("🚀 WebSocket 服务器已启动，监听 ws://localhost:8000/ws")
    
    # 让服务器持续运行
    await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 服务器已通过键盘中断停止")