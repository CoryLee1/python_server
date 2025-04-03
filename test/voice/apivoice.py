import os
from dotenv import load_dotenv
from cartesia import Cartesia
from cartesia.tts import OutputFormat_Mp3

# 加载 .env 中的 API Key
load_dotenv()
client = Cartesia(api_key=os.getenv("CARTESIA_API_KEY"))

# 参数设置
voice_id = "1cbe671e-6373-4686-ac79-424fd4db23d5"
text = "Hello,hello,Field required, I am so dumb."
output_path = r"E:\aiann\anndemo1unity\demo1\python_server\test\voice\outputs\output.mp3"

# 使用 join() 组合生成器中的 chunk
audio_chunks = client.tts.bytes(
    model_id="sonic-2",
    transcript=text,
    voice={"id": voice_id},
    language="en",
    output_format=OutputFormat_Mp3( 
        sample_rate=44100,
        bit_rate=128000
    )
)

# 拼接为完整 mp3 文件并保存
with open(output_path, "wb") as f:
    f.write(b''.join(audio_chunks))

print(f"✅ 成功合成语音：{output_path}")
