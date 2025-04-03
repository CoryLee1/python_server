import os
from datetime import datetime

import langdetect
from cartesia import Cartesia, OutputFormat_Wav
from dotenv import load_dotenv
import uuid

load_dotenv()

voice_ids = {
    "en": "6fc79973-fdc6-4e35-b6cd-4ed7f0d3f07f",
    "zh-cn": "da14a540-4a31-4611-a40a-38b8ae3a296a",
    "jp": "1f6f6bc0-98e4-4547-84ad-59db0bde0f3c",
}

# 语音合成函数，返回生成的文件路径
def synthesize_speech(
    text: str,
    api_key: str = os.getenv("CARTESIA_API_KEY"),
    return_url=True,
    server_base_url=None,
):
    # 生成唯一的文件名
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"output_{timestamp}_{unique_id}.wav"
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)

    wav_path = os.path.join(output_dir, filename)

    lang = langdetect.detect(text)
    if lang not in voice_ids:
        lang = "en"

    voice_id = voice_ids[lang]

    client = Cartesia(api_key=api_key)

    audio_chunks = client.tts.bytes(
        model_id="sonic-2",
        transcript=text,
        voice={"id": voice_id},
        language="en",
        output_format=OutputFormat_Wav(
            sample_rate=44100,
            encoding="pcm_s16le",
        )
    )

    with open(wav_path, "wb") as f:
        f.write(b''.join(audio_chunks))

    if return_url:
        if server_base_url is None:
            server_base_url = os.getenv(
                "SERVER_BASE_URL", "https://server.echuu.cktop.cc"
            )
        audio_url = f"{server_base_url}/audio/{filename}"
        return audio_url
    else:
        return wav_path
