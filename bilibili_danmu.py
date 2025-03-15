from bilipy import LiveClient

# 你的直播间 ID
ROOM_ID = 21678527

def on_danmu(msg):
    print(f"[{msg['user']['name']}] 说: {msg['content']}")

def on_gift(msg):
    print(f"[{msg['user']['name']}] 送出了 {msg['gift']['name']} x {msg['gift']['num']}")

client = LiveClient(ROOM_ID)

# 监听弹幕
client.on("DANMU_MSG", on_danmu)
client.on("SEND_GIFT", on_gift)

# 启动监听
client.start()
