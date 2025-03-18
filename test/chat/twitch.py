import websocket
import threading

# Twitch 直播间信息
TWITCH_CHANNEL = "anngeliving"
OAUTH_TOKEN = "oauth:3qo5af6kq7rwr4uj6xmhpgxpo7sjdy"  # 你的OAuth Token
NICKNAME = "anngeliving"

# Twitch WebSocket 服务器地址
TWITCH_IRC_URL = "wss://irc-ws.chat.twitch.tv:443"

def on_message(ws, message):
    """处理收到的消息"""
    if "PRIVMSG" in message:
        parts = message.split(":", 2)
        if len(parts) > 2:
            user = parts[1].split("!")[0]
            msg = parts[2]
            print(f"{user}: {msg}")

def on_open(ws):
    """连接成功时的回调"""
    print("✅ 连接到 Twitch 服务器成功！")
    
    # 发送身份认证
    ws.send(f"PASS {OAUTH_TOKEN}")
    ws.send(f"NICK {NICKNAME}")
    
    # 监听直播间弹幕
    ws.send(f"JOIN #{TWITCH_CHANNEL}")
    print(f"🎥 监听中: {TWITCH_CHANNEL} 的弹幕")

def on_close(ws, close_status_code, close_msg):
    """连接关闭时的回调"""
    print("❌ 连接已关闭，正在尝试重连...")
    start_ws()

def start_ws():
    """启动 WebSocket 连接"""
    ws = websocket.WebSocketApp(TWITCH_IRC_URL,
                                on_message=on_message,
                                on_open=on_open,
                                on_close=on_close)
    ws.run_forever()

if __name__ == "__main__":
    print("🚀 启动 Twitch Chat 监听器...")
    threading.Thread(target=start_ws).start()
