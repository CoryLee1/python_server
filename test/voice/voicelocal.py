import requests
import os
from datetime import datetime
from pedalboard import Pedalboard, Reverb
from pedalboard.io import AudioFile
import numpy as np

def synthesize_speech(text, api_url="http://127.0.0.1:9880/tts"):
    payload = {
        "text": text,
        "text_lang": "en",  # 'zh', 'en', 'ja'
        "ref_audio_path": r"E:\BaiduNetdiskDownload\aa\纳西妲\9.早上好…_早上好，我们赶快出发吧，这世上有太多的东西都是「过时不候」的呢。.mp3",  # 可以留空，或者填你的参考音频路径
        "aux_ref_audio_paths": [],
        "prompt_lang": "zh",
        "prompt_text": "早上好…_早上好，我们赶快出发吧，这世上有太多的东西都是「过时不候」的呢。",
        "top_k": 4,
        "top_p": 1,
        "temperature": 0.9,
        "text_split_method": "cut5",
        "batch_size": 1,
        "batch_threshold": 0.6,
        "split_bucket": True,
        "speed_factor": 1,
        "fragment_interval": 0.1,
        "seed": -1,
        "media_type": "wav",  # 可以选 "wav" 或 "mp3"
        "streaming_mode": True,
        "parallel_infer": True,
        "repetition_penalty": 1.5
    }

    response = requests.post(api_url, json=payload)

    if response.status_code == 200:
        # 创建 outputs 文件夹
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)

        # 生成时间戳文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"output_{timestamp}.wav")

        with open(output_path, "wb") as f:
            f.write(response.content)

        print(f"语音合成成功，已保存为 {output_path}")
    else:
        print(f"语音合成失败，错误信息：{response.text}")


synthesize_speech("That said, I firmly reject the **narrative of AI as merely a tool for cost-cutting and efficiency gains**, as well as the fear-mongering around it. These are often tactics used by the market to capture attention and manufacture anxiety. As creators, we should **redirect the conversation towards where attention should be placed**—exploring new ways to **co-create with AI** rather than being caught up in artificially induced fears or oversimplified narratives.At the same time, I think **decentralized, lightweight generative models** are a direction worth looking forward to. Giving creators the ability to **customize and have partial ownership over their AI agents** presents an exciting vision for the future—one where AI becomes an extension of individual artistic intent rather than a monolithic, corporate-controlled tool.")
