import googleapiclient.discovery
import time
from dotenv import load_dotenv

# 加载 .env 配置
load_dotenv()

# 从 .env 获取配置
API_KEY = os.getenv("YOUTUBE_API_KEY")
VIDEO_ID = os.getenv("YOUTUBE_VIDEO_ID")

def get_live_chat_id(youtube, video_id):
    """获取直播聊天室 ID"""
    request = youtube.videos().list(
        part="liveStreamingDetails",
        id=video_id
    )
    response = request.execute()

    if "items" in response and response["items"]:
        return response["items"][0]["liveStreamingDetails"].get("activeLiveChatId")
    return None

def get_chat_messages(youtube, live_chat_id):
    """获取直播间弹幕，并避免重复"""
    next_page_token = None
    while True:
        request = youtube.liveChatMessages().list(
            liveChatId=live_chat_id,
            part="snippet,authorDetails",
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response.get("items", []):
            author = item["authorDetails"]["displayName"]
            message = item["snippet"]["displayMessage"]
            print(f"{author}: {message}")

        # 获取新的 `nextPageToken` 以避免重复
        next_page_token = response.get("nextPageToken")

        # 根据 API 返回的 `pollingIntervalMillis` 进行延迟（最小值 1 秒）
        delay = response.get("pollingIntervalMillis", 2000) / 1000
        time.sleep(max(delay, 1))

if __name__ == "__main__":
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)
    
    live_chat_id = get_live_chat_id(youtube, VIDEO_ID)
    if live_chat_id:
        print(f"✅ 获取到直播聊天室 ID: {live_chat_id}")
        print("🎥 监听中...")
        get_chat_messages(youtube, live_chat_id)
    else:
        print("❌ 未找到该视频的直播聊天室")
