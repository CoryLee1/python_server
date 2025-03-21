import os
import json
import struct
import websocket
import threading
import time
import zlib
from dotenv import load_dotenv

# 加载 .env 配置
load_dotenv()
ROOM_ID = int(os.getenv("BILIBILI_ROOM_ID", "21678527"))  # 直播间 ID
BILIBILI_WS_URL = "wss://broadcastlv.chat.bilibili.com:2245/sub"

def encode_packet(op, body):
    """封装 WebSocket 数据包"""
    body = json.dumps(body).encode("utf-8") if isinstance(body, dict) else body
    header = struct.pack(">IHHII", 16 + len(body), 16, 1, op, 1)
    return header + body

def send_heartbeat(ws):
    """定期发送心跳包，防止连接超时"""
    while True:
        try:
            ws.send(encode_packet(2, b""))  # 发送心跳包
            time.sleep(30)  # 30 秒发送一次
        except Exception as e:
            print("❌ 发送心跳失败:", e)
            break

def decode_packet(data):
    """解压缩 WebSocket 数据（Bilibili 服务器返回的是 zlib 压缩数据）"""
    try:
        decompressed_data = zlib.decompress(data)
        return json.loads(decompressed_data[16:].decode("utf-8"))
    except:
        return None

def on_message(ws, message):
    """解析 WebSocket 服务器返回的消息"""
    try:
        data = decode_packet(message)
        if not data:
            return

        for item in data.get("body", []):
            cmd = item.get("cmd", "")

            # 监听弹幕
            if cmd == "DANMU_MSG":
                username = item["info"][2][1]
                content = item["info"][1]
                print(f"💬 {username}: {content}")

            # 监听礼物
            elif cmd == "SEND_GIFT":
                gift_name = item["data"]["giftName"]
                gift_count = item["data"]["num"]
                username = item["data"]["uname"]
                print(f"🎁 {username} 送出 {gift_count} 个 {gift_name}")

            # 监听点赞
            elif cmd == "LIKE_INFO_V3_CLICK":
                username = item["data"]["uname"]
                print(f"👍 {username} 点了个赞")

    except Exception as e:
        print("❌ 解析 WebSocket 数据出错:", e)

def on_open(ws):
    """WebSocket 连接建立时，发送认证包"""
    print(f"✅ 连接到 Bilibili 直播间 {ROOM_ID}")

    # 发送认证包（使用 protover: 3，支持 JSON 压缩格式）
    auth_data = {
        "uid": 0,
        "roomid": ROOM_ID,
        "protover": 3,
        "platform": "web",
        "type": 2,
    }
    ws.send(encode_packet(7, auth_data))

    # 启动心跳线程
    threading.Thread(target=send_heartbeat, args=(ws,), daemon=True).start()

def on_close(ws, close_status_code, close_msg):
    """WebSocket 连接关闭时"""
    print("❌ 连接已断开，尝试重连...")
    start_ws()

def start_ws():
    """启动 WebSocket 连接"""
    ws = websocket.WebSocketApp(
        BILIBILI_WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_close=on_close
    )
    ws.run_forever()

if __name__ == "__main__":
    print("🚀 启动 Bilibili 直播监听...")
    threading.Thread(target=start_ws).start()
