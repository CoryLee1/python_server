import requests
import os
from datetime import datetime
from pedalboard import Pedalboard, Reverb
from pedalboard.io import AudioFile
import numpy as np
import uuid
from pydub import AudioSegment  # 添加pydub库用于格式转换


# 语音合成函数，返回生成的文件路径
def synthesize_speech(text, api_url="https://9pxgcoxlb9fk3n-9880.proxy.runpod.net/tts", return_url=True, server_base_url=None):
    """语音合成函数，可返回文件路径或URL"""
    # 请求TTS API时使用wav格式
    media_type = "wav"
    payload = {
        "text": text,
        "text_lang": "en",  # 'zh', 'en', 'ja'
        "ref_audio_path":  "/workspace/ref_audio.mp3",
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
        "media_type": media_type,  # 请求时使用wav格式
        "streaming_mode": True,
        "parallel_infer": True,
        "repetition_penalty": 1.5
    }

    response = requests.post(api_url, json=payload)
    if response.status_code == 200:
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)

        # 生成唯一的文件名
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        wav_filename = f"output_{timestamp}_{unique_id}.wav"
        wav_path = os.path.join(output_dir, wav_filename)
        
        with open(wav_path, "wb") as f:
            f.write(response.content)

        print(f"✅ 生成 WAV 文件: {wav_path}")

        # 返回 URL 或本地路径
        if return_url:
            if server_base_url is None:
                server_base_url = "http://localhost:8000"
            audio_url = f"{server_base_url}/audio/{wav_filename}"
            return audio_url
        else:
            return wav_path
    else:
        raise RuntimeError(f"TTS 生成失败：{response.text}")

# 添加回声或混响效果的函数，返回处理后的音频路径
def add_echo_effect(input_path):
    output_path = input_path.replace(".wav", "_echo.wav")
    
    # 分段读取并处理音频
    with AudioFile(input_path) as input_file:
        # 获取音频属性
        samplerate = input_file.samplerate
        num_channels = input_file.num_channels
        
        # 创建混响效果板
        board = Pedalboard([Reverb(room_size=0.7)])
        
        # 准备输出文件
        with AudioFile(output_path, 'w', samplerate, num_channels) as output_file:
            # 读取音频数据 - 每次处理1024帧
            chunk_size = 1024
            
            # 循环读取并处理音频块
            while input_file.tell() < input_file.frames:
                # 读取一个块
                chunk = input_file.read(chunk_size)
                
                # 应用效果
                effected_chunk = board(chunk, samplerate)
                
                # 写入处理后的块
                output_file.write(effected_chunk)
    
    return output_path