import requests
import os
from datetime import datetime
from pedalboard import Pedalboard, Reverb
from pedalboard.io import AudioFile
import numpy as np

TTS_API_URL = "http://127.0.0.1:9880/tts"

# 语音合成函数，返回生成的文件路径
def synthesize_speech(text, media_type="wav"):
    payload = {
        "text": text,
        "text_lang": "en",
        "ref_audio_path": r"E:\BaiduNetdiskDownload\aa\纳西妲\9.早上好…_早上好，我们赶快出发吧，这世上有太多的东西都是「过时不候」的呢。.mp3",
        "aux_ref_audio_paths": [],
        "prompt_lang": "zh",
        "prompt_text": "早上好…_早上好，我们赶快出发吧，这世上有太多的东西都是「过时不候」的呢。",
        "top_k": 5,
        "top_p": 1,
        "temperature": 0.9,
        "text_split_method": "cut5",
        "batch_size": 1,
        "batch_threshold": 0.75,
        "split_bucket": True,
        "speed_factor": 1,
        "fragment_interval": 0.3,
        "seed": -1,
        "media_type": media_type,
        "streaming_mode": False,
        "parallel_infer": True,
        "repetition_penalty": 1.35
    }

    response = requests.post(TTS_API_URL, json=payload)
    if response.status_code == 200:
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"output_{timestamp}.{media_type}")

        with open(output_path, "wb") as f:
            f.write(response.content)

        return output_path
    else:
        raise RuntimeError(f"TTS生成失败：{response.text}")


# 添加回声或混响效果的函数，返回处理后的音频路径
def add_echo_effect(input_path):
    output_path = input_path.replace(".wav", "_echo.wav")

    with AudioFile(input_path) as f:
        audio = f.read(f.frames)
        samplerate = f.samplerate

    # 添加回声/混响效果
    board = Pedalboard([Reverb(room_size=0.7)])

    effected = board(audio, samplerate)

    # 写入处理后的音频
    with AudioFile(output_path, 'w', samplerate, effected.shape[0]) as f:
        f.write(effected)

    return output_path